"""玩家工具测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.tools import world_tool, player_tool

DB_PATH = None


def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    world_tool.set_active(result["world_id"], result["player_id"])


def test_get_player_info():
    result = player_tool.get_player_info(DB_PATH)
    assert "HP:" in result
    assert "等级:" in result


def test_update_player_info():
    result = player_tool.update_player_info(DB_PATH, hp=80, gold=100)
    assert "hp=80" in result
    assert "gold=100" in result
    # 验证更新生效
    info = player_tool.get_player_info(DB_PATH)
    assert "80" in info
