"""管理端 - 日志和对话记录路由"""
from fastapi import APIRouter
from src.models import log_repo
from src.services.database import get_db

router = APIRouter(prefix="/api/admin/logs", tags=["管理端-日志"])


@router.get("/game-events")
def get_game_events(world_id: int, limit: int = 100, event_type: str | None = None):
    """获取游戏事件日志"""
    logs = log_repo.get_recent_logs(world_id, limit)
    if event_type:
        logs = [l for l in logs if l["event_type"] == event_type]
    return logs


@router.get("/conversations")
def get_conversations(world_id: int, limit: int = 100):
    """获取对话历史"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM game_messages WHERE world_id = ? ORDER BY timestamp ASC LIMIT ?",
            (world_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/conversations/search")
def search_conversations(world_id: int, keyword: str):
    """搜索对话内容"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM game_messages WHERE world_id = ? AND content LIKE ? ORDER BY timestamp DESC LIMIT 50",
            (world_id, f"%{keyword}%"),
        ).fetchall()
    return [dict(r) for r in rows]
