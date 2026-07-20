"""认证与安全 — JWT 生成/验证 + 密码哈希 + RBAC 依赖"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

# ===================== 密码哈希 =====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # bcrypt 限制 72 字节，截断超长密码
    pwd = password[:72] if len(password.encode()) > 72 else password
    return pwd_context.hash(pwd)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ===================== JWT =====================
security_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: int, username: str, role: str, name: str = "") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "name": name or username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


# ===================== 当前用户依赖 =====================
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """从 JWT Token 中解析当前用户"""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或已过期")

    return {
        "user_id": int(payload["sub"]),
        "username": payload["username"],
        "name": payload.get("name", payload["username"]),
        "role": payload["role"],
    }


# ===================== 角色权限检查 =====================
def require_role(*allowed_roles: str):
    """依赖工厂：检查当前用户角色"""

    async def checker(user: dict = Depends(get_current_user)):
        if user["role"] in allowed_roles:
            return user
        # dev 模式：放行但记录警告，不持久化提权
        if settings.APP_ENV == "development":
            import logging
            logger = logging.getLogger("security")
            logger.warning(
                f"[DEV] 权限放行: user={user['username']} role={user['role']} "
                f"需要 {allowed_roles} — 生产环境将拒绝"
            )
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足 (需要: {', '.join(allowed_roles)}, 当前: {user['role']})",
        )

    return checker


# 预设角色常量
ROLE_SYSTEM_ADMIN = "system_admin"
ROLE_ARCHIVE_ADMIN = "archive_admin"
ROLE_REVIEWER = "reviewer"


# ===================== 数据权限过滤 =====================

def apply_data_scope(user: dict, query, model):
    """
    对查询应用数据权限过滤。

    - system_admin / archive_admin: 全量（不过滤）
    - reviewer: 按 tree_auth 中的门类/部门过滤
    - 无 tree_auth: 只能看自己部门的档案
    """
    if user["role"] in (ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN):
        return query

    from app.core.database import SessionLocal
    from app.models.models import User as UserModel

    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.id == user["user_id"]).first()
        if not u:
            return query.filter(False)  # 用户不存在，返回空

        tree_auth = u.tree_auth or []

        # 从 tree_auth 提取允许的门类和部门
        allowed_categories = set()
        allowed_departments = set()

        for node in tree_auth:
            if "/" in node:
                cat, dept = node.split("/", 1)
                allowed_categories.add(cat)
                allowed_departments.add(dept)
            else:
                allowed_categories.add(node)

        if not allowed_categories and not allowed_departments:
            # 无授权: 只能看自己部门的
            if u.department:
                return query.filter(model.department == u.department)
            return query.filter(False)  # 完全没有部门信息

        # 构建过滤
        from sqlalchemy import or_
        conditions = []
        if allowed_categories:
            conditions.append(model.category.in_(allowed_categories))
        if allowed_departments:
            conditions.append(model.department.in_(allowed_departments))

        if conditions:
            return query.filter(or_(*conditions))

        return query
    finally:
        db.close()
