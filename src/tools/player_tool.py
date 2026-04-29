"""玩家工具 - 查询和更新玩家信息"""
from src.models import player_repo
from src.tools import world_tool
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_player_info(db_path: str | None = None) -> str:
    """获取玩家完整信息"""
    pid = world_tool._active_player_id
    player = player_repo.get_player(pid, db_path)
    if not player:
        return "未找到玩家信息"
    lines = [
        f"【{player['name']}】",
        f"HP: {player['hp']}/{player['max_hp']} | MP: {player['mp']}/{player['max_mp']}",
        f"等级: {player['level']} | 经验: {player['exp']} | 金币: {player['gold']}",
    ]
    inventory = player_repo.get_inventory(pid, db_path)
    if inventory:
        lines.append("背包:")
        for item in inventory:
            qty = f" x{item['quantity']}" if item["quantity"] > 1 else ""
            lines.append(f"  - {item['name']}({item['rarity']}){qty}")
    else:
        lines.append("背包: 空")
    return "\n".join(lines)


def update_player_info(db_path: str | None = None, **kwargs) -> str:
    """更新玩家属性"""
    pid = world_tool._active_player_id
    if not kwargs:
        return "没有指定要更新的属性"
    valid_keys = {"hp", "max_hp", "mp", "max_mp", "level", "exp", "gold", "name", "location_id"}
    updates = {k: v for k, v in kwargs.items() if k in valid_keys}
    if not updates:
        return f"无效的属性名，支持: {', '.join(valid_keys)}"
    player_repo.update_player(pid, db_path=db_path, **updates)
    logger.info(f"更新玩家属性: {updates}")
    return f"玩家属性已更新: {', '.join(f'{k}={v}' for k, v in updates.items())}"
