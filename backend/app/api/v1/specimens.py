from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import get_db
from app.models.specimen import Specimen
from app.models.patient import Patient
from app.models.instrument import Instrument
from app.models.test_result import TestResult
from app.models.test_order import TestOrder, OrderTestItem
from app.models.test_item import TestItem, ComboPackage, ComboItem
from app.models.audit_log import AuditLog
from app.schemas import SpecimenCreate, SpecimenReceive, SpecimenResponse
from app.utils.helpers import generate_barcode, generate_order_no
from app.utils.permissions import check_permission_or_raise
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("", response_model=list[SpecimenResponse])
async def list_specimens(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    keyword: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            Specimen,
            Patient.name.label("patient_name"),
            Patient.patient_no.label("patient_no"),
            Instrument.name.label("instrument_name"),
        )
        .outerjoin(Patient, Specimen.patient_id == Patient.id)
        .outerjoin(Instrument, Specimen.instrument_id == Instrument.id)
        .order_by(Specimen.created_at.desc())
    )

    if status:
        query = query.where(Specimen.status == status)
    if keyword:
        query = query.where(
            Specimen.barcode.contains(keyword)
            | Patient.name.contains(keyword)
            | Patient.patient_no.contains(keyword)
        )

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    items = []
    for row in result.all():
        s = row[0]
        # 获取结果数
        rc = await db.execute(
            select(func.count(TestResult.id)).where(TestResult.specimen_id == s.id)
        )
        items.append(SpecimenResponse(
            id=s.id, barcode=s.barcode, patient_id=s.patient_id,
            order_id=s.order_id, sample_type=s.sample_type,
            collect_time=s.collect_time, collector=s.collector,
            receive_time=s.receive_time, receiver=s.receiver,
            instrument_id=s.instrument_id, status=s.status,
            remark=s.remark, created_at=s.created_at,
            patient_name=row.patient_name,
            patient_no=row.patient_no,
            instrument_name=row.instrument_name,
            result_count=rc.scalar() or 0,
        ))

    return items


@router.post("", response_model=SpecimenResponse)
async def create_specimen(req: SpecimenCreate, db: AsyncSession = Depends(get_db)):
    # ---- 处理新患者 ----
    patient_id = req.patient_id
    if not patient_id and not req.new_patient_name:
        raise HTTPException(400, "请输入患者姓名")

    if req.new_patient_name and not patient_id:
        from app.utils.helpers import generate_patient_no
        patient = Patient(
            patient_no=generate_patient_no(),
            name=req.new_patient_name,
            gender=req.new_patient_gender,
            age=req.new_patient_age,
            phone=req.new_patient_phone,
        )
        db.add(patient)
        await db.flush()
        patient_id = patient.id
    elif patient_id:
        p = await db.execute(select(Patient).where(Patient.id == patient_id))
        if not p.scalar_one_or_none():
            raise HTTPException(400, "患者不存在")

    # ---- 合并项目 ID：combo_ids → test_item_ids ----
    all_item_ids = list(req.test_item_ids)
    if req.combo_ids:
        combo_rows = await db.execute(
            select(ComboItem.test_item_id)
            .where(ComboItem.combo_id.in_(req.combo_ids))
        )
        for row in combo_rows.all():
            if row[0] not in all_item_ids:
                all_item_ids.append(row[0])

    # ---- 自动推断仪器（取项目绑定的仪器，取出现最多的） ----
    instrument_id = None
    if all_item_ids:
        items = await db.execute(
            select(TestItem.instrument_id)
            .where(TestItem.id.in_(all_item_ids), TestItem.instrument_id.isnot(None))
        )
        instr_counts: dict = {}
        for row in items.all():
            instr_counts[row[0]] = instr_counts.get(row[0], 0) + 1
        if instr_counts:
            instrument_id = max(instr_counts, key=instr_counts.get)

    # ---- 创建申请单 ----
    order_id = req.order_id
    if all_item_ids and not order_id:
        order = TestOrder(
            order_no=generate_order_no(),
            patient_id=patient_id,
            order_time=datetime.now(),
            status="PENDING",
        )
        db.add(order)
        await db.flush()
        for item_id in all_item_ids:
            db.add(OrderTestItem(order_id=order.id, test_item_id=item_id))
        order_id = order.id

    barcode = req.barcode or generate_barcode()
    specimen = Specimen(
        barcode=barcode,
        patient_id=patient_id,
        order_id=order_id,
        sample_type=req.sample_type,
        collector=req.collector,
        collect_time=datetime.now(),
        instrument_id=instrument_id,
        status="COLLECTED",
    )
    db.add(specimen)
    await db.flush()

    # 写入审计日志
    db.add(AuditLog(
        action="CREATE", target_table="specimens", target_id=specimen.id,
        detail=f"创建标本 {barcode}，患者ID={patient_id}，项目数={len(all_item_ids)}",
    ))

    await db.commit()
    await db.refresh(specimen)
    return SpecimenResponse(
        **{k: getattr(specimen, k) for k in SpecimenResponse.model_fields if hasattr(specimen, k)}
    )


@router.post("/{specimen_id}/receive")
async def receive_specimen(
    specimen_id: int, req: SpecimenReceive, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Specimen).where(Specimen.id == specimen_id))
    specimen = result.scalar_one_or_none()
    if not specimen:
        raise HTTPException(404, "标本不存在")

    if specimen.status not in ("COLLECTED",):
        raise HTTPException(400, f"当前状态 {specimen.status} 不允许接收")

    specimen.status = "RECEIVED"
    specimen.receive_time = datetime.now()
    specimen.receiver = req.receiver
    if req.instrument_id:
        specimen.instrument_id = req.instrument_id
    if req.remark:
        specimen.remark = req.remark

    # 如果还没分配仪器，根据申请单的检验项目自动分配
    if not specimen.instrument_id and specimen.order_id:
        from app.models.test_order import OrderTestItem
        items = (await db.execute(
            select(TestItem.instrument_id)
            .join(OrderTestItem, OrderTestItem.test_item_id == TestItem.id)
            .where(OrderTestItem.order_id == specimen.order_id, TestItem.instrument_id.isnot(None))
        )).all()
        if items:
            # 取出现最多的仪器
            from collections import Counter
            counts = Counter(row[0] for row in items)
            specimen.instrument_id = counts.most_common(1)[0][0]

    db.add(AuditLog(
        action="UPDATE", target_table="specimens", target_id=specimen_id,
        detail=f"接收标本 {specimen.barcode}，接收人={req.receiver}",
    ))

    await db.commit()
    return {"message": "接收成功", "specimen_id": specimen_id}


@router.post("/{specimen_id}/complete")
async def complete_specimen(specimen_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Specimen).where(Specimen.id == specimen_id))
    specimen = result.scalar_one_or_none()
    if not specimen:
        raise HTTPException(404, "标本不存在")

    specimen.status = "COMPLETED"
    await db.commit()
    return {"message": "已完成", "specimen_id": specimen_id}


@router.post("/{specimen_id}/reject")
async def reject_specimen(
    specimen_id: int,
    reason: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """拒收标本，将状态改为 REJECTED"""
    check_permission_or_raise(current_user.role, "specimen:receive")

    result = await db.execute(select(Specimen).where(Specimen.id == specimen_id))
    specimen = result.scalar_one_or_none()
    if not specimen:
        raise HTTPException(404, "标本不存在")

    if specimen.status == "REJECTED":
        raise HTTPException(400, "标本已被拒收")

    reject_reason = reason.get("reason", "")
    if not reject_reason:
        raise HTTPException(400, "请提供拒收原因")

    specimen.status = "REJECTED"
    specimen.remark = f"拒收原因：{reject_reason}"

    db.add(AuditLog(
        action="REJECT",
        target_table="specimens",
        target_id=specimen_id,
        detail=f"拒收标本 {specimen.barcode}，原因：{reject_reason}",
    ))

    await db.commit()
    return {"message": "标本已拒收", "specimen_id": specimen_id, "reason": reject_reason}


@router.get("/{specimen_id}/test-items")
async def get_specimen_test_items(specimen_id: int, db: AsyncSession = Depends(get_db)):
    """获取标本关联的检验项目，含已录入的结果值"""
    specimen = (await db.execute(select(Specimen).where(Specimen.id == specimen_id))).scalar_one_or_none()
    if not specimen:
        raise HTTPException(404, "标本不存在")

    # 查已录入的结果（含值）
    existing_results = await db.execute(
        select(TestResult).where(TestResult.specimen_id == specimen_id)
    )
    result_map = {}  # test_item_id -> result
    for r in existing_results.scalars().all():
        result_map[r.test_item_id] = r

    # 查患者信息
    patient = None
    if specimen.patient_id:
        p = await db.execute(select(Patient).where(Patient.id == specimen.patient_id))
        patient = p.scalar_one_or_none()

    # 查申请单关联的项目
    items = []
    if specimen.order_id:
        order_items = await db.execute(
            select(OrderTestItem, TestItem)
            .join(TestItem, OrderTestItem.test_item_id == TestItem.id)
            .where(OrderTestItem.order_id == specimen.order_id)
        )
        for oi, ti in order_items.all():
            result = result_map.get(ti.id)
            items.append({
                "id": ti.id, "code": ti.code, "name": ti.name,
                "unit": ti.unit, "category": ti.category,
                "ref_range_low": float(ti.ref_range_low) if ti.ref_range_low else None,
                "ref_range_high": float(ti.ref_range_high) if ti.ref_range_high else None,
                "already_entered": ti.id in result_map,
                "result_value": result.result_value if result else None,
                "result_numeric": float(result.result_numeric) if result and result.result_numeric else None,
                "abnormal_flag": result.abnormal_flag if result else None,
                "result_status": result.status if result else None,
            })

    # 如果没有申请单（没有关联项目），返回全部未录入项目
    if not items:
        all_items = await db.execute(
            select(TestItem).where(TestItem.is_active == True).order_by(TestItem.sort_order)
        )
        for ti in all_items.scalars().all():
            result = result_map.get(ti.id)
            if ti.id not in result_map:
                items.append({
                    "id": ti.id, "code": ti.code, "name": ti.name,
                    "unit": ti.unit, "category": ti.category,
                    "ref_range_low": float(ti.ref_range_low) if ti.ref_range_low else None,
                    "ref_range_high": float(ti.ref_range_high) if ti.ref_range_high else None,
                    "already_entered": False,
                    "result_value": None, "result_numeric": None,
                    "abnormal_flag": None, "result_status": None,
                })

    return {
        "specimen_id": specimen_id,
        "barcode": specimen.barcode,
        "patient_id": specimen.patient_id,
        "patient_name": patient.name if patient else None,
        "patient_no": patient.patient_no if patient else None,
        "status": specimen.status,
        "test_items": items,
    }


@router.post("/{specimen_id}/enter-results")
async def enter_results_for_specimen(
    specimen_id: int,
    results_data: list[dict],
    db: AsyncSession = Depends(get_db),
):
    """
    为标本批量录入结果（手工/模拟仪器）
    results_data: [{"test_item_id": 1, "result_value": "5.6", "result_numeric": 5.6, "unit": "mmol/L"}, ...]
    """
    from app.models.test_item import TestItem
    from app.utils.helpers import judge_abnormal, format_ref_range

    specimen = (await db.execute(select(Specimen).where(Specimen.id == specimen_id))).scalar_one_or_none()
    if not specimen:
        raise HTTPException(404, "标本不存在")

    saved = []
    for rd in results_data:
        test_item = (await db.execute(
            select(TestItem).where(TestItem.id == rd["test_item_id"], TestItem.is_active == True)
        )).scalar_one_or_none()
        if not test_item:
            continue

        value_str = str(rd.get("result_value", ""))
        result_numeric = rd.get("result_numeric")
        if result_numeric is None:
            try:
                result_numeric = float(value_str)
            except (ValueError, TypeError):
                pass

        abnormal_flag = "N"
        if result_numeric is not None:
            abnormal_flag = judge_abnormal(
                result_numeric,
                float(test_item.ref_range_low) if test_item.ref_range_low else None,
                float(test_item.ref_range_high) if test_item.ref_range_high else None,
            )

        ref_range = format_ref_range(test_item.ref_range_low, test_item.ref_range_high)

        tr = TestResult(
            specimen_id=specimen.id,
            order_id=specimen.order_id,
            test_item_id=test_item.id,
            instrument_id=specimen.instrument_id,
            result_value=value_str,
            result_numeric=result_numeric,
            unit=rd.get("unit", test_item.unit),
            ref_range=ref_range,
            abnormal_flag=abnormal_flag,
            status="MANUAL",
            raw_data='{"source":"manual_entry"}',
        )
        db.add(tr)
        saved.append(test_item.code)

    if saved:
        specimen.status = "TESTING"
        if specimen.instrument_id is None:
            specimen.instrument_id = None  # 手工录入不绑定仪器

    await db.commit()
    return {"message": f"已录入 {len(saved)} 项结果", "items": saved}
