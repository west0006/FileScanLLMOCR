"""数据同步 API — 配置 + 执行 + 监控 + 历史"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.security import get_current_user

router = APIRouter()


class FileSyncConfigRequest(BaseModel):
    share_path: str
    sync_frequency: str = "daily"   # daily/weekly/monthly
    sync_mode: str = "incremental"  # full/incremental
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
    """配置文件同步"""
    return {"status": "saved", "config": req.model_dump()}


@router.post("/config/database")
def set_database_sync_config(req: DatabaseSyncConfigRequest, user: dict = Depends(get_current_user)):
    """配置数据库同步"""
    return {"status": "saved", "config": req.model_dump()}


@router.get("/config")
def get_sync_configs(user: dict = Depends(get_current_user)):
    """查看同步配置"""
    return {"file_sync": {}, "database_sync": {}}


@router.post("/trigger/file")
def trigger_file_sync(
    mode: str = "incremental",
    user: dict = Depends(get_current_user),
):
    """手动触发文件同步"""
    return {"sync_id": 1, "type": "file", "mode": mode, "status": "started"}


@router.post("/trigger/database")
def trigger_database_sync(
    mode: str = "incremental",
    user: dict = Depends(get_current_user),
):
    """手动触发数据库同步"""
    return {"sync_id": 2, "type": "database", "mode": mode, "status": "started"}


@router.get("/progress/{sync_id}")
def get_sync_progress(sync_id: int, user: dict = Depends(get_current_user)):
    """同步进度"""
    return {
        "sync_id": sync_id,
        "status": "running",
        "synced_files": 0,
        "total_files": 0,
        "synced_records": 0,
        "speed": "0 MB/s",
    }


@router.get("/history")
def sync_history(
    user: dict = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
    sync_type: Optional[str] = None,
):
    """同步历史记录"""
    return {"total": 0, "page": page, "page_size": page_size, "items": []}
