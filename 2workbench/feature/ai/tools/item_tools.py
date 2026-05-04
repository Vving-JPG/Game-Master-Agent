# 2workbench/feature/ai/tools/item_tools.py
"""物品工具 — 给予/移除物品"""
from __future__ import annotations

from langchain_core.tools import tool
from foundation.logger import get_logger

from feature.ai.tools.context import get_tool_context

logger = get_logger(__name__)


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
