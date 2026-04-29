"""NPC Repository 测试"""
import tempfile
import os
from src.services.database import init_db
from src.models import world_repo, location_repo, npc_repo

DB_PATH = None

def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    init_db(DB_PATH)

def test_create_and_get():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    lid = location_repo.create_location(wid, "村庄", db_path=DB_PATH)
    nid = npc_repo.create_npc(wid, "村长", lid, {"openness": 0.8}, "老村长", db_path=DB_PATH)
    npc = npc_repo.get_npc(nid, DB_PATH)
    assert npc["name"] == "村长"
    assert npc["personality"]["openness"] == 0.8

def test_list_by_location():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    lid = location_repo.create_location(wid, "村庄", db_path=DB_PATH)
    npc_repo.create_npc(wid, "NPC_A", lid, db_path=DB_PATH)
    npc_repo.create_npc(wid, "NPC_B", lid, db_path=DB_PATH)
    npcs = npc_repo.get_npcs_by_location(lid, DB_PATH)
    assert len(npcs) == 2

def test_update():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    nid = npc_repo.create_npc(wid, "旅者", db_path=DB_PATH)
    npc_repo.update_npc(nid, mood="happy", db_path=DB_PATH)
    npc = npc_repo.get_npc(nid, DB_PATH)
    assert npc["mood"] == "happy"
