# 2workbench/feature/ai/tools/world_tools.py
"""世界工具 — 移动、NPC关系等"""
from __future__ import annotations

from langchain_core.tools import tool
from foundation.logger import get_logger

from feature.ai.tools.context import get_tool_context

logger = get_logger(__name__)


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
