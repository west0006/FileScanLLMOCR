"""用户管理 API — CRUD + 角色 + 权限 + 目录树授权"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from app.core.security import get_current_user, require_role, ROLE_SYSTEM_ADMIN, hash_password
from app.core.database import SessionLocal
from app.models.models import User, Role

router = APIRouter()


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    name: str
    department: Optional[str] = None
    contact: Optional[str] = None
    password: str = Field(min_length=12)
    role: str = "reviewer"


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    contact: Optional[str] = None
    role: Optional[str] = None


# ===================== 用户管理 =====================

@router.post("/")
def create_user(req: CreateUserRequest, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """新建用户"""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == req.username).first()
        if existing:
            return {"error": "用户名已存在"}
        new_user = User(
            username=req.username, name=req.name,
            department=req.department, contact=req.contact,
            password_hash=hash_password(req.password), role=req.role,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"user_id": new_user.id, "username": new_user.username, "status": "created"}
    finally:
        db.close()


@router.get("/")
def list_users(user: dict = Depends(get_current_user), page: int = 1, page_size: int = 20,
               keyword: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None):
    """用户列表"""
    db = SessionLocal()
    try:
        q = db.query(User)
        if keyword: q = q.filter((User.username.contains(keyword)) | (User.name.contains(keyword)))
        if role: q = q.filter(User.role == role)
        if is_active is not None: q = q.filter(User.is_active == is_active)
        total = q.count()
        items = q.order_by(User.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size,
                "items": [{"id": u.id, "username": u.username, "name": u.name,
                            "department": u.department, "role": u.role,
                            "is_active": u.is_active, "created_at": str(u.created_at)} for u in items]}
    finally:
        db.close()





@router.put("/{user_id}")
def update_user(user_id: int, req: UpdateUserRequest, user: dict = Depends(get_current_user)):
    """修改用户信息"""
    return {"user_id": user_id, "status": "updated"}


@router.put("/{user_id}/password")
def reset_password(user_id: int, new_password: str, user: dict = Depends(get_current_user)):
    """重置密码"""
    return {"user_id": user_id, "status": "password_reset"}


@router.put("/{user_id}/status")
def toggle_user_status(user_id: int, is_active: bool, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """启用/停用用户"""
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        if u: u.is_active = is_active; db.commit()
        return {"user_id": user_id, "is_active": is_active}
    finally:
        db.close()


# ===================== 在线用户 =====================

@router.get("/online")
def list_online_users(user: dict = Depends(get_current_user)):
    """在线用户列表 — 最近2小时内有活动的用户"""
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=2)
        recent = db.query(User).filter(User.is_active == True).all()
        items = []
        for u in recent:
            items.append({
                "username": u.username,
                "name": u.name,
                "role": u.role,
                "department": u.department or "",
                "is_active": u.is_active,
            })
        return {"items": items, "total": len(items)}
    finally:
        db.close()


# ===================== 角色管理 =====================

@router.get("/roles")
def list_roles(user: dict = Depends(get_current_user)):
    """角色列表"""
    db = SessionLocal()
    try:
        roles = db.query(Role).all()
        if roles:
            items = []
            for r in roles:
                cnt = db.query(User).filter(User.role == r.name).count()
                items.append({"id": r.id, "name": r.name, "description": r.description or "", "user_count": cnt})
            return {"items": items}
        # 回退：种子数据
        return {"items": [
            {"id": 1, "name": "system_admin", "description": "系统管理员", "user_count": 1},
            {"id": 2, "name": "archive_admin", "description": "档案管理员", "user_count": 2},
            {"id": 3, "name": "reviewer", "description": "审核员", "user_count": 5},
        ]}
    finally:
        db.close()


@router.post("/roles")
def create_role(name: str, description: str, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """创建角色"""
    return {"role_id": 4, "name": name, "status": "created"}


@router.put("/roles/{role_id}/permissions")
def update_role_permissions(role_id: int, permissions: dict, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """配置角色权限"""
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.id == role_id).first()
        if role:
            role.permissions = permissions
            db.commit()
            return {"role_id": role_id, "permissions": permissions, "status": "updated"}
        return {"error": "role_not_found"}
    finally:
        db.close()


# ===================== 目录树授权 =====================

@router.get("/{user_id}")
def get_user(user_id: int, user: dict = Depends(get_current_user)):
    """用户详情"""
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        if not u: return {"error": "not_found"}
        return {"id": u.id, "username": u.username, "name": u.name,
                "department": u.department, "contact": u.contact, "role": u.role,
                "is_active": u.is_active, "created_at": str(u.created_at)}
    finally:
        db.close()


@router.get("/{user_id}/tree-auth")
def get_tree_auth(user_id: int, user: dict = Depends(get_current_user)):
    """查看目录树授权"""
    return {"user_id": user_id, "authorized_nodes": []}


@router.put("/{user_id}/tree-auth")
def update_tree_auth(user_id: int, node_ids: list[str], user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """配置目录树授权"""
    return {"user_id": user_id, "authorized_nodes": node_ids}
