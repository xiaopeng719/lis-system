from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter()


@router.get("/audit-logs")
async def list_audit_logs(
    keyword: str = Query(None),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AuditLog, User.username)
        .outerjoin(User, AuditLog.user_id == User.id)
        .order_by(AuditLog.created_at.desc())
        .limit(page_size)
    )
    if keyword:
        query = query.where(AuditLog.detail.contains(keyword))

    result = await db.execute(query)
    return [
        {
            "id": row[0].id,
            "user_id": row[0].user_id,
            "username": row[1],
            "action": row[0].action,
            "target_table": row[0].target_table,
            "target_id": row[0].target_id,
            "detail": row[0].detail,
            "ip_address": row[0].ip_address,
            "created_at": row[0].created_at,
        }
        for row in result.all()
    ]
