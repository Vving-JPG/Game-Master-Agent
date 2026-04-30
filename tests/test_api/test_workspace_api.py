"""Workspace API 测试"""
import pytest
import frontmatter
from fastapi.testclient import TestClient


@pytest.fixture
def workspace(tmp_path):
    """创建临时 workspace 目录"""
    ws = tmp_path / "workspace"
    ws.mkdir()
    # 创建测试文件
    (ws / "npcs").mkdir()
    (ws / "npcs" / "铁匠.md").write_text(
        "---\nname: 铁匠\ntype: npc\nhp: 80\nversion: 1\n---\n## 交互记录\n[第1天] 初始接触。",
        encoding="utf-8"
    )
    (ws / "session").mkdir()
    (ws / "session" / "current.md").write_text(
        "---\ntype: session\nversion: 1\n---\n会话记录。",
        encoding="utf-8"
    )
    return ws


@pytest.fixture
def client(workspace, monkeypatch):
    """创建测试客户端"""
    from src.api.routes.workspace import router, set_workspace_path
    set_workspace_path(str(workspace))

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    return TestClient(app)


class TestWorkspaceTree:
    """文件树 API 测试"""

    def test_root_tree(self, client):
        resp = client.get("/api/workspace/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert "children" in data
        names = [c["name"] for c in data["children"]]
        assert "npcs" in names
        assert "session" in names

    def test_subdirectory_tree(self, client):
        resp = client.get("/api/workspace/tree?path=npcs")
        assert resp.status_code == 200
        data = resp.json()
        names = [c["name"] for c in data["children"]]
        assert "铁匠.md" in names

    def test_nonexistent_directory(self, client):
        resp = client.get("/api/workspace/tree?path=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["children"] == []


class TestWorkspaceFile:
    """文件 CRUD API 测试"""

    def test_get_file(self, client):
        resp = client.get("/api/workspace/file?path=npcs/铁匠.md")
        assert resp.status_code == 200
        data = resp.json()
        assert data["frontmatter"]["name"] == "铁匠"
        assert "交互记录" in data["content"]
        assert "raw" in data

    def test_get_file_not_found(self, client):
        resp = client.get("/api/workspace/file?path=nonexistent.md")
        assert resp.status_code == 404

    def test_update_file_frontmatter(self, client, workspace):
        resp = client.put("/api/workspace/file", json={
            "path": "npcs/铁匠.md",
            "frontmatter": {"hp": 75},
        })
        assert resp.status_code == 200

        # 验证文件更新
        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert post["hp"] == 75
        assert "交互记录" in post.content  # content 不变

    def test_update_file_content(self, client, workspace):
        resp = client.put("/api/workspace/file", json={
            "path": "npcs/铁匠.md",
            "content": "## 新记录\n[第2天] 玩家来了。",
        })
        assert resp.status_code == 200

        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert "新记录" in post.content
        assert post["name"] == "铁匠"  # frontmatter 不变

    def test_update_file_raw(self, client, workspace):
        resp = client.put("/api/workspace/file", json={
            "path": "npcs/铁匠.md",
            "raw": "---\nname: 铁匠\n---\n全新内容。",
        })
        assert resp.status_code == 200

        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert post.content == "全新内容。"

    def test_create_file(self, client, workspace):
        resp = client.post("/api/workspace/file", json={
            "path": "npcs/新NPC.md",
            "content": "---\nname: 新NPC\n---\n## 初始印象\n新角色。",
        })
        assert resp.status_code == 200

        assert (workspace / "npcs" / "新NPC.md").exists()

    def test_create_file_already_exists(self, client):
        resp = client.post("/api/workspace/file", json={
            "path": "npcs/铁匠.md",
            "content": "重复",
        })
        assert resp.status_code == 409

    def test_delete_file(self, client, workspace):
        resp = client.delete("/api/workspace/file?path=npcs/铁匠.md")
        assert resp.status_code == 200
        assert not (workspace / "npcs" / "铁匠.md").exists()

    def test_delete_file_not_found(self, client):
        resp = client.delete("/api/workspace/file?path=nonexistent.md")
        assert resp.status_code == 404
