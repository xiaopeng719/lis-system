"""
种子数据脚本 — 初始化基础数据
运行方式: cd backend && python -m app.seed
"""
import asyncio
from app.database import engine, Base, AsyncSessionLocal
from app.models import *  # noqa
from app.utils.security import get_password_hash


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select, func

        r = await db.execute(select(func.count(User.id)))
        if r.scalar() > 0:
            print("⏭️  数据库已有数据，跳过 seed")
            return

        print("🌱 开始初始化种子数据...")

        # 1. 管理员
        db.add(User(
            username="admin", password_hash=get_password_hash("admin123"),
            real_name="系统管理员", role="ADMIN", department="检验科",
        ))
        db.add(User(
            username="technician", password_hash=get_password_hash("tech123"),
            real_name="张检验", role="TECHNICIAN", department="检验科",
        ))

        # 2. 科室
        db.add_all([
            Department(code="LAB", name="检验科"),
            Department(code="ICU", name="ICU"),
            Department(code="ER", name="急诊科"),
            Department(code="IM", name="内科"),
            Department(code="SUR", name="外科"),
        ])

        # 3. 检验项目（绑定仪器 + 危急值）
        # instrument_id=1 → CBC-001（血常规）, instrument_id=2 → CHEM-001（生化）
        db.add_all([
            TestItem(code="WBC", name="白细胞计数", category="血常规", sample_type="全血",
                     unit="×10⁹/L", ref_range_low=4.0, ref_range_high=10.0,
                     critical_low=2.0, critical_high=30.0, instrument_id=1, sort_order=1),
            TestItem(code="RBC", name="红细胞计数", category="血常规", sample_type="全血",
                     unit="×10¹²/L", ref_range_low=3.5, ref_range_high=5.5,
                     critical_low=2.0, critical_high=7.0, instrument_id=1, sort_order=2),
            TestItem(code="HGB", name="血红蛋白", category="血常规", sample_type="全血",
                     unit="g/L", ref_range_low=110, ref_range_high=160,
                     critical_low=50, critical_high=200, instrument_id=1, sort_order=3),
            TestItem(code="PLT", name="血小板计数", category="血常规", sample_type="全血",
                     unit="×10⁹/L", ref_range_low=100, ref_range_high=300,
                     critical_low=30, critical_high=1000, instrument_id=1, sort_order=4),
            TestItem(code="GLU", name="葡萄糖", category="生化", sample_type="血清",
                     unit="mmol/L", ref_range_low=3.9, ref_range_high=6.1,
                     critical_low=2.2, critical_high=22.2, instrument_id=2, sort_order=10),
            TestItem(code="ALT", name="谷丙转氨酶", category="生化", sample_type="血清",
                     unit="U/L", ref_range_low=0, ref_range_high=40,
                     critical_low=None, critical_high=500, instrument_id=2, sort_order=11),
            TestItem(code="AST", name="谷草转氨酶", category="生化", sample_type="血清",
                     unit="U/L", ref_range_low=0, ref_range_high=40,
                     critical_low=None, critical_high=500, instrument_id=2, sort_order=12),
            TestItem(code="CRE", name="肌酐", category="生化", sample_type="血清",
                     unit="μmol/L", ref_range_low=44, ref_range_high=133,
                     critical_low=None, critical_high=650, instrument_id=2, sort_order=13),
            TestItem(code="BUN", name="尿素氮", category="生化", sample_type="血清",
                     unit="mmol/L", ref_range_low=2.9, ref_range_high=8.2,
                     critical_low=None, critical_high=35.7, instrument_id=2, sort_order=14),
            TestItem(code="TC", name="总胆固醇", category="生化", sample_type="血清",
                     unit="mmol/L", ref_range_low=2.8, ref_range_high=5.7,
                     critical_low=None, critical_high=None, instrument_id=2, sort_order=16),
            TestItem(code="TG", name="甘油三酯", category="生化", sample_type="血清",
                     unit="mmol/L", ref_range_low=0.3, ref_range_high=1.7,
                     critical_low=None, critical_high=None, instrument_id=2, sort_order=17),
        ])

        await db.flush()  # 获取 test_item.id 和 instrument.id

        # 4. 组合项目（套餐）
        # 血常规套餐：WBC, RBC, HGB, PLT
        combo1 = ComboPackage(code="CBC", name="血常规", category="血常规", sample_type="全血")
        db.add(combo1)
        await db.flush()
        for idx, item in enumerate(["WBC", "RBC", "HGB", "PLT"]):
            tid = (await db.execute(select(TestItem.id).where(TestItem.code == item))).scalar()
            db.add(ComboItem(combo_id=combo1.id, test_item_id=tid, sort_order=idx))

        # 肝功套餐：ALT, AST
        combo2 = ComboPackage(code="LFT", name="肝功能", category="生化", sample_type="血清")
        db.add(combo2)
        await db.flush()
        for idx, item in enumerate(["ALT", "AST"]):
            tid = (await db.execute(select(TestItem.id).where(TestItem.code == item))).scalar()
            db.add(ComboItem(combo_id=combo2.id, test_item_id=tid, sort_order=idx))

        # 肾功套餐：CRE, BUN
        combo3 = ComboPackage(code="RFT", name="肾功能", category="生化", sample_type="血清")
        db.add(combo3)
        await db.flush()
        for idx, item in enumerate(["CRE", "BUN"]):
            tid = (await db.execute(select(TestItem.id).where(TestItem.code == item))).scalar()
            db.add(ComboItem(combo_id=combo3.id, test_item_id=tid, sort_order=idx))

        # 血脂套餐：TC, TG
        combo4 = ComboPackage(code="LIP", name="血脂", category="生化", sample_type="血清")
        db.add(combo4)
        await db.flush()
        for idx, item in enumerate(["TC", "TG"]):
            tid = (await db.execute(select(TestItem.id).where(TestItem.code == item))).scalar()
            db.add(ComboItem(combo_id=combo4.id, test_item_id=tid, sort_order=idx))

        # 4. 仪器
        db.add_all([
            Instrument(code="CBC-001", name="迈瑞BC-6800", model="BC-6800",
                       manufacturer="迈瑞医疗", data_format="JSON"),
            Instrument(code="CHEM-001", name="日立7180", model="7180",
                       manufacturer="日立", data_format="JSON"),
        ])

        # 5. 示例患者
        db.add_all([
            Patient(patient_no="P20260001", name="张三", gender="男"),
            Patient(patient_no="P20260002", name="李四", gender="女"),
            Patient(patient_no="P20260003", name="王五", gender="男"),
        ])

        await db.commit()
        print("✅ 种子数据初始化完成！")
        print("   管理员: admin / admin123")
        print("   技师:   technician / tech123")


if __name__ == "__main__":
    asyncio.run(seed())
