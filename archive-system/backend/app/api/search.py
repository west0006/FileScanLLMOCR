"""智能检索 API — 关键词/语义/高级检索 + 结果导出 + 档案详情"""

import os
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from typing import Optional

from app.core.security import get_current_user, apply_data_scope
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.models import Archive, OperationLog
from app.services import search_service

router = APIRouter()


class KeywordSearchRequest(BaseModel):
    keywords: str
    scope_nodes: Optional[list[str]] = None
    level: Optional[str] = "all"
    exact: bool = False
    dimension: Optional[str] = "all"
    page: int = 1
    page_size: int = 20
    sort: Optional[str] = "score"


class SemanticSearchRequest(BaseModel):
    query: str
    scope_nodes: Optional[list[str]] = None
    page: int = 1
    page_size: int = 20
    sort: Optional[str] = "score"


class AdvancedSearchRequest(BaseModel):
    keywords: Optional[str] = None
    author: Optional[str] = None
    file_code: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    category: Optional[str] = None
    department: Optional[str] = None
    fonds_id: Optional[str] = None
    fonds_ids: Optional[list[str]] = None
    retention_period: Optional[str] = None
    open_status: Optional[str] = None
    level: Optional[str] = "all"
    page: int = 1
    page_size: int = 20
    sort: Optional[str] = "score"


@router.post("/keyword")
def keyword_search(req: KeywordSearchRequest, request: Request, user: dict = Depends(get_current_user)):
    """关键词检索"""
    request.state.log_description = f"关键词检索: {req.keywords}" if req.keywords else "关键词检索"
    return search_service.search_keyword(req.keywords, req.scope_nodes, req.level or "all", req.page, req.page_size, req.sort, req.exact, req.dimension or "all", user)


@router.post("/semantic")
def semantic_search(req: SemanticSearchRequest, request: Request, user: dict = Depends(get_current_user)):
    """语义检索 — LLM 理解意图后构造 ES 查询"""
    request.state.log_description = f"语义检索: {req.query[:80]}" if req.query else "语义检索"
    return search_service.search_semantic(req.query, req.scope_nodes, req.page, req.page_size, req.sort, user)


@router.post("/advanced")
def advanced_search(req: AdvancedSearchRequest, request: Request, user: dict = Depends(get_current_user)):
    """高级条件检索"""
    parts = []
    if req.keywords: parts.append(f"关键词={req.keywords}")
    if req.category: parts.append(f"门类={req.category}")
    if req.department: parts.append(f"单位={req.department}")
    request.state.log_description = f"高级检索: {'; '.join(parts)}" if parts else "高级检索"
    return search_service.search_advanced(
        keywords=req.keywords, author=req.author, file_code=req.file_code,
        year_from=req.year_from, year_to=req.year_to,
        category=req.category, department=req.department, fonds_id=req.fonds_id,
        fonds_ids=req.fonds_ids,
        retention_period=req.retention_period, open_status=req.open_status,
        level=req.level, page=req.page, page_size=req.page_size, sort=req.sort, user=user,
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
    """档案详情 — 含数据权限过滤"""
    db = SessionLocal()
    try:
        q = db.query(Archive)
        q = apply_data_scope(user, q, Archive)
        a = q.filter(Archive.archive_id == archive_id).first()
        if a:
            return {"archive_id": a.archive_id, "title": a.title,
                    "author": a.author or "", "file_code": a.file_code or "",
                    "subject": a.subject or "", "year": a.year,
                    "category": a.category, "department": a.department,
                    "fonds_id": a.fonds_id, "retention_period": a.retention_period,
                    "security_level": a.security_level, "level": a.level or "file",
                    "open_status": a.open_status or "未审核", "file_count": a.file_count,
                    "ocr_status": a.ocr_status,
                    "ocr_engine": a.ocr_engine or "", "ocr_model_version": a.ocr_model_version or "",
                    "ocr_duration_ms": a.ocr_duration_ms or 0}
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


@router.get("/archives/{archive_id}/download")
def archive_download(archive_id: str, page: int = 1, user: dict = Depends(get_current_user)):
    """单件原文下载 — 返回原始文件（Content-Disposition: attachment）"""
    import glob as _glob
    from fastapi.responses import FileResponse

    db = SessionLocal()
    try:
        a = db.query(Archive).filter(Archive.archive_id == archive_id).first()
        if not a:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"error": "archive_not_found"})

        year_dir = str(a.year) if a.year else "unknown"
        fonds_dir = a.fonds_id or "XX"
        pattern = os.path.join(settings.SYNC_DATA_DIR, year_dir, fonds_dir, f"{archive_id}*.*")
        files = sorted(_glob.glob(pattern))

        if not files:
            return {"error": "file_not_found", "hint": f"在 {settings.SYNC_DATA_DIR}/{year_dir}/{fonds_dir}/ 下未找到 {archive_id} 的文件"}

        idx = max(0, min(page - 1, len(files) - 1))
        target = files[idx]
        filename = os.path.basename(target)
        return FileResponse(
            target,
            media_type="application/octet-stream",
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        db.close()


@router.get("/archives/{archive_id}/knowledge-graph")
def archive_knowledge_graph(archive_id: str, depth: int = 1, user: dict = Depends(get_current_user)):
    """
    档案知识图谱 — 基于实体共现的关联网络

    返回以当前档案为中心的实体-档案关系图:
    - nodes: 档案节点 + 实体节点
    - edges: 档案-实体 和 档案-档案 关联边
    """
    from app.services.entity_extractor import extract_entities, extract_entity_summary, find_shared_entities

    db = SessionLocal()
    try:
        center = db.query(Archive).filter(Archive.archive_id == archive_id).first()
        if not center:
            return {"archive_id": archive_id, "nodes": [], "edges": []}

        if not center.entities and center.ocr_text:
            center.entities = extract_entities(center.ocr_text)
            db.commit()

        center_entities = center.entities or []
        center_summary = extract_entity_summary(center_entities)

        nodes, edges, node_ids = [], [], {archive_id}

        nodes.append({
            "id": archive_id, "type": "archive",
            "label": center.title[:20], "year": center.year, "category": center.category,
        })

        entity_ids = set()
        for e in center_entities:
            eid = f"E-{e['type']}-{e['name']}"
            if eid not in entity_ids:
                entity_ids.add(eid)
                nodes.append({"id": eid, "type": "entity", "label": e["name"], "entityType": e["type"]})
            edges.append({"source": archive_id, "target": eid, "type": "has_entity"})

        candidates = db.query(Archive).filter(
            Archive.archive_id != archive_id,
            Archive.ocr_text.isnot(None), Archive.ocr_text != "",
        ).limit(200).all()

        for c in candidates:
            if not c.entities and c.ocr_text:
                c.entities = extract_entities(c.ocr_text)
            shared = find_shared_entities(center_entities, c.entities or [])
            if shared and c.archive_id not in node_ids:
                node_ids.add(c.archive_id)
                nodes.append({
                    "id": c.archive_id, "type": "archive",
                    "label": c.title[:20], "year": c.year, "category": c.category,
                })
                edges.append({
                    "source": archive_id, "target": c.archive_id, "type": "shared_entity",
                    "shared": [f"{s['type']}:{s['name']}" for s in shared[:5]],
                })
            if len(node_ids) > 15:
                break

        db.commit()
        return {
            "archive_id": archive_id, "center_summary": center_summary,
            "nodes": nodes, "edges": edges,
            "entity_count": len(entity_ids), "related_count": len(node_ids) - len(entity_ids) - 1,
        }
    finally:
        db.close()


@router.get("/archives/{archive_id}/related")
def archive_related(archive_id: str, limit: int = 5, user: dict = Depends(get_current_user)):
    """关联档案推荐 — 规则引擎：同门类/同单位/同时期/标题相似"""
    from sqlalchemy import or_

    db = SessionLocal()
    try:
        a = db.query(Archive).filter(Archive.archive_id == archive_id).first()
        if not a:
            return {"archive_id": archive_id, "related": []}

        # 提取标题关键词（2字以上中文词）
        import re
        title_words = set(re.findall(r"[\u4e00-\u9fff]{2,}", a.title or ""))

        # 候选：排除自身
        candidates = db.query(Archive).filter(Archive.archive_id != archive_id)
        candidates = apply_data_scope(user, candidates, Archive)

        related = []
        seen = set()

        # 优先级 1：同门类 + 同单位
        same_scope = candidates.filter(
            Archive.category == a.category,
            Archive.department == a.department,
        ).limit(limit).all()
        for r in same_scope:
            if r.archive_id not in seen:
                related.append(_format_related(r, "同部门·同门类"))
                seen.add(r.archive_id)

        # 优先级 2：同时期（±5年）
        if len(related) < limit:
            same_period = candidates.filter(
                Archive.year.between((a.year or 0) - 5, (a.year or 0) + 5),
            ).limit(limit).all()
            for r in same_period:
                if r.archive_id not in seen:
                    related.append(_format_related(r, "同时期"))
                    seen.add(r.archive_id)

        # 优先级 3：标题关键词重叠
        if len(related) < limit and title_words:
            for r in candidates.limit(100).all():
                if r.archive_id in seen:
                    continue
                r_words = set(re.findall(r"[\u4e00-\u9fff]{2,}", r.title or ""))
                overlap = title_words & r_words
                if overlap:
                    related.append(_format_related(r, f"标题相关: {', '.join(list(overlap)[:3])}"))
                    seen.add(r.archive_id)
                    if len(related) >= limit:
                        break

        return {"archive_id": archive_id, "related": related[:limit]}
    finally:
        db.close()


def _format_related(a: Archive, reason: str) -> dict:
    return {
        "archive_id": a.archive_id,
        "title": a.title,
        "year": a.year,
        "category": a.category or "",
        "department": a.department or "",
        "reason": reason,
    }


@router.get("/archives/{archive_id}/image")
def archive_image(archive_id: str, page: int = 1, user: dict = Depends(get_current_user)):
    """原文图像预览 — 返回文件路径供前端加载（需接入文件转码服务）"""
    db = SessionLocal()
    try:
        a = db.query(Archive).filter(Archive.archive_id == archive_id).first()
        if not a:
            return {"archive_id": archive_id, "page": page, "image_url": None, "error": "archives_not_found"}

        # 按年度/fonds_id/archive_id 构造文件路径
        import os
        from app.core.config import settings

        year_dir = str(a.year) if a.year else "unknown"
        fonds_dir = a.fonds_id or "XX"
        candidate_path = os.path.join(settings.SYNC_DATA_DIR, year_dir, fonds_dir, archive_id)

        # 扫描实际文件
        image_files = []
        for ext in (".tiff", ".tif", ".jpg", ".jpeg", ".png", ".pdf"):
            pattern = os.path.join(settings.SYNC_DATA_DIR, year_dir, fonds_dir, f"{archive_id}*{ext}")
            import glob
            for f in glob.glob(pattern):
                rel = os.path.relpath(f, settings.SYNC_DATA_DIR).replace("\\", "/")
                image_files.append({
                    "page": len(image_files) + 1,
                    "filename": os.path.basename(f),
                    "path": rel,
                    "size_bytes": os.path.getsize(f),
                    "format": ext.lstrip("."),
                })

        if image_files:
            return {
                "archive_id": archive_id,
                "page": page,
                "total_pages": len(image_files),
                "files": image_files,
                "image_url": f"/api/sync/files/{image_files[0]['path']}",
            }

        return {
            "archive_id": archive_id,
            "page": page,
            "image_url": None,
            "file_count": a.file_count or 0,
            "hint": "文件转码服务未接入 — TIFF/PDF 需转码为 WebP 后在线预览",
        }
    finally:
        db.close()


@router.post("/export")
def export_results(format: str = "excel", archive_ids: list[str] = [], user: dict = Depends(get_current_user)):
    """检索结果导出"""
    db = SessionLocal()
    try:
        q = db.query(Archive)
        q = apply_data_scope(user, q, Archive)
        if archive_ids: q = q.filter(Archive.archive_id.in_(archive_ids))
        rows = q.limit(500).all()
        from app.services.export_service import export_to_excel
        from app.core.config import settings
        data = [{
            "档案编号": r.archive_id, "题名": r.title, "归档年度": r.year,
            "门类": r.category or "", "归口单位": r.department or "",
            "保管期限": r.retention_period or "", "密级": r.security_level or "",
        } for r in rows]
        path = export_to_excel("档案检索结果", data,
            ["档案编号","题名","归档年度","门类","归口单位","保管期限","密级"],
            output_dir=settings.UPLOAD_DIR or "/tmp")
        return {"status": "ok", "file": os.path.basename(path), "count": len(data)}
    finally:
        db.close()


@router.get("/facets")
def search_facets(user: dict = Depends(get_current_user)):
    """检索筛选面板 — 返回门类/年度分布计数"""
    from sqlalchemy import func

    db = SessionLocal()
    try:
        cat_rows = db.query(Archive.category, func.count()).group_by(Archive.category).all()
        categories = [{"key": r[0], "label": r[0], "count": r[1]} for r in cat_rows if r[0]]

        year_rows = db.query(Archive.year, func.count()).group_by(Archive.year).order_by(Archive.year.desc()).all()
        years = [{"year": r[0], "count": r[1]} for r in year_rows if r[0]]

        return {"categories": categories, "years": years}
    finally:
        db.close()
