"""查询利用统计 API — 按用户/时段/利用方式统计"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.core.security import get_current_user
from app.core.database import SessionLocal
from app.models.models import OperationLog
from sqlalchemy import func, extract

router = APIRouter()


@router.get("/by-user")
def stats_by_user(user: dict = Depends(get_current_user), top_n: int = 20):
    """按用户账号统计 — 检索/浏览/下载/打印分维度"""
    db = SessionLocal()
    try:
        rows = (
            db.query(
                OperationLog.username,
                OperationLog.operation_type,
                func.count().label("cnt"),
            )
            .group_by(OperationLog.username, OperationLog.operation_type)
            .order_by(func.count().desc())
            .all()
        )

        # 按用户聚合
        users: dict[str, dict] = {}
        for r in rows:
            uname = r[0]
            if uname not in users:
                users[uname] = {"username": uname, "total": 0, "by_type": {}}
            users[uname]["total"] += r[2]
            users[uname]["by_type"][r[1]] = r[2]

        items = sorted(users.values(), key=lambda x: -x["total"])[:top_n]
        return {"items": items}
    finally:
        db.close()


@router.get("/by-time")
def stats_by_time(
    user: dict = Depends(get_current_user),
    granularity: str = Query("day", description="day | week | month"),
    days: int = Query(30, description="统计最近 N 天"),
):
    """按时间段统计 — 支持日/周/月粒度"""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        logs = (
            db.query(OperationLog)
            .filter(OperationLog.created_at >= cutoff)
            .order_by(OperationLog.created_at.asc())
            .all()
        )

        if not logs:
            return {"items": [], "granularity": granularity, "days": days}

        # 时间分桶
        buckets: dict[str, int] = {}
        for log in logs:
            dt = log.created_at
            if granularity == "day":
                key = dt.strftime("%Y-%m-%d")
            elif granularity == "week":
                key = dt.strftime("%Y-W%W")
            else:  # month
                key = dt.strftime("%Y-%m")

            buckets[key] = buckets.get(key, 0) + 1

        items = [{"period": k, "count": v} for k, v in sorted(buckets.items())]
        return {"items": items, "granularity": granularity, "days": days}
    finally:
        db.close()


@router.get("/by-type")
def stats_by_type(user: dict = Depends(get_current_user)):
    """按利用方式统计"""
    db = SessionLocal()
    try:
        rows = (
            db.query(OperationLog.operation_type, func.count())
            .group_by(OperationLog.operation_type)
            .all()
        )
        return {"items": [{"type": r[0], "count": r[1]} for r in rows]}
    finally:
        db.close()
