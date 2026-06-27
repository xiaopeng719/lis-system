from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.database import get_db
from app.models.instrument import Instrument
from app.utils.permissions import check_permission_or_raise
from app.api.v1.auth import get_current_user
from app.mqtt.service import get_all_heartbeats

router = APIRouter()


@router.get("/status")
async def get_instruments_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取每个仪器的 MQTT 连接状态"""
    check_permission_or_raise(current_user.role, "instrument:manage")

    result = await db.execute(
        select(Instrument).where(Instrument.is_active == True).order_by(Instrument.id)
    )
    instruments = result.scalars().all()

    heartbeats = get_all_heartbeats()
    now = datetime.now()
    offline_threshold = timedelta(minutes=5)

    statuses = []
    for inst in instruments:
        last_heartbeat = heartbeats.get(inst.code)
        if last_heartbeat:
            is_online = (now - last_heartbeat) < offline_threshold
            last_heartbeat_str = last_heartbeat.strftime("%Y-%m-%d %H:%M:%S")
        else:
            is_online = False
            last_heartbeat_str = None

        statuses.append({
            "instrument_id": inst.id,
            "instrument_code": inst.code,
            "instrument_name": inst.name,
            "model": inst.model,
            "mqtt_topic": inst.mqtt_topic,
            "is_online": is_online,
            "last_heartbeat": last_heartbeat_str,
        })

    return statuses
