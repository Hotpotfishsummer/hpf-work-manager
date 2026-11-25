from fastapi import APIRouter
from app.services.quota import quota_service

router = APIRouter(prefix="/quota", tags=["quota"])


@router.get("")
async def get_quota():
    """获取当前 5 小时与周额度窗口、倒计时及调度策略建议"""
    return await quota_service.get_quota_status()


@router.get("/driver-mode")
async def get_driver_mode():
    """获取当前 Agent 驱动模式（双重认证 DUAL_CERTIFIED vs 外驱降级 EXTERNAL_DRIVEN）及行动指南"""
    return await quota_service.get_driver_mode()

