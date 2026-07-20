"""数据同步 API — 配置 + 执行 + 监控 + 历史"""

import json
import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.security import get_current_user
from app.core.database import SessionLocal
from app.models.models import SyncLog

router = APIRouter()

_SYNC_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sync_config.json")


def _load_config() -> dict:
    try:
        with open(_SYNC_CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"file_sync": {}, "database_sync": {}}


def _save_config(config: dict):
    with open(_SYNC_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


class FileSyncConfigRequest(BaseModel):
    share_path: str
    sync_frequency: str = "daily"
    sync_mode: str = "incremental"
    sync_window_start: str = "02:00"
    sync_window_end: str = "06:00"


class DatabaseSyncConfigRequest(BaseModel):
    db_type: str = "mysql"
    host: str
    port: int = 3306
    database: str
    username: str
    password: str
    sync_frequency: str = "daily"
    field_mapping: dict = {}
    increment_field: str = "updated_at"


@router.post("/config/file")
def set_file_sync_config(req: FileSyncConfigRequest, user: dict = Depends(get_current_user)):
    """配置文件同步 — 持久化到 JSON"""
    cfg = _load_config()
    cfg["file_sync"] = req.model_dump()
    _save_config(cfg)
    return {"status": "saved", "config": cfg["file_sync"]}


@router.post("/config/database")
def set_database_sync_config(req: DatabaseSyncConfigRequest, user: dict = Depends(get_current_user)):
    """配置数据库同步 — 持久化到 JSON"""
    cfg = _load_config()
    cfg["database_sync"] = req.model_dump()
    _save_config(cfg)
    return {"status": "saved", "config": cfg["database_sync"]}


@router.get("/config")
def get_sync_configs(user: dict = Depends(get_current_user)):
    """查看同步配置"""
    return _load_config()


@router.post("/trigger/file")
def trigger_file_sync(mode: str = "incremental", user: dict = Depends(get_current_user)):
    """手动触发文件同步"""
    db = SessionLocal()
    try:
        log = SyncLog(sync_type="file", sync_mode=mode, status="running")
        db.add(log); db.commit(); db.refresh(log)
        try:
            from app.tasks.sync_tasks import sync_files_task
            sync_files_task.delay(mode)
        except Exception: log.status = "queued"; db.commit()
        return {"sync_id": log.id, "type": "file", "mode": mode, "status": log.status}
    finally: db.close()


@router.post("/trigger/database")
def trigger_database_sync(mode: str = "incremental", user: dict = Depends(get_current_user)):
    """手动触发数据库同步"""
    db = SessionLocal()
    try:
        log = SyncLog(sync_type="database", sync_mode=mode, status="running")
        db.add(log); db.commit(); db.refresh(log)
        try:
            from app.tasks.sync_tasks import sync_database_task
            sync_database_task.delay(mode)
        except Exception: log.status = "queued"; db.commit()
        return {"sync_id": log.id, "type": "database", "mode": mode, "status": log.status}
    finally: db.close()


@router.get("/progress/{sync_id}")
def get_sync_progress(sync_id: int, user: dict = Depends(get_current_user)):
    """同步进度"""
    db = SessionLocal()
    try:
        log = db.query(SyncLog).filter(SyncLog.id == sync_id).first()
        if log: return {"sync_id": sync_id, "status": log.status, "synced_files": log.new_files, "total_files": 0}
        return {"sync_id": sync_id, "status": "not_found"}
    finally: db.close()


@router.get("/history")
def sync_history(user: dict = Depends(get_current_user), page: int = 1, page_size: int = 20, sync_type: Optional[str] = None):
    """同步历史记录"""
    db = SessionLocal()
    try:
        q = db.query(SyncLog)
        if sync_type: q = q.filter(SyncLog.sync_type == sync_type)
        total = q.count()
        items = q.order_by(SyncLog.started_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size,
                "items": [{"id": s.id, "sync_type": s.sync_type, "sync_mode": s.sync_mode,
                            "new_files": s.new_files, "updated_files": s.updated_files,
                            "status": s.status, "started_at": str(s.started_at)} for s in items]}
    finally: db.close()
