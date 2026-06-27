from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, func
from app.database import Base


class MqttMessageLog(Base):
    __tablename__ = "mqtt_message_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    topic = Column(String(500))
    payload = Column(Text)
    instrument_id = Column(Integer)
    parse_status = Column(String(20))       # SUCCESS/FAILED
    error_message = Column(String(1000))
    received_at = Column(DateTime, default=datetime.utcnow)
