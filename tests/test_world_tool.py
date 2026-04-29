"""世界状态工具测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.tools import world_tool

DB_PATH = None


def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    world_tool.set_active(result["world_id"], 1)


def test_query_overview():
    result = world_tool.query_world_state("overview", DB_PATH)
    assert "艾泽拉斯" in result
    assert "玩家" in result


def test_query_player_location():
    result = world_tool.query_world_state("player_location", DB_PATH)
    assert "位于" in result or "未知" in result


def test_get_location_info():
    result = world_tool.get_location_info(1, DB_PATH)
    assert "【" in result


def test_list_npcs():
    result = world_tool.list_npcs_at_location(1, DB_PATH)
    assert isinstance(result, str)


def test_update_player_location():
    result = world_tool.update_world_state("player_location", "1", DB_PATH)
    assert isinstance(result, str)
