from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import csv
import io

from app.database import get_db
from app.models.test_result import TestResult
from app.models.test_item import TestItem
from app.models.specimen import Specimen
from app.models.instrument import Instrument
from app.models.patient import Patient
from app.models.audit_log import AuditLog
from app.models.test_report import TestReport
from app.schemas import TestResultResponse, ReviewRequest, ManualResultCreate
from app.utils.helpers import judge_abnormal, format_ref_range
from app.utils.permissions import check_permission_or_raise
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("", response_model=list[TestResultResponse])
async def list_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    specimen_id: int = Query(None),
    status: str = Query(None),
    abnormal_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(TestResult, TestItem.code, TestItem.name, Instrument.name,
               Patient.name, Patient.patient_no, Specimen.barcode)
        .outerjoin(TestItem, TestResult.test_item_id == TestItem.id)
        .outerjoin(Instrument, TestResult.instrument_id == Instrument.id)
        .outerjoin(Specimen, TestResult.specimen_id == Specimen.id)
        .outerjoin(Patient, Specimen.patient_id == Patient.id)
        .order_by(TestResult.created_at.desc())
    )
    if specimen_id:
        query = query.where(TestResult.specimen_id == specimen_id)
    if status:
        query = query.where(TestResult.status == status)
    if abnormal_only:
        query = query.where(TestResult.abnormal_flag.in_(["H", "L", "A"]))

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    return [
        TestResultResponse(
            id=row[0].id, specimen_id=row[0].specimen_id,
            test_item_id=row[0].test_item_id,
            result_value=row[0].result_value,
            result_numeric=float(row[0].result_numeric) if row[0].result_numeric else None,
            unit=row[0].unit, ref_range=row[0].ref_range,
            abnormal_flag=row[0].abnormal_flag,
            status=row[0].status,
            reviewed_by=row[0].reviewed_by,
            reviewed_at=row[0].reviewed_at,
            created_at=row[0].created_at,
            item_code=row[1], item_name=row[2],
            instrument_name=row[3],
            patient_name=row[4],
            patient_no=row[5],
            barcode=row[6],
        )
        for row in result.all()
    ]


@router.get("/by-specimen/{specimen_id}", response_model=list[TestResultResponse])
async def get_results_by_specimen(specimen_id: int, db: AsyncSession = Depends(get_db)):
    """获取指定标本的所有结果"""
    query = (
        select(TestResult, TestItem.code, TestItem.name, Instrument.name)
        .outerjoin(TestItem, TestResult.test_item_id == TestItem.id)
        .outerjoin(Instrument, TestResult.instrument_id == Instrument.id)
        .where(TestResult.specimen_id == specimen_id)
        .order_by(TestItem.sort_order)
    )
    result = await db.execute(query)

    return [
        TestResultResponse(
            id=row[0].id, specimen_id=row[0].specimen_id,
            test_item_id=row[0].test_item_id,
            result_value=row[0].result_value,
            result_numeric=float(row[0].result_numeric) if row[0].result_numeric else None,
            unit=row[0].unit, ref_range=row[0].ref_range,
            abnormal_flag=row[0].abnormal_flag,
            status=row[0].status,
            reviewed_by=row[0].reviewed_by,
            reviewed_at=row[0].reviewed_at,
            created_at=row[0].created_at,
            item_code=row[1], item_name=row[2],
            instrument_name=row[3],
        )
        for row in result.all()
    ]


@router.get("/trends")
async def get_result_trends(
    patient_id: int = Query(..., description="患者ID"),
    test_item_id: int = Query(..., description="检验项目ID"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取患者某项目的历史结果趋势"""
    check_permission_or_raise(current_user.role, "result:view")

    query = (
        select(
            TestResult.result_value,
            TestResult.result_numeric,
            TestResult.unit,
            TestResult.abnormal_flag,
            TestResult.created_at,
            Specimen.barcode,
            TestItem.name.label("item_name"),
            TestItem.code.label("item_code"),
        )
        .outerjoin(Specimen, TestResult.specimen_id == Specimen.id)
        .outerjoin(TestItem, TestResult.test_item_id == TestItem.id)
        .where(
            Specimen.patient_id == patient_id,
            TestResult.test_item_id == test_item_id,
        )
        .order_by(TestResult.created_at.asc())
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "date": row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else None,
            "result_value": row.result_value,
            "result_numeric": float(row.result_numeric) if row.result_numeric else None,
            "unit": row.unit,
            "abnormal_flag": row.abnormal_flag,
            "barcode": row.barcode,
            "item_name": row.item_name,
            "item_code": row.item_code,
        }
        for row in rows
    ]


@router.post("/auto-review")
async def auto_review_results(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """自动审核所有 status=AUTO 且 abnormal_flag=N 的结果"""
    check_permission_or_raise(current_user.role, "result:review")

    result = await db.execute(
        select(TestResult).where(
            TestResult.status == "AUTO",
            TestResult.abnormal_flag == "N",
        )
    )
    results = result.scalars().all()

    if not results:
        return {"message": "没有符合条件的结果需要自动审核", "count": 0}

    for r in results:
        r.status = "REVIEWED"
        r.reviewed_by = current_user.real_name or current_user.username
        r.reviewed_at = datetime.now()

    db.add(AuditLog(
        action="AUTO_REVIEW",
        target_table="test_results",
        target_id=0,
        detail=f"自动审核了 {len(results)} 条结果（status=AUTO, abnormal_flag=N）",
    ))

    await db.commit()
    return {"message": f"已自动审核 {len(results)} 条结果", "count": len(results)}


@router.get("/export")
async def export_results(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """导出所有结果为 CSV 格式"""
    check_permission_or_raise(current_user.role, "result:view")

    query = (
        select(
            TestResult.id,
            TestResult.result_value,
            TestResult.result_numeric,
            TestResult.unit,
            TestResult.ref_range,
            TestResult.abnormal_flag,
            TestResult.status,
            TestResult.created_at,
            TestItem.code.label("item_code"),
            TestItem.name.label("item_name"),
            Specimen.barcode,
            Patient.name.label("patient_name"),
            Patient.patient_no,
            Instrument.name.label("instrument_name"),
        )
        .outerjoin(TestItem, TestResult.test_item_id == TestItem.id)
        .outerjoin(Specimen, TestResult.specimen_id == Specimen.id)
        .outerjoin(Patient, Specimen.patient_id == Patient.id)
        .outerjoin(Instrument, TestResult.instrument_id == Instrument.id)
        .order_by(TestResult.id.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "结果ID", "标本条码", "患者姓名", "患者编号",
        "项目编码", "项目名称", "结果值", "数值结果",
        "单位", "参考范围", "异常标志", "状态", "仪器", "创建时间",
    ])
    for row in rows:
        writer.writerow([
            row.id,
            row.barcode,
            row.patient_name,
            row.patient_no,
            row.item_code,
            row.item_name,
            row.result_value,
            float(row.result_numeric) if row.result_numeric else "",
            row.unit,
            row.ref_range,
            row.abnormal_flag,
            row.status,
            row.instrument_name,
            row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
        ])

    output.seek(0)
    # Add BOM for Excel compatibility
    bom_output = io.BytesIO()
    bom_output.write(b'\xef\xbb\xbf')
    bom_output.write(output.getvalue().encode("utf-8"))
    bom_output.seek(0)

    return StreamingResponse(
        bom_output,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=results_export.csv"},
    )


@router.post("/review")
async def review_results(
    req: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """审核检验结果"""
    check_permission_or_raise(current_user.role, "result:review")

    if not req.result_ids:
        raise HTTPException(400, "请选择要审核的结果")

    result = await db.execute(
        select(TestResult).where(TestResult.id.in_(req.result_ids))
    )
    results = result.scalars().all()

    if not results:
        raise HTTPException(404, "未找到结果")

    for r in results:
        if r.status == "REVIEWED":
            continue  # 已审核的跳过
        r.status = "REVIEWED" if req.action == "approve" else "REJECTED"
        r.reviewed_by = req.reviewer
        r.reviewed_at = datetime.now()

    action_label = "通过" if req.action == "approve" else "退回"
    db.add(AuditLog(
        action=f"审核{action_label}", target_table="test_results",
        target_id=req.result_ids[0] if req.result_ids else 0,
        detail=f"{req.reviewer} 审核{action_label}了 {len(results)} 条检验结果",
    ))

    await db.commit()
    return {"message": f"已审核 {len(results)} 条结果", "action": req.action}


@router.post("/manual", response_model=TestResultResponse)
async def create_manual_result(req: ManualResultCreate, db: AsyncSession = Depends(get_db)):
    """手工录入结果"""
    specimen = await db.execute(select(Specimen).where(Specimen.id == req.specimen_id))
    specimen = specimen.scalar_one_or_none()
    if not specimen:
        raise HTTPException(404, "标本不存在")

    test_item = await db.execute(select(TestItem).where(TestItem.id == req.test_item_id))
    test_item = test_item.scalar_one_or_none()
    if not test_item:
        raise HTTPException(404, "检验项目不存在")

    result_numeric = req.result_numeric
    if result_numeric is None:
        try:
            result_numeric = float(req.result_value)
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

    test_result = TestResult(
        specimen_id=req.specimen_id,
        order_id=specimen.order_id,
        test_item_id=req.test_item_id,
        result_value=req.result_value,
        result_numeric=result_numeric,
        unit=req.unit or test_item.unit,
        ref_range=ref_range,
        abnormal_flag=abnormal_flag,
        status="MANUAL",
        raw_data=f'{{"source":"manual","operator":"{req.operator}"}}',
    )
    db.add(test_result)
    await db.commit()
    await db.refresh(test_result)

    return TestResultResponse(
        id=test_result.id, specimen_id=test_result.specimen_id,
        test_item_id=test_result.test_item_id,
        result_value=test_result.result_value,
        result_numeric=float(test_result.result_numeric) if test_result.result_numeric else None,
        unit=test_result.unit, ref_range=test_result.ref_range,
        abnormal_flag=test_result.abnormal_flag,
        status=test_result.status,
        item_code=test_item.code, item_name=test_item.name,
    )
