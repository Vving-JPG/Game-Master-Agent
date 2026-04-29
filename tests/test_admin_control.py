"""管理端控制测试"""
from fastapi.testclient import TestClient
from src.api.app import app
from src.api.routes.admin_control import runtime_config

client = TestClient(app)

def test_get_config():
    resp = client.get("/api/admin/control/config")
    assert resp.status_code == 200
    assert "temperature" in resp.json()

def test_update_config():
    resp = client.post("/api/admin/control/config", json={"temperature": 0.9})
    assert resp.status_code == 200
    assert runtime_config["temperature"] == 0.9

def test_pause_resume():
    client.post("/api/admin/control/pause")
    assert runtime_config["paused"] == True
    client.post("/api/admin/control/resume")
    assert runtime_config["paused"] == False
