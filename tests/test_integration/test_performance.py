"""
性能基准测试。
测量单回合延迟、token 消耗、记忆加载时间。
注意: 这些测试使用 mock LLM，测量的是框架开销而非 LLM 延迟。
"""
import pytest
import json
import time
from unittest.mock import MagicMock
from pathlib import Path

from src.adapters.base import EngineEvent
from src.adapters.text_adapter import TextAdapter
from src.agent.game_master import GameMaster
from src.agent.command_parser import CommandParser
from src.memory.manager import MemoryManager
from src.memory.loader import MemoryLoader
from src.skills.loader import SkillLoader


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    for d in ["npcs", "locations", "story", "quests", "items", "player", "session"]:
        (ws / d).mkdir()
    # 创建 10 个 NPC 文件测试加载性能
    for i in range(10):
        (ws / "npcs" / f"npc_{i}.md").write_text(
            f"---\nname: NPC_{i}\ntype: npc\nhp: {50 + i * 10}\nversion: 1\n---\n"
            f"## 记录\n[第1天] NPC_{i} 的初始记录。\n" * 5,
            encoding="utf-8",
        )
    return ws


@pytest.fixture
def skills_dir(tmp_path):
    sd = tmp_path / "skills"
    d = sd / "builtin" / "narration"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: narration\ndescription: 叙事。\nversion: 1.0.0\n"
        "triggers: []\nallowed-tools: []\n---\n\n# 叙事\n使用中文。",
        encoding="utf-8",
    )
    return sd


@pytest.fixture
def system_prompt(tmp_path):
    sp = tmp_path / "system_prompt.md"
    sp.write_text("你是 GM Agent。", encoding="utf-8")
    return str(sp)


@pytest.fixture
def mock_services():
    s = {k: MagicMock() for k in ("world", "player", "npc", "item", "quest")}
    s["world"].list_worlds.return_value = [{"id": "w1"}]
    s["player"].list_players.return_value = [{"id": "p1"}]
    s["player"].get_player.return_value = {"id": "p1", "hp": 100, "version": 1}
    s["npc"].get_npc.return_value = {"id": "npc_1", "name": "NPC_1", "version": 1}
    s["npc"].list_npcs.return_value = [{"id": f"npc_{i}", "name": f"NPC_{i}"} for i in range(10)]
    return s


def make_fast_llm():
    """创建快速 mock LLM"""
    client = MagicMock()
    response_json = json.dumps({
        "narrative": "测试叙事。",
        "commands": [],
        "memory_updates": [],
    }, ensure_ascii=False)

    async def mock_stream(messages):
        yield {"event": "token", "data": {"text": response_json}}

    client.stream = mock_stream
    return client


class TestPerformance:
    """性能基准测试"""

    def test_memory_loader_index_speed(self, workspace):
        """记忆索引加载速度: 10 个文件应在 50ms 内"""
        loader = MemoryLoader(str(workspace))
        files = [f"npcs/npc_{i}.md" for i in range(10)]

        start = time.perf_counter()
        result = loader.load_index(files)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.05, f"索引加载耗时 {elapsed:.3f}s，超过 50ms"
        assert len(result) > 0

    def test_memory_loader_activation_speed(self, workspace):
        """记忆激活加载速度: 10 个文件应在 100ms 内"""
        loader = MemoryLoader(str(workspace))
        files = [f"npcs/npc_{i}.md" for i in range(10)]

        start = time.perf_counter()
        result = loader.load_activation(files)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"激活加载耗时 {elapsed:.3f}s，超过 100ms"

    def test_skill_loader_discover_speed(self, skills_dir):
        """Skill 发现速度: 应在 50ms 内"""
        loader = SkillLoader(str(skills_dir))

        start = time.perf_counter()
        skills = loader.discover_all()
        elapsed = time.perf_counter() - start

        assert elapsed < 0.05, f"Skill 发现耗时 {elapsed:.3f}s"
        assert len(skills) >= 1

    def test_command_parser_speed(self):
        """JSON 解析速度: 1000 次解析应在 100ms 内"""
        parser = CommandParser()
        test_json = json.dumps({
            "narrative": "测试叙事文本。",
            "commands": [{"intent": "no_op", "params": {}}],
            "memory_updates": [],
        })

        start = time.perf_counter()
        for _ in range(1000):
            parser.parse(test_json)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"1000 次解析耗时 {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_single_turn_framework_overhead(
        self, workspace, skills_dir, system_prompt, mock_services
    ):
        """单回合框架开销（不含 LLM）: 应在 200ms 内"""
        adapter = TextAdapter(
            mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"]
        )
        await adapter.connect()

        gm = GameMaster(
            llm_client=make_fast_llm(),
            memory_manager=MemoryManager(str(workspace)),
            skill_loader=SkillLoader(str(skills_dir)),
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )

        event = EngineEvent(
            event_id="perf_001", timestamp="t", type="player_action",
            data={"raw_text": "测试性能"}, context_hints=["npcs/npc_0"], game_state={},
        )

        start = time.perf_counter()
        response = await gm.handle_event(event)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.2, f"单回合框架开销 {elapsed:.3f}s，超过 200ms"
        assert response["narrative"] != ""
