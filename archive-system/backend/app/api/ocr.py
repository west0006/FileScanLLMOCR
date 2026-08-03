"""OCR 识别 API — 任务管理 + 结果查看 + 质量报告 + 版面分析"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional

from app.core.security import get_current_user
from app.core.database import SessionLocal
from app.models.models import OcrTask, Archive

router = APIRouter()


from pydantic import Field

class CreateOcrTaskRequest(BaseModel):
    task_name: str = Field(min_length=1, max_length=50)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    category: Optional[str] = None
    department: Optional[str] = None
    engine: Optional[str] = "paddleocr"  # paddleocr | mock
    enable_preprocess: Optional[bool] = True
    priority: Optional[int] = 0  # 0=普通, 1=高, 2=紧急


@router.post("/tasks")
def create_ocr_task(req: CreateOcrTaskRequest, request: Request, user: dict = Depends(get_current_user)):
    """创建 OCR 任务"""
    request.state.log_target_id = f"task-ocr-{req.task_name}"
    db = SessionLocal()
    try:
        # 检查任务名称是否重复
        existing = db.query(OcrTask).filter(OcrTask.task_name == req.task_name).first()
        if existing:
            return {"error": "任务名称已存在，请重新输入"}
        task = OcrTask(
            task_name=req.task_name,
            filter_criteria={"year_from": req.year_from, "year_to": req.year_to,
                             "category": req.category, "department": req.department},
            created_by=user["user_id"],
            priority=req.priority or 0,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        try:
            from app.tasks.ocr_tasks import process_ocr_task
            process_ocr_task.delay(task.id)
        except Exception:
            pass
        return {"task_id": task.id, "task_name": task.task_name, "status": "queued"}
    finally:
        db.close()


@router.put("/tasks/{task_id}")
def update_ocr_task(task_id: int, action: str, user: dict = Depends(get_current_user)):
    """暂停/恢复/取消 OCR 任务"""
    db = SessionLocal()
    try:
        t = db.query(OcrTask).filter(OcrTask.id == task_id).first()
        if not t: return {"error": "not_found"}
        if action == "start":
            t.status = "running"
            from app.tasks.ocr_tasks import process_ocr_task
            try: process_ocr_task.delay(task_id)
            except: pass
        elif action == "pause": t.status = "paused"
        elif action == "resume":
            t.status = "running"
            from app.tasks.ocr_tasks import process_ocr_task
            try: process_ocr_task.delay(task_id)
            except: pass
        elif action == "cancel": t.status = "cancelled"
        db.commit()
        return {"task_id": task_id, "action": action, "status": t.status}
    finally:
        db.close()


@router.get("/tasks")
def list_ocr_tasks(user: dict = Depends(get_current_user), page: int = 1, page_size: int = 20, status: Optional[str] = None):
    """OCR 任务列表"""
    db = SessionLocal()
    try:
        q = db.query(OcrTask)
        if status: q = q.filter(OcrTask.status == status)
        total = q.count()
        items = q.order_by(OcrTask.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size,
                "items": [{"id": t.id, "task_name": t.task_name, "total_pages": t.total_pages,
                            "processed_pages": t.processed_pages, "failed_pages": t.failed_pages or 0,
                            "status": t.status,
                            "priority": t.priority or 0,
                            "created_at": str(t.created_at)} for t in items]}
    finally:
        db.close()


@router.get("/tasks/{task_id}")
def get_ocr_task(task_id: int, user: dict = Depends(get_current_user)):
    """OCR 任务详情 + 进度"""
    db = SessionLocal()
    try:
        t = db.query(OcrTask).filter(OcrTask.id == task_id).first()
        if not t: return {"error": "not_found"}
        return {"id": t.id, "task_id": t.id, "task_name": t.task_name,
                "status": t.status, "total_pages": t.total_pages,
                "processed_pages": t.processed_pages,
                "failed_pages": t.failed_pages or 0,
                "priority": t.priority or 0,
                "filter_criteria": t.filter_criteria,
                "created_at": str(t.created_at)}
    finally:
        db.close()


@router.get("/results/{archive_id}")
def get_ocr_result(archive_id: str, user: dict = Depends(get_current_user)):
    """查看某档案的 OCR 识别结果"""
    db = SessionLocal()
    try:
        a = db.query(Archive).filter(Archive.archive_id == archive_id).first()
        if a:
            return {"archive_id": archive_id, "ocr_text": a.ocr_text,
                    "confidence": a.ocr_confidence, "status": a.ocr_status}
        return {"archive_id": archive_id, "ocr_text": None}
    finally:
        db.close()


@router.get("/quality-report")
def quality_report(task_id: Optional[int] = None, user: dict = Depends(get_current_user)):
    """OCR 质量报告 — 基于实际数据动态计算"""
    db = SessionLocal()
    try:
        q = db.query(Archive).filter(Archive.ocr_status.in_(["done", "low_quality"]))

        if task_id:
            task = db.query(OcrTask).filter(OcrTask.id == task_id).first()
            if task and task.filter_criteria:
                c = task.filter_criteria
                if c.get("year_from"): q = q.filter(Archive.year >= c["year_from"])
                if c.get("year_to"): q = q.filter(Archive.year <= c["year_to"])
                if c.get("category"): q = q.filter(Archive.category == c["category"])

        archives = q.all()
        total = len(archives)
        if total == 0:
            return {"overall_accuracy": 0, "total": 0, "low_confidence_count": 0, "common_errors": []}

        # 平均置信度
        confidences = [a.ocr_confidence for a in archives if a.ocr_confidence is not None]
        overall = round(sum(confidences) / len(confidences), 4) if confidences else 0

        # 低置信度 (< 0.7) — 附带 OCR 文本前 200 字供抽查
        low_conf = []
        for a in archives:
            if a.ocr_confidence is not None and a.ocr_confidence < 0.7:
                low_conf.append({
                    "archive_id": a.archive_id,
                    "title": a.title,
                    "confidence": a.ocr_confidence,
                    "ocr_preview": (a.ocr_text or "")[:200],
                })

        # 常见错误类型统计
        error_counts: dict[str, int] = {}
        for a in archives:
            if a.ocr_status == "low_quality":
                error_counts["低置信度"] = error_counts.get("低置信度", 0) + 1
            if a.ocr_status == "failed":
                error_counts["识别失败"] = error_counts.get("识别失败", 0) + 1
        common_errors = [{"type": k, "count": v} for k, v in sorted(error_counts.items(), key=lambda x: -x[1])]

        return {
            "overall_accuracy": overall,
            "total": total,
            "low_confidence_count": len(low_conf),
            "low_confidence_ids": [a.archive_id for a in low_conf[:20]],
            "failed_count": sum(1 for a in archives if a.ocr_status == "failed"),
            "common_errors": common_errors,
        }
    finally:
        db.close()


# ===================== 版面分析 =====================

@router.post("/detect")
def detect_structure(image_path: str, user: dict = Depends(get_current_user)):
    """版面分析 — 检测标题/表格/段落/印章"""
    from app.services.ocr_client import ocr_client
    return ocr_client.recognize_structure(image_path)


# ===================== 模型信息 =====================

@router.get("/models")
def ocr_models_info(user: dict = Depends(get_current_user)):
    """OCR 引擎信息 — GPU/CPU 状态 + 模型版本"""
    from app.services.ocr_client import ocr_client
    info = ocr_client.get_info()
    info["ocr_mode"] = info.get("mode", "mock")
    return info


# ===================== 调试/测试端点（需认证） =====================

class DebugOcrRequest(BaseModel):
    text: Optional[str] = None
    image_path: Optional[str] = None


@router.post("/debug/test")
def debug_ocr_test(req: DebugOcrRequest, user: dict = Depends(get_current_user)):
    """
    测试专用端点 — 同步识别，返回详细信息。
    需有效 Token，用于开发调试和问题排查。
    """
    import time
    from app.core.config import settings
    from app.services.ocr_client import ocr_client

    # 检测环境
    debug_info = {
        "mode": settings.OCR_MODE,
        "ocr_available": settings.OCR_MODE == "real",
        "celery_available": False,
    }

    # 检测 Celery
    try:
        from app.tasks.celery_app import celery_app
        debug_info["celery_available"] = True
    except Exception:
        pass

    # 同步识别
    t0 = time.time()
    image_path = req.image_path or "debug_test_sample"
    result = ocr_client.recognize(image_path)

    # Mock 模式下覆盖文本
    if settings.OCR_MODE == "mock" and req.text:
        result["text"] = req.text
        result["confidence"] = 0.98

    result["processing_time_ms"] = round((time.time() - t0) * 1000)
    result["engine"] = "paddleocr" if settings.OCR_MODE == "real" else "mock"

    return {
        "mode": settings.OCR_MODE,
        "result": result,
        "debug": debug_info,
    }
