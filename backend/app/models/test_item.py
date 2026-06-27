from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, func
from app.database import Base


class TestItem(Base):
    __tablename__ = "test_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))          # 血常规/生化/免疫/尿液
    sample_type = Column(String(30))       # 血清/尿液/全血
    unit = Column(String(20))
    ref_range_low = Column(Numeric(10, 3))
    ref_range_high = Column(Numeric(10, 3))
    critical_low = Column(Numeric(10, 3))       # 危急值下限
    critical_high = Column(Numeric(10, 3))      # 危急值上限
    decimal_places = Column(Integer, default=2)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=True)  # 绑定仪器
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ComboPackage(Base):
    """组合项目（套餐）"""
    __tablename__ = "combo_packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)      # 如：肝功、肾功、血常规
    code = Column(String(30), unique=True, nullable=False)
    category = Column(String(50))                    # 生化/血液/免疫
    sample_type = Column(String(30))                 # 血清/全血
    remark = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ComboItem(Base):
    """组合项目明细"""
    __tablename__ = "combo_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    combo_id = Column(Integer, ForeignKey("combo_packages.id"), nullable=False)
    test_item_id = Column(Integer, ForeignKey("test_items.id"), nullable=False)
    sort_order = Column(Integer, default=0)


class ReferenceRange(Base):
    """按性别/年龄区分的参考范围"""
    __tablename__ = "reference_ranges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_item_id = Column(Integer, ForeignKey("test_items.id"), nullable=False)
    gender = Column(String(10))           # 男/女/通用(空)
    age_min = Column(Integer)             # 最小年龄（含）
    age_max = Column(Integer)             # 最大年龄（含）
    ref_low = Column(Numeric(10, 3))
    ref_high = Column(Numeric(10, 3))
    created_at = Column(DateTime, default=datetime.utcnow)
