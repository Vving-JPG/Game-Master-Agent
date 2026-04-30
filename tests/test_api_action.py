"""游戏行动API测试 (V1 已删除 - V2 使用 /api/agent/event)"""
import pytest
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)


def test_action_endpoint_removed():
    """V1 action 端点已删除，应返回 404"""
    resp = client.post("/api/worlds/1/action", json={"content": "测试"})
    assert resp.status_code == 404


def test_action_endpoint_removed_empty():
    """V1 action 端点已删除（空输入也应返回 404）"""
    resp = client.post("/api/worlds/1/action", json={"content": ""})
    assert resp.status_code == 404


def test_action_endpoint_removed_invalid_world():
    """V1 action 端点已删除（不存在的世界也返回 404）"""
    resp = client.post("/api/worlds/99999/action", json={"content": "测试"})
    assert resp.status_code == 404
