"""API 综合测试"""
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


class TestRESTAPI:
    """REST API 测试"""

    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_list_worlds(self):
        resp = client.get("/api/worlds")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_world(self):
        resp = client.get(f"/api/worlds/{WORLD_ID}")
        assert resp.status_code == 200

    def test_get_world_404(self):
        resp = client.get("/api/worlds/99999")
        assert resp.status_code == 404

    def test_get_player(self):
        resp = client.get(f"/api/worlds/{WORLD_ID}/player")
        assert resp.status_code == 200
        data = resp.json()
        assert "hp" in data

    def test_get_inventory(self):
        resp = client.get(f"/api/worlds/{WORLD_ID}/inventory")
        assert resp.status_code == 200

    def test_action_endpoint_removed(self):
        """V1 action 端点已删除，应返回 404"""
        resp = client.post(f"/api/worlds/{WORLD_ID}/action", json={"content": "测试"})
        assert resp.status_code == 404


class TestWebSocket:
    """WebSocket 测试 (V1 已删除)"""

    def test_ws_endpoint_removed(self):
        """V1 WebSocket 端点已删除，应返回 404"""
        with pytest.raises(Exception):  # WebSocket 连接会失败
            with client.websocket_connect(f"/ws/worlds/{WORLD_ID}") as ws:
                pass

    def test_ws_invalid_world_removed(self):
        """V1 WebSocket 端点已删除，无效世界也返回 404"""
        with pytest.raises(Exception):  # WebSocket 连接会失败
            with client.websocket_connect("/ws/worlds/99999") as ws:
                pass
