"""AI 预审核异步任务 — 批量处理 + 结果入库"""

import time
from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.models import Archive, ReviewTask, ReviewRecord
from app.services.review_service import hybrid_review

logger = get_task_logger(__name__)


def _sync_open_status(db, archive_id: str, suggestion: str):
    """根据 AI 建议同步 Archive.open_status（与单件预审 preview 行为一致）"""
    a = db.query(Archive).filter(Archive.archive_id == archive_id).first()
    if not a:
        return
    if "不予开放" in suggestion:
        a.open_status = "不开放"
    elif "延期" in suggestion:
        a.open_status = "延期开放"
    elif "开放" in suggestion:
        a.open_status = "已开放"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_review_task(self, task_id: int):
    """批量 AI 预审任务"""
    db = SessionLocal()
    try:
        task = db.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        if not task:
            return {"error": "task_not_found"}

        criteria = task.filter_criteria or {}

        # 查询待审核档案（需已有 OCR 文本）
        q = db.query(Archive).filter(
            Archive.ocr_status.in_(["done", "low_quality"]),
            Archive.ocr_text.isnot(None),
            Archive.ocr_text != "",
        )
        if criteria.get("year_from"):
            q = q.filter(Archive.year >= criteria["year_from"])
        if criteria.get("year_to"):
            q = q.filter(Archive.year <= criteria["year_to"])
        if criteria.get("category"):
            q = q.filter(Archive.category == criteria["category"])
        if criteria.get("department"):
            q = q.filter(Archive.department == criteria["department"])

        archives = q.all()
        total = len(archives)

        task.status = "running"
        task.total_count = total
        task.completed_count = 0
        db.commit()

        model_name = "deepseek-r1-32b-lora-v1"

        for archive in archives:
            t_start = time.time()

            metadata = {
                "archive_id": archive.archive_id,
                "title": archive.title,
                "year": archive.year,
                "department": archive.department,
                "category": archive.category,
            }

            try:
                result = hybrid_review(archive.ocr_text or "", metadata)
                elapsed_ms = round((time.time() - t_start) * 1000)

                record = ReviewRecord(
                    task_id=task.id,
                    archive_id=archive.archive_id,
                    risk_score=result["risk_score"],
                    risk_level=result["risk_level"],
                    sensitive_items=result["sensitive_items"],
                    suggestion=result["suggestion"],
                    reason=result["reason"],
                    confidence=result.get("llm_confidence", 0),
                    model_name=model_name,
                    processing_time_ms=elapsed_ms,
                )
                db.add(record)
                task.completed_count += 1
                # 同步更新 Archive 开放状态（与单件预审 preview 行为一致）
                _sync_open_status(db, archive.archive_id, result["suggestion"])
                db.commit()

            except Exception as e:
                logger.error(f"Review failed for {archive.archive_id}: {e}")
                task.completed_count += 1
                db.commit()

        task.status = "completed"
        db.commit()

    except Exception as exc:
        task = db.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        if task:
            task.status = "failed"
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()

    return {"task_id": task_id, "reviewed": task.completed_count}


@celery_app.task(bind=True, max_retries=2)
def process_single_review(self, archive_id: str):
    """单件审核"""
    db = SessionLocal()
    try:
        archive = db.query(Archive).filter(Archive.archive_id == archive_id).first()
        if not archive or not archive.ocr_text:
            return {"error": "no_ocr_text"}

        t0 = time.time()
        metadata = {
            "archive_id": archive_id,
            "title": archive.title,
            "year": archive.year,
            "department": archive.department,
        }
        result = hybrid_review(archive.ocr_text, metadata)

        record = ReviewRecord(
            archive_id=archive_id,
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            sensitive_items=result["sensitive_items"],
            suggestion=result["suggestion"],
            reason=result["reason"],
            confidence=result.get("llm_confidence", 0),
            model_name="deepseek-r1-32b-lora-v1",
            processing_time_ms=round((time.time() - t0) * 1000),
        )
        db.add(record)
        db.commit()
        return result
    finally:
        db.close()
