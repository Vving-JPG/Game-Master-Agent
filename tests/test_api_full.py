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

    def test_action_empty(self):
        resp = client.post(f"/api/worlds/{WORLD_ID}/action", json={"content": ""})
        assert resp.status_code == 400

    def test_action_invalid_world(self):
        resp = client.post("/api/worlds/99999/action", json={"content": "测试"})
        assert resp.status_code == 404


class TestWebSocket:
    """WebSocket 测试"""

    def test_ws_connect(self):
        """WebSocket 连接"""
        from fastapi.testclient import TestClient
        with TestClient(app) as c:
            with c.websocket_connect(f"/ws/worlds/{WORLD_ID}") as ws:
                ws.send_json({"type": "action", "content": "你好"})
                # 应该收到 narrative 类型的消息
                data = ws.receive_json()
                assert data["type"] in ["narrative", "system"]

    def test_ws_invalid_world(self):
        """无效世界的 WebSocket - 应该返回系统消息然后关闭"""
        from fastapi.testclient import TestClient
        with TestClient(app) as c:
            with c.websocket_connect("/ws/worlds/99999") as ws:
                # 应该收到系统消息告知世界不存在
                data = ws.receive_json()
                assert data["type"] == "system"
                assert "不存在" in data["content"]
