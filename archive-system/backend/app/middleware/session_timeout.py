"""
会话闲置超时中间件

追踪每个 JWT Token 的最后活动时间，闲置超过 SESSION_IDLE_TIMEOUT
分钟则返回 401，要求用户重新登录。

生产环境建议用 Redis 替代内存字典以支持多进程部署。
"""

import time
import threading
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

_log = get_logger("session_timeout")

# 内存存储: token_hash → last_activity_timestamp
# 定期清理过期条目
_session_store: dict[str, float] = {}
_cleanup_lock = threading.Lock()


def _token_key(token: str) -> str:
    """对 token 做哈希，避免在内存中存储原始 token"""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def _cleanup_expired():
    """清理超过 2 倍超时时间的过期条目"""
    with _cleanup_lock:
        cutoff = time.time() - settings.SESSION_IDLE_TIMEOUT * 60 * 2
        expired = [k for k, v in _session_store.items() if v < cutoff]
        for k in expired:
            del _session_store[k]


class SessionTimeoutMiddleware(BaseHTTPMiddleware):
    """
    检查会话闲置时间，超时返回 401。

    排除路径：
    - /api/auth/login  (登录请求)
    - /api/health      (健康检查)
    - /docs, /redoc, /openapi.json (API 文档)
    """

    EXCLUDE_PREFIXES = (
        "/api/auth/login",
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # 跳过不需要检查的路径
        if any(path.startswith(p) for p in self.EXCLUDE_PREFIXES):
            return await call_next(request)

        # 提取 Token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            key = _token_key(token)

            now = time.time()
            idle_sec = settings.SESSION_IDLE_TIMEOUT * 60

            # 检查闲置时间
            if key in _session_store:
                last_activity = _session_store[key]
                if now - last_activity > idle_sec:
                    del _session_store[key]
                    _log.warn(f"会话闲置超时: {request.url.path}")
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error": "session_timeout",
                            "detail": f"会话闲置超过 {settings.SESSION_IDLE_TIMEOUT} 分钟，请重新登录",
                        },
                    )

            # 更新最后活动时间
            _session_store[key] = now

            # 定期清理（每 100 次请求触发一次）
            if len(_session_store) % 100 == 0:
                try:
                    _cleanup_expired()
                except Exception:
                    pass

        return await call_next(request)
