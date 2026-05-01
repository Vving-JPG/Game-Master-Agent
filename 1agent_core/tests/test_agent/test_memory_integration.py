"""记忆更新集成测试"""
import pytest
from pathlib import Path
import frontmatter
from src.memory.manager import MemoryManager
from src.agent.command_parser import CommandParser


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    for d in ["npcs", "session"]:
        (ws / d).mkdir()
    return ws


@pytest.fixture
def manager(workspace):
    return MemoryManager(str(workspace))


@pytest.fixture
def parser():
    return CommandParser()


class TestMemoryUpdateIntegration:
    """验证 CommandParser 输出 → MemoryManager 文件更新"""

    def test_append_to_existing_file(self, manager, workspace, parser):
        (workspace / "npcs" / "铁匠.md").write_text(
            "---\nname: 铁匠\ntype: npc\nversion: 1\n---\n## 初始印象\n[第1天] 铁匠。",
            encoding="utf-8"
        )

        raw = '{"narrative": "铁匠点了点头。", "commands": [], "memory_updates": [{"file": "npcs/铁匠.md", "action": "append", "content": "\\n[第2天] 玩家来买剑。"}]}'
        response = parser.parse(raw)

        manager.apply_memory_updates(response["memory_updates"])

        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert "第1天" in post.content
        assert "第2天" in post.content
        assert post["version"] == 2

    def test_create_new_file(self, manager, workspace, parser):
        raw = '{"narrative": "一个陌生人出现了。", "commands": [], "memory_updates": [{"file": "npcs/流浪商人.md", "action": "create", "content": "---\\nname: 流浪商人\\ntype: npc\\nversion: 1\\n---\\n## 初始印象\\n[第1天] 神秘的商人。"}]}'
        response = parser.parse(raw)

        manager.apply_memory_updates(response["memory_updates"])

        assert (workspace / "npcs" / "流浪商人.md").exists()
        post = frontmatter.load(str(workspace / "npcs" / "流浪商人.md"))
        assert post["name"] == "流浪商人"

    def test_state_changes_update_frontmatter(self, manager, workspace):
        (workspace / "npcs" / "铁匠.md").write_text(
            "---\nname: 铁匠\nhp: 80\nversion: 1\n---\n记录",
            encoding="utf-8"
        )

        manager.apply_state_changes([{
            "file": "npcs/铁匠.md",
            "frontmatter": {"hp": 75, "version": 2}
        }])

        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert post["hp"] == 75
        assert "记录" in post.content
