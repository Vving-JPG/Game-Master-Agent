"""Agent API + Skills API 测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def skills_dir(tmp_path):
    """创建临时 skills 目录"""
    sd = tmp_path / "skills"
    builtin = sd / "builtin" / "combat"
    builtin.mkdir(parents=True)
    (builtin / "SKILL.md").write_text(
        "---\nname: combat\ndescription: 战斗系统。\nversion: 1.0.0\n"
        "tags: [combat]\n---\n\n# 战斗系统\n\n伤害公式。",
        encoding="utf-8"
    )
    agent_dir = sd / "builtin" / "dialogue"
    agent_dir.mkdir(parents=True)
    (agent_dir / "SKILL.md").write_text(
        "---\nname: dialogue\ndescription: 对话系统。\nversion: 1.0.0\n---\n\n# 对话",
        encoding="utf-8"
    )
    return sd


@pytest.fixture
def agent_client(tmp_path):
    """创建 Agent API 测试客户端"""
    from src.api.routes.agent import router as agent_router, set_agent_refs

    # 创建 mock 实例
    mock_gm = MagicMock()
    mock_gm.turn_count = 5
    mock_gm.total_tokens = 15000
    mock_gm.history = [{"role": "user", "content": "test"}] * 10
    mock_gm.prompt_builder = MagicMock()
    mock_gm.prompt_builder.load_system_prompt.return_value = "你是 GM Agent。"
    mock_gm.reset = MagicMock()

    mock_handler = MagicMock()
    mock_handler.is_processing = False
    mock_handler.current_event = None

    set_agent_refs(mock_handler, mock_gm, None)

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(agent_router)
    return TestClient(app)


class TestAgentAPI:
    """Agent 交互 API 测试"""

    def test_get_status(self, agent_client):
        resp = agent_client.get("/api/agent/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "idle"
        assert data["turn_count"] == 5
        assert data["total_tokens"] == 15000
        assert data["history_length"] == 5

    def test_get_context(self, agent_client):
        resp = agent_client.get("/api/agent/context")
        assert resp.status_code == 200
        data = resp.json()
        assert "system_prompt" in data
        assert data["system_prompt"] == "你是 GM Agent。"

    def test_reset_session(self, agent_client):
        resp = agent_client.post("/api/agent/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_send_event_not_initialized(self):
        """Agent 未初始化时应返回 503"""
        from src.api.routes.agent import router, set_agent_refs
        set_agent_refs(None, None, None)

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post("/api/agent/event", json={
            "event_id": "test", "timestamp": "t", "type": "player_action",
            "data": {"raw_text": "test"}, "context_hints": [], "game_state": {}
        })
        assert resp.status_code == 503


class TestSkillsAPI:
    """Skill 管理 API 测试"""

    @pytest.fixture
    def skills_client(self, skills_dir):
        from src.api.routes.skills import router, set_skills_path
        set_skills_path(str(skills_dir))

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_list_skills(self, skills_client):
        resp = skills_client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = [s["name"] for s in data]
        assert "combat" in names
        assert "dialogue" in names

    def test_get_skill(self, skills_client):
        resp = skills_client.get("/api/skills/combat")
        assert resp.status_code == 200
        data = resp.json()
        assert data["frontmatter"]["name"] == "combat"
        assert "伤害公式" in data["content"]

    def test_get_skill_not_found(self, skills_client):
        resp = skills_client.get("/api/skills/nonexistent")
        assert resp.status_code == 404

    def test_update_skill(self, skills_client, skills_dir):
        resp = skills_client.put("/api/skills/combat", json={
            "content": "---\nname: combat\ndescription: 更新后的战斗系统。\n---\n\n# 战斗\n新内容。"
        })
        assert resp.status_code == 200

        # 验证文件更新
        import frontmatter
        post = frontmatter.load(str(skills_dir / "builtin" / "combat" / "SKILL.md"))
        assert "新内容" in post.content

    def test_create_skill(self, skills_client, skills_dir):
        resp = skills_client.post("/api/skills", json={
            "name": "custom_skill",
            "content": "---\nname: custom_skill\ndescription: 自定义技能。\n---\n\n# 自定义",
            "source": "agent_created",
        })
        assert resp.status_code == 200

        assert (skills_dir / "agent_created" / "custom_skill" / "SKILL.md").exists()

    def test_create_skill_builtin_forbidden(self, skills_client):
        resp = skills_client.post("/api/skills", json={
            "name": "hacked",
            "content": "---\nname: hacked\n---\n",
            "source": "builtin",
        })
        assert resp.status_code == 403

    def test_delete_skill_builtin_forbidden(self, skills_client):
        resp = skills_client.delete("/api/skills/combat")
        assert resp.status_code == 403

    def test_delete_skill_agent_created(self, skills_client, skills_dir):
        # 先创建
        (skills_dir / "agent_created" / "temp_skill").mkdir(parents=True)
        (skills_dir / "agent_created" / "temp_skill" / "SKILL.md").write_text(
            "---\nname: temp_skill\n---\n", encoding="utf-8"
        )

        resp = skills_client.delete("/api/skills/temp_skill")
        assert resp.status_code == 200
        assert not (skills_dir / "agent_created" / "temp_skill").exists()

    def test_delete_skill_not_found(self, skills_client):
        resp = skills_client.delete("/api/skills/nonexistent")
        assert resp.status_code == 404
