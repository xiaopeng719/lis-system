from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import get_db
from app.models.qc import QcRecord
from app.models.test_item import TestItem
from app.models.instrument import Instrument

router = APIRouter()


@router.get("/records")
async def list_qc_records(
    test_item_id: int = Query(None),
    instrument_id: int = Query(None),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(QcRecord, TestItem.name, TestItem.code, Instrument.name)
        .outerjoin(TestItem, QcRecord.test_item_id == TestItem.id)
        .outerjoin(Instrument, QcRecord.instrument_id == Instrument.id)
        .order_by(QcRecord.record_time.desc())
    )
    if test_item_id:
        query = query.where(QcRecord.test_item_id == test_item_id)
    if instrument_id:
        query = query.where(QcRecord.instrument_id == instrument_id)
    query = query.limit(page_size)

    result = await db.execute(query)
    return [
        {
            "id": row[0].id,
            "instrument_id": row[0].instrument_id,
            "test_item_id": row[0].test_item_id,
            "item_name": row[1],
            "item_code": row[2],
            "instrument_name": row[3],
            "qc_level": row[0].qc_level,
            "qc_lot": row[0].qc_lot,
            "result_value": float(row[0].result_value) if row[0].result_value else None,
            "mean_value": float(row[0].mean_value) if row[0].mean_value else None,
            "sd_value": float(row[0].sd_value) if row[0].sd_value else None,
            "deviation": float(row[0].deviation) if row[0].deviation else None,
            "is_in_control": row[0].is_in_control,
            "rule_violated": row[0].rule_violated,
            "record_time": row[0].record_time,
            "operator": row[0].operator,
        }
        for row in result.all()
    ]


@router.post("/records")
async def create_qc_record(data: dict, db: AsyncSession = Depends(get_db)):
    result_val = data.get("result_value")
    mean_val = data.get("mean_value")
    sd_val = data.get("sd_value")

    # 计算偏差和失控规则
    deviation = None
    is_in_control = True
    rule_violated = None

    if result_val is not None and mean_val is not None and sd_val and sd_val > 0:
        deviation = round(((result_val - mean_val) / (mean_val or 1)) * 100, 2)
        z_score = (result_val - mean_val) / sd_val

        # Westgard 规则简化版
        if abs(z_score) > 3:
            is_in_control = False
            rule_violated = "1-3s"
        elif abs(z_score) > 2:
            # 连续 2 次同侧超过 2SD 需要更多数据，这里简化为警告
            rule_violated = "2-2s (warning)"

    qc = QcRecord(
        instrument_id=data.get("instrument_id"),
        test_item_id=data.get("test_item_id"),
        qc_level=data.get("qc_level"),
        qc_lot=data.get("qc_lot"),
        result_value=result_val,
        mean_value=mean_val,
        sd_value=sd_val,
        deviation=deviation,
        is_in_control=is_in_control,
        rule_violated=rule_violated,
        record_time=datetime.now(),
        operator=data.get("operator"),
    )
    db.add(qc)
    await db.commit()
    await db.refresh(qc)
    return {"id": qc.id, "is_in_control": is_in_control, "rule_violated": rule_violated}
