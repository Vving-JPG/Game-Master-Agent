# 2workbench/feature/ai/tools.py
"""LangGraph Tools — 游戏机制工具

将游戏机制封装为 LangChain Tool 格式，供 LLM 在推理时调用。
这些工具通过 LangGraph 的 ToolNode 执行。
"""
from __future__ import annotations

import random
from typing import Any, Callable

from langchain_core.tools import tool
from foundation.logger import get_logger
from core.models.repository import NPCRepo, LocationRepo, ItemRepo, QuestRepo
from core.models.entities import ItemType, QuestType, QuestStatus
from foundation.config import settings

logger = get_logger(__name__)


def _get_db_path() -> str:
    """获取数据库路径"""
    return getattr(settings, 'database_path', 'data/game.db')


# === 工具上下文 ===
class ToolContext:
    """工具执行上下文 — 让工具能访问数据库"""

    def __init__(self, db_path: str, world_id: str, player_id: int):
        self.db_path = db_path
        self.world_id = world_id
        self.player_id = player_id
        self._repos: dict[str, Any] = {}

    def get_repo(self, repo_class) -> Any:
        """获取 Repository 实例（懒加载）"""
        if repo_class.__name__ not in self._repos:
            self._repos[repo_class.__name__] = repo_class(self.db_path)
        return self._repos[repo_class.__name__]


_tool_context: ToolContext | None = None


def set_tool_context(ctx: ToolContext | None):
    """设置当前工具上下文"""
    global _tool_context
    _tool_context = ctx


def get_tool_context() -> ToolContext | None:
    """获取当前工具上下文"""
    return _tool_context


# === 工具注册表 ===
_REGISTERED_TOOLS: dict[str, dict] = {}


def register_tool(name: str, description: str, parameters_schema: dict,
                   handler: Callable):
    """注册一个工具

    Args:
        name: 工具名称
        description: 工具描述（会作为 LLM 的 tool description）
        parameters_schema: JSON Schema 格式的参数定义
        handler: 实际执行函数
    """
    _REGISTERED_TOOLS[name] = {
        "name": name,
        "description": description,
        "parameters_schema": parameters_schema,
        "handler": handler,
    }
    logger.info(f"工具已注册: {name}")


def get_all_tools() -> list:
    """获取所有已注册的工具（包括内置和动态注册的）

    Returns:
        LangChain Tool 对象列表（用于 LangGraph 执行）
    """
    tools = list(ALL_TOOLS)
    for name, tool_def in _REGISTERED_TOOLS.items():
        # 动态创建 @tool 装饰的函数
        func = _create_tool_function(name, tool_def)
        tools.append(func)
    return tools


def get_all_tools_info() -> list[dict]:
    """获取所有工具的元数据信息（用于工具管理器显示）

    Returns:
        工具信息字典列表，每个字典包含 name, description 等字段
    """
    tools_info = []

    # 内置工具
    for tool in ALL_TOOLS:
        tools_info.append({
            "name": tool.name,
            "description": tool.description or "",
            "category": "builtin",
        })

    # 动态注册的工具
    for name, tool_def in _REGISTERED_TOOLS.items():
        tools_info.append({
            "name": name,
            "description": tool_def.get("description", ""),
            "category": "custom",
        })

    return tools_info


def _create_tool_function(name: str, tool_def: dict):
    """从注册信息动态创建 LangChain Tool"""
    handler = tool_def["handler"]

    # 创建带正确元数据的函数
    func = lambda **kwargs: handler(**kwargs)
    func.__name__ = name
    func.__doc__ = tool_def["description"]

    # 使用 @tool 装饰
    return tool(func)


@tool
def roll_dice(sides: int = 20, count: int = 1, modifier: int = 0) -> str:
    """掷骰子进行随机判定。

    Args:
        sides: 骰子面数（默认 20，即 D20）
        count: 掷骰次数（默认 1）
        modifier: 加值（默认 0）

    Returns:
        掷骰结果描述
    """
    results = [random.randint(1, sides) for _ in range(count)]
    total = sum(results) + modifier
    rolls_str = " + ".join(str(r) for r in results)
    if modifier:
        rolls_str += f" + {modifier}"
    return f"掷骰结果: [{rolls_str}] = {total}"


@tool
def update_player_stat(stat_name: str, value: int, player_id: int = 0) -> str:
    """更新玩家属性值。

    Args:
        stat_name: 属性名（hp, mp, exp, gold, level）
        value: 变化值（正数增加，负数减少）
        player_id: 玩家 ID（0 表示使用当前上下文中的玩家）

    Returns:
        更新结果描述
    """
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"

    valid_stats = {"hp", "mp", "exp", "gold", "level", "max_hp", "max_mp", "attack", "defense", "speed"}
    if stat_name not in valid_stats:
        return f"无效的属性名: {stat_name}，可用: {valid_stats}"

    try:
        from core.models.repository import PlayerRepo
        repo = ctx.get_repo(PlayerRepo)

        # 使用上下文中的玩家 ID
        pid = player_id if player_id > 0 else ctx.player_id
        player = repo.get_by_id(pid)

        if not player:
            return f"错误：玩家不存在 (ID: {pid})"

        # 获取当前值
        current = getattr(player, stat_name, 0)
        new_value = max(0, current + value)

        # HP/MP 不超过上限
        if stat_name in ("hp", "mp"):
            max_val = getattr(player, f"max_{stat_name}", 999)
            new_value = min(new_value, max_val)

        # 更新数据库
        repo.update(pid, **{stat_name: new_value})

        return f"玩家属性已更新: {stat_name} {current} → {new_value} ({value:+d})"
    except Exception as e:
        logger.error(f"更新玩家属性失败: {e}")
        return f"错误：{e}"


@tool
def give_item(item_name: str, quantity: int = 1, player_id: int = 0) -> str:
    """给予玩家道具。

    Args:
        item_name: 道具名称
        quantity: 数量
        player_id: 玩家 ID（0 表示使用当前上下文中的玩家）

    Returns:
        给予结果描述
    """
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"

    try:
        from core.models.repository import ItemRepo, PlayerRepo
        item_repo = ctx.get_repo(ItemRepo)
        player_repo = ctx.get_repo(PlayerRepo)

        pid = player_id if player_id > 0 else ctx.player_id

        # 查找或创建物品
        items = item_repo.search(name=item_name)
        if items:
            item = items[0]
        else:
            # 创建新物品
            item = item_repo.create(
                name=item_name,
                description=f"由 AI 生成的物品: {item_name}",
                item_type="misc",
                world_id=int(ctx.world_id) if ctx.world_id else 1,
            )

        # 添加到玩家背包
        player_repo.add_item(pid, item.id, quantity)

        return f"已给予玩家 {quantity} 个 {item_name}"
    except Exception as e:
        logger.error(f"给予物品失败: {e}")
        return f"错误：{e}"


@tool
def remove_item(item_name: str, quantity: int = 1, player_id: int = 0) -> str:
    """从玩家身上移除道具。

    Args:
        item_name: 道具名称
        quantity: 数量
        player_id: 玩家 ID（0 表示使用当前上下文中的玩家）

    Returns:
        移除结果描述
    """
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"

    try:
        from core.models.repository import ItemRepo, PlayerRepo
        item_repo = ctx.get_repo(ItemRepo)
        player_repo = ctx.get_repo(PlayerRepo)

        pid = player_id if player_id > 0 else ctx.player_id

        # 查找物品
        items = item_repo.search(name=item_name)
        if not items:
            return f"错误：物品 '{item_name}' 不存在"

        item = items[0]

        # 从玩家背包移除
        player_repo.remove_item(pid, item.id, quantity)

        return f"已从玩家身上移除 {quantity} 个 {item_name}"
    except Exception as e:
        logger.error(f"移除物品失败: {e}")
        return f"错误：{e}"


@tool
def move_to_location(location_name: str, player_id: int = 0) -> str:
    """移动玩家到指定地点。

    Args:
        location_name: 目标地点名称
        player_id: 玩家 ID（0 表示使用当前上下文中的玩家）

    Returns:
        移动结果描述
    """
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"

    try:
        from core.models.repository import LocationRepo, PlayerRepo
        location_repo = ctx.get_repo(LocationRepo)
        player_repo = ctx.get_repo(PlayerRepo)

        pid = player_id if player_id > 0 else ctx.player_id

        # 查找地点
        locations = location_repo.search(name=location_name)
        if not locations:
            return f"错误：地点 '{location_name}' 不存在"

        location = locations[0]

        # 更新玩家位置
        player_repo.update(pid, current_location_id=location.id)

        return f"玩家已移动到: {location_name}"
    except Exception as e:
        logger.error(f"移动玩家失败: {e}")
        return f"错误：{e}"


@tool
def update_npc_relationship(npc_name: str, change: float, player_id: int = 0) -> str:
    """修改 NPC 对玩家的关系值。

    Args:
        npc_name: NPC 名称
        change: 关系值变化（正数=好感增加，负数=好感降低），范围 -1.0 到 1.0
        player_id: 玩家 ID（0 表示使用当前上下文中的玩家）

    Returns:
        关系变化描述
    """
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"

    try:
        from core.models.repository import NPCRepo
        npc_repo = ctx.get_repo(NPCRepo)

        # 获取世界中的所有 NPC
        npcs = npc_repo.get_by_world(int(ctx.world_id) if ctx.world_id else 1)

        # 查找匹配的 NPC
        for npc in npcs:
            if npc.name == npc_name:
                # 更新关系值（限制在 -1.0 到 1.0 之间）
                current_rel = npc.relationships.get("player", 0.0)
                new_rel = max(-1.0, min(1.0, current_rel + change))
                npc.relationships["player"] = new_rel

                # 保存到数据库
                npc_repo.update(npc.id, relationships=npc.relationships)

                direction = "增加" if change > 0 else "降低"
                return f"{npc_name} 对玩家的好感度{direction}了 {abs(change):.2f}（当前: {new_rel:.2f}）"

        return f"错误：未找到 NPC '{npc_name}'"
    except Exception as e:
        logger.error(f"更新 NPC 关系失败: {e}")
        return f"错误：{e}"


@tool
def update_quest_status(quest_title: str, status: str) -> str:
    """更新任务状态。

    Args:
        quest_title: 任务标题
        status: 新状态（active, completed, failed, abandoned）

    Returns:
        任务状态更新描述
    """
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"

    valid = {"active", "completed", "failed", "abandoned"}
    if status not in valid:
        return f"无效的任务状态: {status}，可用: {valid}"

    try:
        from core.models.repository import QuestRepo
        quest_repo = ctx.get_repo(QuestRepo)

        # 获取玩家相关的所有任务
        quests = quest_repo.get_by_player(ctx.player_id)

        # 查找匹配标题的任务
        for quest in quests:
            if quest.title.lower() == quest_title.lower():
                # 更新任务状态
                success = quest_repo.update_status(quest.id, status)
                if success:
                    return f"任务 [{quest_title}] 状态已更新为: {status}"
                else:
                    return f"错误：无法将任务 [{quest_title}] 状态更新为 {status}"

        # 如果没有找到匹配的任务，尝试在所有任务中搜索
        # 这里使用 list_all 作为备选方案
        all_quests = quest_repo.list_all()
        for quest in all_quests:
            if quest.title.lower() == quest_title.lower():
                success = quest_repo.update_status(quest.id, status)
                if success:
                    return f"任务 [{quest_title}] 状态已更新为: {status}"
                else:
                    return f"错误：无法将任务 [{quest_title}] 状态更新为 {status}"

        return f"错误：未找到任务 '{quest_title}'"
    except Exception as e:
        logger.error(f"更新任务状态失败: {e}")
        return f"错误：{e}"


@tool
def store_memory(content: str, category: str, importance: float = 0.5, player_id: int = 0) -> str:
    """存储一条记忆（用于后续检索）。

    Args:
        content: 记忆内容
        category: 类别（npc, location, player, quest, world, session）
        importance: 重要性 0.0-1.0
        player_id: 玩家 ID（0 表示使用当前上下文中的玩家）

    Returns:
        存储结果
    """
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"

    valid = {"npc", "location", "player", "quest", "world", "session"}
    if category not in valid:
        return f"无效的记忆类别: {category}，可用: {valid}"

    try:
        from core.models.repository import MemoryRepo
        memory_repo = ctx.get_repo(MemoryRepo)

        world_id = int(ctx.world_id) if ctx.world_id else 1
        pid = player_id if player_id > 0 else ctx.player_id

        # 存储记忆到数据库
        memory = memory_repo.store(
            world_id=world_id,
            category=category,
            source=f"player_{pid}",
            content=content,
            importance=max(0.0, min(1.0, importance)),
            turn=0,  # 可以从 AgentState 获取当前回合
        )

        return f"记忆已存储: [{category}] {content[:50]}... (id={memory.id})"
    except Exception as e:
        logger.error(f"存储记忆失败: {e}")
        return f"错误：{e}"


@tool
def check_quest_prerequisites(quest_title: str) -> str:
    """检查任务的前置条件是否满足。

    Args:
        quest_title: 任务标题

    Returns:
        前置条件检查结果
    """
    return f"任务 [{quest_title}] 的前置条件检查完成。"


# ============================================================
# 知识库管理工具 — 让 AI 自动创建/查询世界元素
# ============================================================

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
        db_path = _get_db_path()
        repo = NPCRepo()

        # 如果指定了地点，查找地点 ID
        location_id = 0
        if location_name:
            loc_repo = LocationRepo()
            locations = loc_repo.get_by_world(world_id=1, db_path=db_path)
            for loc in locations:
                if loc.name == location_name:
                    location_id = loc.id
                    break

        # 解析目标
        goal_list = [g.strip() for g in goals.split(",") if g.strip()] if goals else []

        npc = repo.create(
            world_id=1,
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
        db_path = _get_db_path()
        repo = NPCRepo()

        npcs = repo.get_by_world(world_id=1, db_path=db_path)

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
        db_path = _get_db_path()
        repo = LocationRepo()

        # 解析连接
        conn_dict = {}
        if connections:
            for part in connections.split(","):
                part = part.strip()
                if ":" in part:
                    direction, target_id = part.split(":", 1)
                    conn_dict[direction.strip()] = int(target_id.strip())

        location = repo.create(
            world_id=1,
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
        db_path = _get_db_path()
        repo = ItemRepo()

        item = repo.create(
            name=name,
            item_type=item_type,
            description=description,
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
        db_path = _get_db_path()
        repo = QuestRepo()

        quest = repo.create(
            world_id=1,
            title=title,
            description=description,
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
        db_path = _get_db_path()

        parts = []

        # 地点
        loc_repo = LocationRepo()
        locations = loc_repo.get_by_world(world_id=1, db_path=db_path)
        parts.append(f"=== 地点 ({len(locations)}) ===")
        for loc in locations:
            conn_str = ", ".join([f"{d}:{tid}" for d, tid in (loc.connections or {}).items()]) if loc.connections else "无"
            parts.append(f"  [{loc.id}] {loc.name} - 出口: {conn_str}")

        # NPC
        npc_repo = NPCRepo()
        npcs = npc_repo.get_by_world(world_id=1, db_path=db_path)
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
        db_path = _get_db_path()
        repo = NPCRepo()

        # 查找 NPC
        npcs = repo.get_by_world(world_id=1, db_path=db_path)
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
            locations = loc_repo.get_by_world(world_id=1, db_path=db_path)
            for loc in locations:
                if loc.name == location_name:
                    updates["location_id"] = loc.id
                    break

        if updates:
            updated = repo.update(npc.id, db_path=db_path, **updates)
            if updated:
                result = f"已更新 NPC: {npc_name}"
                if mood:
                    result += f"，心情 → {mood}"
                if location_name:
                    result += f"，移动到 {location_name}"
                return result

        return f"NPC {npc_name} 无需更新"
    except Exception as e:
        return f"更新 NPC 失败: {str(e)}"


# 所有工具列表
ALL_TOOLS = [
    # 原有工具
    roll_dice,
    update_player_stat,
    give_item,
    remove_item,
    move_to_location,
    update_npc_relationship,
    update_quest_status,
    store_memory,
    check_quest_prerequisites,
    # 知识库管理工具
    create_npc,
    search_npcs,
    create_location,
    create_item,
    create_quest,
    get_world_state,
    update_npc_state,
]


def get_tools_schema() -> list[dict]:
    """获取所有工具的 OpenAI function calling schema"""
    from langchain_core.utils.function_calling import convert_to_openai_tool
    all_tools = get_all_tools()
    return [convert_to_openai_tool(t) for t in all_tools]
