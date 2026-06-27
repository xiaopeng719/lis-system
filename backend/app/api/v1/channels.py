from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.instrument import Instrument, InstrumentTestItem
from app.models.test_item import TestItem
from app.models.audit_log import AuditLog
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("/{instrument_id}/channels")
async def get_channels(instrument_id: int, db: AsyncSession = Depends(get_db)):
    """获取仪器的通道号映射列表"""
    query = (
        select(InstrumentTestItem, TestItem.code, TestItem.name, TestItem.unit)
        .join(TestItem, InstrumentTestItem.test_item_id == TestItem.id)
        .where(InstrumentTestItem.instrument_id == instrument_id)
        .order_by(InstrumentTestItem.channel_code)
    )
    result = await db.execute(query)
    return [
        {
            "id": row[0].id,
            "channel_code": row[0].channel_code,
            "test_item_id": row[0].test_item_id,
            "item_code": row[1],
            "item_name": row[2],
            "unit": row[3],
        }
        for row in result.all()
    ]


@router.post("/{instrument_id}/channels")
async def create_channel(
    instrument_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建通道号映射"""
    # 检查仪器存在
    inst = (await db.execute(select(Instrument).where(Instrument.id == instrument_id))).scalar_one_or_none()
    if not inst:
        raise HTTPException(404, "仪器不存在")

    channel_code = data.get("channel_code")
    test_item_id = data.get("test_item_id")

    if not channel_code or not test_item_id:
        raise HTTPException(400, "通道号和检验项目不能为空")

    # 检查重复
    existing = await db.execute(
        select(InstrumentTestItem)
        .where(
            InstrumentTestItem.instrument_id == instrument_id,
            InstrumentTestItem.channel_code == str(channel_code),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"通道号 {channel_code} 已存在")

    # 检查检验项目存在
    item = (await db.execute(select(TestItem).where(TestItem.id == test_item_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "检验项目不存在")

    mapping = InstrumentTestItem(
        instrument_id=instrument_id,
        test_item_id=test_item_id,
        channel_code=str(channel_code),
    )
    db.add(mapping)

    db.add(AuditLog(
        action="创建", target_table="instrument_test_items", target_id=mapping.id,
        detail=f"仪器 {inst.name} 创建通道号 {channel_code} → {item.code} {item.name}",
    ))
    await db.commit()
    await db.refresh(mapping)
    return {"id": mapping.id, "message": "创建成功"}


@router.delete("/{instrument_id}/channels/{channel_id}")
async def delete_channel(
    instrument_id: int,
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除通道号映射"""
    mapping = (await db.execute(
        select(InstrumentTestItem)
        .where(InstrumentTestItem.id == channel_id, InstrumentTestItem.instrument_id == instrument_id)
    )).scalar_one_or_none()

    if not mapping:
        raise HTTPException(404, "通道号映射不存在")

    await db.delete(mapping)
    db.add(AuditLog(
        action="删除", target_table="instrument_test_items", target_id=channel_id,
        detail=f"删除通道号映射 ID={channel_id}",
    ))
    await db.commit()
    return {"message": "已删除"}
