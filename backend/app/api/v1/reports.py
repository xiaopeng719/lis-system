from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import get_db
from app.models.test_report import TestReport
from app.models.test_result import TestResult
from app.models.specimen import Specimen
from app.models.patient import Patient
from app.models.test_item import TestItem
from app.schemas import TestReportResponse
from app.utils.helpers import generate_report_no
from app.utils.permissions import check_permission_or_raise
from app.utils.settings import get_setting
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("", response_model=list[TestReportResponse])
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(TestReport, Patient.name, Patient.patient_no)
        .outerjoin(Patient, TestReport.patient_id == Patient.id)
        .order_by(TestReport.created_at.desc())
    )
    if status:
        query = query.where(TestReport.status == status)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    return [
        TestReportResponse(
            id=row[0].id, report_no=row[0].report_no,
            order_id=row[0].order_id, patient_id=row[0].patient_id,
            specimen_id=row[0].specimen_id, status=row[0].status,
            reviewed_by=row[0].reviewed_by, reviewed_at=row[0].reviewed_at,
            created_at=row[0].created_at,
            patient_name=row[1], patient_no=row[2],
        )
        for row in result.all()
    ]


@router.post("/generate/{specimen_id}")
async def generate_report(specimen_id: int, db: AsyncSession = Depends(get_db)):
    """根据标本生成检验报告"""
    specimen = await db.execute(select(Specimen).where(Specimen.id == specimen_id))
    specimen = specimen.scalar_one_or_none()
    if not specimen:
        raise HTTPException(404, "标本不存在")

    # 检查是否已有报告
    existing = await db.execute(
        select(TestReport).where(TestReport.specimen_id == specimen_id, TestReport.status != "REVOKED")
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "该标本已有报告")

    # 获取患者信息
    patient = await db.execute(select(Patient).where(Patient.id == specimen.patient_id))
    patient = patient.scalar_one_or_none()

    # 获取检验结果
    results_query = (
        select(TestResult, TestItem.code, TestItem.name)
        .outerjoin(TestItem, TestResult.test_item_id == TestItem.id)
        .where(TestResult.specimen_id == specimen_id)
        .order_by(TestItem.sort_order)
    )
    results = (await db.execute(results_query)).all()

    if not results:
        raise HTTPException(400, "该标本尚无检验结果")

    # 生成报告 HTML（A4 打印优化）
    result_rows = ""
    for row in results:
        r = row[0]
        flag_display = ""
        flag_class = ""
        if r.abnormal_flag in ("H", "A"):
            flag_display = "↑ 偏高"
            flag_class = 'style="color:#ff4d4f;font-weight:bold"'
        elif r.abnormal_flag == "L":
            flag_display = "↓ 偏低"
            flag_class = 'style="color:#ff4d4f;font-weight:bold"'
        elif r.abnormal_flag == "C":
            flag_display = "⚠ 危急"
            flag_class = 'style="color:#fff;background:#ff4d4f;font-weight:bold;padding:2px 6px"'
        else:
            flag_display = "正常"

        result_rows += f"""
        <tr>
            <td style="padding:8px 12px">{row[2]}</td>
            <td style="padding:8px 12px;color:#666">{row[1]}</td>
            <td style="padding:8px 12px;font-weight:bold" {flag_class}>{r.result_value or '-'}</td>
            <td style="padding:8px 12px">{r.unit or '-'}</td>
            <td style="padding:8px 12px;color:#666">{r.ref_range or '-'}</td>
            <td style="padding:8px 12px" {flag_class}>{flag_display}</td>
        </tr>"""

    report_no = generate_report_no()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    hospital_name = get_setting("hospital_name") or "XX医院检验科"
    report_html = f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><style>
        @page {{ size: A4; margin: 15mm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'SimSun', 'Songti SC', serif; color: #333; padding: 0; }}
        .report {{ width: 100%; max-width: 210mm; margin: 0 auto; padding: 20px; }}

        /* 医院抬头 */
        .header {{ text-align: center; border-bottom: 3px double #333; padding-bottom: 12px; margin-bottom: 15px; }}
        .hospital-name {{ font-size: 26px; font-weight: bold; letter-spacing: 6px; color: #1a1a1a; }}
        .report-title {{ font-size: 20px; margin-top: 6px; color: #333; letter-spacing: 4px; }}
        .report-no {{ font-size: 12px; color: #999; margin-top: 4px; }}

        /* 患者信息 */
        .patient-info {{ display: flex; flex-wrap: wrap; gap: 6px 30px; font-size: 13px; padding: 10px 0; border-bottom: 1px solid #e8e8e8; margin-bottom: 10px; }}
        .patient-info .item {{ white-space: nowrap; }}
        .patient-info .label {{ color: #666; }}
        .patient-info .value {{ color: #333; font-weight: bold; }}

        /* 结果表格 */
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        thead th {{ background: #f5f5f5; padding: 8px 12px; text-align: left; border: 1px solid #d9d9d9; font-weight: bold; color: #333; }}
        tbody td {{ border: 1px solid #e8e8e8; }}

        /* 签字栏 */
        .footer {{ margin-top: 30px; display: flex; justify-content: space-between; font-size: 13px; padding-top: 15px; border-top: 1px solid #e8e8e8; }}
        .footer .sig {{ display: flex; gap: 8px; align-items: center; }}

        /* 打印时隐藏非打印元素 */
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        }}
    </style></head><body>
    <div class="report">
        <div class="header">
            <div class="hospital-name">{hospital_name}</div>
            <div class="report-title">检验报告单</div>
            <div class="report-no">报告编号：{report_no} &nbsp;&nbsp; 打印时间：{now_str}</div>
        </div>

        <div class="patient-info">
            <div class="item"><span class="label">姓名：</span><span class="value">{patient.name if patient else '-'}</span></div>
            <div class="item"><span class="label">编号：</span><span class="value">{patient.patient_no if patient else '-'}</span></div>
            <div class="item"><span class="label">性别：</span><span class="value">{patient.gender if patient and patient.gender else '-'}</span></div>
            <div class="item"><span class="label">条码：</span><span class="value">{specimen.barcode}</span></div>
            <div class="item"><span class="label">标本类型：</span><span class="value">{specimen.sample_type or '-'}</span></div>
            <div class="item"><span class="label">采集时间：</span><span class="value">{specimen.collect_time.strftime('%Y-%m-%d %H:%M') if specimen.collect_time else '-'}</span></div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>项目名称</th>
                    <th>项目编码</th>
                    <th>结果</th>
                    <th>单位</th>
                    <th>参考范围</th>
                    <th>异常标记</th>
                </tr>
            </thead>
            <tbody>
                {result_rows}
            </tbody>
        </table>

        <div class="footer">
            <div class="sig"><span class="label">检验者：</span>{specimen.receiver or '____________'}</div>
            <div class="sig"><span class="label">审核者：</span>{'____________'}</div>
            <div class="sig"><span class="label">报告日期：</span>{now_str}</div>
        </div>

        <div style="text-align:center; margin-top:20px; font-size:11px; color:#999;">
            ※ 本报告仅对本次送检标本负责，如有疑问请在7日内与检验科联系
        </div>
    </div>
    </body></html>
    """

    report = TestReport(
        report_no=report_no,
        order_id=specimen.order_id,
        patient_id=specimen.patient_id,
        specimen_id=specimen.id,
        status="DRAFT",
        report_html=report_html,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return {"message": "报告生成成功", "report_id": report.id, "report_no": report.report_no}


@router.get("/{report_id}")
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestReport).where(TestReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "报告不存在")
    return {
        "id": report.id,
        "report_no": report.report_no,
        "status": report.status,
        "report_html": report.report_html,
        "created_at": report.created_at,
    }


@router.post("/{report_id}/review")
async def review_report(
    report_id: int, reviewer: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    check_permission_or_raise(current_user.role, "report:review")

    result = await db.execute(select(TestReport).where(TestReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "报告不存在")
    if report.status not in ("DRAFT",):
        raise HTTPException(400, f"当前状态 {report.status} 不允许审核")

    report.status = "REVIEWED"
    report.reviewed_by = reviewer
    report.reviewed_at = datetime.now()
    await db.commit()
    return {"message": "审核通过"}
