from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.instrument import Instrument
from app.schemas import InstrumentCreate, InstrumentResponse

router = APIRouter()


@router.get("", response_model=list[InstrumentResponse])
async def list_instruments(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Instrument).order_by(Instrument.id))
    return result.scalars().all()


@router.post("", response_model=InstrumentResponse)
async def create_instrument(req: InstrumentCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Instrument).where(Instrument.code == req.code))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"仪器编码 {req.code} 已存在")

    instrument = Instrument(
        **req.model_dump(),
        mqtt_topic=f"lis/instrument/{req.code}/result",
        mqtt_client_id=f"instrument-{req.code}",
    )
    db.add(instrument)
    await db.commit()
    await db.refresh(instrument)
    return instrument


@router.get("/{instrument_id}", response_model=InstrumentResponse)
async def get_instrument(instrument_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Instrument).where(Instrument.id == instrument_id))
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(404, "仪器不存在")
    return inst


@router.put("/{instrument_id}")
async def update_instrument(
    instrument_id: int, req: InstrumentCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Instrument).where(Instrument.id == instrument_id))
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(404, "仪器不存在")

    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(inst, key, value)

    await db.commit()
    return {"message": "更新成功"}
