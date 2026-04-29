"""游戏日志数据访问层"""
from src.services.database import get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

VALID_EVENT_TYPES = {"dialog", "combat", "quest", "discovery", "system", "death", "trade"}


def log_event(world_id: int, event_type: str, content: str, db_path: str | None = None) -> int:
    """记录游戏事件"""
    if event_type not in VALID_EVENT_TYPES:
        event_type = "system"
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO game_logs (world_id, event_type, content) VALUES (?, ?, ?)",
            (world_id, event_type, content),
        )
        return cursor.lastrowid


def get_recent_logs(world_id: int, limit: int = 50, db_path: str | None = None) -> list[dict]:
    """获取最近的游戏日志"""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM game_logs WHERE world_id = ? ORDER BY timestamp DESC LIMIT ?",
            (world_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]
