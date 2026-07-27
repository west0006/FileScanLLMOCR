"""
操作日志中间件 — 自动记录 API 操作

记录规则：
- POST/PUT/DELETE: 记录为功能操作（operation_type = 具体操作类型）
- GET: 记录为功能访问（operation_type = view，模块为具体页面名）
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

# 需要记录的 GET 路径 → (操作类型, 中文描述)
_GET_PAGE_MAP = {
    "/api/search/": ("view", "查看检索页面"),
    "/api/search/history": ("view", "查看检索历史"),
    "/api/log/": ("view", "查看操作日志"),
    "/api/stats/": ("view", "查看查询统计"),
    "/api/ocr/": ("view", "查看OCR任务"),
    "/api/review/": ("view", "查看预审记录"),
    "/api/review/tasks": ("view", "查看预审任务"),
    "/api/sync/": ("view", "查看数据同步"),
    "/api/user/": ("view", "查看用户管理"),
    "/api/user/online": ("view", "查看在线用户"),
    "/api/user/roles": ("view", "查看角色权限"),
}

# POST/PUT/DELETE 模块 → (操作类型, 操作名称)
_OP_DETAIL_MAP = {
    "auth": {"login": ("login", "用户登录"), "logout": ("logout", "用户登出")},
    "search": {"default": ("search", "检索操作")},
    "ocr": {"default": ("ocr", "OCR操作")},
    "review": {"default": ("review", "预审操作")},
    "sync": {"default": ("sync", "数据同步操作")},
    "user": {"default": ("admin", "用户管理操作")},
    "log": {"default": ("admin", "日志管理操作")},
    "stats": {"default": ("admin", "统计查询操作")},
}


def _write_log_sync(
    user_id: int, username: str, op_type: str, module: str,
    description: str, target_id: str, ip: str, result: str,
    user_agent: str = "",
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
            user_agent=user_agent,
        )
        db.add(log)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def _extract_target_id(path: str, request) -> str:
    """从 URL 路径提取操作对象 ID"""
    custom = getattr(request.state, "log_target_id", None)
    if custom: return str(custom)
    import re
    for pat in [r"/archives/([^/]+)", r"/tasks/(\d+)", r"/user/(\d+)", r"/records/(\d+)", r"/sync/progress/(\d+)"]:
        m = re.search(pat, path)
        if m: return m.group(1)
    return ""


class OperationLogMiddleware(BaseHTTPMiddleware):
    """操作日志中间件"""

    async def dispatch(self, request: Request, call_next) -> Response:
        t0 = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - t0) * 1000)

        method = request.method
        path = request.url.path

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

        op_type = "other"
        module = "other"
        description = ""

        if method == "GET":
            # GET 请求 → 功能访问
            for prefix, (ot, desc) in _GET_PAGE_MAP.items():
                if path.startswith(prefix):
                    op_type = ot
                    module = prefix.strip("/").replace("api/", "").replace("/", "")
                    description = desc
                    break
            else:
                return response  # 不记录

        elif method in ("POST", "PUT", "DELETE"):
            # 写操作 → 功能操作
            op_tag = path.split("/")[2] if len(path.split("/")) > 2 else "other"

            # 登录端点：从 request.state 获取用户名（由 auth endpoint 设置）
            login_user = getattr(request.state, "log_username", None)
            if login_user:
                username = login_user
                user_name = login_user

            if op_tag in _OP_DETAIL_MAP:
                detail = _OP_DETAIL_MAP[op_tag]
                if op_tag == "auth":
                    op_type, description = detail.get("logout" if path.endswith("/logout") else "login", detail.get("login", ("login", "用户登录")))
                else:
                    op_type, description = detail["default"]
                module = op_tag
            else:
                op_type = op_tag
                module = op_tag
                description = f"{method} {path}"

            # 路由自定义描述优先
            custom_desc = getattr(request.state, "log_description", None)
            if custom_desc:
                description = custom_desc
        else:
            return response

        result = "success" if response.status_code < 400 else "failure"

        # 登录失败时标注失败原因
        if path.endswith("/login") and result == "failure":
            if response.status_code == 423:
                description = "用户登录 — 账户已锁定"
            elif response.status_code == 403:
                description = "用户登录 — 密码已过期"
            else:
                description = "用户登录 — 密码错误"
        elif path.endswith("/login"):
            description = "用户登录"

        # 补充用户姓名
        if user_name and user_name != username:
            description = f"[{user_name}] {description}"

        # 耗时标注
        if duration_ms > 500:
            description += f" (耗时{duration_ms}ms)"

        # 提取操作对象 ID（target_id）
        target_id = _extract_target_id(path, request)

        # 慢请求+失败观测
        if duration_ms > 1000:
            _mw_log.obs("SLOW_REQUEST", path=path, method=method, ms=duration_ms)
        if response.status_code >= 400:
            _mw_log.obs("REQUEST_FAILED", path=path, method=method, status=response.status_code, ms=duration_ms)

        # 异步写日志
        ip = request.client.host if request.client else ""
        user_agent = request.headers.get("User-Agent", "")[:300]
        threading.Thread(
            target=_write_log_sync,
            args=(user_id, username, op_type, module, description, target_id, ip, result, user_agent),
            daemon=True,
        ).start()

        return response
