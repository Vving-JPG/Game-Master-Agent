"""Skill 加载集成测试"""
import pytest
from pathlib import Path
from src.skills.loader import SkillLoader
from src.agent.prompt_builder import PromptBuilder
from src.memory.manager import MemoryManager


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    for d in ["npcs", "locations", "session"]:
        (ws / d).mkdir()
    return ws


@pytest.fixture
def skills_dir(tmp_path):
    sd = tmp_path / "skills"
    combat_dir = sd / "builtin" / "combat"
    combat_dir.mkdir(parents=True)
    (combat_dir / "SKILL.md").write_text(
        "---\nname: combat\ndescription: 战斗系统管理。\nversion: 1.0.0\n"
        "tags: [combat]\ntriggers:\n  - event_type: combat_start\n"
        "  - keyword: [\"战斗\", \"攻击\"]\nallowed-tools:\n  - modify_stat\n---\n\n"
        "# 战斗系统\n\n## 伤害公式\n基础伤害 = 攻击力 - 防御力 * 0.5\n",
        encoding="utf-8"
    )
    dialogue_dir = sd / "builtin" / "dialogue"
    dialogue_dir.mkdir(parents=True)
    (dialogue_dir / "SKILL.md").write_text(
        "---\nname: dialogue\ndescription: 对话系统管理。\nversion: 1.0.0\n"
        "tags: [dialogue]\ntriggers:\n  - event_type: npc_interact\n"
        "  - keyword: [\"聊天\", \"对话\"]\nallowed-tools:\n  - update_npc_relationship\n---\n\n"
        "# 对话系统\n\n## 好感度影响\n0-20: 冷淡\n",
        encoding="utf-8"
    )
    return sd


@pytest.fixture
def system_prompt(tmp_path):
    sp = tmp_path / "system_prompt.md"
    sp.write_text("你是 GM Agent。", encoding="utf-8")
    return str(sp)


class TestSkillIntegration:
    """Skill 匹配和嵌入 Prompt 测试"""

    def test_combat_skill_matched_by_event(self, skills_dir, workspace, system_prompt):
        loader = SkillLoader(str(skills_dir))
        manager = MemoryManager(str(workspace))
        builder = PromptBuilder(system_prompt, manager, loader)

        event = {
            "type": "combat_start",
            "data": {"raw_text": "攻击哥布林", "player_id": "p1"},
            "context_hints": [],
            "game_state": {},
        }
        messages = builder.build(event, history=[])

        system_msg = messages[0]["content"]
        assert "combat" in system_msg
        assert "伤害公式" in system_msg

    def test_dialogue_skill_matched_by_keyword(self, skills_dir, workspace, system_prompt):
        loader = SkillLoader(str(skills_dir))
        manager = MemoryManager(str(workspace))
        builder = PromptBuilder(system_prompt, manager, loader)

        event = {
            "type": "player_action",
            "data": {"raw_text": "和铁匠聊天", "player_id": "p1"},
            "context_hints": ["npcs/铁匠"],
            "game_state": {},
        }
        messages = builder.build(event, history=[])

        system_msg = messages[0]["content"]
        assert "dialogue" in system_msg

    def test_no_skill_matched(self, skills_dir, workspace, system_prompt):
        loader = SkillLoader(str(skills_dir))
        manager = MemoryManager(str(workspace))
        builder = PromptBuilder(system_prompt, manager, loader)

        event = {
            "type": "player_action",
            "data": {"raw_text": "查看背包", "player_id": "p1"},
            "context_hints": [],
            "game_state": {},
        }
        messages = builder.build(event, history=[])

        system_msg = messages[0]["content"]
        assert "可用能力" not in system_msg

    def test_memory_in_prompt(self, workspace, skills_dir, system_prompt):
        (workspace / "npcs" / "铁匠.md").write_text(
            "---\nname: 铁匠\ntype: npc\nhp: 80\nversion: 2\n---\n"
            "## 交互记录\n[第1天] 初始接触。\n",
            encoding="utf-8"
        )

        loader = SkillLoader(str(skills_dir))
        manager = MemoryManager(str(workspace))
        builder = PromptBuilder(system_prompt, manager, loader)

        event = {
            "type": "player_action",
            "data": {"raw_text": "和铁匠聊聊", "player_id": "p1"},
            "context_hints": ["npcs/铁匠"],
            "game_state": {"location": "town"},
        }
        messages = builder.build(event, history=[])

        system_msg = messages[0]["content"]
        assert "铁匠" in system_msg
        assert "相关记忆" in system_msg

    def test_game_state_in_prompt(self, workspace, skills_dir, system_prompt):
        loader = SkillLoader(str(skills_dir))
        manager = MemoryManager(str(workspace))
        builder = PromptBuilder(system_prompt, manager, loader)

        event = {
            "type": "player_action",
            "data": {"raw_text": "看看周围", "player_id": "p1"},
            "context_hints": [],
            "game_state": {"location": "黑铁镇", "player_hp": 85, "time": "第3天"},
        }
        messages = builder.build(event, history=[])

        system_msg = messages[0]["content"]
        assert "当前游戏状态" in system_msg
        assert "黑铁镇" in system_msg
