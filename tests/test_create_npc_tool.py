"""create_npc工具测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.tools import world_tool, npc_tool
from src.models import npc_repo

DB_PATH = None


def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    world_tool.set_active(result["world_id"], result["player_id"])


def test_create_npc_basic():
    """基本创建"""
    result = npc_tool.create_npc("测试骑士", 1, db_path=DB_PATH)
    assert "测试骑士" in result
    assert "ID:" in result


def test_create_npc_with_template():
    """用模板创建"""
    result = npc_tool.create_npc("铁锤", 1, personality_type="brave_warrior", db_path=DB_PATH)
    assert "铁锤" in result
    assert "brave_warrior" in result


def test_create_npc_in_db():
    """创建后能从数据库查到"""
    npc_tool.create_npc("持久化NPC", 1, personality_type="wise_elder", db_path=DB_PATH)
    npcs = npc_repo.get_npcs_by_location(1, DB_PATH)
    found = [n for n in npcs if n["name"] == "持久化NPC"]
    assert len(found) == 1
    assert found[0]["mood"] == "serene"
