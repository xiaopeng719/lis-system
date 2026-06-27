from fastapi import APIRouter
from app.api.v1 import (auth, patients, specimens, orders, results, reports,
                         instruments, base_data, dashboard, qc, audit,
                         settings, instruments_status, ref_ranges, channels)

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["工作台"])
router.include_router(patients.router, prefix="/patients", tags=["患者"])
router.include_router(specimens.router, prefix="/specimens", tags=["标本"])
router.include_router(orders.router, prefix="/orders", tags=["检验申请"])
router.include_router(results.router, prefix="/results", tags=["检验结果"])
router.include_router(reports.router, prefix="/reports", tags=["检验报告"])
router.include_router(instruments.router, prefix="/instruments", tags=["仪器"])
router.include_router(instruments_status.router, prefix="/instrument-status", tags=["仪器状态"])
router.include_router(base_data.router, prefix="/base-data", tags=["基础数据"])
router.include_router(qc.router, prefix="/qc", tags=["质控管理"])
router.include_router(settings.router, prefix="/settings", tags=["系统设置"])
router.include_router(ref_ranges.router, prefix="/ref-ranges", tags=["参考范围"])
router.include_router(channels.router, prefix="/instruments", tags=["通道号管理"])
router.include_router(audit.router, tags=["操作日志"])
