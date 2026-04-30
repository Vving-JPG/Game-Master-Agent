"""GameMaster + TextAdapter 集成测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agent.game_master import GameMaster
from src.agent.command_parser import CommandParser
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
    return ws


@pytest.fixture
def skills_dir(tmp_path):
    sd = tmp_path / "skills"
    builtin = sd / "builtin" / "narration"
    builtin.mkdir(parents=True)
    (builtin / "SKILL.md").write_text(
        "---\nname: narration\ndescription: 叙事风格控制。\nversion: 1.0.0\n"
        "triggers: []\nallowed-tools: []\n---\n\n# 叙事风格\n\n使用中文第二人称。",
        encoding="utf-8"
    )
    return sd


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
    s["npc"].list_npcs.return_value = [
        {"id": "npc_1", "name": "铁匠"}, {"id": "npc_2", "name": "药剂师"}
    ]
    return s


@pytest.fixture
def memory_manager(workspace):
    return MemoryManager(str(workspace))


@pytest.fixture
def skill_loader(skills_dir):
    return SkillLoader(str(skills_dir))


@pytest.fixture
def adapter(mock_services):
    return TextAdapter(
        mock_services["world"], mock_services["player"],
        mock_services["npc"], mock_services["item"], mock_services["quest"]
    )


@pytest.fixture
def mock_llm_client():
    client = MagicMock()

    async def mock_stream(messages):
        yield {"event": "token", "data": {"text": '{"narrative": "铁匠点了点头。", "commands": [{"intent": "no_op", "params": {}}], "memory_updates": [{"file": "session/current.md", "action": "append", "content": "\\n[回合1] 测试。"}]}'}}

    client.stream = mock_stream
    return client


@pytest.fixture
def system_prompt(tmp_path):
    sp = tmp_path / "system_prompt.md"
    sp.write_text("你是一个游戏 GM Agent。输出 JSON 格式。", encoding="utf-8")
    return str(sp)


class TestGameMasterIntegration:
    """GameMaster 集成测试"""

    @pytest.mark.asyncio
    async def test_handle_player_action(
        self, mock_llm_client, memory_manager, skill_loader, adapter, system_prompt
    ):
        gm = GameMaster(
            llm_client=mock_llm_client,
            memory_manager=memory_manager,
            skill_loader=skill_loader,
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )
        await adapter.connect()

        event = EngineEvent(
            event_id="evt_001",
            timestamp="2026-04-28T14:00:00",
            type="player_action",
            data={"raw_text": "你好铁匠", "player_id": "p1"},
            context_hints=["npcs/铁匠"],
            game_state={"location": "town", "player_hp": 100},
        )

        response = await gm.handle_event(event)

        assert "response_id" in response
        assert response["event_id"] == "evt_001"
        assert "铁匠" in response["narrative"]
        assert response["stats"]["turn"] == 1

    @pytest.mark.asyncio
    async def test_history_updated(
        self, mock_llm_client, memory_manager, skill_loader, adapter, system_prompt
    ):
        gm = GameMaster(
            llm_client=mock_llm_client,
            memory_manager=memory_manager,
            skill_loader=skill_loader,
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )
        await adapter.connect()

        event = EngineEvent(
            event_id="evt_002", timestamp="t", type="player_action",
            data={"raw_text": "测试"}, context_hints=[], game_state={},
        )
        await gm.handle_event(event)

        assert len(gm.history) >= 2

    @pytest.mark.asyncio
    async def test_reset(
        self, mock_llm_client, memory_manager, skill_loader, adapter, system_prompt
    ):
        gm = GameMaster(
            llm_client=mock_llm_client,
            memory_manager=memory_manager,
            skill_loader=skill_loader,
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )
        await adapter.connect()

        event = EngineEvent(
            event_id="evt_003", timestamp="t", type="player_action",
            data={"raw_text": "测试"}, context_hints=[], game_state={},
        )
        await gm.handle_event(event)
        assert gm.turn_count == 1

        gm.reset()
        assert gm.turn_count == 0
        assert len(gm.history) == 0
