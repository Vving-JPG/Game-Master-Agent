# 2workbench/feature/ai/tools/__init__.py
"""LangGraph Tools — 游戏机制工具包

将游戏机制封装为 LangChain Tool 格式，供 LLM 在推理时调用。
"""
from __future__ import annotations

from feature.ai.tools.context import ToolContext, set_tool_context, get_tool_context
from feature.ai.tools.core_tools import (
    roll_dice,
    update_player_stat,
    store_memory,
    check_quest_prerequisites,
)
from feature.ai.tools.item_tools import give_item, remove_item
from feature.ai.tools.world_tools import move_to_location, update_npc_relationship
from feature.ai.tools.quest_tools import update_quest_status
from feature.ai.tools.knowledge_tools import (
    create_npc,
    search_npcs,
    create_location,
    create_item,
    create_quest,
    get_world_state,
    update_npc_state,
)
from feature.ai.tools.registry import (
    register_tool,
    get_all_tools,
    get_all_tools_info,
    get_tools_schema,
)

# 导入并初始化工具注册服务（自动订阅 EventBus）
from feature.ai.tools.tool_registration_service import tool_registration_service

# 所有内置工具列表
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
    create_npc,
    search_npcs,
    create_location,
    create_item,
    create_quest,
    get_world_state,
    update_npc_state,
]

__all__ = [
    # 上下文
    "ToolContext",
    "set_tool_context",
    "get_tool_context",
    # 核心工具
    "roll_dice",
    "update_player_stat",
    "store_memory",
    "check_quest_prerequisites",
    # 物品工具
    "give_item",
    "remove_item",
    # 世界工具
    "move_to_location",
    "update_npc_relationship",
    # 任务工具
    "update_quest_status",
    # 知识库工具
    "create_npc",
    "search_npcs",
    "create_location",
    "create_item",
    "create_quest",
    "get_world_state",
    "update_npc_state",
    # 注册表
    "register_tool",
    "get_all_tools",
    "get_all_tools_info",
    "get_tools_schema",
    # 工具列表
    "ALL_TOOLS",
]
