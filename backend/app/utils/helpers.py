from datetime import datetime, date
import re


def generate_order_no(prefix: str = "ORD") -> str:
    """生成申请单号: ORD20260619001"""
    now = datetime.now()
    return f"{prefix}{now.strftime('%Y%m%d')}{now.strftime('%H%M%S')}"


def generate_report_no(prefix: str = "RPT") -> str:
    """生成报告单号"""
    now = datetime.now()
    return f"{prefix}{now.strftime('%Y%m%d')}{now.strftime('%H%M%S')}"


def generate_patient_no(prefix: str = "P") -> str:
    """生成患者编号: P202606190001"""
    now = datetime.now()
    import random
    return f"{prefix}{now.strftime('%Y%m%d')}{random.randint(1000, 9999)}"


def generate_barcode(prefix: str = "SP") -> str:
    """生成标本条码"""
    now = datetime.now()
    return f"{prefix}{now.strftime('%Y%m%d%H%M%S')}"


def judge_abnormal(value: float, low: float, high: float) -> str:
    """判断结果异常标记"""
    if low is not None and value < low:
        return "L"
    if high is not None and value > high:
        return "H"
    return "N"


def format_ref_range(low, high) -> str:
    """格式化参考范围"""
    if low is not None and high is not None:
        return f"{low}-{high}"
    if low is not None:
        return f">={low}"
    if high is not None:
        return f"<={high}"
    return ""
