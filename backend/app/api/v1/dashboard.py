from fastapi import APIRouter, Depends
from sqlalchemy import select, func, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models.test_order import TestOrder
from app.models.specimen import Specimen
from app.models.test_result import TestResult
from app.models.test_report import TestReport
from app.schemas import DashboardStats
from app.utils.permissions import check_permission_or_raise
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    today = datetime.combine(date.today(), datetime.min.time())

    # 今日申请单数
    r = await db.execute(
        select(func.count(TestOrder.id)).where(TestOrder.created_at >= today)
    )
    today_orders = r.scalar() or 0

    # 今日标本数
    r = await db.execute(
        select(func.count(Specimen.id)).where(Specimen.created_at >= today)
    )
    today_specimens = r.scalar() or 0

    # 今日结果数
    r = await db.execute(
        select(func.count(TestResult.id)).where(TestResult.created_at >= today)
    )
    today_results = r.scalar() or 0

    # 待审核数
    r = await db.execute(
        select(func.count(TestResult.id)).where(TestResult.status == "AUTO")
    )
    pending_review = r.scalar() or 0

    # 急诊数
    r = await db.execute(
        select(func.count(TestOrder.id)).where(
            TestOrder.status.in_(["PENDING", "COLLECTED", "TESTING"]),
            TestOrder.priority.in_(["URGENT", "STAT"]),
        )
    )
    urgent_count = r.scalar() or 0

    # 异常结果数
    r = await db.execute(
        select(func.count(TestResult.id)).where(
            TestResult.abnormal_flag.in_(["H", "L", "A"]),
            TestResult.created_at >= today,
        )
    )
    abnormal_count = r.scalar() or 0

    # 危急值数
    r = await db.execute(
        select(func.count(TestResult.id)).where(
            TestResult.abnormal_flag == "C",
            TestResult.created_at >= today,
        )
    )
    critical_count = r.scalar() or 0

    return DashboardStats(
        today_orders=today_orders,
        today_specimens=today_specimens,
        today_results=today_results,
        pending_review=pending_review,
        urgent_count=urgent_count,
        abnormal_count=abnormal_count,
        critical_count=critical_count,
    )


@router.get("/tat")
async def get_tat_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取按检验分类的平均 TAT（采集到出结果的分钟数）"""
    check_permission_or_raise(current_user.role, "result:view")

    thirty_days_ago = datetime.now() - timedelta(days=30)

    # TAT = 最后一个结果的 created_at - 标本的 collect_time
    # 按检验项目分类分组
    from app.models.test_item import TestItem
    query = (
        select(
            TestItem.category.label("category"),
            func.avg(
                cast(
                    func.julianday(TestResult.created_at) - func.julianday(Specimen.collect_time),
                    Float,
                ) * 24 * 60
            ).label("avg_tat_minutes"),
            func.count(func.distinct(Specimen.id)).label("specimen_count"),
        )
        .join(Specimen, TestResult.specimen_id == Specimen.id)
        .join(TestItem, TestResult.test_item_id == TestItem.id)
        .where(
            Specimen.collect_time.isnot(None),
            TestResult.created_at >= thirty_days_ago,
            TestItem.category.isnot(None),
        )
        .group_by(TestItem.category)
        .order_by(func.count(func.distinct(Specimen.id)).desc())
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "label": row.category or "其他",
            "count": row.specimen_count,
            "avg_minutes": round(abs(float(row.avg_tat_minutes)), 1) if row.avg_tat_minutes else 0,
        }
        for row in rows
        if row.avg_tat_minutes
    ]


@router.get("/notifications")
async def get_notifications(db: AsyncSession = Depends(get_db)):
    """获取危急值和异常结果通知（最近24小时）"""
    from app.models.test_item import TestItem
    from app.models.patient import Patient

    yesterday = datetime.now() - timedelta(hours=24)

    # 危急值结果
    critical_query = (
        select(TestResult, TestItem.code, TestItem.name, TestItem.unit,
               Patient.name, Specimen.barcode)
        .join(TestItem, TestResult.test_item_id == TestItem.id)
        .join(Specimen, TestResult.specimen_id == Specimen.id)
        .join(Patient, Specimen.patient_id == Patient.id)
        .where(
            TestResult.abnormal_flag == "C",
            TestResult.created_at >= yesterday,
        )
        .order_by(TestResult.created_at.desc())
        .limit(20)
    )
    critical_results = (await db.execute(critical_query)).all()

    # 异常结果（偏高/偏低）
    abnormal_query = (
        select(TestResult, TestItem.code, TestItem.name, TestItem.unit,
               Patient.name, Specimen.barcode)
        .join(TestItem, TestResult.test_item_id == TestItem.id)
        .join(Specimen, TestResult.specimen_id == Specimen.id)
        .join(Patient, Specimen.patient_id == Patient.id)
        .where(
            TestResult.abnormal_flag.in_(["H", "L"]),
            TestResult.created_at >= yesterday,
        )
        .order_by(TestResult.created_at.desc())
        .limit(10)
    )
    abnormal_results = (await db.execute(abnormal_query)).all()

    notifications = []
    for row in critical_results:
        r = row[0]
        flag_text = "↑ 偏高" if r.abnormal_flag in ("H", "C") else "↓ 偏低"
        notifications.append({
            "id": r.id,
            "type": "critical",
            "title": "危急值警报",
            "message": f"患者{row[4]} {row[2]} {r.result_value} {row[3] or ''} (危急值{flag_text})",
            "time": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            "read": False,
        })

    for row in abnormal_results:
        r = row[0]
        flag_text = "↑ 偏高" if r.abnormal_flag == "H" else "↓ 偏低"
        notifications.append({
            "id": r.id + 10000,
            "type": "warning",
            "title": "异常结果",
            "message": f"患者{row[4]} {row[2]} {r.result_value} {row[3] or ''} ({flag_text})",
            "time": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            "read": False,
        })

    return notifications
