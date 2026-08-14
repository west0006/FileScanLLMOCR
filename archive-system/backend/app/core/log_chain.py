"""日志哈希链辅助 — 统一链计算与串行化写入

审计完整性依赖「每条日志的 chain_hash = SHA256(prev_chain_hash + content)」。
该逻辑原本在 4 处重复（API 中间件、数据同步任务、审计任务×2），且只有 API 进程
内用线程锁串行化；Celery 进程（或 eager 模式下的任务）无锁读「最新一条链哈希」
再写，并发时读到同一个 prev → 链分叉 → /log/audit/chain-verify 误报 tampered。

本模块提供唯一的写入入口 append_chain_log，用线程锁（同进程）+ 文件锁（跨进程）
串行化「读 prev → 算 hash → 写 → commit」。content 格式由 build_log_content 统一，
校验侧（api/log.py verify_chain、tasks/audit_tasks 的链校验）也必须复用该函数，
保证写入与校验永远一致。
"""

import os
import hashlib
import threading

from app.models.models import OperationLog

# 同进程线程锁：覆盖 eager 模式（任务与 API 同进程）下的并发
_chain_lock = threading.Lock()

# 跨进程文件锁路径：覆盖生产环境 Celery worker 独立进程写日志
_LOCK_PATH = os.path.join(os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp", "archive_chain.lock")


class _CrossProcessFileLock:
    """跨进程文件锁 — Windows 用 msvcrt，Unix 用 fcntl"""

    def __init__(self, path: str):
        self.path = path
        self._fh = None

    def acquire(self):
        self._fh = open(self.path, "a+")
        if os.name == "nt":
            import msvcrt
            # msvcrt.locking 要求锁定区域存在，空文件先写入 1 字节占位
            self._fh.seek(0, os.SEEK_END)
            if self._fh.tell() == 0:
                self._fh.write("0")
                self._fh.flush()
            self._fh.seek(0)
            msvcrt.locking(self._fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)

    def release(self):
        if self._fh is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._fh = None


def build_log_content(username, operation_type, module, description, target_id, result) -> str:
    """日志内容串 — 写入与校验共用的唯一格式（缺省值一律归空串，避免 None 漂移）"""
    return f"{username or ''}|{operation_type or ''}|{module or ''}|{description or ''}|{target_id or ''}|{result or ''}"


def compute_chain_hash(prev_hash: str, content: str) -> str:
    """计算本条日志的链哈希：SHA256(prev_hash + content)"""
    return hashlib.sha256(f"{prev_hash}{content}".encode("utf-8")).hexdigest()


def append_chain_log(db, **fields) -> OperationLog:
    """串行化追加一条操作日志并计算哈希链

    fields 需包含 OperationLog 的字段（不含 id/chain_hash/created_at），
    chain_hash 由本函数计算填充。返回写入的 OperationLog 对象。
    """
    with _chain_lock:
        fl = _CrossProcessFileLock(_LOCK_PATH)
        try:
            fl.acquire()
        except Exception:
            # 文件锁不可用（如只读临时目录）时退化为仅线程锁，仍保证同进程串行化
            fl = None
        try:
            prev = db.query(OperationLog).order_by(OperationLog.id.desc()).first()
            prev_hash = prev.chain_hash if prev and prev.chain_hash else "0" * 64

            content = build_log_content(
                fields.get("username"), fields.get("operation_type"),
                fields.get("module"), fields.get("description"),
                fields.get("target_id"), fields.get("result"),
            )
            fields["chain_hash"] = compute_chain_hash(prev_hash, content)

            log = OperationLog(**fields)
            db.add(log)
            db.commit()
            return log
        finally:
            if fl is not None:
                fl.release()
