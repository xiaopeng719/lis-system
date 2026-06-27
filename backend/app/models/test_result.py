from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.database import Base


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    specimen_id = Column(Integer, ForeignKey("specimens.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("test_orders.id"))
    test_item_id = Column(Integer, ForeignKey("test_items.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"))
    result_value = Column(String(200))         # 结果值（兼容定性）
    result_numeric = Column(Numeric(12, 4))    # 数值结果
    unit = Column(String(20))
    ref_range = Column(String(50))
    abnormal_flag = Column(String(10))         # H/L/N/A
    status = Column(String(20), default="AUTO")  # AUTO/MANUAL/REVIEWED
    reviewed_by = Column(String(50))
    reviewed_at = Column(DateTime)
    raw_data = Column(Text)                    # MQTT 原始数据
    created_at = Column(DateTime, default=datetime.utcnow)

    specimen = relationship("Specimen", back_populates="results")
    test_item = relationship("TestItem")
    instrument = relationship("Instrument")
