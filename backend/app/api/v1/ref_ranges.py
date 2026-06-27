from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.test_item import TestItem, ReferenceRange
from app.models.patient import Patient
from app.models.audit_log import AuditLog
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("")
async def get_ref_ranges(
    test_item_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取参考范围列表"""
    query = select(ReferenceRange).order_by(ReferenceRange.test_item_id, ReferenceRange.gender)
    if test_item_id:
        query = query.where(ReferenceRange.test_item_id == test_item_id)
    result = await db.execute(query)
    ranges = result.scalars().all()
    return [
        {
            "id": r.id, "test_item_id": r.test_item_id,
            "gender": r.gender, "age_min": r.age_min, "age_max": r.age_max,
            "ref_low": float(r.ref_low) if r.ref_low else None,
            "ref_high": float(r.ref_high) if r.ref_high else None,
        }
        for r in ranges
    ]


@router.get("/lookup")
async def lookup_ref_range(
    test_item_id: int = Query(...),
    gender: str = Query(None),
    age: int = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """根据项目、性别、年龄查找适用的参考范围"""
    # 优先匹配：性别+年龄 > 性别 > 通用
    query = (
        select(ReferenceRange)
        .where(ReferenceRange.test_item_id == test_item_id)
        .order_by(ReferenceRange.gender.desc())  # 非空排前面
    )
    result = await db.execute(query)
    ranges = result.scalars().all()

    # 筛选匹配的范围
    for r in ranges:
        gender_match = (not r.gender) or (r.gender == gender)
        age_match = True
        if age is not None:
            if r.age_min is not None and age < r.age_min:
                age_match = False
            if r.age_max is not None and age > r.age_max:
                age_match = False
        if gender_match and age_match:
            return {
                "ref_low": float(r.ref_low) if r.ref_low else None,
                "ref_high": float(r.ref_high) if r.ref_high else None,
                "matched_rule": f"{r.gender or '通用'} {r.age_min or 0}-{r.age_max or '∞'}岁",
            }

    # 没有匹配的范围，返回项目默认值
    item = (await db.execute(select(TestItem).where(TestItem.id == test_item_id))).scalar_one_or_none()
    if item:
        return {
            "ref_low": float(item.ref_range_low) if item.ref_range_low else None,
            "ref_high": float(item.ref_range_high) if item.ref_range_high else None,
            "matched_rule": "默认",
        }
    return {"ref_low": None, "ref_high": None, "matched_rule": "无"}


@router.post("")
async def create_ref_range(data: dict, db: AsyncSession = Depends(get_db)):
    """创建参考范围"""
    r = ReferenceRange(
        test_item_id=data["test_item_id"],
        gender=data.get("gender"),
        age_min=data.get("age_min"),
        age_max=data.get("age_max"),
        ref_low=data.get("ref_low"),
        ref_high=data.get("ref_high"),
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return {"id": r.id, "message": "创建成功"}


@router.delete("/{range_id}")
async def delete_ref_range(range_id: int, db: AsyncSession = Depends(get_db)):
    """删除参考范围"""
    r = (await db.execute(select(ReferenceRange).where(ReferenceRange.id == range_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "参考范围不存在")
    await db.delete(r)
    await db.commit()
    return {"message": "已删除"}
