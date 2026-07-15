"""查询利用统计 API — 按用户/时段/利用方式统计"""

from fastapi import APIRouter, Depends
from typing import Optional

from app.core.security import get_current_user
from app.core.database import SessionLocal
from app.models.models import OperationLog
from sqlalchemy import func

router = APIRouter()


@router.get("/by-user")
def stats_by_user(user: dict = Depends(get_current_user), top_n: int = 20):
    """按用户账号统计"""
    db = SessionLocal()
    try:
        rows = db.query(OperationLog.username, func.count().label('cnt')).group_by(
            OperationLog.username).order_by(func.count().desc()).limit(top_n).all()
        return {"items": [{"username": r[0], "count": r[1]} for r in rows]}
    finally:
        db.close()


@router.get("/by-time")
def stats_by_time(user: dict = Depends(get_current_user)):
    """按时间段统计"""
    db = SessionLocal()
    try:
        total = db.query(OperationLog).count()
        return {"items": [{"period": "total", "count": total}]}
    finally:
        db.close()


@router.get("/by-type")
def stats_by_type(user: dict = Depends(get_current_user)):
    """按利用方式统计"""
    db = SessionLocal()
    try:
        rows = db.query(OperationLog.operation_type, func.count()).group_by(
            OperationLog.operation_type).all()
        return {"items": [{"type": r[0], "count": r[1]} for r in rows]}
    finally:
        db.close()
