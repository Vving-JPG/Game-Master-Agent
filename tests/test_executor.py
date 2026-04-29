"""工具执行器测试"""
import pytest
from src.tools.executor import register_tool, execute_tool, get_all_schemas, get_tool_names, TOOL_REGISTRY
from src.tools import dice, world_tool, player_tool, npc_tool, log_tool
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
    LOG_EVENT_SCHEMA,
)


def setup_module():
    TOOL_REGISTRY.clear()
    # 重新注册核心工具
    register_tool("roll_dice", dice.roll_dice, ROLL_DICE_SCHEMA)
    register_tool("query_world_state", world_tool.query_world_state, QUERY_WORLD_STATE_SCHEMA)
    register_tool("update_world_state", world_tool.update_world_state, UPDATE_WORLD_STATE_SCHEMA)
    register_tool("get_location_info", world_tool.get_location_info, GET_LOCATION_INFO_SCHEMA)
    register_tool("list_npcs_at_location", world_tool.list_npcs_at_location, LIST_NPCS_AT_LOCATION_SCHEMA)
    register_tool("get_player_info", player_tool.get_player_info, GET_PLAYER_INFO_SCHEMA)
    register_tool("update_player_info", player_tool.update_player_info, UPDATE_PLAYER_INFO_SCHEMA)
    register_tool("get_npc_info", npc_tool.get_npc_info, GET_NPC_INFO_SCHEMA)
    register_tool("search_npc", npc_tool.search_npc, SEARCH_NPC_SCHEMA)
    register_tool("log_event", log_tool.log_event, LOG_EVENT_SCHEMA)


def test_register_and_execute():
    """注册→执行→结果正确"""
    def add(a: int, b: int) -> int:
        return a + b

    schema = {
        "type": "function",
        "function": {
            "name": "add",
            "description": "加法",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                "required": ["a", "b"]
            }
        }
    }
    register_tool("add", add, schema)
    result = execute_tool("add", {"a": 3, "b": 5})
    assert result == "8"


def test_unknown_tool():
    """未知工具抛出异常"""
    with pytest.raises(KeyError):
        execute_tool("nonexistent", {})


def test_get_all_schemas():
    """获取所有schema"""
    def dummy2(): pass
    schema = {"type": "function", "function": {"name": "dummy2", "description": "", "parameters": {"type": "object", "properties": {}}}}
    register_tool("dummy2", dummy2, schema)
    schemas = get_all_schemas()
    assert len(schemas) >= 1
    names = [s["function"]["name"] for s in schemas]
    assert "dummy2" in names


def test_get_tool_names():
    names = get_tool_names()
    assert "dummy2" in names
