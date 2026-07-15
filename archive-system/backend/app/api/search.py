"""智能检索 API — 关键词/语义/高级检索 + 结果导出 + 档案详情"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

from app.core.security import get_current_user
from app.core.database import SessionLocal
from app.models.models import Archive, OperationLog
from app.services import search_service

router = APIRouter()


class KeywordSearchRequest(BaseModel):
    keywords: str
    scope_nodes: Optional[list[str]] = None   # 目录树节点
    level: Optional[str] = "all"              # all/project/box/file
    page: int = 1
    page_size: int = 20


class SemanticSearchRequest(BaseModel):
    query: str
    scope_nodes: Optional[list[str]] = None
    page: int = 1
    page_size: int = 20


class AdvancedSearchRequest(BaseModel):
    keywords: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    category: Optional[str] = None
    department: Optional[str] = None
    fonds_id: Optional[str] = None
    retention_period: Optional[str] = None
    open_status: Optional[str] = None
    page: int = 1
    page_size: int = 20


@router.post("/keyword")
def keyword_search(req: KeywordSearchRequest, user: dict = Depends(get_current_user)):
    """关键词检索"""
    return search_service.search_keyword(req.keywords, req.scope_nodes, req.level or "all", req.page, req.page_size)


@router.post("/semantic")
def semantic_search(req: SemanticSearchRequest, user: dict = Depends(get_current_user)):
    """语义检索 — LLM 理解意图后构造 ES 查询"""
    return search_service.search_semantic(req.query, req.scope_nodes, req.page, req.page_size)


@router.post("/advanced")
def advanced_search(req: AdvancedSearchRequest, user: dict = Depends(get_current_user)):
    """高级条件检索"""
    return search_service.search_advanced(
        keywords=req.keywords, year_from=req.year_from, year_to=req.year_to,
        category=req.category, department=req.department, fonds_id=req.fonds_id,
        retention_period=req.retention_period, open_status=req.open_status,
        page=req.page, page_size=req.page_size,
    )


@router.get("/history")
def search_history(user: dict = Depends(get_current_user), page: int = 1, page_size: int = 20):
    """检索历史"""
    db = SessionLocal()
    try:
        total = db.query(OperationLog).filter(
            OperationLog.user_id == user["user_id"],
            OperationLog.operation_type == "search"
        ).count()
        items = db.query(OperationLog).filter(
            OperationLog.user_id == user["user_id"],
            OperationLog.operation_type == "search"
        ).order_by(OperationLog.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size,
                "items": [{"query": i.description, "searched_at": str(i.created_at)} for i in items]}
    finally:
        db.close()


@router.get("/archives/{archive_id}")
def archive_detail(archive_id: str, user: dict = Depends(get_current_user)):
    """档案详情"""
    db = SessionLocal()
    try:
        a = db.query(Archive).filter(Archive.archive_id == archive_id).first()
        if a:
            return {"archive_id": a.archive_id, "title": a.title, "year": a.year,
                    "category": a.category, "department": a.department,
                    "fonds_id": a.fonds_id, "retention_period": a.retention_period,
                    "security_level": a.security_level, "file_count": a.file_count,
                    "ocr_status": a.ocr_status}
        return {"archive_id": archive_id, "error": "not_found"}
    finally:
        db.close()


@router.get("/archives/{archive_id}/ocr")
def archive_ocr_text(archive_id: str, user: dict = Depends(get_current_user)):
    """OCR 对照文本"""
    db = SessionLocal()
    try:
        a = db.query(Archive).filter(Archive.archive_id == archive_id).first()
        if a and a.ocr_text:
            return {"archive_id": archive_id, "ocr_text": a.ocr_text,
                    "ocr_confidence": a.ocr_confidence, "ocr_status": a.ocr_status}
        return {"archive_id": archive_id, "ocr_text": None}
    finally:
        db.close()


@router.get("/archives/{archive_id}/image")
def archive_image(archive_id: str, page: int = 1, user: dict = Depends(get_current_user)):
    """原文图像预览"""
    return {"archive_id": archive_id, "page": page, "image_url": None}


@router.post("/export")
def export_results(format: str = "excel", archive_ids: list[str] = [], user: dict = Depends(get_current_user)):
    """检索结果导出 — 异步任务"""
    return {"task_id": "export-task", "status": "queued", "message": "导出任务已提交"}
