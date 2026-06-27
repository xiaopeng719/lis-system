from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime
from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_no = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    gender = Column(String(10))           # 男/女
    age = Column(Integer)                 # 年龄
    birth_date = Column(Date)
    phone = Column(String(20))
    id_card = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
