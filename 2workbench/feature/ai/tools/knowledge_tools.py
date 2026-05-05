# 2workbench/feature/ai/tools/knowledge_tools.py
"""知识库工具 — 世界元素创建和查询"""
from __future__ import annotations

from langchain_core.tools import tool
from foundation.logger import get_logger

from feature.ai.tools.context import _get_db_path, _get_world_id

logger = get_logger(__name__)


@tool
def create_npc(name: str, location_name: str = "", personality: str = "neutral",
               backstory: str = "", speech_style: str = "", goals: str = "",
               mood: str = "neutral") -> str:
    """创建一个新的 NPC 角色。

    Args:
        name: NPC 名称（必填）
        location_name: 所在地点名称（可选）
        personality: 性格描述，如"热情好客"（可选）
        backstory: 背景故事（可选）
        speech_style: 说话风格描述（可选）
        goals: 目标列表，用逗号分隔（可选）
        mood: 当前心情，可选值: serene/happy/neutral/sad/angry/fearful（默认 neutral）

    Returns:
        创建结果描述
    """
    try:
        from core.models.repository import NPCRepo, LocationRepo
        db_path = _get_db_path()
        repo = NPCRepo()
        world_id = _get_world_id()

        # 如果指定了地点，查找地点 ID
        location_id = 0
        if location_name:
            loc_repo = LocationRepo()
            locations = loc_repo.get_by_world(world_id=world_id, db_path=db_path)
            for loc in locations:
                if loc.name == location_name:
                    location_id = loc.id
                    break

        # 解析目标
        goal_list = [g.strip() for g in goals.split(",") if g.strip()] if goals else []

        npc = repo.create(
            world_id=world_id,
            name=name,
            location_id=location_id,
            mood=mood,
            backstory=backstory,
            speech_style=speech_style,
            goals=goal_list,
            db_path=db_path
        )

        result = f"已创建 NPC: {npc.name} (ID: {npc.id})"
        if location_id:
            result += f"，位于 {location_name}"
        if backstory:
            result += f"。背景: {backstory[:50]}..."
        return result
    except Exception as e:
        return f"创建 NPC 失败: {str(e)}"


@tool
def search_npcs(location_name: str = "", name_keyword: str = "") -> str:
    """搜索 NPC，可按地点或名称关键词过滤。

    Args:
        location_name: 地点名称（可选）
        name_keyword: 名称关键词（可选）

    Returns:
        匹配的 NPC 列表
    """
    try:
        from core.models.repository import NPCRepo, LocationRepo
        db_path = _get_db_path()
        repo = NPCRepo()
        world_id = _get_world_id()

        npcs = repo.get_by_world(world_id=world_id, db_path=db_path)

        results = []
        for npc in npcs:
            # 按地点过滤
            if location_name and npc.location_id != 0:
                loc_repo = LocationRepo()
                loc = loc_repo.get_by_id(npc.location_id, db_path=db_path)
                if loc and loc.name != location_name:
                    continue

            # 按名称关键词过滤
            if name_keyword and name_keyword.lower() not in npc.name.lower():
                continue

            results.append(f"- {npc.name} (ID:{npc.id}, 心情:{npc.mood}, 位置ID:{npc.location_id})")

        if not results:
            return "未找到匹配的 NPC"
        return f"找到 {len(results)} 个 NPC:\n" + "\n".join(results)
    except Exception as e:
        return f"搜索 NPC 失败: {str(e)}"


@tool
def create_location(name: str, description: str = "", connections: str = "") -> str:
    """创建一个新的地点。

    Args:
        name: 地点名称（必填）
        description: 地点描述（可选）
        connections: 出口连接，格式 "方向:目标地点ID"，用逗号分隔。如 "north:2, south:3"（可选）

    Returns:
        创建结果描述
    """
    try:
        from core.models.repository import LocationRepo
        db_path = _get_db_path()
        repo = LocationRepo()
        world_id = _get_world_id()

        # 解析连接
        conn_dict = {}
        if connections:
            for part in connections.split(","):
                part = part.strip()
                if ":" in part:
                    direction, target_id = part.split(":", 1)
                    conn_dict[direction.strip()] = int(target_id.strip())

        location = repo.create(
            world_id=world_id,
            name=name,
            description=description,
            connections=conn_dict if conn_dict else None,
            db_path=db_path
        )

        result = f"已创建地点: {location.name} (ID: {location.id})"
        if description:
            result += f"。{description[:80]}"
        if conn_dict:
            result += f"。出口: {connections}"
        return result
    except Exception as e:
        return f"创建地点失败: {str(e)}"


@tool
def create_item(name: str, item_type: str = "misc", description: str = "",
                rarity: str = "common") -> str:
    """创建一个新的物品/道具模板。

    Args:
        name: 物品名称（必填）
        item_type: 物品类型，可选: weapon/armor/consumable/material/quest/misc（默认 misc）
        description: 物品描述（可选）
        rarity: 稀有度，可选: common/uncommon/rare/epic/legendary（默认 common）

    Returns:
        创建结果描述
    """
    try:
        from core.models.repository import ItemRepo
        db_path = _get_db_path()
        repo = ItemRepo()

        item = repo.create(
            name=name,
            item_type=item_type,
            description=description,
            rarity=rarity,
            db_path=db_path
        )

        result = f"已创建物品: {item.name} (ID: {item.id}, 类型: {item_type}, 稀有度: {rarity})"
        if description:
            result += f"。{description[:80]}"
        return result
    except Exception as e:
        return f"创建物品失败: {str(e)}"


@tool
def create_quest(title: str, description: str = "", quest_type: str = "side",
                 rewards: str = "", prerequisites: str = "") -> str:
    """创建一个新的任务/剧情。

    Args:
        title: 任务标题（必填）
        description: 任务描述（可选）
        quest_type: 任务类型，可选: main/side/daily/hidden（默认 side）
        rewards: 奖励描述（可选）
        prerequisites: 前置条件描述（可选）

    Returns:
        创建结果描述
    """
    try:
        from core.models.repository import QuestRepo
        db_path = _get_db_path()
        repo = QuestRepo()
        world_id = _get_world_id()

        quest = repo.create(
            world_id=world_id,
            title=title,
            description=description,
            quest_type=quest_type,
            rewards=rewards,
            prerequisites=prerequisites,
            db_path=db_path
        )

        result = f"已创建任务: {quest.title} (ID: {quest.id}, 类型: {quest_type})"
        if description:
            result += f"。{description[:80]}"
        if rewards:
            result += f"。奖励: {rewards}"
        return result
    except Exception as e:
        return f"创建任务失败: {str(e)}"


@tool
def get_world_state() -> str:
    """获取当前世界的完整状态概览，包括所有地点、NPC、物品和任务。

    Returns:
        世界状态摘要
    """
    try:
        from core.models.repository import LocationRepo, NPCRepo, ItemRepo, QuestRepo
        db_path = _get_db_path()
        world_id = _get_world_id()

        parts = []

        # 地点
        loc_repo = LocationRepo()
        locations = loc_repo.get_by_world(world_id=world_id, db_path=db_path)
        parts.append(f"=== 地点 ({len(locations)}) ===")
        for loc in locations:
            conn_str = ", ".join([f"{d}:{tid}" for d, tid in (loc.connections or {}).items()]) if loc.connections else "无"
            parts.append(f"  [{loc.id}] {loc.name} - 出口: {conn_str}")

        # NPC
        npc_repo = NPCRepo()
        npcs = npc_repo.get_by_world(world_id=world_id, db_path=db_path)
        parts.append(f"\n=== NPC ({len(npcs)}) ===")
        for npc in npcs:
            parts.append(f"  [{npc.id}] {npc.name} - 心情:{npc.mood}, 位置ID:{npc.location_id}")

        # 物品
        item_repo = ItemRepo()
        items = item_repo.search(name="", db_path=db_path)
        parts.append(f"\n=== 物品 ({len(items)}) ===")
        for item in items:
            parts.append(f"  [{item.id}] {item.name} - 类型:{item.item_type.value}, 稀有度:{item.rarity.value}")

        # 任务
        quest_repo = QuestRepo()
        quests = quest_repo.list_all(db_path=db_path)
        parts.append(f"\n=== 任务 ({len(quests)}) ===")
        for quest in quests:
            parts.append(f"  [{quest.id}] {quest.title} - 状态:{quest.status.value}, 类型:{quest.quest_type.value}")

        return "\n".join(parts)
    except Exception as e:
        return f"获取世界状态失败: {str(e)}"


@tool
def update_npc_state(npc_name: str, mood: str = None, location_name: str = None,
                     add_goal: str = None, remove_goal: str = None) -> str:
    """更新 NPC 的状态（心情、位置、目标等）。

    Args:
        npc_name: NPC 名称（必填，用于查找）
        mood: 新的心情（可选）
        location_name: 移动到的新地点名称（可选）
        add_goal: 添加一个目标（可选）
        remove_goal: 移除一个目标（可选）

    Returns:
        更新结果描述
    """
    try:
        from core.models.repository import NPCRepo, LocationRepo
        db_path = _get_db_path()
        repo = NPCRepo()
        world_id = _get_world_id()

        # 查找 NPC
        npcs = repo.get_by_world(world_id=world_id, db_path=db_path)
        target = None
        for npc in npcs:
            if npc.name == npc_name:
                target = npc
                break

        if not target:
            return f"未找到名为 '{npc_name}' 的 NPC"

        updates = {}
        if mood:
            updates["mood"] = mood
        if location_name:
            loc_repo = LocationRepo()
            locations = loc_repo.get_by_world(world_id=world_id, db_path=db_path)
            for loc in locations:
                if loc.name == location_name:
                    updates["location_id"] = loc.id
                    break

        # 处理目标添加/移除
        goals = list(target.goals) if target.goals else []
        if add_goal:
            goals.append(add_goal)
            updates["goals"] = goals
        if remove_goal and remove_goal in goals:
            goals.remove(remove_goal)
            updates["goals"] = goals

        if updates:
            updated = repo.update(npc.id, db_path=db_path, **updates)
            if updated:
                result = f"已更新 NPC: {npc_name}"
                if mood:
                    result += f"，心情 → {mood}"
                if location_name:
                    result += f"，移动到 {location_name}"
                if add_goal:
                    result += f"，添加目标: {add_goal}"
                if remove_goal:
                    result += f"，移除目标: {remove_goal}"
                return result

        return f"NPC {npc_name} 无需更新"
    except Exception as e:
        return f"更新 NPC 失败: {str(e)}"
