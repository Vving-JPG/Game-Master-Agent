"""世界API测试"""
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from src.api.app import app
from src.data.seed_data import seed_world
from src.models import world_repo
from src.services.database import init_db

client = TestClient(app)


def setup_module():
    """测试前初始化数据库"""
    # 确保数据库已初始化
    init_db()


def test_list_worlds():
    """列出世界"""
    # 先创建一个世界确保有数据
    seed_world()
    resp = client.get("/api/worlds")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_world():
    """创建世界"""
    resp = client.post("/api/worlds", json={"name": "测试世界", "setting": "测试"})
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data


def test_get_world():
    """获取世界详情"""
    # 先创建
    worlds = world_repo.list_worlds()
    if not worlds:
        seed_world()
        worlds = world_repo.list_worlds()
    wid = worlds[0]["id"]
    resp = client.get(f"/api/worlds/{wid}")
    assert resp.status_code == 200
    assert "name" in resp.json()


def test_get_world_not_found():
    """不存在的世界"""
    resp = client.get("/api/worlds/99999")
    assert resp.status_code == 404


def test_delete_world():
    """删除世界"""
    result = seed_world()
    wid = result["world_id"]
    resp = client.delete(f"/api/worlds/{wid}")
    assert resp.status_code == 200
