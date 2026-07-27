"""查询利用统计 API — 按用户/时段/利用方式统计"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.core.security import get_current_user, ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN
from app.core.database import SessionLocal
from app.models.models import OperationLog, User
from sqlalchemy import func

router = APIRouter()


def _apply_stats_scope(user: dict, query):
    """非管理员只能看自己的数据"""
    if user["role"] in (ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN):
        return query
    return query.filter(OperationLog.username == user["username"])


@router.get("/by-user")
def stats_by_user(
    user: dict = Depends(get_current_user),
    top_n: int = 20,
    role: Optional[str] = None,
    period: Optional[str] = "month",
):
    """按用户账号统计"""
    db = SessionLocal()
    try:
        q = db.query(
            OperationLog.username,
            OperationLog.operation_type,
            func.count().label("cnt"),
        )
        q = _apply_stats_scope(user, q)

        # 时间筛选
        if period and period != "all":
            now = datetime.utcnow()
            if period == "month":
                cutoff = now - timedelta(days=30)
            elif period == "quarter":
                cutoff = now - timedelta(days=90)
            elif period == "year":
                cutoff = now - timedelta(days=365)
            else:
                cutoff = now - timedelta(days=30)
            q = q.filter(OperationLog.created_at >= cutoff)

        # 角色筛选
        if role:
            role_users = db.query(User.username).filter(User.role == role).all()
            role_names = [r[0] for r in role_users]
            if role_names:
                q = q.filter(OperationLog.username.in_(role_names))
            else:
                return {"items": []}

        rows = q.group_by(OperationLog.username, OperationLog.operation_type).order_by(func.count().desc()).all()

        # 按用户聚合
        users: dict[str, dict] = {}
        for r in rows:
            uname = r[0]
            if uname not in users:
                users[uname] = {"username": uname, "name": uname, "role": "reviewer",
                                "search": 0, "view": 0, "download": 0, "print": 0}
            op_type = r[1]
            if op_type in ("search", "view", "download", "print"):
                users[uname][op_type] = (users[uname].get(op_type, 0) or 0) + r[2]

        # 补全用户姓名和角色
        all_usernames = list(users.keys())
        if all_usernames:
            user_rows = db.query(User).filter(User.username.in_(all_usernames)).all()
            for u in user_rows:
                if u.username in users:
                    users[u.username]["name"] = u.name or u.username
                    users[u.username]["role"] = u.role or "reviewer"

        items = sorted(users.values(), key=lambda x: -(x["search"]+x["view"]+x["download"]+x["print"]))[:top_n]
        return {"items": items}
    finally:
        db.close()


@router.get("/by-time")
def stats_by_time(
    user: dict = Depends(get_current_user),
    granularity: str = Query("day", description="day | week | month | quarter | year"),
    days: int = Query(30, description="统计最近 N 天"),
):
    """按时间段统计 — 支持日/周/月/季度/年粒度"""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        logs = (
            _apply_stats_scope(user, db.query(OperationLog))
            .filter(OperationLog.created_at >= cutoff)
            .order_by(OperationLog.created_at.asc())
            .all()
        )

        if not logs:
            return {"items": [], "granularity": granularity, "days": days}

        buckets: dict[str, int] = {}
        for log in logs:
            dt = log.created_at
            if granularity == "day":
                key = dt.strftime("%Y-%m-%d")
            elif granularity == "week":
                key = dt.strftime("%Y-W%W")
            elif granularity == "month":
                key = dt.strftime("%Y-%m")
            elif granularity == "quarter":
                q = (dt.month - 1) // 3 + 1
                key = f"{dt.year}-Q{q}"
            else:  # year
                key = dt.strftime("%Y")
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
            _apply_stats_scope(user, db.query(OperationLog.operation_type, func.count()))
            .group_by(OperationLog.operation_type)
            .all()
        )
        return {"items": [{"type": r[0], "count": r[1]} for r in rows]}
    finally:
        db.close()
