"""OCR 异步任务 — 批量处理 + 进度更新 + ES 增量索引

真实模式 (OCR_MODE=real):
  - 调用 PaddleOCR PP-OCRv5 + PP-StructureV2
  - GPU 自动加速，CPU 降级
  - 多页 TIFF/PDF 自动分离
  - 每页粒度进度更新

Mock 模式 (OCR_MODE=mock):
  - 确定性哈希模拟结果（同一输入始终一致）
"""

import logging
import os
import time

from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal, get_es
from app.models.models import Archive, OcrTask
from app.services.ocr_client import ocr_client
from app.services.ocr_processor import ocr_processor, PageSplitter

logger = get_task_logger(__name__)


# ============================================================
# 批量 OCR 任务
# ============================================================

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_ocr_task(self, task_id: int):
    """
    批量 OCR 识别任务 — 自动处理多页文件 + GPU/CPU 自适应

    流程:
      1. 查任务 + 筛选条件
      2. 遍历待处理档案
      3. 查找图像文件
      4. 多页分离 (TIFF → PNG pages)
      5. 逐页 OCR (PaddleOCR 或 mock)
      6. 合并文本 → 写入 Archive.ocr_text
      7. ES 增量索引更新
      8. 进度更新 (页级粒度)
    """
    db = SessionLocal()
    task = None
    try:
        task = db.query(OcrTask).filter(OcrTask.id == task_id).first()
        if not task:
            return {"error": "task_not_found", "task_id": task_id}

        criteria = task.filter_criteria or {}

        # 查询待处理档案
        q = db.query(Archive).filter(Archive.ocr_status.in_(["pending", "failed"]))
        if criteria.get("year_from"):
            q = q.filter(Archive.year >= criteria["year_from"])
        if criteria.get("year_to"):
            q = q.filter(Archive.year <= criteria["year_to"])
        if criteria.get("category"):
            q = q.filter(Archive.category == criteria["category"])
        if criteria.get("department"):
            q = q.filter(Archive.department == criteria["department"])

        archives = q.limit(500).all()  # 单次最多 500 条，分批
        total_archives = len(archives)

        # 估算总页数
        estimated_pages = sum(max(a.file_count or 1, 1) for a in archives)

        task.status = "running"
        task.total_pages = estimated_pages
        task.processed_pages = 0
        db.commit()

        logger.info(
            f"OCR 任务 #{task_id} 启动: {total_archives} 件档案, "
            f"预估 {estimated_pages} 页, 引擎={settings.OCR_MODE}"
        )

        processed_count = 0
        failed_count = 0

        for archive in archives:
            try:
                # 查找图像文件
                image_paths = _find_images(archive.archive_id)

                if not image_paths:
                    archive.ocr_status = "failed"
                    archive.ocr_text = "[无图像文件]"
                    db.commit()
                    failed_count += 1
                    continue

                # 多页分离
                all_pages: list[str] = []
                for img_path in image_paths:
                    ext = os.path.splitext(img_path)[1].lower()
                    if ext in (".tiff", ".tif"):
                        # TIFF 多页 → 临时 PNG 文件
                        pages = PageSplitter.split(img_path)
                        import tempfile
                        for page_bytes in pages:
                            fd, tmp_path = tempfile.mkstemp(suffix=".png")
                            with os.fdopen(fd, "wb") as f:
                                f.write(page_bytes)
                            all_pages.append(tmp_path)
                    else:
                        all_pages.append(img_path)

                if not all_pages:
                    archive.ocr_status = "failed"
                    archive.ocr_text = "[无法解析图像]"
                    db.commit()
                    failed_count += 1
                    continue

                # 使用 OcrProcessor 处理
                result = ocr_processor.process_archive(
                    archive_id=archive.archive_id,
                    image_paths=all_pages,
                    metadata={
                        "title": archive.title,
                        "year": archive.year,
                        "department": archive.department,
                    },
                )

                # 写入 Archive
                archive.ocr_text = result["ocr_text"]
                archive.ocr_confidence = result["overall_confidence"]
                archive.file_count = max(archive.file_count or 0, result["total_pages"])
                archive.ocr_status = "done" if result["overall_confidence"] >= 0.7 else "low_quality"
                archive.ocr_engine = result.get("engine", "paddleocr")
                archive.ocr_model_version = "PP-OCRv5" if result.get("engine") == "paddleocr" else "mock-v1"
                archive.ocr_duration_ms = result.get("total_time_ms", 0)

                # 页级进度
                task.processed_pages += result["total_pages"]
                db.commit()

                # 清理临时文件
                for tmp_path in all_pages:
                    if tmp_path.startswith(tempfile.gettempdir()):
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

                # 增量更新 ES 索引
                _update_es_index(archive)

                processed_count += 1

                if processed_count % 10 == 0:
                    logger.info(
                        f"OCR 任务 #{task_id}: {processed_count}/{total_archives} 件完成 "
                        f"({task.processed_pages} 页)"
                    )

            except Exception as e:
                logger.error(f"OCR 失败: {archive.archive_id} — {e}")
                archive.ocr_status = "failed"
                archive.ocr_text = f"[OCR 失败: {str(e)[:100]}]"
                task.failed_pages = (task.failed_pages or 0) + 1
                db.commit()
                failed_count += 1

        task.status = "completed"
        db.commit()

        logger.info(
            f"OCR 任务 #{task_id} 完成: {processed_count} 成功, "
            f"{failed_count} 失败, {task.processed_pages} 页"
        )

        return {
            "task_id": task_id,
            "processed": processed_count,
            "failed": failed_count,
            "pages": task.processed_pages,
        }

    except Exception as exc:
        if task:
            task.status = "failed"
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


# ============================================================
# 单条 OCR
# ============================================================

@celery_app.task(bind=True, max_retries=2)
def process_single_ocr(self, archive_id: str, image_path: str):
    """单条 OCR 处理 — 用于实时请求"""
    db = SessionLocal()
    try:
        archive = db.query(Archive).filter(Archive.archive_id == archive_id).first()

        # 分离多页
        ext = os.path.splitext(image_path)[1].lower()
        if ext in (".tiff", ".tif"):
            pages = PageSplitter.split(image_path)
            import tempfile
            page_paths = []
            for page_bytes in pages:
                fd, tmp_path = tempfile.mkstemp(suffix=".png")
                with os.fdopen(fd, "wb") as f:
                    f.write(page_bytes)
                page_paths.append(tmp_path)
            result = ocr_processor.process_archive(archive_id, page_paths)
            # 清理
            for p in page_paths:
                try: os.unlink(p)
                except OSError: pass
        else:
            result = ocr_processor.process_archive(archive_id, [image_path])

        if archive:
            archive.ocr_text = result["ocr_text"]
            archive.ocr_confidence = result["overall_confidence"]
            archive.ocr_status = "done" if result["overall_confidence"] >= 0.7 else "low_quality"
            archive.file_count = max(archive.file_count or 0, result["total_pages"])
            db.commit()
            _update_es_index(archive)

        return result
    finally:
        db.close()


# ============================================================
# 辅助函数
# ============================================================

def _find_images(archive_id: str) -> list[str]:
    """根据档案编号查找所有图像文件路径"""
    sync_dir = getattr(settings, "SYNC_DATA_DIR", os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "sync_data"
    ))

    if not os.path.isdir(sync_dir):
        return []

    parts = archive_id.split("-")
    found = []

    # 策略 1: 年度目录下按编号搜索
    for year_dir in parts[:1] if parts else []:
        year_path = os.path.join(sync_dir, year_dir)
        if not os.path.isdir(year_path):
            continue
        for root, _, files in os.walk(year_path):
            for f in files:
                if archive_id in f and f.lower().endswith(
                    (".tiff", ".tif", ".jpg", ".jpeg", ".png", ".pdf")
                ):
                    found.append(os.path.join(root, f))

    if found:
        return sorted(found)

    # 策略 2: 全目录搜索（回退）
    for root, _, files in os.walk(sync_dir):
        for f in files:
            if archive_id in f and f.lower().endswith(
                (".tiff", ".tif", ".jpg", ".jpeg", ".png", ".pdf")
            ):
                found.append(os.path.join(root, f))
        if found:
            break

    return sorted(found)


def _update_es_index(archive: Archive):
    """增量更新 ES 全文索引"""
    es = get_es()
    if es is None:
        return

    doc = {
        "archive_id": archive.archive_id,
        "title": archive.title,
        "author": archive.author or "",
        "file_code": archive.file_code or "",
        "subject": archive.subject or "",
        "full_text": archive.ocr_text or "",
        "year": archive.year,
        "category": archive.category,
        "department": archive.department,
        "fonds_id": archive.fonds_id,
        "retention_period": archive.retention_period,
        "security_level": archive.security_level,
        "level": archive.level or "file",
        "open_status": archive.open_status or "未审核",
        "ocr_confidence": archive.ocr_confidence,
        "ocr_text_quality": archive.ocr_status,
        "file_count": archive.file_count,
    }
    try:
        index = f"{settings.ES_INDEX_PREFIX}_fulltext"
        es.index(index=index, id=archive.archive_id, body=doc, refresh="wait_for")
    except Exception as e:
        logger.warning(f"ES 索引更新失败: {archive.archive_id} — {e}")
