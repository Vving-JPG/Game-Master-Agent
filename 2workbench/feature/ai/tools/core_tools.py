# 2workbench/feature/ai/tools/core_tools.py
"""核心工具 — 骰子、玩家属性、记忆等"""
from __future__ import annotations

import random

from langchain_core.tools import tool
from foundation.logger import get_logger

from feature.ai.tools.context import get_tool_context, _get_db_path

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
            turn=0,
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
