"""管理端 - AI 监控路由"""
from fastapi import APIRouter
from src.models import metrics_repo

router = APIRouter(prefix="/api/admin/monitor", tags=["管理端-监控"])


@router.get("/calls")
def get_recent_calls(world_id: int | None = None, limit: int = 50):
    """获取最近的 LLM 调用记录"""
    return metrics_repo.get_recent_calls(world_id, limit)


@router.get("/stats")
def get_stats():
    """获取 Token 消耗统计"""
    return metrics_repo.get_token_stats()
