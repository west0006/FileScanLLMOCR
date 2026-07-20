"""
操作日志中间件 — 自动记录 API 操作

记录规则：
- 所有 POST/PUT/DELETE 操作自动记录
- GET 请求仅记录 search/export/download 类
- 日志异步写入，不阻塞请求
"""

import time
import threading
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.database import SessionLocal
from app.models.models import OperationLog
from app.core.logging import get_logger

_mw_log = get_logger("middleware")

# 需要记录的 GET 操作前缀
_LOG_GET_PREFIXES = ("/api/search/", "/api/log/", "/api/stats/")

# 操作类型映射
_OP_MAP = {
    "login": "login", "logout": "logout",
    "search": "search", "export": "export",
    "ocr": "ocr", "review": "review",
    "user": "admin", "sync": "admin", "log": "admin", "stats": "admin",
    "auth": "login",
}


def _write_log_sync(
    user_id: int, username: str, op_type: str, module: str,
    description: str, target_id: str, ip: str, result: str,
):
    """同步写日志（在独立线程中执行）"""
    db = SessionLocal()
    try:
        log = OperationLog(
            user_id=user_id,
            username=username,
            operation_type=op_type,
            module=module,
            description=description,
            target_id=target_id,
            ip_address=ip,
            result=result,
        )
        db.add(log)
        db.commit()
    except Exception:
        pass  # 日志写入失败不影响业务
    finally:
        db.close()


class OperationLogMiddleware(BaseHTTPMiddleware):
    """操作日志中间件"""

    async def dispatch(self, request: Request, call_next) -> Response:
        t0 = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - t0) * 1000)

        # 确定是否需要记录
        method = request.method
        path = request.url.path

        if method == "GET":
            if not any(path.startswith(p) for p in _LOG_GET_PREFIXES):
                return response
            op_tag = "search" if "/search/" in path else "log"
        elif method in ("POST", "PUT", "DELETE"):
            op_tag = path.split("/")[2] if len(path.split("/")) > 2 else "other"
        else:
            return response

        # 提取用户信息
        user_id = 0
        username = "anonymous"
        user_name = ""
        try:
            token = request.headers.get("Authorization", "")
            if token.startswith("Bearer "):
                from app.core.security import decode_access_token
                payload = decode_access_token(token[7:])
                if payload:
                    user_id = int(payload.get("sub", 0))
                    username = payload.get("username", "anonymous")
                    user_name = payload.get("name", username)
        except Exception:
            pass

        op_type = _OP_MAP.get(op_tag, op_tag)

        # 修正 auth 路径下的 logout 被映射为 login
        if path.endswith("/logout"):
            op_type = "logout"
        result = "success" if response.status_code < 400 else "failure"

        # 优先使用路由设置的自定义描述（通过 request.state）
        custom_desc = getattr(request.state, "log_description", None)
        if custom_desc:
            description = custom_desc
        elif method == "POST" and "/api/search/" in path:
            description = f"检索操作 (耗时 {duration_ms}ms)"
        else:
            description = f"{method} {path}"

        # 慢请求观测
        if duration_ms > 1000:
            _mw_log.obs("SLOW_REQUEST", path=path, method=method, ms=duration_ms)

        # 失败观测
        if response.status_code >= 400:
            _mw_log.obs("REQUEST_FAILED", path=path, method=method, status=response.status_code, ms=duration_ms)

        # 异步写日志
        ip = request.client.host if request.client else ""
        # 未提供自定义描述时，补充用户姓名
        if not custom_desc and user_name:
            description = f"[{user_name}] {description}"
        threading.Thread(
            target=_write_log_sync,
            args=(user_id, username, op_type, op_tag, description, "", ip, result),
            daemon=True,
        ).start()

        return response
