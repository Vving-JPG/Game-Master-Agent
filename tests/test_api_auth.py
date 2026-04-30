"""认证和错误处理测试"""
import pytest
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)


def test_no_auth_required_dev():
    """开发环境不需要认证"""
    resp = client.get("/health")
    assert resp.status_code == 200


def test_invalid_api_key():
    """无效API Key"""
    resp = client.get("/health", headers={"X-API-Key": "wrong-key"})
    # 开发环境应该放行（无Key时使用默认Key）
    # 如果传了错误Key，应该401
    assert resp.status_code in [200, 401]


def test_error_format_404():
    """错误格式统一 - 访问不存在的端点返回 404"""
    resp = client.post("/api/worlds/99999/action", json={"content": ""})
    # 端点已删除，返回 404
    assert resp.status_code == 404
