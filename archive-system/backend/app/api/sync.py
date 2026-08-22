"""数据同步 API — 配置 + 执行 + 监控 + 历史"""

import json
import os
import re
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import FileResponse

from app.core.security import get_current_user, require_role, ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN, apply_data_scope
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.models import SyncLog, Archive

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
    share_paths: list[str] = []
    share_path: str = ""  # 向后兼容：旧单值配置
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
def set_file_sync_config(req: FileSyncConfigRequest, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """配置文件同步 — 持久化到 JSON（share_paths 多目录，兼容旧 share_path）"""
    cfg = _load_config()
    data = req.model_dump()
    # 归一化：兼容旧 share_path 单值，统一为 share_paths 列表
    paths = list(data.get("share_paths") or [])
    if data.get("share_path") and data["share_path"] not in paths:
        paths.append(data["share_path"])
    data["share_paths"] = [p for p in paths if p]
    data.pop("share_path", None)
    cfg["file_sync"] = data
    _save_config(cfg)
    return {"status": "saved", "config": cfg["file_sync"]}


@router.post("/config/database")
def set_database_sync_config(req: DatabaseSyncConfigRequest, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """配置数据库同步 — 持久化到 JSON"""
    cfg = _load_config()
    cfg["database_sync"] = req.model_dump()
    _save_config(cfg)
    return {"status": "saved", "config": cfg["database_sync"]}


@router.get("/config")
def get_sync_configs(user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """查看同步配置（数据库密码脱敏，避免明文回传）"""
    cfg = _load_config()
    db_cfg = cfg.get("database_sync")
    if isinstance(db_cfg, dict) and db_cfg.get("password"):
        db_cfg["password"] = "******"
    return cfg


@router.post("/trigger/file")
def trigger_file_sync(mode: str = "incremental", user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """手动触发文件同步"""
    db = SessionLocal()
    try:
        log = SyncLog(sync_type="file", sync_mode=mode, status="pending")
        db.add(log); db.commit(); db.refresh(log)
        try:
            from app.tasks.sync_tasks import sync_files_task
            sync_files_task.delay(log.id, mode)
        except Exception:
            log.status = "queued"; db.commit()
        return {"sync_id": log.id, "type": "file", "mode": mode, "status": log.status}
    finally:
        db.close()


@router.post("/trigger/database")
def trigger_database_sync(mode: str = "incremental", user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """手动触发数据库同步"""
    db = SessionLocal()
    try:
        log = SyncLog(sync_type="database", sync_mode=mode, status="pending")
        db.add(log); db.commit(); db.refresh(log)
        try:
            from app.tasks.sync_tasks import sync_database_task
            sync_database_task.delay(log.id, mode)
        except Exception:
            log.status = "queued"; db.commit()
        return {"sync_id": log.id, "type": "database", "mode": mode, "status": log.status}
    finally:
        db.close()


@router.get("/progress/{sync_id}")
def get_sync_progress(sync_id: int, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """同步进度"""
    db = SessionLocal()
    try:
        log = db.query(SyncLog).filter(SyncLog.id == sync_id).first()
        if log: return {"sync_id": sync_id, "status": log.status, "synced_files": log.new_files, "total_files": 0}
        return {"sync_id": sync_id, "status": "not_found"}
    finally: db.close()


@router.get("/history")
def sync_history(user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN)), page: int = 1, page_size: int = 20, sync_type: Optional[str] = None):
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
    finally:
        db.close()


# ===================== 文件转码与静态服务 =====================

_CACHE_DIR = os.path.join(os.path.dirname(settings.SYNC_DATA_DIR), ".transcode_cache")


@router.get("/files/{file_path:path}")
def serve_sync_file(file_path: str, user: dict = Depends(get_current_user)):
    """
    提供同步目录中的文件访问。

    支持格式：
    - PNG/JPEG/GIF → 直接返回
    - TIFF/TIF → 转码为 PNG 后返回（结果缓存）
    - PDF → 暂不支持，返回提示
    """
    sync_root = os.path.normpath(settings.SYNC_DATA_DIR)
    real_root = os.path.realpath(sync_root)
    full_path = os.path.normpath(os.path.join(sync_root, file_path))
    real_path = os.path.realpath(full_path)

    # 安全检查：
    # 1. 词法路径必须在 SYNC_DATA_DIR 内（等值或子路径，防 /app/sync_data_evil 前缀绕过）
    # 2. 真实路径（跟随符号链接）也不能逃出目录，防链接指向目录外文件
    if (full_path != sync_root and not full_path.startswith(sync_root + os.sep)) or \
       (real_path != real_root and not real_path.startswith(real_root + os.sep)):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"error": "forbidden"})

    # 数据范围校验：非管理员仅可访问其数据权限范围内的档案原文
    if user["role"] not in (ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN):
        _m = re.search(r'\d{4}-[A-Z]{2,3}-\d{3}', os.path.basename(full_path))
        if not _m:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content={"error": "forbidden"})
        _db = SessionLocal()
        try:
            _scoped = apply_data_scope(user, _db.query(Archive), Archive)
            if not _scoped.filter(Archive.archive_id == _m.group(0)).first():
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=403, content={"error": "forbidden"})
        finally:
            _db.close()

    if not os.path.isfile(full_path):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "file_not_found", "path": file_path})

    ext = os.path.splitext(full_path)[1].lower()

    # 图片格式直接返回
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
        media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                       ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}
        return FileResponse(full_path, media_type=media_types.get(ext, "application/octet-stream"))

    # TIFF 转码
    if ext in (".tiff", ".tif"):
        return _transcode_tiff(full_path, file_path)

    # PDF — 浏览器原生渲染（Chrome/Firefox/Edge 内置 PDF viewer），前端 iframe 加载
    if ext == ".pdf":
        return FileResponse(full_path, media_type="application/pdf")

    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=415, content={"error": "unsupported_format", "ext": ext})


def _transcode_tiff(full_path: str, rel_path: str):
    """TIFF → PNG 转码，结果缓存到 .transcode_cache/"""
    from fastapi.responses import FileResponse, JSONResponse

    src_mtime = os.path.getmtime(full_path)
    cache_key = rel_path.replace("/", "_").replace("\\", "_")
    cache_path = os.path.join(_CACHE_DIR, f"{cache_key}_{int(src_mtime)}.png")

    # 命中缓存
    if os.path.isfile(cache_path):
        return FileResponse(cache_path, media_type="image/png")

    try:
        from PIL import Image

        # 清理旧版本缓存
        if os.path.exists(_CACHE_DIR):
            for f in os.listdir(_CACHE_DIR):
                if f.startswith(cache_key) and not f.endswith(f"_{int(src_mtime)}.png"):
                    try:
                        os.remove(os.path.join(_CACHE_DIR, f))
                    except OSError:
                        pass

        os.makedirs(_CACHE_DIR, exist_ok=True)

        with Image.open(full_path) as img:
            w, h = img.size
            max_w = 2000
            if w > max_w:
                ratio = max_w / w
                img = img.resize((max_w, int(h * ratio)), Image.LANCZOS)

            # 统一到 RGB
            if img.mode in ("CMYK", "LA"):
                img = img.convert("RGB")
            elif img.mode == "P":
                img = img.convert("RGBA")
            elif img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            img.save(cache_path, "PNG", optimize=True)

        return FileResponse(cache_path, media_type="image/png")

    except ImportError:
        return JSONResponse(status_code=500, content={
            "error": "pillow_not_installed",
            "hint": "pip install Pillow",
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": "transcode_failed",
            "detail": str(e)[:200],
        })
