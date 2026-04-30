"""memory/manager.py 单元测试"""
import pytest
from pathlib import Path
import frontmatter
from src.memory.manager import MemoryManager
from src.memory.file_io import atomic_write


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def manager(workspace):
    return MemoryManager(str(workspace))


class TestMemoryManager:
    def test_load_context_default(self, manager):
        result = manager.load_context(["npcs/铁匠"])
        assert "相关实体索引" in result

    def test_append_creates_file(self, manager, workspace):
        (workspace / "npcs").mkdir()
        manager.apply_memory_updates([
            {"file": "npcs/铁匠.md", "action": "append", "content": "\n[第1天] 初始记录。"}])
        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert "第1天" in post.content
        assert post["version"] >= 1

    def test_create_file(self, manager, workspace):
        manager.apply_memory_updates([
            {"file": "npcs/新NPC.md", "action": "create",
             "content": "---\nname: 新NPC\n---\n## 初始印象\n新角色。"}])
        assert (workspace / "npcs" / "新NPC.md").exists()

    def test_state_changes_updates_fm(self, manager, workspace):
        (workspace / "npcs").mkdir()
        atomic_write(str(workspace / "npcs" / "铁匠.md"),
                     "---\nname: 铁匠\nhp: 80\nversion: 1\n---\n记录")
        manager.apply_state_changes([
            {"file": "npcs/铁匠.md", "frontmatter": {"hp": 75, "version": 2}}])
        assert frontmatter.load(str(workspace / "npcs" / "铁匠.md"))["hp"] == 75

    def test_initialize_workspace(self, manager):
        manager.initialize_workspace()
        assert (manager.workspace / "npcs" / "_index.md").exists()
        assert (manager.workspace / "locations" / "_index.md").exists()

    def test_load_full_file(self, manager, workspace):
        (workspace / "npcs").mkdir()
        atomic_write(str(workspace / "npcs" / "铁匠.md"),
                     "---\nname: 铁匠\nhp: 80\n---\n## 记录\n内容。")
        result = manager.load_full_file("npcs/铁匠.md")
        assert result["frontmatter"]["name"] == "铁匠"
        assert "内容" in result["content"]

    def test_load_full_file_missing(self, manager):
        assert manager.load_full_file("npcs/不存在") is None
