"""NPC关系追踪测试"""
import tempfile
import os
import json
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.tools import world_tool, npc_tool
from src.models import npc_repo

DB_PATH = None
NPC_ID = None


def setup_module():
    global DB_PATH, NPC_ID
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    world_tool.set_active(result["world_id"], result["player_id"])
    NPC_ID = npc_repo.create_npc(result["world_id"], "关系NPC", 1, db_path=DB_PATH)


def test_update_relationship_positive():
    """帮助NPC后关系上升"""
    result = npc_tool.update_relationship(NPC_ID, 1, 20, DB_PATH)
    assert "提升" in result
    assert "20" in result


def test_update_relationship_negative():
    """伤害NPC后关系下降"""
    result = npc_tool.update_relationship(NPC_ID, 1, -15, DB_PATH)
    assert "下降" in result


def test_relationship_persisted():
    """关系值持久化"""
    # 创建新NPC来测试持久化
    new_npc_id = npc_repo.create_npc(world_tool._active_world_id, "持久化NPC", 1, db_path=DB_PATH)
    npc_tool.update_relationship(new_npc_id, 1, 50, DB_PATH)
    npc = npc_repo.get_npc(new_npc_id, DB_PATH)
    rels = npc["relationships"]
    assert rels["1"] == 50


def test_relationship_clamp():
    """关系值不超过-100~100"""
    npc_tool.update_relationship(NPC_ID, 1, 200, DB_PATH)
    npc = npc_repo.get_npc(NPC_ID, DB_PATH)
    rels = npc["relationships"]
    assert rels["1"] <= 100
