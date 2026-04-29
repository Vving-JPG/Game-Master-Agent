"""管理端数据管理测试"""
import tempfile, os
from fastapi.testclient import TestClient
from src.api.app import app
from src.data.seed_data import seed_world
from src.models import npc_repo

client = TestClient(app)
WORLD_ID = None

def setup_module():
    global WORLD_ID
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    WORLD_ID = result["world_id"]

def test_list_npcs():
    resp = client.get(f"/api/admin/data/npcs?world_id={WORLD_ID}")
    assert resp.status_code == 200

def test_list_quests():
    resp = client.get(f"/api/admin/data/quests?world_id={WORLD_ID}")
    assert resp.status_code == 200

def test_list_players():
    resp = client.get(f"/api/admin/data/players?world_id={WORLD_ID}")
    assert resp.status_code == 200
