from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import get_db
from app.models.test_order import TestOrder, OrderTestItem
from app.models.patient import Patient
from app.schemas import TestOrderCreate, TestOrderResponse
from app.utils.helpers import generate_order_no

router = APIRouter()


@router.get("", response_model=list[TestOrderResponse])
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    priority: str = Query(None),
    keyword: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(TestOrder, Patient.name, Patient.patient_no)
        .outerjoin(Patient, TestOrder.patient_id == Patient.id)
        .order_by(TestOrder.created_at.desc())
    )
    if status:
        query = query.where(TestOrder.status == status)
    if priority:
        query = query.where(TestOrder.priority == priority)
    if keyword:
        query = query.where(
            TestOrder.order_no.contains(keyword)
            | Patient.name.contains(keyword)
        )
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    return [
        TestOrderResponse(
            id=row[0].id, order_no=row[0].order_no, patient_id=row[0].patient_id,
            ordering_doctor=row[0].ordering_doctor, order_time=row[0].order_time,
            diagnosis=row[0].diagnosis, priority=row[0].priority,
            status=row[0].status, created_at=row[0].created_at,
            patient_name=row[1], patient_no=row[2],
        )
        for row in result.all()
    ]


@router.post("", response_model=TestOrderResponse)
async def create_order(req: TestOrderCreate, db: AsyncSession = Depends(get_db)):
    patient = await db.execute(select(Patient).where(Patient.id == req.patient_id))
    if not patient.scalar_one_or_none():
        raise HTTPException(400, "患者不存在")

    order = TestOrder(
        order_no=generate_order_no(),
        patient_id=req.patient_id,
        ordering_doctor=req.ordering_doctor,
        diagnosis=req.diagnosis,
        priority=req.priority,
        order_time=datetime.now(),
        status="PENDING",
    )
    db.add(order)
    await db.flush()

    # 添加检验项目
    for item_id in req.test_item_ids:
        db.add(OrderTestItem(order_id=order.id, test_item_id=item_id))

    await db.commit()
    await db.refresh(order)

    p = await db.execute(select(Patient).where(Patient.id == order.patient_id))
    patient = p.scalar_one()

    return TestOrderResponse(
        id=order.id, order_no=order.order_no, patient_id=order.patient_id,
        ordering_doctor=order.ordering_doctor, order_time=order.order_time,
        diagnosis=order.diagnosis, priority=order.priority,
        status=order.status, created_at=order.created_at,
        patient_name=patient.name, patient_no=patient.patient_no,
    )


@router.post("/{order_id}/cancel")
async def cancel_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestOrder).where(TestOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "申请单不存在")
    if order.status not in ("PENDING",):
        raise HTTPException(400, "只能取消待处理的申请单")

    order.status = "CANCELLED"
    await db.commit()
    return {"message": "已取消", "order_id": order_id}
