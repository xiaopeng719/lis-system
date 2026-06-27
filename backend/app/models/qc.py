from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, func
from app.database import Base


class QcRecord(Base):
    __tablename__ = "qc_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    test_item_id = Column(Integer, ForeignKey("test_items.id"), nullable=False)
    qc_level = Column(String(20))             # L1/L2/L3
    qc_lot = Column(String(50))
    result_value = Column(Numeric(12, 4))
    mean_value = Column(Numeric(12, 4))
    sd_value = Column(Numeric(12, 4))
    deviation = Column(Numeric(12, 4))
    is_in_control = Column(Boolean)
    rule_violated = Column(String(100))
    record_time = Column(DateTime)
    operator = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
