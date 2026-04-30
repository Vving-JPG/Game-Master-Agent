"""memory/file_io.py 单元测试"""
import pytest
from pathlib import Path
import frontmatter
from src.memory.file_io import atomic_write, update_memory_file


class TestAtomicWrite:
    def test_creates_file(self, tmp_path):
        target = str(tmp_path / "test.md")
        atomic_write(target, "# Test\n\nContent")
        assert Path(target).exists()
        assert "Content" in Path(target).read_text(encoding="utf-8")

    def test_overwrites_existing(self, tmp_path):
        target = str(tmp_path / "test.md")
        atomic_write(target, "first")
        atomic_write(target, "second")
        assert Path(target).read_text(encoding="utf-8") == "second"

    def test_creates_parent_dirs(self, tmp_path):
        target = str(tmp_path / "sub" / "dir" / "test.md")
        atomic_write(target, "nested")
        assert Path(target).exists()

    def test_atomic_no_corruption(self, tmp_path):
        target = str(tmp_path / "test.md")
        atomic_write(target, "first")
        atomic_write(target, "second")
        content = Path(target).read_text(encoding="utf-8")
        assert content in ("first", "second")

    def test_utf8_encoding(self, tmp_path):
        target = str(tmp_path / "test.md")
        atomic_write(target, "---\nname: 铁匠\n---\n## 记录\n[第1天] 铁匠铺。")
        assert "铁匠" in Path(target).read_text(encoding="utf-8")


class TestUpdateMemoryFile:
    def test_create_new_file(self, tmp_path):
        target = str(tmp_path / "new.md")
        update_memory_file(filepath=target,
            frontmatter_updates={"name": "新NPC", "type": "npc", "version": 1},
            append_content="\n## 初始印象\n[第1天] 新角色。")
        post = frontmatter.load(target)
        assert post["name"] == "新NPC"
        assert "初始印象" in post.content

    def test_append_preserves_existing(self, tmp_path):
        target = str(tmp_path / "npc.md")
        atomic_write(target, "---\nname: 铁匠\nversion: 1\n---\n## 记录\n[第1天] 初始。")
        update_memory_file(filepath=target, append_content="\n[第2天] 新记录。")
        post = frontmatter.load(target)
        assert "第1天" in post.content
        assert "第2天" in post.content
        assert post["version"] == 2

    def test_update_fm_preserves_body(self, tmp_path):
        target = str(tmp_path / "npc.md")
        atomic_write(target, "---\nname: 铁匠\nhp: 80\nversion: 1\n---\n## 记录\n原有内容。")
        update_memory_file(filepath=target, frontmatter_updates={"hp": 75})
        post = frontmatter.load(target)
        assert post["hp"] == 75
        assert "原有内容" in post.content

    def test_auto_increment_version(self, tmp_path):
        target = str(tmp_path / "npc.md")
        update_memory_file(filepath=target, frontmatter_updates={"name": "铁匠", "version": 1})
        update_memory_file(filepath=target, frontmatter_updates={"hp": 80})
        assert frontmatter.load(target)["version"] >= 2

    def test_auto_update_last_modified(self, tmp_path):
        target = str(tmp_path / "npc.md")
        update_memory_file(filepath=target, frontmatter_updates={"name": "铁匠"})
        assert "last_modified" in frontmatter.load(target).metadata
