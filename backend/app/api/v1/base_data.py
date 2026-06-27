from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.department import Department
from app.models.test_item import TestItem, ComboPackage, ComboItem
from app.models.instrument import Instrument
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas import (
    DepartmentCreate, DepartmentResponse,
    TestItemCreate, TestItemResponse,
    ComboPackageCreate, ComboPackageResponse,
)
from app.utils.security import get_password_hash

router = APIRouter()


# ==================== 科室 ====================
@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).order_by(Department.id))
    return result.scalars().all()


@router.post("/departments", response_model=DepartmentResponse)
async def create_department(req: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Department).where(Department.code == req.code))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"科室编码 {req.code} 已存在")

    dept = Department(**req.model_dump())
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


# ==================== 检验项目 ====================
@router.get("/test-items", response_model=list[TestItemResponse])
async def list_test_items(
    category: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(TestItem, Instrument.name)
        .outerjoin(Instrument, TestItem.instrument_id == Instrument.id)
        .where(TestItem.is_active == True)
        .order_by(TestItem.sort_order)
    )
    if category:
        query = query.where(TestItem.category == category)
    result = await db.execute(query)
    return [
        TestItemResponse(
            **{k: v for k, v in row[0].__dict__.items() if not k.startswith('_')},
            instrument_name=row[1],
        )
        for row in result.all()
    ]


@router.post("/test-items", response_model=TestItemResponse)
async def create_test_item(req: TestItemCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(TestItem).where(TestItem.code == req.code))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"项目编码 {req.code} 已存在")

    item = TestItem(**req.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)

    instr_name = None
    if item.instrument_id:
        instr = await db.execute(select(Instrument.name).where(Instrument.id == item.instrument_id))
        instr_name = instr.scalar_one_or_none()

    db.add(AuditLog(action="CREATE", target_table="test_items", target_id=item.id,
                    detail=f"创建检验项目 {item.code} {item.name}"))
    await db.commit()

    return TestItemResponse(
        **{k: v for k, v in item.__dict__.items() if not k.startswith('_')},
        instrument_name=instr_name,
    )


@router.put("/test-items/{item_id}")
async def update_test_item(item_id: int, req: TestItemCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestItem).where(TestItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "项目不存在")

    # 检查编码重复（排除自身）
    if req.code != item.code:
        dup = await db.execute(select(TestItem).where(TestItem.code == req.code, TestItem.id != item_id))
        if dup.scalar_one_or_none():
            raise HTTPException(400, f"项目编码 {req.code} 已存在")

    for field in ['code', 'name', 'category', 'sample_type', 'unit',
                  'ref_range_low', 'ref_range_high', 'critical_low', 'critical_high',
                  'decimal_places', 'instrument_id', 'sort_order']:
        val = getattr(req, field, None)
        if val is not None:
            setattr(item, field, val)

    db.add(AuditLog(action="UPDATE", target_table="test_items", target_id=item_id,
                    detail=f"修改检验项目 {item.code} {item.name}"))
    await db.commit()
    return {"message": "修改成功"}


@router.delete("/test-items/{item_id}")
async def delete_test_item(item_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestItem).where(TestItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "项目不存在")

    item.is_active = False
    db.add(AuditLog(action="DELETE", target_table="test_items", target_id=item_id,
                    detail=f"删除检验项目 {item.code} {item.name}"))
    await db.commit()
    return {"message": "已删除"}


# ==================== 组合项目（套餐）====================
@router.get("/combos")
async def list_combos(db: AsyncSession = Depends(get_db)):
    combos = (await db.execute(
        select(ComboPackage).where(ComboPackage.is_active == True).order_by(ComboPackage.id)
    )).scalars().all()

    result = []
    for combo in combos:
        items = (await db.execute(
            select(ComboItem, TestItem.code, TestItem.name, TestItem.unit)
            .join(TestItem, ComboItem.test_item_id == TestItem.id)
            .where(ComboItem.combo_id == combo.id)
            .order_by(ComboItem.sort_order)
        )).all()
        result.append({
            "id": combo.id,
            "name": combo.name,
            "code": combo.code,
            "category": combo.category,
            "sample_type": combo.sample_type,
            "remark": combo.remark,
            "is_active": combo.is_active,
            "items": [
                {"test_item_id": row[0].test_item_id, "code": row[1], "name": row[2], "unit": row[3]}
                for row in items
            ]
        })
    return result


@router.post("/combos")
async def create_combo(req: ComboPackageCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(ComboPackage).where(ComboPackage.code == req.code))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"组合编码 {req.code} 已存在")

    combo = ComboPackage(
        name=req.name, code=req.code, category=req.category,
        sample_type=req.sample_type, remark=req.remark,
    )
    db.add(combo)
    await db.flush()

    for idx, item_id in enumerate(req.test_item_ids):
        db.add(ComboItem(combo_id=combo.id, test_item_id=item_id, sort_order=idx))

    db.add(AuditLog(action="CREATE", target_table="combo_packages", target_id=combo.id,
                    detail=f"创建组合项目 {combo.code} {combo.name}"))
    await db.commit()
    return {"id": combo.id, "name": combo.name, "code": combo.code}


@router.put("/combos/{combo_id}")
async def update_combo(combo_id: int, req: ComboPackageCreate, db: AsyncSession = Depends(get_db)):
    combo = (await db.execute(select(ComboPackage).where(ComboPackage.id == combo_id))).scalar_one_or_none()
    if not combo:
        raise HTTPException(404, "组合项目不存在")

    # 更新基本信息
    if req.name: combo.name = req.name
    if req.code: combo.code = req.code
    if req.category: combo.category = req.category
    if req.sample_type: combo.sample_type = req.sample_type
    if req.remark is not None: combo.remark = req.remark

    # 更新子项目：删除旧的，插入新的
    old_items = (await db.execute(select(ComboItem).where(ComboItem.combo_id == combo_id))).scalars().all()
    for item in old_items:
        await db.delete(item)

    for idx, item_id in enumerate(req.test_item_ids):
        db.add(ComboItem(combo_id=combo_id, test_item_id=item_id, sort_order=idx))

    db.add(AuditLog(action="UPDATE", target_table="combo_packages", target_id=combo_id,
                    detail=f"修改组合项目 {combo.code} {combo.name}"))
    await db.commit()
    return {"message": "修改成功"}


@router.delete("/combos/{combo_id}")
async def delete_combo(combo_id: int, db: AsyncSession = Depends(get_db)):
    combo = await db.execute(select(ComboPackage).where(ComboPackage.id == combo_id))
    combo = combo.scalar_one_or_none()
    if not combo:
        raise HTTPException(404, "组合项目不存在")

    items = await db.execute(select(ComboItem).where(ComboItem.combo_id == combo_id))
    for item in items.scalars().all():
        await db.delete(item)

    combo.is_active = False
    db.add(AuditLog(action="DELETE", target_table="combo_packages", target_id=combo_id,
                    detail=f"删除组合项目 {combo.code} {combo.name}"))
    await db.commit()
    return {"message": "已删除"}


# ==================== 初始化默认管理员 ====================
@router.post("/init-admin")
async def init_admin(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none():
        return {"message": "管理员已存在，跳过初始化"}

    admin = User(
        username="admin",
        password_hash=get_password_hash("admin123"),
        real_name="系统管理员",
        role="ADMIN",
        department="检验科",
    )
    db.add(admin)
    await db.commit()
    return {"message": "默认管理员已创建", "username": "admin", "password": "***"}
