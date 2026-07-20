"""认证 API — 登录 / 登出 / Token 刷新"""

from fastapi import APIRouter, Depends, HTTPException, status
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
def login(req: LoginRequest):
    """用户登录 — 含锁定检查、密码过期检查"""
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
            token = create_access_token(user_id=user.id, username=user.username, role=user.role, name=user.name)
            return LoginResponse(
                access_token=token,
                expires_in=settings.JWT_EXPIRE_MINUTES * 60,
                user={"id": user.id, "username": user.username, "role": user.role, "name": user.name},
            )

        # ====== 生产模式：完整安全检查 ======

        from datetime import datetime, timezone, timedelta

        # 用户不存在
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

        # 账户锁定检查
        if user.locked_until and user.locked_until > datetime.now():
            remaining = int((user.locked_until - datetime.now()).total_seconds() / 60)
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
                user.locked_until = datetime.now() + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
                user.login_attempts = 0
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

        # 密码过期检查
        if user.password_updated_at:
            days_since = (datetime.now() - user.password_updated_at).days
            if days_since > settings.PASSWORD_EXPIRE_DAYS:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"密码已过期（超过 {settings.PASSWORD_EXPIRE_DAYS} 天），请修改密码",
                )

        # 登录成功：重置计数器
        user.login_attempts = 0
        user.locked_until = None
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
