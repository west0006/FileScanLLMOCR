"""数据同步异步任务 — 文件增量同步 + 数据库定期同步"""

import os
import json
import hashlib
import time
from datetime import datetime

from celery.utils.log import get_task_logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.models import SyncLog, Archive

logger = get_task_logger(__name__)

# 配置文件路径
_SYNC_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sync_config.json")


def _load_config() -> dict:
    try:
        with open(_SYNC_CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"file_sync": {}, "database_sync": {}}


def _compute_file_hash(filepath: str, sample_bytes: int = 4096) -> str:
    """快速文件哈希：前 4KB 快速比对，用于增量检测"""
    try:
        hasher = hashlib.md5()
        with open(filepath, "rb") as f:
            hasher.update(f.read(sample_bytes))
        # 小文件读全量，大文件读尾
        size = os.path.getsize(filepath)
        if size > sample_bytes * 2:
            with open(filepath, "rb") as f:
                f.seek(-sample_bytes, os.SEEK_END)
                hasher.update(f.read(sample_bytes))
        return hasher.hexdigest()
    except Exception:
        return ""


# ==================== 文件同步 ====================

def _sync_single_directory(share_path: str, mode: str) -> tuple[int, int, int, list[str]]:
    """同步单个共享目录，返回 (new_count, updated_count, failed_count, errors)"""
    ARCHIVE_EXTENSIONS = {".tiff", ".tif", ".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"}
    new_count = 0
    updated_count = 0
    failed_count = 0
    errors = []

    for root, dirs, files in os.walk(share_path):
        for filename in files:
            if not any(filename.lower().endswith(ext) for ext in ARCHIVE_EXTENSIONS):
                continue

            src_path = os.path.join(root, filename)
            rel_path = os.path.relpath(src_path, share_path)

            try:
                src_stat = os.stat(src_path)
                src_mtime = src_stat.st_mtime
                src_size = src_stat.st_size

                local_path = _local_file_path(rel_path)
                if os.path.exists(local_path):
                    local_stat = os.stat(local_path)
                    if mode == "incremental":
                        if (abs(src_mtime - local_stat.st_mtime) < 2 and
                            src_size == local_stat.st_size):
                            continue

                    src_hash = _compute_file_hash(src_path)
                    local_hash = _compute_file_hash(local_path)
                    if src_hash == local_hash:
                        continue

                    updated_count += 1
                else:
                    new_count += 1

                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(src_path, "rb") as sf, open(local_path, "wb") as df:
                    while True:
                        chunk = sf.read(1024 * 1024)
                        if not chunk:
                            break
                        df.write(chunk)

                os.utime(local_path, (src_mtime, src_mtime))

            except Exception as e:
                failed_count += 1
                errors.append(f"{rel_path}: {str(e)[:100]}")
                logger.error(f"Sync failed: {rel_path}: {e}")

    return new_count, updated_count, failed_count, errors


@celery_app.task(bind=True, max_retries=3)
def sync_files_task(self, sync_log_id: int, mode: str = "incremental"):
    """文件增量同步 — 比对时间戳+哈希，仅同步新增/变更文件"""
    db = SessionLocal()
    try:
        sync_log = db.query(SyncLog).filter(SyncLog.id == sync_log_id).first()
        if not sync_log:
            return {"error": "sync_log_not_found"}

        config = _load_config().get("file_sync", {})
        # 兼容：share_paths 列表（SY-001 多目录）与旧 share_path 单值
        share_paths = list(config.get("share_paths") or [])
        if config.get("share_path"):
            share_paths.append(config["share_path"])
        share_paths = [p for p in share_paths if p]
        if not share_paths:
            sync_log.status = "failed"
            sync_log.log_detail = "未配置共享目录"
            sync_log.finished_at = datetime.utcnow()
            db.commit()
            return {"error": "share_path_not_found", "path": ""}

        new_count = 0
        updated_count = 0
        failed_count = 0
        errors = []

        # 遍历多个共享目录
        for share_path in share_paths:
            if not os.path.isdir(share_path):
                errors.append(f"{share_path}: 目录不存在")
                failed_count += 1
                continue
            n, u, f, errs = _sync_single_directory(share_path, mode)
            new_count += n
            updated_count += u
            failed_count += f
            errors.extend(errs)

        # 更新日志
        sync_log.new_files = new_count
        sync_log.updated_files = updated_count
        sync_log.failed_count = failed_count
        sync_log.status = "completed"
        sync_log.finished_at = datetime.utcnow()
        sync_log.log_detail = json.dumps({"errors": errors[:20]}) if errors else ""
        db.commit()

        _log_sync_op(db, "file", mode, new_count, updated_count, failed_count)

        logger.info(f"File sync done: {new_count} new, {updated_count} updated, {failed_count} failed")
        return {"mode": mode, "status": "completed", "new": new_count, "updated": updated_count, "failed": failed_count}

    except Exception as exc:
        if sync_log:
            sync_log.status = "failed"
            sync_log.log_detail = str(exc)[:500]
            sync_log.finished_at = datetime.utcnow()
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


# ==================== 数据库同步 ====================

@celery_app.task(bind=True, max_retries=3)
def sync_database_task(self, sync_log_id: int, mode: str = "incremental"):
    """数据库元数据同步 — 从源库只读查询→写入本地 MySQL"""
    db = SessionLocal()
    try:
        sync_log = db.query(SyncLog).filter(SyncLog.id == sync_log_id).first()
        if not sync_log:
            return {"error": "sync_log_not_found"}

        config = _load_config().get("database_sync", {})
        if not config.get("host"):
            sync_log.status = "completed"
            sync_log.log_detail = "数据库同步未配置"
            sync_log.finished_at = datetime.utcnow()
            db.commit()
            return {"status": "skipped", "reason": "not_configured"}

        # 连接源数据库（只读）
        source_url = (
            f"mysql+pymysql://{config['username']}:{config['password']}"
            f"@{config['host']}:{config.get('port', 3306)}/{config['database']}"
            f"?charset=utf8mb4"
        )
        source_engine = create_engine(source_url, pool_size=2, pool_pre_ping=True)

        new_count = 0
        updated_count = 0
        failed_count = 0

        try:
            inspector = inspect(source_engine)
            tables = inspector.get_table_names()

            # 优先同步 archives 表（如果存在）
            target_tables = [t for t in tables if t.lower().startswith("esp_") or t.lower() in ("archives", "archive")]
            if not target_tables:
                target_tables = tables[:5]  # fallback: 前 5 张表

            SourceSession = sessionmaker(bind=source_engine)
            source_db = SourceSession()

            try:
                for table_name in target_tables:
                    try:
                        columns = [c["name"] for c in inspector.get_columns(table_name)]

                        # 构建查询
                        query = f"SELECT * FROM `{table_name}`"
                        increment_field = config.get("increment_field", "updated_at")
                        field_mapping = config.get("field_mapping", {})

                        if mode == "incremental":
                            # 查上次同步时间
                            last_sync = db.query(SyncLog).filter(
                                SyncLog.sync_type == "database",
                                SyncLog.status == "completed",
                            ).order_by(SyncLog.started_at.desc()).first()

                            if last_sync and last_sync.started_at:
                                # 用原生 SQL 加时间过滤
                                query += f" WHERE `{increment_field}` > :last_sync"
                                rows = source_db.execute(
                                    text(query),
                                    {"last_sync": last_sync.started_at.strftime("%Y-%m-%d %H:%M:%S")},
                                ).fetchall()
                            else:
                                rows = source_db.execute(text(query)).fetchall()
                        else:
                            rows = source_db.execute(text(query)).fetchall()

                        for row in rows:
                            row_dict = dict(row._mapping)
                            # 应用字段映射
                            mapped = {}
                            for src_field, local_field in (field_mapping.items() or {}):
                                if src_field in row_dict:
                                    mapped[local_field] = row_dict[src_field]

                            # 尝试写入本地 Archive 表
                            if mapped:
                                _upsert_archive(db, mapped)

                        new_count += len(rows)

                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Sync table {table_name} failed: {e}")

            finally:
                source_db.close()

        finally:
            source_engine.dispose()

        sync_log.new_records = new_count
        sync_log.updated_records = updated_count
        sync_log.failed_count = failed_count
        sync_log.status = "completed"
        sync_log.finished_at = datetime.utcnow()
        db.commit()

        _log_sync_op(db, "database", mode, new_count, 0, failed_count)

        logger.info(f"DB sync done: {new_count} records synced")
        return {"mode": mode, "status": "completed", "synced": new_count, "failed": failed_count}

    except Exception as exc:
        if sync_log:
            sync_log.status = "failed"
            sync_log.log_detail = str(exc)[:500]
            sync_log.finished_at = datetime.utcnow()
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


# ==================== 辅助函数 ====================

def _local_file_path(rel_path: str) -> str:
    """计算本地存储路径"""
    from app.core.config import settings
    return os.path.join(settings.SYNC_DATA_DIR, rel_path)


def _upsert_archive(db, data: dict):
    """插入或更新 Archive 记录"""
    from app.models.models import Archive

    archive_id = data.get("archive_id") or data.get("档案编号") or data.get("id")
    if not archive_id:
        return

    existing = db.query(Archive).filter(Archive.archive_id == str(archive_id)).first()
    if existing:
        for key_map in [("title", "题名"), ("author", "责任者"), ("file_code", "文件编号"),
                        ("subject", "主题词"), ("year", "归档年度"), ("category", "门类"),
                        ("department", "归口单位"), ("fonds_id", "全宗号"),
                        ("retention_period", "保管期限"), ("security_level", "密级")]:
            model_attr, data_key = key_map
            val = data.get(data_key) or data.get(model_attr)
            if val is not None and hasattr(existing, model_attr):
                setattr(existing, model_attr, val)
        existing.updated_at = datetime.utcnow()
    else:
        new_archive = Archive(
            archive_id=str(archive_id),
            title=data.get("title") or data.get("题名") or "",
            author=data.get("author") or data.get("责任者") or "",
            file_code=data.get("file_code") or data.get("文件编号") or "",
            subject=data.get("subject") or data.get("主题词") or "",
            year=data.get("year") or data.get("归档年度"),
            category=data.get("category") or data.get("门类") or "",
            department=data.get("department") or data.get("归口单位") or "",
            fonds_id=data.get("fonds_id") or data.get("全宗号") or "",
            retention_period=data.get("retention_period") or data.get("保管期限") or "",
            security_level=data.get("security_level") or data.get("密级") or "",
        )
        db.add(new_archive)

    db.commit()


def _log_sync_op(db, sync_type: str, mode: str, new_count: int, updated_count: int, failed_count: int):
    """写入操作日志 — 以"系统"用户记录同步操作，含哈希链"""
    from app.core.log_chain import append_chain_log
    try:
        type_label = '文件同步' if sync_type == 'file' else '数据库同步'
        desc = f'{type_label}（{"增量" if mode == "incremental" else "全量"}）完成：新增{new_count}，更新{updated_count}'
        if failed_count: desc += f'，失败{failed_count}'

        append_chain_log(
            db,
            user_id=0, username='系统', operation_type='sync', module='sync',
            description=desc, result='success' if failed_count == 0 else 'failure',
        )
    except Exception as e:
        logger.warning(f"同步操作日志写入失败: {e}")
