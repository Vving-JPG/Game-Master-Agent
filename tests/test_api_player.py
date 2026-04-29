"""玩家API测试"""
import pytest
from fastapi.testclient import TestClient
from src.api.app import app
from src.data.seed_data import seed_world

client = TestClient(app)
WORLD_ID = None

def setup_module():
    global WORLD_ID
    result = seed_world()
    WORLD_ID = result["world_id"]

def test_get_player():
    resp = client.get(f"/api/worlds/{WORLD_ID}/player")
    assert resp.status_code == 200
    data = resp.json()
    assert "hp" in data
    assert "level" in data

def test_update_player():
    resp = client.patch(f"/api/worlds/{WORLD_ID}/player", json={"gold": 999})
    assert resp.status_code == 200

def test_get_inventory():
    resp = client.get(f"/api/worlds/{WORLD_ID}/inventory")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_player_not_found():
    resp = client.get("/api/worlds/99999/player")
    assert resp.status_code == 404
