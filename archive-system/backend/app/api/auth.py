"""认证 API — 登录 / 登出 / Token 刷新"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.core.database import SessionLocal
from app.models.models import User
from app.core.config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request):
    """用户登录 — 含锁定检查、密码过期检查"""
    # 设置用户名到 request.state（供中间件日志使用，失败时也能记录）
    request.state.log_username = req.username
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == req.username).first()

        if settings.APP_ENV == "development":
            # 开发模式：用户不存在则自动创建（reviewer 权限）；Token 使用实际角色，权限门禁由 require_role dev 放行
            if user is None:
                user = User(
                    username=req.username,
                    name=req.username,
                    password_hash=hash_password(req.password),
                    role="reviewer",
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            # 停用检查：dev 模式也拦截停用用户（UM-004 停用后无法登录），避免「能登录但接口全 403」的矛盾
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已停用")
            user.last_login_at = datetime.utcnow()
            db.commit()
            token = create_access_token(user_id=user.id, username=user.username, role=user.role, name=user.name)
            return LoginResponse(
                access_token=token,
                expires_in=settings.JWT_EXPIRE_MINUTES * 60,
                user={"id": user.id, "username": user.username, "role": user.role, "name": user.name},
            )

        # ====== 生产模式：完整安全检查 ======

        # 用户不存在
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

        # 账户锁定检查
        if user.locked_until and user.locked_until > datetime.utcnow():
            remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"账户已锁定，请 {remaining} 分钟后重试",
            )

        # 账户停用检查
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已停用")

        # 密码校验
        if not verify_password(req.password, user.password_hash):
            user.login_attempts = (user.login_attempts or 0) + 1
            if user.login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
                user.login_attempts = 0
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

        # 密码过期检查
        if user.password_updated_at:
            days_since = (datetime.utcnow() - user.password_updated_at).days
            if days_since > settings.PASSWORD_EXPIRE_DAYS:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"密码已过期（超过 {settings.PASSWORD_EXPIRE_DAYS} 天），请修改密码",
                )

        # 登录成功：重置计数器 + 记录登录时间
        user.login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        db.commit()

        token = create_access_token(user_id=user.id, username=user.username, role=user.role, name=user.name)
        return LoginResponse(
            access_token=token,
            expires_in=settings.JWT_EXPIRE_MINUTES * 60,
            user={"id": user.id, "username": user.username, "role": user.role, "name": user.name},
        )
    finally:
        db.close()


@router.post("/logout")
def logout(user: dict = Depends(get_current_user)):
    return {"message": "已退出登录"}


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return user


@router.get("/permissions")
def get_permissions(user: dict = Depends(get_current_user)):
    """获取当前用户的模块级权限列表（供前端菜单控制）"""
    from app.core.security import ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN
    from app.core.database import SessionLocal
    from app.models.models import Role, User as UserModel

    # 管理员拥有全部权限
    if user["role"] in (ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN):
        return {
            "role": user["role"],
            "permissions": {
                "search": True, "ocr": True, "review": True,
                "sync": True, "user": True, "log": True, "stats": True,
                "all": True,
            },
        }

    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.id == user["user_id"]).first()
        if u:
            role = db.query(Role).filter(Role.name == u.role).first()
            if role and role.permissions:
                return {"role": user["role"], "permissions": role.permissions}
        # 回退：reviewer 默认权限
        return {
            "role": user["role"],
            "permissions": {"search": True, "review": True},
        }
    finally:
        db.close()
