"""OCR 异步任务 — 批量处理 + 进度更新 + ES 增量索引"""

import time
from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal, get_es
from app.models.models import Archive, OcrTask
from app.services.ocr_client import ocr_client

logger = get_task_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_ocr_task(self, task_id: int):
    """批量 OCR 识别任务"""
    db = SessionLocal()
    try:
        task = db.query(OcrTask).filter(OcrTask.id == task_id).first()
        if not task:
            return {"error": "task_not_found"}

        criteria = task.filter_criteria or {}

        # 查询待处理档案
        q = db.query(Archive).filter(Archive.ocr_status.in_(["pending", "failed"]))
        if criteria.get("year_from"):
            q = q.filter(Archive.year >= criteria["year_from"])
        if criteria.get("year_to"):
            q = q.filter(Archive.year <= criteria["year_to"])
        if criteria.get("category"):
            q = q.filter(Archive.category == criteria["category"])

        archives = q.all()
        total = len(archives)

        task.status = "running"
        task.total_pages = total
        task.processed_pages = 0
        db.commit()

        for i, archive in enumerate(archives):
            try:
                img_path = _find_image(archive.archive_id)
                if not img_path:
                    archive.ocr_status = "failed"
                    db.commit()
                    continue

                result = ocr_client.recognize(img_path)

                archive.ocr_text = result.get("text", "")
                archive.ocr_confidence = result.get("confidence", 0)
                archive.ocr_status = "done" if result.get("confidence", 0) >= 0.7 else "low_quality"
                task.processed_pages = i + 1
                db.commit()

                # 增量更新 ES 索引
                _update_es_index(archive)

            except Exception as e:
                logger.error(f"OCR failed for {archive.archive_id}: {e}")
                archive.ocr_status = "failed"
                task.processed_pages = i + 1
                db.commit()

        task.status = "completed"
        db.commit()

    except Exception as exc:
        task = db.query(OcrTask).filter(OcrTask.id == task_id).first()
        if task:
            task.status = "failed"
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()

    return {"task_id": task_id, "processed": task.processed_pages}


@celery_app.task(bind=True, max_retries=2)
def process_single_ocr(self, archive_id: str, image_path: str):
    """单条 OCR 处理"""
    db = SessionLocal()
    try:
        result = ocr_client.recognize(image_path)
        archive = db.query(Archive).filter(Archive.archive_id == archive_id).first()
        if archive:
            archive.ocr_text = result.get("text", "")
            archive.ocr_confidence = result.get("confidence", 0)
            archive.ocr_status = "done"
            db.commit()
            _update_es_index(archive)
        return result
    finally:
        db.close()


def _find_image(archive_id: str) -> str | None:
    """根据档案编号查找图像路径"""
    from app.core.config import settings
    import os

    sync_dir = settings.SYNC_DATA_DIR
    # 按 "年度-门类-案卷号" 结构检索
    parts = archive_id.split("-")
    for year_dir in [parts[0]] if parts else []:
        year_path = os.path.join(sync_dir, year_dir)
        if not os.path.isdir(year_path):
            continue
        for root, _, files in os.walk(year_path):
            for f in files:
                if archive_id in f and f.lower().endswith((".tiff", ".tif", ".jpg", ".jpeg", ".png", ".pdf")):
                    return os.path.join(root, f)
    return None


def _update_es_index(archive: Archive):
    """增量更新 ES 全文索引"""
    es = get_es()
    if es is None:
        return
    from app.core.config import settings

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
    except Exception:
        pass
