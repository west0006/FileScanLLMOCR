"""用户管理 API — CRUD + 角色 + 权限 + 目录树授权"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional

from app.core.security import get_current_user, require_role, ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN, hash_password, verify_password
from app.core.database import SessionLocal
from app.models.models import User, Role

router = APIRouter()

# 系统预设角色（不可删除，前端据此置灰删除按钮）。清单 UM-006：系统管理员、档案馆员。
# reviewer（审核员）为业务自定义角色，可删除（有关联用户时 delete_role 兜底拦截）。
_BUILTIN_ROLES = {"system_admin", "archive_admin"}


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
def create_user(req: CreateUserRequest, request: Request, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
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
        request.state.log_target_id = new_user.username
        return {"user_id": new_user.id, "username": new_user.username, "status": "created"}
    finally:
        db.close()


@router.get("/")
def list_users(user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN)), page: int = 1, page_size: int = 20,
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
                            "is_active": u.is_active,
                            "last_login_at": str(u.last_login_at) if u.last_login_at else None,
                            "created_at": str(u.created_at)} for u in items]}
    finally:
        db.close()





@router.put("/{user_id}")
def update_user(user_id: int, req: UpdateUserRequest, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """修改用户信息"""
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        if not u: return {"error": "not_found"}
        if req.name is not None: u.name = req.name
        if req.department is not None: u.department = req.department
        if req.contact is not None: u.contact = req.contact
        if req.role is not None: u.role = req.role
        db.commit()
        return {"user_id": user_id, "status": "updated"}
    finally:
        db.close()


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.put("/me/password")
def change_my_password(req: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    """用户自助修改密码（校验原密码 + 12 位四类复杂度，UM-003）

    注意：必须注册在 /{user_id}/password 之前，否则 /me/password 会被动态路由遮蔽。
    """
    err = _password_complexity_error(req.new_password)
    if err:
        return {"error": err}
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user["user_id"]).first()
        if not u:
            return {"error": "用户不存在"}
        # 校验原密码（开发模式自动创建的用户密码即登录密码）
        if not verify_password(req.old_password, u.password_hash):
            return {"error": "原密码错误"}
        from datetime import datetime
        u.password_hash = hash_password(req.new_password)
        u.password_updated_at = datetime.utcnow()
        db.commit()
        return {"status": "password_changed"}
    finally:
        db.close()


@router.put("/{user_id}/password")
def reset_password(user_id: int, new_password: str, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """重置密码"""
    err = _password_complexity_error(new_password)
    if err:
        return {"error": err}
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        if not u: return {"error": "not_found"}
        from datetime import datetime
        u.password_hash = hash_password(new_password)
        u.password_updated_at = datetime.utcnow()
        db.commit()
        return {"user_id": user_id, "status": "password_reset"}
    finally:
        db.close()


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


class BatchStatusRequest(BaseModel):
    user_ids: list[int]
    is_active: bool


@router.post("/batch-status")
def batch_toggle_status(req: BatchStatusRequest, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """批量启用/停用用户（UM-004，排除当前管理员自身）"""
    db = SessionLocal()
    try:
        ids = [i for i in req.user_ids if i != user["user_id"]]
        if not ids:
            return {"error": "无有效用户"}
        db.query(User).filter(User.id.in_(ids)).update(
            {User.is_active: req.is_active}, synchronize_session=False)
        db.commit()
        return {"status": "updated", "count": len(ids)}
    finally:
        db.close()


# ===================== 在线用户 =====================

@router.get("/online")
def list_online_users(user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN, ROLE_ARCHIVE_ADMIN))):
    """在线用户列表 — 最近2小时内有登录/活动的用户

    注：last_login_at 在登录时更新（无按请求的活动刷新中间件），
    因此本过滤是「最近2小时登录过」的近似，长时间持续在线的用户
    会随窗口滑出，属已知语义边界。
    """
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=2)
        recent = db.query(User).filter(
            User.is_active == True,
            User.last_login_at >= cutoff,
        ).all()
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
def list_roles(user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """角色列表"""
    db = SessionLocal()
    try:
        roles = db.query(Role).all()
        if roles:
            items = []
            for r in roles:
                cnt = db.query(User).filter(User.role == r.name).count()
                items.append({"id": r.id, "name": r.name, "description": r.description or "", "user_count": cnt,
                            "permissions": r.permissions or {}, "data_permissions": r.data_permissions or {},
                            "builtin": r.name in _BUILTIN_ROLES})
            return {"items": items}
        # 回退：种子数据
        return {"items": [
            {"id": 1, "name": "system_admin", "description": "系统管理员", "user_count": 1},
            {"id": 2, "name": "archive_admin", "description": "档案馆员", "user_count": 2},
            {"id": 3, "name": "reviewer", "description": "审核员", "user_count": 5},
        ]}
    finally:
        db.close()


@router.post("/roles")
def create_role(name: str, description: str = "", user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """创建角色"""
    db = SessionLocal()
    try:
        existing = db.query(Role).filter(Role.name == name).first()
        if existing: return {"error": "角色已存在"}
        role = Role(name=name, description=description)
        db.add(role)
        db.commit()
        db.refresh(role)
        return {"role_id": role.id, "name": role.name, "status": "created"}
    finally:
        db.close()


@router.put("/roles/{role_id}/permissions")
def update_role_permissions(role_id: int, permissions: dict, data_permissions: Optional[dict] = None, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """配置角色权限（含案卷级/卷内级数据权限）"""
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.id == role_id).first()
        if role:
            role.permissions = permissions
            if data_permissions is not None:
                role.data_permissions = data_permissions
            db.commit()
            return {"role_id": role_id, "permissions": permissions,
                    "data_permissions": role.data_permissions or {}, "status": "updated"}
        return {"error": "role_not_found"}
    finally:
        db.close()


@router.delete("/roles/{role_id}")
def delete_role(role_id: int, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """删除角色"""
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            return {"error": "role_not_found"}
        # 内置角色不可删除
        if role.name in _BUILTIN_ROLES:
            return {"error": "系统内置角色不可删除"}
        # 检查是否有用户使用此角色
        user_count = db.query(User).filter(User.role == role.name).count()
        if user_count > 0:
            return {"error": f"该角色下有 {user_count} 个用户，请先移除用户后再删除"}
        db.delete(role)
        db.commit()
        return {"role_id": role_id, "status": "deleted"}
    finally:
        db.close()


# ===================== 目录树授权 =====================

@router.get("/{user_id}")
def get_user(user_id: int, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
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
def get_tree_auth(user_id: int, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """查看目录树授权"""
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            return {"error": "not_found"}
        return {"user_id": user_id, "authorized_nodes": u.tree_auth or []}
    finally:
        db.close()


class TreeAuthRequest(BaseModel):
    node_ids: list[str]


@router.put("/{user_id}/tree-auth")
def update_tree_auth(user_id: int, req: TreeAuthRequest, user: dict = Depends(require_role(ROLE_SYSTEM_ADMIN))):
    """配置目录树授权 — 持久化到用户记录"""
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            return {"error": "not_found"}
        # 继承：上级节点授权自动包含所有下级节点
        expanded = _expand_tree_nodes(req.node_ids)
        u.tree_auth = expanded
        db.commit()
        return {"user_id": user_id, "authorized_nodes": expanded}
    finally:
        db.close()


# ==================== 辅助函数 ====================

def _password_complexity_error(password: str) -> str | None:
    """密码复杂度校验：不少于12位 + 大小写/数字/特殊字符。返回错误信息或 None"""
    import re
    if len(password) < 12:
        return "密码不少于12个字符"
    if not re.search(r'[A-Z]', password):
        return "密码需包含大写字母"
    if not re.search(r'[a-z]', password):
        return "密码需包含小写字母"
    if not re.search(r'[0-9]', password):
        return "密码需包含数字"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\/]', password):
        return "密码需包含特殊字符"
    return None

# 档案目录树结构：大类 → 年份 → 部门
_TREE_HIERARCHY: dict[str, list[str]] = {
    "行政档案": ["校长办公室", "发展规划部", "人事部"],
    "教学档案": ["教务处", "研究生院", "招生办公室"],
    "党群档案": ["组织部", "宣传部", "纪委", "统战部", "工会", "团委"],
    "科研档案": ["科研处"],
    "人事档案": ["人事处"],
    "财务档案": ["财务处"],
    "基建档案": ["基建处"],
    "声像档案": ["档案馆"],
}


def _expand_tree_nodes(node_ids: list[str]) -> list[str]:
    """将目录树节点扩展：大类节点自动包含所有子部门"""
    expanded = list(node_ids)
    for nid in node_ids:
        if nid in _TREE_HIERARCHY:
            for child in _TREE_HIERARCHY[nid]:
                child_path = f"{nid}/{child}"
                if child_path not in expanded:
                    expanded.append(child_path)
    return expanded
