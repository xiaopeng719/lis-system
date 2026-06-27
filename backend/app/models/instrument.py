from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    model = Column(String(100))
    manufacturer = Column(String(100))
    mqtt_topic = Column(String(200))
    mqtt_client_id = Column(String(100))
    data_format = Column(String(30), default="JSON")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    test_items = relationship("InstrumentTestItem", back_populates="instrument")


class InstrumentTestItem(Base):
    __tablename__ = "instrument_test_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    test_item_id = Column(Integer, ForeignKey("test_items.id"), nullable=False)
    channel_code = Column(String(30))

    instrument = relationship("Instrument", back_populates="test_items")
