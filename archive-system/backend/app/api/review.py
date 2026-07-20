"""AI 开放预审 API — 任务管理 + 预审记录 + 结果导出"""

import os
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from typing import Optional

from app.core.security import get_current_user
from app.core.database import SessionLocal
from app.models.models import ReviewTask, ReviewRecord, Archive
from app.services.review_service import hybrid_review

router = APIRouter()


class CreateReviewTaskRequest(BaseModel):
    task_name: str
    batch_name: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    category: Optional[str] = None
    department: Optional[str] = None


class PreviewRequest(BaseModel):
    archive_id: str
    full_text: str
    title: Optional[str] = None
    year: Optional[int] = None
    department: Optional[str] = None


# ===================== 预审工作台 =====================

@router.post("/preview")
def preview_review(req: PreviewRequest, request: Request, user: dict = Depends(get_current_user)):
    """单件实时预审 — 工作台用，结果自动落库"""
    request.state.log_description = f"AI预审: {req.archive_id} — {req.title or '(无题名)'}"
    metadata = {
        "archive_id": req.archive_id,
        "title": req.title,
        "year": req.year,
        "department": req.department,
    }
    import time
    t0 = time.time()
    result = hybrid_review(req.full_text, metadata)
    result["archive_id"] = req.archive_id

    # 落库（记录链路闭环）
    db = SessionLocal()
    try:
        record = ReviewRecord(
            archive_id=req.archive_id,
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            sensitive_items=result["sensitive_items"],
            suggestion=result["suggestion"],
            reason=result["reason"],
            confidence=result.get("llm_confidence", 0),
            model_name="mock" if result.get("llm_confidence", 0) < 0.8 else "llm",
            processing_time_ms=round((time.time()-t0)*1000),
        )
        db.add(record)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()
    return result


# ===================== 预审任务管理 =====================

@router.post("/tasks")
def create_review_task(req: CreateReviewTaskRequest, user: dict = Depends(get_current_user)):
    """创建预审任务 → Celery 异步队列"""
    db = SessionLocal()
    try:
        task = ReviewTask(
            task_name=req.task_name,
            batch_name=req.batch_name,
            status="pending",
            filter_criteria={
                "year_from": req.year_from, "year_to": req.year_to,
                "category": req.category, "department": req.department,
            },
            created_by=user["user_id"],
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        # 派发异步任务
        try:
            from app.tasks.review_tasks import process_review_task
            process_review_task.delay(task.id)
        except Exception:
            pass
        return {"task_id": task.id, "task_name": task.task_name, "status": "queued"}
    finally:
        db.close()


@router.get("/tasks")
def list_review_tasks(user: dict = Depends(get_current_user), page: int = 1, page_size: int = 20, status: Optional[str] = None):
    """预审任务列表"""
    db = SessionLocal()
    try:
        q = db.query(ReviewTask)
        if status: q = q.filter(ReviewTask.status == status)
        total = q.count()
        items = q.order_by(ReviewTask.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size,
                "items": [{"id": t.id, "task_name": t.task_name, "batch_name": t.batch_name,
                            "total_count": t.total_count, "completed_count": t.completed_count,
                            "status": t.status, "created_at": str(t.created_at)} for t in items]}
    finally:
        db.close()


@router.get("/tasks/{task_id}")
def get_review_task(task_id: int, user: dict = Depends(get_current_user)):
    """预审任务进度"""
    db = SessionLocal()
    try:
        t = db.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        if not t: return {"error": "not_found"}
        records = db.query(ReviewRecord).filter(ReviewRecord.task_id == task_id).all()
        dist = {"高": 0, "中": 0, "低": 0}
        for r in records:
            if r.risk_level in dist: dist[r.risk_level] += 1
        return {"task_id": t.id, "status": t.status, "total_count": t.total_count,
                "completed_count": t.completed_count, "risk_distribution": dist}
    finally:
        db.close()


@router.put("/tasks/{task_id}")
def update_review_task(task_id: int, action: str, user: dict = Depends(get_current_user)):
    """启动/暂停/恢复/取消预审任务"""
    db = SessionLocal()
    try:
        t = db.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        if not t: return {"error": "not_found"}
        if action == "start":
            t.status = "running"
            from app.tasks.review_tasks import process_review_task
            try: process_review_task.delay(task_id)
            except: pass
        elif action == "pause": t.status = "paused"
        elif action == "resume":
            t.status = "running"
            from app.tasks.review_tasks import process_review_task
            try: process_review_task.delay(task_id)
            except: pass
        elif action == "cancel": t.status = "cancelled"
        db.commit()
        return {"task_id": task_id, "action": action, "status": t.status}
    finally:
        db.close()


# ===================== 预审记录管理 =====================

@router.get("/records")
def list_review_records(user: dict = Depends(get_current_user), page: int = 1, page_size: int = 20,
                        risk_level: Optional[str] = None, suggestion: Optional[str] = None,
                        year_from: Optional[int] = None, year_to: Optional[int] = None,
                        department: Optional[str] = None):
    """预审记录列表 — 支持多条件筛选"""
    db = SessionLocal()
    try:
        q = db.query(ReviewRecord)
        if risk_level: q = q.filter(ReviewRecord.risk_level == risk_level)
        if suggestion: q = q.filter(ReviewRecord.suggestion == suggestion)
        if year_from or year_to or department:
            archive_ids = [r.archive_id for r in q.all() if r.archive_id]
            if archive_ids:
                aq = db.query(Archive).filter(Archive.archive_id.in_(archive_ids))
                if year_from: aq = aq.filter(Archive.year >= year_from)
                if year_to: aq = aq.filter(Archive.year <= year_to)
                if department: aq = aq.filter(Archive.department == department)
                filtered_ids = [a.archive_id for a in aq.all()]
                q = q.filter(ReviewRecord.archive_id.in_(filtered_ids))
        total = q.count()
        items = q.order_by(ReviewRecord.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        # join Archive 补齐题名/年度/单位
        archive_ids = [r.archive_id for r in items if r.archive_id]
        archives = {}
        if archive_ids:
            for a in db.query(Archive).filter(Archive.archive_id.in_(archive_ids)).all():
                archives[a.archive_id] = a
        return {"total": total, "page": page, "page_size": page_size,
                "items": [{"id": r.id, "archive_id": r.archive_id,
                            "title": archives.get(r.archive_id, Archive()).title if r.archive_id else "",
                            "year": archives.get(r.archive_id, Archive()).year if r.archive_id else None,
                            "department": archives.get(r.archive_id, Archive()).department if r.archive_id else "",
                            "risk_score": r.risk_score, "risk_level": r.risk_level,
                            "suggestion": r.suggestion, "reason": r.reason,
                            "confidence": r.confidence, "sensitive_items": r.sensitive_items,
                            "processing_time_ms": r.processing_time_ms,
                            "model_name": r.model_name, "created_at": str(r.created_at)} for r in items]}
    finally:
        db.close()


@router.get("/records/{record_id}")
def get_review_record(record_id: int, user: dict = Depends(get_current_user)):
    """预审记录详情（12 字段）"""
    db = SessionLocal()
    try:
        r = db.query(ReviewRecord).filter(ReviewRecord.id == record_id).first()
        if not r: return {"error": "not_found"}
        a = db.query(Archive).filter(Archive.archive_id == r.archive_id).first()
        return {"id": r.id, "archive_id": r.archive_id,
                "title": a.title if a else "", "year": a.year if a else None,
                "department": a.department if a else "",
                "risk_score": r.risk_score, "risk_level": r.risk_level,
                "sensitive_items": r.sensitive_items, "suggestion": r.suggestion,
                "reason": r.reason, "confidence": r.confidence,
                "model_name": r.model_name, "processing_time_ms": r.processing_time_ms,
                "created_at": str(r.created_at)}
    finally:
        db.close()


# ===================== 导出 =====================

@router.post("/export")
def export_review_results(task_id: Optional[int] = None, archive_ids: list[str] = [], user: dict = Depends(get_current_user)):
    """导出预审结果"""
    db = SessionLocal()
    try:
        q = db.query(ReviewRecord)
        if task_id: q = q.filter(ReviewRecord.task_id == task_id)
        if archive_ids: q = q.filter(ReviewRecord.archive_id.in_(archive_ids))
        rows = q.limit(500).all()
        from app.services.export_service import export_to_excel
        from app.core.config import settings
        data = [{
            "档案编号": r.archive_id, "风险评分": r.risk_score, "风险等级": r.risk_level,
            "AI建议": r.suggestion, "建议理由": r.reason or "",
            "置信度": f"{(r.confidence or 0)*100:.0f}%",
            "敏感类型": ", ".join(s.get("type","") for s in (r.sensitive_items or [])),
            "预审耗时(ms)": r.processing_time_ms, "模型": r.model_name or "",
            "预审时间": str(r.created_at)[:19] if r.created_at else "",
        } for r in rows]
        path = export_to_excel("AI预审结果", data,
            ["档案编号","风险评分","风险等级","AI建议","建议理由","置信度","敏感类型","预审耗时(ms)","模型","预审时间"],
            output_dir=settings.UPLOAD_DIR or "/tmp")
        return {"status": "ok", "file": os.path.basename(path), "count": len(data)}
    finally:
        db.close()
