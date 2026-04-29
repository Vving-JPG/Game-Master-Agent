"""游戏行动API测试"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.api.app import app
from src.data.seed_data import seed_world

client = TestClient(app)
WORLD_ID = None

def setup_module():
    global WORLD_ID
    result = seed_world()
    WORLD_ID = result["world_id"]

def test_action_empty_input():
    """空输入返回400"""
    resp = client.post(f"/api/worlds/{WORLD_ID}/action", json={"content": ""})
    assert resp.status_code == 400

def test_action_mock_gm():
    """Mock GM返回"""
    with patch("src.api.routes.action._get_gm") as mock_gm:
        mock_instance = MagicMock()
        mock_instance.process.return_value = "你站在宁静的村庄广场上。"
        mock_gm.return_value = mock_instance

        resp = client.post(f"/api/worlds/{WORLD_ID}/action", json={"content": "环顾四周"})
        assert resp.status_code == 200
        assert "宁静" in resp.json()["reply"]

def test_action_world_not_found():
    """不存在的世界"""
    resp = client.post("/api/worlds/99999/action", json={"content": "测试"})
    assert resp.status_code == 404
