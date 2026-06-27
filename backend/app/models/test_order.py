from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class TestOrder(Base):
    __tablename__ = "test_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(30), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ordering_dept = Column(Integer, ForeignKey("departments.id"))
    ordering_doctor = Column(String(50))
    order_time = Column(DateTime)
    diagnosis = Column(String(500))
    priority = Column(String(20), default="NORMAL")  # NORMAL/URGENT/STAT
    status = Column(String(20), default="PENDING")    # PENDING/COLLECTED/TESTING/DONE/CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient")
    items = relationship("OrderTestItem", back_populates="order")
    specimens = relationship("Specimen", back_populates="order")


class OrderTestItem(Base):
    __tablename__ = "order_test_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("test_orders.id"), nullable=False)
    test_item_id = Column(Integer, ForeignKey("test_items.id"), nullable=False)
    status = Column(String(20), default="PENDING")

    order = relationship("TestOrder", back_populates="items")
    test_item = relationship("TestItem")
