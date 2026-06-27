from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Specimen(Base):
    __tablename__ = "specimens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barcode = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("test_orders.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    sample_type = Column(String(30))       # 血清/尿液/全血
    collect_time = Column(DateTime)
    collector = Column(String(50))
    receive_time = Column(DateTime)
    receiver = Column(String(50))
    instrument_id = Column(Integer, ForeignKey("instruments.id"))
    status = Column(String(20), default="COLLECTED")
    # COLLECTED → RECEIVED → TESTING → COMPLETED → ARCHIVED
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("TestOrder", back_populates="specimens")
    patient = relationship("Patient")
    instrument = relationship("Instrument")
    results = relationship("TestResult", back_populates="specimen")
