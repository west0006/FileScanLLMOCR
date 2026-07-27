"""操作日志 API — 日志查询 + 导出 + 审计"""

import os
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
        if date_from:
            try:
                from datetime import datetime
                q = q.filter(OperationLog.created_at >= datetime.fromisoformat(date_from))
            except: pass
        if date_to:
            try:
                from datetime import datetime
                q = q.filter(OperationLog.created_at <= datetime.fromisoformat(date_to.replace('00:00:00','23:59:59')))
            except: pass
        total = q.count()
        items = q.order_by(OperationLog.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size,
                "items": [{"id": i.id, "user_id": i.user_id, "username": i.username,
                            "operation_type": i.operation_type, "module": i.module,
                            "description": i.description, "target_id": i.target_id,
                            "ip_address": i.ip_address, "result": i.result,
                            "chain_hash": i.chain_hash,
                            "created_at": str(i.created_at)} for i in items]}
    finally:
        db.close()


@router.get("/login")
def login_logs(user: dict = Depends(get_current_user), page: int = 1, page_size: int = 20,
               username: Optional[str] = None, result: Optional[str] = None,
               date_from: Optional[str] = None, date_to: Optional[str] = None):
    """登录日志 — 支持按用户/结果/时间筛选"""
    db = SessionLocal()
    try:
        q = db.query(OperationLog).filter(OperationLog.operation_type.in_(["login", "logout"]))
        if username: q = q.filter(OperationLog.username == username)
        if result: q = q.filter(OperationLog.result == result)
        if date_from:
            try: q = q.filter(OperationLog.created_at >= datetime.fromisoformat(date_from))
            except: pass
        if date_to:
            try: q = q.filter(OperationLog.created_at <= datetime.fromisoformat(date_to.replace("00:00:00", "23:59:59")))
            except: pass
        total = q.count()
        items = q.order_by(OperationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total": total, "page": page, "page_size": page_size,
            "items": [{
                "id": i.id, "username": i.username, "operation_type": i.operation_type,
                "ip_address": i.ip_address, "result": i.result,
                "description": i.description or "", "created_at": str(i.created_at),
            } for i in items],
        }
    finally:
        db.close()


@router.post("/export")
def export_logs(format: str = "excel", filters: dict = {}, user: dict = Depends(get_current_user)):
    """日志导出 — 支持筛选条件"""
    db = SessionLocal()
    try:
        q = db.query(OperationLog)
        if filters.get("user_account"): q = q.filter(OperationLog.username == filters["user_account"])
        if filters.get("operation_type"): q = q.filter(OperationLog.operation_type == filters["operation_type"])
        if filters.get("module"): q = q.filter(OperationLog.module == filters["module"])
        rows = q.order_by(OperationLog.created_at.desc()).limit(2000).all()
        from app.services.export_service import export_to_excel
        from app.core.config import settings
        data = [{
            "操作时间": str(r.created_at)[:19] if r.created_at else "",
            "用户": r.username, "操作类型": r.operation_type, "模块": r.module or "",
            "操作描述": r.description or "", "操作对象": r.target_id or "",
            "IP地址": r.ip_address or "", "结果": r.result,
            "链校验": (r.chain_hash or "")[:16],
        } for r in rows]
        path = export_to_excel("操作日志", data,
            ["操作时间","用户","操作类型","模块","操作描述","操作对象","IP地址","结果","链校验"],
            output_dir=settings.UPLOAD_DIR or "/tmp")
        return {"status": "ok", "file": os.path.basename(path), "count": len(data)}
    finally:
        db.close()


@router.get("/audit/summary")
def audit_summary(user: dict = Depends(get_current_user)):
    """安全审计摘要 — 含异常检测"""
    from datetime import datetime, timedelta
    from sqlalchemy import func

    db = SessionLocal()
    try:
        total = db.query(OperationLog).count()
        failed = db.query(OperationLog).filter(OperationLog.result == "failure").count()

        anomalies = []
        now = datetime.utcnow()

        # 1. 最近1小时内大量失败登录（≥5次）
        one_hour_ago = now - timedelta(hours=1)
        failed_logins = (
            db.query(OperationLog.username, func.count().label("cnt"))
            .filter(
                OperationLog.operation_type == "login",
                OperationLog.result == "failure",
                OperationLog.created_at >= one_hour_ago,
            )
            .group_by(OperationLog.username)
            .having(func.count() >= 5)
            .all()
        )
        for row in failed_logins:
            anomalies.append({
                "type": "暴力破解风险",
                "severity": "high",
                "detail": f"用户 {row[0]} 在1小时内失败登录 {row[1]} 次",
                "time": str(now),
            })

        # 2. 非工作时间操作（凌晨0-6点）
        night_ops = (
            db.query(OperationLog)
            .filter(
                func.extract("hour", OperationLog.created_at).between(0, 5),
                OperationLog.created_at >= now - timedelta(days=1),
            )
            .count()
        )
        if night_ops >= 3:
            anomalies.append({
                "type": "非工作时间操作",
                "severity": "medium",
                "detail": f"过去24小时内有 {night_ops} 次凌晨(0-6点)操作",
                "time": str(now),
            })

        # 3. 连续失败操作（最近100条中连续失败≥5次）
        recent = (
            db.query(OperationLog)
            .order_by(OperationLog.created_at.desc())
            .limit(100)
            .all()
        )
        consecutive_fails = 0
        for log in recent:
            if log.result == "failure":
                consecutive_fails += 1
                if consecutive_fails >= 5:
                    break
            else:
                consecutive_fails = 0
        if consecutive_fails >= 5:
            anomalies.append({
                "type": "连续操作失败",
                "severity": "medium",
                "detail": f"最近100条日志中连续失败 {consecutive_fails} 次",
                "time": str(now),
            })

        return {
            "total_operations": total,
            "failed_operations": failed,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
        }
    finally:
        db.close()


@router.get("/audit/chain-verify")
def verify_chain(user: dict = Depends(get_current_user)):
    """哈希链完整性校验 — 检测日志是否被篡改"""
    import hashlib
    db = SessionLocal()
    try:
        logs = db.query(OperationLog).order_by(OperationLog.id.asc()).all()
        if not logs:
            return {"status": "ok", "total": 0, "tampered": 0}

        prev_hash = "0" * 64
        tampered = []
        for log in logs:
            content = f"{log.username}|{log.operation_type}|{log.module}|{log.description or ''}|{log.target_id or ''}|{log.result}"
            expected = hashlib.sha256(f"{prev_hash}{content}".encode()).hexdigest()
            if expected != (log.chain_hash or ""):
                tampered.append({"id": log.id, "expected": expected[:16], "actual": (log.chain_hash or "")[:16]})
            prev_hash = log.chain_hash or expected

        return {
            "status": "tampered" if tampered else "ok",
            "total": len(logs),
            "tampered": len(tampered),
            "details": tampered[:10],
        }
    finally:
        db.close()
