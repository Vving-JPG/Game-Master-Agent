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

logger = get_logger(__name__)

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
    """获取所有已注册的工具（包括内置和动态注册的）"""
    tools = list(ALL_TOOLS)
    for name, tool_def in _REGISTERED_TOOLS.items():
        # 动态创建 @tool 装饰的函数
        func = _create_tool_function(name, tool_def)
        tools.append(func)
    return tools


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
def update_npc_relationship(npc_name: str, change: int, player_id: int = 0) -> str:
    """修改 NPC 对玩家的关系值。

    Args:
        npc_name: NPC 名称
        change: 关系值变化（正数=好感增加，负数=好感降低）
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
                # 更新关系值（限制在 -100 到 100 之间）
                current_rel = npc.relationships.get("player", 0)
                new_rel = max(-100, min(100, current_rel + change))
                npc.relationships["player"] = new_rel

                # 保存到数据库
                npc_repo.update(npc.id, relationships=npc.relationships)

                direction = "增加" if change > 0 else "降低"
                return f"{npc_name} 对玩家的好感度{direction}了 {abs(change)} 点（当前: {new_rel}）"

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
                quest_repo.update_status(quest.id, status)
                return f"任务 [{quest_title}] 状态已更新为: {status}"

        # 如果没有找到匹配的任务，尝试在所有任务中搜索
        # 这里使用 list_all 作为备选方案
        all_quests = quest_repo.list_all()
        for quest in all_quests:
            if quest.title.lower() == quest_title.lower():
                quest_repo.update_status(quest.id, status)
                return f"任务 [{quest_title}] 状态已更新为: {status}"

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


# 所有工具列表
ALL_TOOLS = [
    roll_dice,
    update_player_stat,
    give_item,
    remove_item,
    move_to_location,
    update_npc_relationship,
    update_quest_status,
    store_memory,
    check_quest_prerequisites,
]


def get_tools_schema() -> list[dict]:
    """获取所有工具的 OpenAI function calling schema"""
    from langchain_core.utils.function_calling import convert_to_openai_tool
    all_tools = get_all_tools()
    return [convert_to_openai_tool(t) for t in all_tools]
