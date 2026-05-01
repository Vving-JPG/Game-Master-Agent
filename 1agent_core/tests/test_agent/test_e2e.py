"""端到端测试: 完整回合流程"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.agent.game_master import GameMaster
from src.agent.event_handler import EventHandler
from src.adapters.base import EngineEvent, CommandResult
from src.adapters.text_adapter import TextAdapter
from src.memory.manager import MemoryManager
from src.skills.loader import SkillLoader


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    for d in ["npcs", "locations", "story", "quests", "items", "player", "session"]:
        (ws / d).mkdir()
    (ws / "player" / "profile.md").write_text(
        "---\nname: 玩家\ntype: player\nhp: 100\nversion: 1\n---\n## 初始状态\n[第1天] 冒险开始。",
        encoding="utf-8"
    )
    (ws / "npcs" / "铁匠.md").write_text(
        "---\nname: 铁匠\ntype: npc\nhp: 80\nrelationship_with_player: 30\nversion: 2\n---\n"
        "## 初始印象\n[第1天] 铁匠铺的老板。\n",
        encoding="utf-8"
    )
    return ws


@pytest.fixture
def skills_dir(tmp_path):
    sd = tmp_path / "skills"
    for name, triggers, tools, body in [
        ("narration", "[]", "[]", "# 叙事\n使用中文第二人称。"),
        ("dialogue", '[{"keyword": ["聊天", "对话", "聊聊"]}]', '["update_npc_relationship"]',
         "# 对话\n好感度影响对话风格。"),
        ("combat", '[{"event_type": "combat_start"}, {"keyword": ["攻击", "战斗"]}]',
         '["modify_stat", "update_npc_state"]',
         "# 战斗\n基础伤害 = 攻击力 - 防御力 * 0.5"),
    ]:
        d = sd / "builtin" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {name}系统。\nversion: 1.0.0\n"
            f"triggers: {triggers}\nallowed-tools: {tools}\n---\n\n{body}\n",
            encoding="utf-8"
        )
    return sd


@pytest.fixture
def system_prompt(tmp_path):
    sp = tmp_path / "system_prompt.md"
    sp.write_text("你是 GM Agent。输出 JSON: {narrative, commands, memory_updates}。", encoding="utf-8")
    return str(sp)


@pytest.fixture
def mock_services():
    s = {k: MagicMock() for k in ("world", "player", "npc", "item", "quest")}
    s["world"].list_worlds.return_value = [{"id": "w1"}]
    s["player"].list_players.return_value = [{"id": "p1"}]
    s["player"].get_player.return_value = {
        "id": "p1", "hp": 100, "level": 1, "location": "town", "version": 1
    }
    s["npc"].get_npc.return_value = {
        "id": "npc_1", "name": "铁匠", "relationship": 30, "version": 3
    }
    s["npc"].list_npcs.return_value = [{"id": "npc_1", "name": "铁匠"}]
    return s


def make_mock_llm(narrative, commands=None, memory_updates=None):
    """创建模拟 LLM 客户端"""
    client = MagicMock()
    commands = commands or []
    memory_updates = memory_updates or []

    import json
    response_json = json.dumps({
        "narrative": narrative,
        "commands": commands,
        "memory_updates": memory_updates,
    }, ensure_ascii=False)

    async def mock_stream(messages):
        yield {"event": "token", "data": {"text": response_json}}

    client.stream = mock_stream
    return client


class TestEndToEnd:
    """端到端测试"""

    @pytest.mark.asyncio
    async def test_full_turn_dialogue(
        self, workspace, skills_dir, system_prompt, mock_services
    ):
        """完整回合: 玩家和 NPC 对话"""
        adapter = TextAdapter(
            mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"]
        )
        await adapter.connect()

        gm = GameMaster(
            llm_client=make_mock_llm(
                narrative="铁匠擦了擦汗，说道：'你需要什么？'",
                commands=[{"intent": "update_npc_relationship", "params": {"npc_id": "npc_1", "change": 2}}],
                memory_updates=[{
                    "file": "npcs/铁匠.md",
                    "action": "append",
                    "content": "\n[第2天] 玩家和铁匠交谈。"
                }],
            ),
            memory_manager=MemoryManager(str(workspace)),
            skill_loader=SkillLoader(str(skills_dir)),
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )

        event = EngineEvent(
            event_id="evt_e2e_001",
            timestamp="2026-04-28T14:00:00",
            type="player_action",
            data={"raw_text": "和铁匠聊聊", "player_id": "p1"},
            context_hints=["npcs/铁匠"],
            game_state={"location": "town", "player_hp": 100},
        )

        response = await gm.handle_event(event)

        assert response["narrative"] != ""
        assert response["event_id"] == "evt_e2e_001"
        assert response["stats"]["turn"] == 1
        assert len(response["commands"]) == 1
        assert response["commands"][0]["intent"] == "update_npc_relationship"

        assert len(response["command_results"]) == 1
        assert response["command_results"][0]["status"] == "success"

        import frontmatter
        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert "第2天" in post.content

    @pytest.mark.asyncio
    async def test_event_handler_full_flow(
        self, workspace, skills_dir, system_prompt, mock_services
    ):
        """EventHandler 完整流程"""
        adapter = TextAdapter(
            mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"]
        )
        await adapter.connect()

        gm = GameMaster(
            llm_client=make_mock_llm(
                narrative="你环顾四周，看到铁匠铺里摆满了各种武器。",
                commands=[],
                memory_updates=[],
            ),
            memory_manager=MemoryManager(str(workspace)),
            skill_loader=SkillLoader(str(skills_dir)),
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )

        handler = EventHandler(game_master=gm, engine_adapter=adapter)

        sse_events = []
        async def collect_sse(name, data):
            sse_events.append({"event": name, "data": data})

        handler.register_sse_callback(collect_sse)

        event = EngineEvent(
            event_id="evt_e2e_002", timestamp="t", type="player_action",
            data={"raw_text": "看看周围"}, context_hints=[], game_state={},
        )

        response = await handler.handle_event(event)

        event_names = [e["event"] for e in sse_events]
        assert "turn_start" in event_names
        assert "turn_end" in event_names

        assert response["narrative"] != ""
        assert "response_id" in response

    @pytest.mark.asyncio
    async def test_multiple_turns(
        self, workspace, skills_dir, system_prompt, mock_services
    ):
        """多回合连续交互"""
        adapter = TextAdapter(
            mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"]
        )
        await adapter.connect()

        gm = GameMaster(
            llm_client=make_mock_llm(
                narrative="铁匠点了点头。",
                commands=[],
                memory_updates=[{
                    "file": "session/current.md",
                    "action": "append",
                    "content": "\n[回合N] 测试。",
                }],
            ),
            memory_manager=MemoryManager(str(workspace)),
            skill_loader=SkillLoader(str(skills_dir)),
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )

        for i in range(3):
            event = EngineEvent(
                event_id=f"evt_multi_{i}", timestamp="t", type="player_action",
                data={"raw_text": f"第{i+1}次交互"}, context_hints=[], game_state={},
            )
            response = await gm.handle_event(event)
            assert response["stats"]["turn"] == i + 1

        assert gm.turn_count == 3
        assert len(gm.history) >= 6
