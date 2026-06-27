from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.patient import Patient
from app.schemas import PatientCreate, PatientResponse

router = APIRouter()


@router.get("", response_model=list[PatientResponse])
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Patient).order_by(Patient.created_at.desc())
    if keyword:
        query = query.where(
            Patient.name.contains(keyword) | Patient.patient_no.contains(keyword)
        )
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=PatientResponse)
async def create_patient(req: PatientCreate, db: AsyncSession = Depends(get_db)):
    # 检查重复
    existing = await db.execute(
        select(Patient).where(Patient.patient_no == req.patient_no)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"患者编号 {req.patient_no} 已存在")

    patient = Patient(**req.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "患者不存在")
    return patient
