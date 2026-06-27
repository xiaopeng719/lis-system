from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from app.database import Base


class TestReport(Base):
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_no = Column(String(30), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("test_orders.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    specimen_id = Column(Integer, ForeignKey("specimens.id"))
    status = Column(String(20), default="DRAFT")  # DRAFT/REVIEWED/PRINTED/REVOKED
    reviewed_by = Column(String(50))
    reviewed_at = Column(DateTime)
    printed_by = Column(String(50))
    printed_at = Column(DateTime)
    report_html = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
