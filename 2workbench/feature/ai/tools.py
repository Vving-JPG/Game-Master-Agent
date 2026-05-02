# 2workbench/feature/ai/tools.py
"""LangGraph Tools — 游戏机制工具

将游戏机制封装为 LangChain Tool 格式，供 LLM 在推理时调用。
这些工具通过 LangGraph 的 ToolNode 执行。
"""
from __future__ import annotations

import random
from typing import Any

from langchain_core.tools import tool
from foundation.logger import get_logger

logger = get_logger(__name__)


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
        value: 新的值（如果是负数则减少）
        player_id: 玩家 ID

    Returns:
        更新结果描述
    """
    valid_stats = {"hp", "mp", "exp", "gold", "level"}
    if stat_name not in valid_stats:
        return f"无效的属性名: {stat_name}，可用: {valid_stats}"
    return f"玩家属性已更新: {stat_name} = {value}"


@tool
def give_item(item_name: str, quantity: int = 1, player_id: int = 0) -> str:
    """给予玩家道具。

    Args:
        item_name: 道具名称
        quantity: 数量
        player_id: 玩家 ID

    Returns:
        给予结果描述
    """
    return f"已给予玩家 {quantity} 个 {item_name}"


@tool
def remove_item(item_name: str, quantity: int = 1, player_id: int = 0) -> str:
    """从玩家身上移除道具。

    Args:
        item_name: 道具名称
        quantity: 数量

    Returns:
        移除结果描述
    """
    return f"已从玩家身上移除 {quantity} 个 {item_name}"


@tool
def move_to_location(location_name: str, player_id: int = 0) -> str:
    """移动玩家到指定地点。

    Args:
        location_name: 目标地点名称
        player_id: 玩家 ID

    Returns:
        移动结果描述
    """
    return f"玩家已移动到: {location_name}"


@tool
def update_npc_relationship(npc_name: str, change: int, player_id: int = 0) -> str:
    """修改 NPC 对玩家的关系值。

    Args:
        npc_name: NPC 名称
        change: 关系值变化（正数=好感增加，负数=好感降低）
        player_id: 玩家 ID

    Returns:
        关系变化描述
    """
    direction = "增加" if change > 0 else "降低"
    return f"{npc_name} 对玩家的好感度{direction}了 {abs(change)} 点"


@tool
def update_quest_status(quest_title: str, status: str) -> str:
    """更新任务状态。

    Args:
        quest_title: 任务标题
        status: 新状态（active, completed, failed）

    Returns:
        任务状态更新描述
    """
    valid = {"active", "completed", "failed"}
    if status not in valid:
        return f"无效的任务状态: {status}，可用: {valid}"
    return f"任务 [{quest_title}] 状态已更新为: {status}"


@tool
def store_memory(content: str, category: str, importance: float = 0.5) -> str:
    """存储一条记忆（用于后续检索）。

    Args:
        content: 记忆内容
        category: 类别（npc, location, player, quest, world, session）
        importance: 重要性 0.0-1.0

    Returns:
        存储结果
    """
    valid = {"npc", "location", "player", "quest", "world", "session"}
    if category not in valid:
        return f"无效的记忆类别: {category}，可用: {valid}"
    return f"记忆已存储: [{category}] {content[:50]}..."


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
    return [convert_to_openai_tool(t) for t in ALL_TOOLS]
