# 2workbench/feature/ai/tools/quest_tools.py
"""任务工具 — 任务状态管理"""
from __future__ import annotations

from langchain_core.tools import tool
from foundation.logger import get_logger

from feature.ai.tools.context import get_tool_context

logger = get_logger(__name__)


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
