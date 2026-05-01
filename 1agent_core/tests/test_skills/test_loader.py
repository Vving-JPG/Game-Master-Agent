"""skills/loader.py 单元测试"""
import pytest
from pathlib import Path
from src.skills.loader import SkillLoader


@pytest.fixture
def skills_dir(tmp_path):
    sd = tmp_path / "skills"
    builtin = sd / "builtin" / "combat"
    builtin.mkdir(parents=True)
    (builtin / "SKILL.md").write_text(
        "---\nname: combat\ndescription: 战斗系统管理。\nversion: 1.0.0\n"
        "tags: [combat, battle]\ntriggers:\n  - event_type: combat_start\n"
        "  - keyword: [\"战斗\", \"攻击\"]\nallowed-tools:\n  - modify_stat\n---\n\n"
        "# 战斗系统\n\n## 伤害公式\n基础伤害 = 攻击力 - 防御力 * 0.5\n", encoding="utf-8")
    return sd


class TestSkillLoader:
    def test_discover(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        skills = loader.discover_all()
        assert len(skills) == 1
        assert skills[0].name == "combat"

    def test_cache(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        skills1 = loader.discover_all()
        skills2 = loader.discover_all()
        assert skills1 == skills2

    def test_relevant_by_event(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        result = loader.get_relevant_skills(event_type="combat_start")
        assert len(result) == 1

    def test_relevant_by_keyword(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        result = loader.get_relevant_skills(user_input="我要攻击哥布林")
        assert len(result) == 1

    def test_no_match(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        assert loader.get_relevant_skills(user_input="你好铁匠") == []

    def test_load_content(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        loader.discover_all()
        assert "伤害公式" in loader.load_skill_content("combat")

    def test_load_nonexistent_none(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        assert loader.load_skill_content("nonexistent") is None

    def test_invalidate_cache(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        loader.discover_all()
        dialogue_dir = skills_dir / "builtin" / "dialogue"
        dialogue_dir.mkdir()
        (dialogue_dir / "SKILL.md").write_text(
            "---\nname: dialogue\ndescription: 对话系统\nversion: 1.0.0\n---\n\n# 对话", encoding="utf-8")
        assert len(loader.discover_all()) == 1
        loader.invalidate_cache()
        assert len(loader.discover_all()) == 2
