"""
结构化日志模块 — 支持请求计时、测试观察点、分级输出

用法:
  from app.core.logging import get_logger
  log = get_logger(__name__)
  log.info("search_start", keywords="招生", user="admin")
  log.obs("TEST_MARKER", status="ok", detail="search returned 5 results")
"""

import time
import json
import logging
import sys
from typing import Any

# ==================== JSON 格式化器 ====================

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "module": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        if hasattr(record, "elapsed_ms"):
            log_entry["elapsed_ms"] = record.elapsed_ms
        if hasattr(record, "obs_marker"):
            log_entry["obs"] = record.obs_marker
            log_entry["obs_data"] = getattr(record, "obs_data", {})
        return json.dumps(log_entry, ensure_ascii=False)


# ==================== Logger 包装 ====================

class ObsLogger:
    """带可观测标记的结构化 Logger"""

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._timer: dict[str, float] = {}

    # ---- 标准级别 ----
    def debug(self, msg: str, **kwargs): self._log(logging.DEBUG, msg, kwargs)
    def info(self, msg: str, **kwargs): self._log(logging.INFO, msg, kwargs)
    def warn(self, msg: str, **kwargs): self._log(logging.WARNING, msg, kwargs)
    def error(self, msg: str, **kwargs): self._log(logging.ERROR, msg, kwargs)

    # ---- 可观测标记 ----
    def obs(self, marker: str, status: str = "ok", **detail):
        """测试/调试观察标记: log.obs("REVIEW_DONE", score=85)"""
        record = self._logger.makeRecord(
            self._logger.name, logging.INFO, __file__, 0,
            f"[OBS] {marker} | {status}", (), None
        )
        record.obs_marker = marker
        record.obs_data = {"status": status, **detail}
        self._logger.handle(record)

    # ---- 请求计时 ----
    def time_start(self, label: str):
        self._timer[label] = time.time()

    def time_end(self, label: str, **extra) -> float:
        elapsed = (time.time() - self._timer.pop(label, time.time())) * 1000
        record = self._logger.makeRecord(
            self._logger.name, logging.INFO, __file__, 0,
            f"[TIMER] {label} completed", (), None
        )
        record.elapsed_ms = round(elapsed, 1)
        record.extra_data = extra
        self._logger.handle(record)
        return elapsed

    # ---- 内部 ----
    def _log(self, level: int, msg: str, extra: dict | None = None):
        record = self._logger.makeRecord(self._logger.name, level, __file__, 0, msg, (), None)
        if extra:
            record.extra_data = extra
        self._logger.handle(record)


# ==================== 初始化 ====================

_loggers: dict[str, ObsLogger] = {}

def get_logger(name: str) -> ObsLogger:
    if name not in _loggers:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False
        _loggers[name] = ObsLogger(name)
    return _loggers[name]
