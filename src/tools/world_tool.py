"""世界状态工具 - 查询和更新世界状态"""
from src.models import world_repo, location_repo, npc_repo, player_repo
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 当前活跃的世界ID和玩家ID（由GameMaster设置）
_active_world_id = None
_active_player_id = None


def set_active(world_id: int, player_id: int):
    """设置当前活跃的世界和玩家"""
    global _active_world_id, _active_player_id
    _active_world_id = world_id
    _active_player_id = player_id


def query_world_state(aspect: str | None = None, db_path: str | None = None) -> str:
    """查询世界状态

    Args:
        aspect: 查询方面 (overview/player_location/active_quests)
    """
    wid = _active_world_id
    pid = _active_player_id

    if aspect == "player_location":
        player = player_repo.get_player(pid, db_path)
        if player and player["location_id"]:
            loc = location_repo.get_location(player["location_id"], db_path)
            return f"玩家位于: {loc['name']} - {loc['description']}"
        return "玩家位置未知"

    elif aspect == "active_quests":
        from src.models import quest_repo
        quests = quest_repo.get_quests_by_player(pid, db_path)
        active = [q for q in quests if q["status"] == "active"]
        if not active:
            return "当前没有活跃任务"
        lines = [f"- {q['title']}: {q['description']}" for q in active]
        return "活跃任务:\n" + "\n".join(lines)

    else:  # overview
        world = world_repo.get_world(wid, db_path)
        player = player_repo.get_player(pid, db_path)
        lines = [f"世界: {world['name']} ({world['setting']})"]
        if player:
            lines.append(f"玩家: {player['name']} | HP: {player['hp']}/{player['max_hp']} | MP: {player['mp']}/{player['max_mp']} | 等级: {player['level']} | 金币: {player['gold']}")
            if player["location_id"]:
                loc = location_repo.get_location(player["location_id"], db_path)
                lines.append(f"位置: {loc['name']}")
        return "\n".join(lines)


def update_world_state(aspect: str, value: str, db_path: str | None = None) -> str:
    """更新世界状态"""
    pid = _active_player_id

    if aspect == "player_location":
        try:
            loc_id = int(value)
            player_repo.update_player(pid, location_id=loc_id, db_path=db_path)
            loc = location_repo.get_location(loc_id, db_path)
            logger.info(f"玩家移动到: {loc['name']}")
            return f"玩家已移动到: {loc['name']}"
        except (ValueError, Exception) as e:
            return f"移动失败: {e}"
    else:
        return f"暂不支持更新 '{aspect}'"


def get_location_info(location_id: int, db_path: str | None = None) -> str:
    """获取地点信息"""
    loc = location_repo.get_location(location_id, db_path)
    if not loc:
        return f"未找到ID为{location_id}的地点"
    lines = [f"【{loc['name']}】"]
    lines.append(loc["description"])
    if loc["connections"]:
        exits = []
        for direction, dest_id in loc["connections"].items():
            if dest_id:
                dest = location_repo.get_location(dest_id, db_path)
                if dest:
                    exits.append(f"{direction}: {dest['name']}")
        if exits:
            lines.append("出口: " + ", ".join(exits))
    return "\n".join(lines)


def list_npcs_at_location(location_id: int, db_path: str | None = None) -> str:
    """列出地点中的NPC"""
    npcs = npc_repo.get_npcs_by_location(location_id, db_path)
    if not npcs:
        return "这里没有NPC"
    lines = []
    for npc in npcs:
        mood = npc.get("mood", "neutral")
        lines.append(f"- {npc['name']} (心情: {mood})")
    return "这里的NPC:\n" + "\n".join(lines)
