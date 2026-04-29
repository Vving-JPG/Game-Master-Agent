"""工具包 - 注册所有工具"""
from src.tools.executor import register_tool
from src.tools import dice, world_tool, player_tool, npc_tool, log_tool, quest_tool, item_tool
from src.tools.tool_definitions import (
    ROLL_DICE_SCHEMA,
    QUERY_WORLD_STATE_SCHEMA,
    UPDATE_WORLD_STATE_SCHEMA,
    GET_LOCATION_INFO_SCHEMA,
    LIST_NPCS_AT_LOCATION_SCHEMA,
    GET_PLAYER_INFO_SCHEMA,
    UPDATE_PLAYER_INFO_SCHEMA,
    GET_NPC_INFO_SCHEMA,
    SEARCH_NPC_SCHEMA,
    CREATE_NPC_SCHEMA,
    NPC_DIALOG_SCHEMA,
    UPDATE_RELATIONSHIP_SCHEMA,
    GET_RELATIONSHIP_GRAPH_SCHEMA,
    CREATE_QUEST_SCHEMA,
    UPDATE_QUEST_PROGRESS_SCHEMA,
    HANDLE_CHOICE_SCHEMA,
    CREATE_ITEM_SCHEMA,
    EQUIP_ITEM_SCHEMA,
    USE_ITEM_SCHEMA,
    GET_INVENTORY_SCHEMA,
    LOG_EVENT_SCHEMA,
)

# 注册所有工具
register_tool("roll_dice", dice.roll_dice, ROLL_DICE_SCHEMA)
register_tool("query_world_state", world_tool.query_world_state, QUERY_WORLD_STATE_SCHEMA)
register_tool("update_world_state", world_tool.update_world_state, UPDATE_WORLD_STATE_SCHEMA)
register_tool("get_location_info", world_tool.get_location_info, GET_LOCATION_INFO_SCHEMA)
register_tool("list_npcs_at_location", world_tool.list_npcs_at_location, LIST_NPCS_AT_LOCATION_SCHEMA)
register_tool("get_player_info", player_tool.get_player_info, GET_PLAYER_INFO_SCHEMA)
register_tool("update_player_info", player_tool.update_player_info, UPDATE_PLAYER_INFO_SCHEMA)
register_tool("get_npc_info", npc_tool.get_npc_info, GET_NPC_INFO_SCHEMA)
register_tool("search_npc", npc_tool.search_npc, SEARCH_NPC_SCHEMA)
register_tool("create_npc", npc_tool.create_npc, CREATE_NPC_SCHEMA)
register_tool("npc_dialog", npc_tool.npc_dialog, NPC_DIALOG_SCHEMA)
register_tool("update_relationship", npc_tool.update_relationship, UPDATE_RELATIONSHIP_SCHEMA)
register_tool("get_relationship_graph", npc_tool.get_relationship_graph, GET_RELATIONSHIP_GRAPH_SCHEMA)
register_tool("create_quest", quest_tool.create_quest, CREATE_QUEST_SCHEMA)
register_tool("update_quest_progress", quest_tool.update_quest_progress, UPDATE_QUEST_PROGRESS_SCHEMA)
register_tool("handle_choice", quest_tool.handle_choice, HANDLE_CHOICE_SCHEMA)
register_tool("create_item", item_tool.create_item, CREATE_ITEM_SCHEMA)
register_tool("equip_item", item_tool.equip_item, EQUIP_ITEM_SCHEMA)
register_tool("use_item", item_tool.use_item, USE_ITEM_SCHEMA)
register_tool("get_inventory", item_tool.get_inventory, GET_INVENTORY_SCHEMA)
register_tool("log_event", log_tool.log_event, LOG_EVENT_SCHEMA)
