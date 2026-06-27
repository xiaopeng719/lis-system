from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas import LoginRequest, TokenResponse, UserResponse
from app.utils.security import verify_password, create_access_token, decode_access_token, get_password_hash

router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == int(user_id), User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def write_audit(db: AuditLog, user_id: int, action: str, table: str, target_id: int, detail: str, ip: str = None):
    """写入审计日志"""
    db.add(AuditLog(user_id=user_id, action=action, target_table=table,
                    target_id=target_id, detail=detail, ip_address=ip))


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/permissions")
async def get_permissions(current_user: User = Depends(get_current_user)):
    """获取当前用户的权限列表"""
    from app.utils.permissions import get_role_permissions, PERMISSIONS
    perms = get_role_permissions(current_user.role)
    return {
        "role": current_user.role,
        "permissions": perms,
        "permission_descriptions": {p: PERMISSIONS.get(p, p) for p in perms},
    }


# ==================== 用户管理 ====================
class UserCreate(BaseModel):
    username: str
    password: str
    real_name: Optional[str] = None
    role: str = "TECHNICIAN"
    department: Optional[str] = None

class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    password: Optional[str] = None


@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("ADMIN", "DIRECTOR"):
        raise HTTPException(403, "权限不足：需要管理员或主任权限")

    result = await db.execute(select(User).order_by(User.id))
    return [
        {
            "id": u.id, "username": u.username, "real_name": u.real_name,
            "role": u.role, "department": u.department, "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in result.scalars().all()
    ]


@router.post("/users")
async def create_user(
    req: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "只有管理员可以创建用户")

    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"用户名 {req.username} 已存在")

    user = User(
        username=req.username,
        password_hash=get_password_hash(req.password),
        real_name=req.real_name,
        role=req.role,
        department=req.department,
    )
    db.add(user)
    await db.flush()

    write_audit(db, current_user.id, "CREATE", "users", user.id,
                f"创建用户 {req.username} ({req.role})")
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "username": user.username, "message": "创建成功"}


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    req: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "只有管理员可以修改用户")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    if req.real_name is not None:
        user.real_name = req.real_name
    if req.role is not None:
        user.role = req.role
    if req.department is not None:
        user.department = req.department
    if req.password:
        user.password_hash = get_password_hash(req.password)

    write_audit(db, current_user.id, "UPDATE", "users", user_id,
                f"修改用户 {user.username}")
    await db.commit()
    return {"message": "修改成功"}
