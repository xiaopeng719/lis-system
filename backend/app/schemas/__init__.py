from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ==================== Auth ====================
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    username: str
    real_name: Optional[str] = None
    role: str
    department: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Patient ====================
class PatientCreate(BaseModel):
    patient_no: str
    name: str
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    id_card: Optional[str] = None

class PatientResponse(BaseModel):
    id: int
    patient_no: str
    name: str
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Specimen ====================
class SpecimenCreate(BaseModel):
    patient_id: Optional[int] = None
    order_id: Optional[int] = None
    barcode: Optional[str] = None  # 不传则自动生成
    sample_type: Optional[str] = None
    collector: Optional[str] = None
    new_patient_name: Optional[str] = None
    new_patient_gender: Optional[str] = None
    new_patient_age: Optional[int] = None
    new_patient_phone: Optional[str] = None
    test_item_ids: list[int] = []  # 检验项目 ID 列表
    combo_ids: list[int] = []      # 组合项目 ID 列表

class SpecimenReceive(BaseModel):
    receiver: str
    instrument_id: Optional[int] = None
    remark: Optional[str] = None

class SpecimenResponse(BaseModel):
    id: int
    barcode: str
    patient_id: int
    order_id: Optional[int] = None
    sample_type: Optional[str] = None
    collect_time: Optional[datetime] = None
    collector: Optional[str] = None
    receive_time: Optional[datetime] = None
    receiver: Optional[str] = None
    instrument_id: Optional[int] = None
    status: str
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    # 关联信息
    patient_name: Optional[str] = None
    patient_no: Optional[str] = None
    instrument_name: Optional[str] = None
    result_count: Optional[int] = 0

    class Config:
        from_attributes = True


# ==================== Test Order ====================
class TestOrderCreate(BaseModel):
    patient_id: int
    ordering_doctor: Optional[str] = None
    diagnosis: Optional[str] = None
    priority: str = "NORMAL"
    test_item_ids: list[int] = []

class TestOrderResponse(BaseModel):
    id: int
    order_no: str
    patient_id: int
    ordering_doctor: Optional[str] = None
    order_time: Optional[datetime] = None
    diagnosis: Optional[str] = None
    priority: str
    status: str
    created_at: Optional[datetime] = None
    patient_name: Optional[str] = None
    patient_no: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Test Result ====================
class TestResultResponse(BaseModel):
    id: int
    specimen_id: int
    test_item_id: int
    result_value: Optional[str] = None
    result_numeric: Optional[float] = None
    unit: Optional[str] = None
    ref_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # 关联
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    instrument_name: Optional[str] = None
    patient_name: Optional[str] = None
    patient_no: Optional[str] = None
    barcode: Optional[str] = None

    class Config:
        from_attributes = True

class ReviewRequest(BaseModel):
    result_ids: list[int]
    reviewer: str
    action: str = "approve"  # approve / reject

class ManualResultCreate(BaseModel):
    specimen_id: int
    test_item_id: int
    result_value: str
    result_numeric: Optional[float] = None
    unit: Optional[str] = None
    operator: str


# ==================== Test Report ====================
class TestReportResponse(BaseModel):
    id: int
    report_no: str
    order_id: Optional[int] = None
    patient_id: Optional[int] = None
    specimen_id: Optional[int] = None
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    patient_name: Optional[str] = None
    patient_no: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Instrument ====================
class InstrumentCreate(BaseModel):
    code: str
    name: str
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    data_format: str = "JSON"

class InstrumentResponse(BaseModel):
    id: int
    code: str
    name: str
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    data_format: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Department ====================
class DepartmentCreate(BaseModel):
    code: str
    name: str

class DepartmentResponse(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool

    class Config:
        from_attributes = True


# ==================== Test Item ====================
class TestItemCreate(BaseModel):
    code: str
    name: str
    category: Optional[str] = None
    sample_type: Optional[str] = None
    unit: Optional[str] = None
    ref_range_low: Optional[float] = None
    ref_range_high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    decimal_places: int = 2
    instrument_id: Optional[int] = None  # 绑定仪器
    sort_order: int = 0

class TestItemResponse(BaseModel):
    id: int
    code: str
    name: str
    category: Optional[str] = None
    sample_type: Optional[str] = None
    unit: Optional[str] = None
    ref_range_low: Optional[float] = None
    ref_range_high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    instrument_id: Optional[int] = None
    instrument_name: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# ==================== Combo Package ====================
class ComboPackageCreate(BaseModel):
    name: str
    code: str
    category: Optional[str] = None
    sample_type: Optional[str] = None
    remark: Optional[str] = None
    test_item_ids: list[int] = []  # 包含的检验项目

class ComboPackageResponse(BaseModel):
    id: int
    name: str
    code: str
    category: Optional[str] = None
    sample_type: Optional[str] = None
    remark: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    items: list = []  # 组合包含的项目列表

    class Config:
        from_attributes = True


# ==================== Common ====================
class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int

class DashboardStats(BaseModel):
    today_orders: int = 0
    today_specimens: int = 0
    today_results: int = 0
    pending_review: int = 0
    urgent_count: int = 0
    abnormal_count: int = 0
    critical_count: int = 0
