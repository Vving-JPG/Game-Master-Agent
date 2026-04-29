"""NPC工具测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.tools import world_tool, npc_tool

DB_PATH = None


def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    world_tool.set_active(result["world_id"], result["player_id"])


def test_search_npc():
    result = npc_tool.search_npc("村长", DB_PATH)
    assert "村长" in result


def test_search_npc_not_found():
    result = npc_tool.search_npc("不存在的人", DB_PATH)
    assert "未找到" in result
