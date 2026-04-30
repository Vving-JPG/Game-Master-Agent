"""
端到端集成测试。
验证完整的 Agent 流程：事件 → Prompt → LLM → 解析 → 记忆 → 指令 → 引擎。
"""
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

from src.adapters.base import EngineEvent, CommandResult
from src.adapters.text_adapter import TextAdapter
from src.agent.game_master import GameMaster
from src.agent.event_handler import EventHandler
from src.agent.command_parser import CommandParser
from src.memory.manager import MemoryManager
from src.skills.loader import SkillLoader


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    for d in ["npcs", "locations", "story", "quests", "items", "player", "session"]:
        (ws / d).mkdir()
    # 创建初始记忆文件
    (ws / "player" / "profile.md").write_text(
        "---\nname: 测试玩家\ntype: player\nhp: 100\nversion: 1\n---\n"
        "## 状态\n[第1天] 冒险开始。",
        encoding="utf-8",
    )
    (ws / "npcs" / "铁匠.md").write_text(
        "---\nname: 铁匠\ntype: npc\nhp: 80\nrelationship_with_player: 30\nversion: 2\n---\n"
        "## 交互记录\n[第1天] 铁匠铺的老板。",
        encoding="utf-8",
    )
    (ws / "session" / "current.md").write_text(
        "---\ntype: session\nversion: 1\n---\n会话开始。",
        encoding="utf-8",
    )
    return ws


@pytest.fixture
def skills_dir(tmp_path):
    sd = tmp_path / "skills"
    for name, triggers, tools, body in [
        ("narration", "[]", "[]", "# 叙事\n使用中文第二人称。"),
        ("dialogue", '[{"keyword": ["聊天", "对话"]}]', '["update_npc_relationship"]',
         "# 对话\n好感度影响对话风格。"),
        ("combat", '[{"event_type": "combat_start"}]', '["modify_stat"]',
         "# 战斗\n伤害 = 攻击 - 防御 * 0.5"),
    ]:
        d = sd / "builtin" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {name}系统。\nversion: 1.0.0\n"
            f"triggers: {triggers}\nallowed-tools: {tools}\n---\n\n{body}\n",
            encoding="utf-8",
        )
    return sd


@pytest.fixture
def system_prompt(tmp_path):
    sp = tmp_path / "system_prompt.md"
    sp.write_text(
        "你是 GM Agent。输出 JSON: {narrative, commands, memory_updates}。",
        encoding="utf-8",
    )
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
    s["npc"].update_npc.return_value = True
    return s


def make_llm(narrative: str, commands: list = None, memory_updates: list = None):
    """创建模拟 LLM 客户端"""
    client = MagicMock()
    commands = commands or []
    memory_updates = memory_updates or []
    response_json = json.dumps({
        "narrative": narrative,
        "commands": commands,
        "memory_updates": memory_updates,
    }, ensure_ascii=False)

    async def mock_stream(messages):
        yield {"event": "token", "data": {"text": response_json}}

    client.stream = mock_stream
    return client


class TestFullFlow:
    """完整流程集成测试"""

    @pytest.mark.asyncio
    async def test_dialogue_flow(
        self, workspace, skills_dir, system_prompt, mock_services
    ):
        """完整对话流程: 玩家输入 → Agent → 叙事 + 指令 + 记忆"""
        adapter = TextAdapter(
            mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"]
        )
        await adapter.connect()

        gm = GameMaster(
            llm_client=make_llm(
                narrative="铁匠擦了擦汗，说道：'你需要什么？'",
                commands=[{
                    "intent": "update_npc_relationship",
                    "params": {"npc_id": "npc_1", "change": 2, "reason": "友好对话"}
                }],
                memory_updates=[{
                    "file": "npcs/铁匠.md",
                    "action": "append",
                    "content": "\n[第2天] 玩家和铁匠友好交谈。"
                }],
            ),
            memory_manager=MemoryManager(str(workspace)),
            skill_loader=SkillLoader(str(skills_dir)),
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )

        event = EngineEvent(
            event_id="e2e_001",
            timestamp="2026-04-29T10:00:00",
            type="player_action",
            data={"raw_text": "和铁匠聊聊", "player_id": "p1"},
            context_hints=["npcs/铁匠"],
            game_state={"location": "town", "player_hp": 100},
        )

        response = await gm.handle_event(event)

        # 验证叙事
        assert "铁匠" in response["narrative"]

        # 验证指令执行
        assert len(response["command_results"]) >= 1
        assert response["command_results"][0]["status"] == "success"

        # 验证记忆更新
        import frontmatter
        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert "第2天" in post.content

        # 验证会话记录
        session = frontmatter.load(str(workspace / "session" / "current.md"))
        assert "回合1" in session.content

    @pytest.mark.asyncio
    async def test_multi_turn_consistency(
        self, workspace, skills_dir, system_prompt, mock_services
    ):
        """多回合一致性: 连续 3 轮交互，验证历史和记忆累积"""
        adapter = TextAdapter(
            mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"]
        )
        await adapter.connect()

        gm = GameMaster(
            llm_client=make_llm(
                narrative="你环顾四周。",
                commands=[],
                memory_updates=[{
                    "file": "session/current.md",
                    "action": "append",
                    "content": f"\n[回合N] 测试交互。",
                }],
            ),
            memory_manager=MemoryManager(str(workspace)),
            skill_loader=SkillLoader(str(skills_dir)),
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )

        for i in range(3):
            event = EngineEvent(
                event_id=f"multi_{i}",
                timestamp="t",
                type="player_action",
                data={"raw_text": f"第{i+1}次操作"},
                context_hints=[],
                game_state={},
            )
            response = await gm.handle_event(event)
            assert response["stats"]["turn"] == i + 1

        # 验证历史累积
        assert gm.turn_count == 3
        assert len(gm.history) >= 6  # 3 轮 * 2 条

    @pytest.mark.asyncio
    async def test_command_rejection_handling(
        self, workspace, skills_dir, system_prompt, mock_services
    ):
        """指令拒绝处理: 引擎拒绝指令时 Agent 不崩溃"""
        adapter = TextAdapter(
            mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"]
        )
        await adapter.connect()

        # 模拟引擎拒绝 teleport
        original_send = adapter.send_commands

        async def mock_send_reject(commands):
            results = []
            for cmd in commands:
                if cmd["intent"] == "teleport_player":
                    results.append(CommandResult(
                        intent="teleport_player",
                        status="rejected",
                        reason="传送魔法被禁用",
                        suggestion="步行前往",
                    ))
                else:
                    results.append(CommandResult(
                        intent=cmd["intent"],
                        status="success",
                    ))
            return results

        adapter.send_commands = mock_send_reject

        gm = GameMaster(
            llm_client=make_llm(
                narrative="你试图传送，但失败了。",
                commands=[{"intent": "teleport_player", "params": {"location_id": "castle"}}],
                memory_updates=[],
            ),
            memory_manager=MemoryManager(str(workspace)),
            skill_loader=SkillLoader(str(skills_dir)),
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )

        event = EngineEvent(
            event_id="reject_001", timestamp="t", type="player_action",
            data={"raw_text": "传送到城堡"}, context_hints=[], game_state={},
        )

        response = await gm.handle_event(event)

        # 验证拒绝被正确记录
        assert len(response["command_results"]) == 1
        assert response["command_results"][0]["status"] == "rejected"
        assert "传送" in response["command_results"][0].get("reason", "")

        # 验证拒绝信息进入历史
        reject_found = any(
            "传送" in msg.get("content", "") and "失败" in msg.get("content", "")
            for msg in gm.history
        )
        assert reject_found

    @pytest.mark.asyncio
    async def test_event_handler_sse_sequence(
        self, workspace, skills_dir, system_prompt, mock_services
    ):
        """EventHandler SSE 事件序列验证"""
        adapter = TextAdapter(
            mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"]
        )
        await adapter.connect()

        gm = GameMaster(
            llm_client=make_llm(
                narrative="测试叙事。",
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
        async def collect(name, data):
            sse_events.append(name)

        handler.register_sse_callback(collect)

        event = EngineEvent(
            event_id="sse_001", timestamp="t", type="player_action",
            data={"raw_text": "测试"}, context_hints=[], game_state={},
        )

        await handler.handle_event(event)

        event_names = sse_events
        assert "turn_start" in event_names
        assert "turn_end" in event_names

    @pytest.mark.asyncio
    async def test_parser_fallback(
        self, workspace, skills_dir, system_prompt, mock_services
    ):
        """解析器兜底: LLM 返回非 JSON 时作为 narrative"""
        adapter = TextAdapter(
            mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"]
        )
        await adapter.connect()

        # LLM 返回纯文本（非 JSON）
        client = MagicMock()
        async def mock_stream(messages):
            yield {"event": "token", "data": {"text": "这是一段纯文本叙事，没有 JSON 格式。"}}
        client.stream = mock_stream

        gm = GameMaster(
            llm_client=client,
            memory_manager=MemoryManager(str(workspace)),
            skill_loader=SkillLoader(str(skills_dir)),
            engine_adapter=adapter,
            system_prompt_path=system_prompt,
        )

        event = EngineEvent(
            event_id="parse_001", timestamp="t", type="player_action",
            data={"raw_text": "测试"}, context_hints=[], game_state={},
        )

        response = await gm.handle_event(event)

        # 兜底: 整个文本作为 narrative
        assert "纯文本叙事" in response["narrative"]
        assert response["commands"] == []
