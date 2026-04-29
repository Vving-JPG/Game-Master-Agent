"""NPC扩展属性模型测试"""
import tempfile
import os
import json
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.models import npc_repo

DB_PATH = None
WORLD_ID = None


def setup_module():
    global DB_PATH, WORLD_ID
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    WORLD_ID = result["world_id"]


def test_create_npc_with_personality():
    """创建带性格的NPC"""
    personality = {"openness": 0.8, "conscientiousness": 0.3, "extraversion": 0.9, "agreeableness": 0.6, "neuroticism": 0.2}
    goals = [{"description": "探索世界", "priority": 1}]
    npc_id = npc_repo.create_npc(
        WORLD_ID, "测试NPC", 1,
        personality=json.dumps(personality),
        mood="happy",
        goals=json.dumps(goals),
        speech_style="说话很热情！",
        db_path=DB_PATH,
    )
    npc = npc_repo.get_npc(npc_id, DB_PATH)
    assert npc["mood"] == "happy"
    assert npc["personality"]["openness"] == 0.8
    assert npc["goals"][0]["description"] == "探索世界"
    assert npc["speech_style"] == "说话很热情！"


def test_create_npc_with_dict():
    """使用字典直接创建NPC"""
    personality = {"openness": 0.5, "conscientiousness": 0.5}
    goals = [{"description": "保护村庄", "priority": 1}]
    relationships = {"1": 50, "2": -20}
    npc_id = npc_repo.create_npc(
        WORLD_ID, "字典NPC", 1,
        personality=personality,
        mood="confident",
        goals=goals,
        relationships=relationships,
        db_path=DB_PATH,
    )
    npc = npc_repo.get_npc(npc_id, DB_PATH)
    assert npc["personality"]["openness"] == 0.5
    assert npc["goals"][0]["description"] == "保护村庄"
    assert npc["relationships"]["1"] == 50


def test_update_npc_mood():
    """更新NPC心情"""
    npc_id = npc_repo.create_npc(WORLD_ID, "心情NPC", 1, db_path=DB_PATH)
    npc_repo.update_npc(npc_id, mood="angry", db_path=DB_PATH)
    npc = npc_repo.get_npc(npc_id, DB_PATH)
    assert npc["mood"] == "angry"


def test_update_relationships():
    """更新NPC关系"""
    rel = {"1": 50, "2": -30}
    npc_id = npc_repo.create_npc(WORLD_ID, "关系NPC", 1, relationships=rel, db_path=DB_PATH)
    npc = npc_repo.get_npc(npc_id, DB_PATH)
    rels = npc["relationships"]
    assert rels["1"] == 50
    assert rels["2"] == -30


def test_update_relationships_with_dict():
    """使用字典更新关系"""
    npc_id = npc_repo.create_npc(WORLD_ID, "更新关系NPC", 1, db_path=DB_PATH)
    npc_repo.update_npc(npc_id, relationships={"1": 75, "3": 10}, db_path=DB_PATH)
    npc = npc_repo.get_npc(npc_id, DB_PATH)
    assert npc["relationships"]["1"] == 75
    assert npc["relationships"]["3"] == 10


def test_get_npcs_by_location_with_new_fields():
    """获取地点NPC包含新字段"""
    npc_repo.create_npc(
        WORLD_ID, "地点NPC", 1,
        mood="curious",
        goals=[{"description": "寻找宝藏"}],
        db_path=DB_PATH,
    )
    npcs = npc_repo.get_npcs_by_location(1, DB_PATH)
    found = [n for n in npcs if n["name"] == "地点NPC"]
    assert len(found) == 1
    assert found[0]["mood"] == "curious"
    assert found[0]["goals"][0]["description"] == "寻找宝藏"
