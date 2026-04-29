"""日志工具 - 记录游戏事件"""
from src.models import log_repo
from src.tools import world_tool
from src.utils.logger import get_logger

logger = get_logger(__name__)


def log_event(event_type: str, content: str, db_path: str | None = None) -> str:
    """记录游戏事件

    Args:
        event_type: dialog/combat/quest/discovery/system/death/trade
        content: 事件内容
    """
    wid = world_tool._active_world_id
    log_repo.log_event(wid, event_type, content, db_path)
    logger.info(f"[{event_type}] {content}")
    return f"事件已记录: [{event_type}] {content}"
