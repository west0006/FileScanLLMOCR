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
    """用户登录"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == req.username).first()

        if settings.APP_ENV == "development":
            # 开发模式：用户不存在则自动创建；不校验密码
            if user is None:
                user = User(
                    username=req.username,
                    name=req.username,
                    password_hash=hash_password(req.password),
                    role="reviewer",  # 默认最低权限
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            token = create_access_token(user_id=user.id, username=user.username, role=user.role)
            return LoginResponse(
                access_token=token,
                expires_in=settings.JWT_EXPIRE_MINUTES * 60,
                user={"id": user.id, "username": user.username, "role": user.role, "name": user.name},
            )

        # 生产模式：严格校验
        if user is None or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已停用")

        token = create_access_token(user_id=user.id, username=user.username, role=user.role)
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
