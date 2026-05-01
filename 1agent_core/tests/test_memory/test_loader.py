"""memory/loader.py 单元测试"""
import pytest
from pathlib import Path
from src.memory.loader import MemoryLoader


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    npc_dir = ws / "npcs"
    npc_dir.mkdir()
    (npc_dir / "铁匠.md").write_text(
        "---\nname: 铁匠\ntype: npc\nhp: 80\nrelationship_with_player: 30\n"
        "version: 3\nlast_modified: 2026-04-28T14:00:00\nmodified_by: engine\n"
        "tags: [npc, 黑铁镇]\n---\n\n## 初始印象\n[第1天] 铁匠铺的老板。\n\n"
        "## 交互记录\n[第2天] 玩家来买剑。\n", encoding="utf-8")
    return ws


class TestMemoryLoader:
    def test_load_index_compact(self, workspace):
        loader = MemoryLoader(str(workspace))
        result = loader.load_index(["npcs/铁匠"])
        assert "铁匠" in result
        assert "npc" in result
        assert "v3" in result
        assert "铁匠铺的老板" not in result

    def test_load_index_missing(self, workspace):
        loader = MemoryLoader(str(workspace))
        result = loader.load_index(["npcs/不存在"])
        assert "不存在" in result

    def test_load_activation_metadata_and_headings(self, workspace):
        loader = MemoryLoader(str(workspace))
        result = loader.load_activation(["npcs/铁匠"])
        assert "hp: 80" in result
        assert "初始印象" in result
        assert "交互记录" in result
        assert "铁匠铺的老板" not in result

    def test_load_activation_skips_meta(self, workspace):
        loader = MemoryLoader(str(workspace))
        result = loader.load_activation(["npcs/铁匠"])
        assert "last_modified" not in result
        assert "modified_by" not in result

    def test_load_execution_full(self, workspace):
        loader = MemoryLoader(str(workspace))
        result = loader.load_execution(["npcs/铁匠"])
        assert "铁匠铺的老板" in result
        assert "玩家来买剑" in result

    def test_load_execution_missing_skipped(self, workspace):
        loader = MemoryLoader(str(workspace))
        assert loader.load_execution(["npcs/不存在"]) == ""
