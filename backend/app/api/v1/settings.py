from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.utils.permissions import check_permission_or_raise
from app.api.v1.auth import get_current_user
from app.utils.settings import get_all_settings, _load_settings, _save_settings

router = APIRouter()


class SettingsUpdate(BaseModel):
    hospital_name: Optional[str] = None
    mqtt_host: Optional[str] = None
    mqtt_port: Optional[int] = None
    tat_warning_minutes: Optional[int] = None
    auto_review_enabled: Optional[bool] = None


@router.get("")
async def get_settings(current_user=Depends(get_current_user)):
    """获取系统配置"""
    check_permission_or_raise(current_user.role, "base_data:edit")
    return get_all_settings()


@router.put("")
async def update_settings(
    req: SettingsUpdate,
    current_user=Depends(get_current_user),
):
    """更新系统配置"""
    check_permission_or_raise(current_user.role, "base_data:edit")

    settings = _load_settings()
    update_data = req.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if value is not None:
            settings[key] = value

    _save_settings(settings)
    return {"message": "配置已更新", "settings": settings}
