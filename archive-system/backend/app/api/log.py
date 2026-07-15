"""操作日志 API — 日志查询 + 导出 + 审计"""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.core.security import get_current_user
from app.core.database import SessionLocal
from app.models.models import OperationLog
from datetime import datetime

router = APIRouter()


@router.get("/")
def list_logs(user: dict = Depends(get_current_user), page: int = 1, page_size: int = 20,
              user_account: Optional[str] = None, operation_type: Optional[str] = None,
              module: Optional[str] = None, result: Optional[str] = None,
              date_from: Optional[str] = None, date_to: Optional[str] = None, keyword: Optional[str] = None):
    """操作日志查询"""
    db = SessionLocal()
    try:
        q = db.query(OperationLog)
        if user_account: q = q.filter(OperationLog.username == user_account)
        if operation_type: q = q.filter(OperationLog.operation_type == operation_type)
        if module: q = q.filter(OperationLog.module == module)
        if result: q = q.filter(OperationLog.result == result)
        if keyword: q = q.filter(OperationLog.description.contains(keyword))
        total = q.count()
        items = q.order_by(OperationLog.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size,
                "items": [{"id": i.id, "user_id": i.user_id, "username": i.username,
                            "operation_type": i.operation_type, "module": i.module,
                            "description": i.description, "target_id": i.target_id,
                            "ip_address": i.ip_address, "result": i.result,
                            "created_at": str(i.created_at)} for i in items]}
    finally:
        db.close()


@router.get("/login")
def login_logs(user: dict = Depends(get_current_user), page: int = 1, page_size: int = 20):
    """登录日志"""
    db = SessionLocal()
    try:
        q = db.query(OperationLog).filter(OperationLog.operation_type.in_(["login", "logout"]))
        total = q.count()
        items = q.order_by(OperationLog.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size,
                "items": [{"id": i.id, "username": i.username, "operation_type": i.operation_type,
                            "ip_address": i.ip_address, "result": i.result,
                            "created_at": str(i.created_at)} for i in items]}
    finally:
        db.close()


@router.post("/export")
def export_logs(
    format: str = "excel",
    filters: dict = {},
    user: dict = Depends(get_current_user),
):
    """日志导出"""
    return {"task_id": "mock-export-log", "status": "queued"}


@router.get("/audit/summary")
def audit_summary(user: dict = Depends(get_current_user)):
    """安全审计摘要"""
    db = SessionLocal()
    try:
        total = db.query(OperationLog).count()
        failed = db.query(OperationLog).filter(OperationLog.result == "failure").count()
        return {"total_operations": total, "failed_operations": failed, "anomalies": []}
    finally:
        db.close()
