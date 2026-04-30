# Game Master Agent V2 - P4: 集成与清理

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户将 V1 的 Game Master Agent **重构为 V2 通用游戏驱动 Agent**。
- **技术栈**: Python 3.11+ / DeepSeek API / FastAPI / SQLite / python-frontmatter
- **包管理器**: uv
- **LLM**: DeepSeek（通过 OpenAI 兼容接口调用）
- **开发IDE**: Trae

### 前置条件

**P0-P3 已完成**。以下模块全部就绪：

**后端 (P0+P1+P2)**:
- `src/memory/` — 记忆系统（file_io + loader + manager）
- `src/skills/` — Skill 系统（loader + 5 个内置 SKILL.md）
- `src/adapters/` — 引擎适配层（base + text_adapter）
- `src/agent/` — Agent 核心（command_parser + prompt_builder + game_master + event_handler）
- `src/services/llm_client.py` — AsyncOpenAI + stream()
- `src/api/routes/` — workspace + skills + agent 路由
- `src/api/sse.py` — SSE 流式推送
- `prompts/system_prompt.md` — Agent 主提示词
- 基线测试 **188+** 个通过

**前端 (P3)**:
- `workbench/` — Vue 3 + Naive UI + Vite 管理端
- FileTree / MdEditor / AgentStatus / SSEEventLog / ChatDebug 组件

### P4 阶段目标

1. **清理 V1 遗留代码** — 修复 ws.py/action.py 旧接口、清理废弃引用
2. **TextAdapter 命令行模式** — 实现 MUD 交互入口
3. **端到端集成测试** — 完整流程验证
4. **性能基准测试** — 单回合延迟、token 消耗
5. **文档更新** — README + 使用说明

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行，每完成一步都验证通过后再进行下一步
2. **先验证再继续**：每个步骤都有"验收标准"，必须验证通过才能继续
3. **主动执行**：用户说"开始"后，你应该主动执行每一步，不需要用户反复催促
4. **遇到错误先尝试解决**：如果某步出错，先尝试自行排查修复，3次失败后再询问用户
5. **每步完成后汇报**：完成一步后，简要汇报结果和下一步计划
6. **代码规范**：
   - 所有文件使用 UTF-8 编码
   - Python 文件使用中文注释
   - 遵循 PEP 8 风格
   - 使用 `from __future__ import annotations` 启用延迟注解
7. **不要跳步**：即使用户让你跳过，也要提醒风险后再决定
8. **谨慎删除**：删除文件前确认没有其他模块依赖

## 参考设计文档

| 文档 | 内容 |
|------|------|
| `docs/architecture_v2.md` | V2 架构总览 |
| `docs/communication_protocol.md` | JSON 命令流、SSE 协议 |
| `docs/engine_adapter.md` | TextAdapter 设计 |
| `docs/dev_plan_v2.md` | V2 开发计划总览 |

## V1 经验教训（必须遵守）

1. **PowerShell `&&` 语法**: 用 `;` 分隔多条命令
2. **测试隔离**: 每个测试模块用 `teardown_module()` 清理全局状态
3. **SQLite datetime('now')**: 同一秒内时间戳相同，测试用 `>=` 而非 `==`
4. **中文括号**: 测试中用英文括号 `()`
5. **原子写入**: 所有 .md 文件写入必须用 `atomic_write()`
6. **YAML Front Matter**: 引擎写 FM，Agent 写 Body
7. **DeepSeek reasoning_content**: 用 `getattr(delta, 'reasoning_content', None)` 获取
8. **tool_calls 增量拼接**: 用 dict 按 index 累积
9. **AsyncOpenAI**: 所有 `self.client` 调用需要 `await`

---

## P4: 集成与清理（共 5 步）

### 步骤 4.1 - 清理 V1 遗留代码

**目的**: 修复 API 层兼容问题，删除被 V2 替代的废弃模块

**背景**:
1. P1 重写了 `game_master.py`，但 `ws.py` 和 `action.py` 仍使用 V1 旧构造函数
2. P3 创建了 `workbench/`，V1 的 `src/web/` 和 `src/admin/` 已被替代
3. P1 创建了 `prompts/system_prompt.md`，V1 的 `src/prompts/gm_system.py` 已被替代

**执行**:

**4.1.1 修复 ws.py 和 action.py**

先阅读 `src/api/routes/ws.py` 和 `src/api/routes/action.py`，理解它们如何创建和使用 GameMaster。

V1 旧接口: `GameMaster(world_id, player_id, llm_client)`
V2 新接口: 通过 `set_agent_refs(event_handler, game_master, engine_adapter)` 注入

两种方案：
- **方案 A（推荐）**: 如果 ws.py/action.py 的功能已被 P2 的 `/api/agent/event` 端点覆盖，注释掉旧 GameMaster 创建代码，添加 `# TODO: V2 迁移 - 已被 /api/agent/event 替代`
- **方案 B**: 如果仍有独立价值，改用 V2 的 `EventHandler` 实例

具体操作：
1. 阅读 `src/api/routes/ws.py` 完整代码
2. 阅读 `src/api/routes/action.py` 完整代码
3. 阅读 `tests/test_api_full.py`，理解它测试什么
4. 选择方案 A 或 B 执行
5. 运行测试确认修复

**4.1.2 删除被 V2 替代的废弃目录**

以下目录/文件已被 V2 新模块完全替代，可以安全删除：

```powershell
# 1. 删除 V1 旧静态前端（被 workbench/ 替代）
Remove-Item -Recurse -Force "d:\worldSim-master\src\web"

# 2. 删除 V1 旧管理端（被 workbench/ 替代）
Remove-Item -Recurse -Force "d:\worldSim-master\src\admin"

# 3. 删除 V1 旧系统提示词（被 prompts/system_prompt.md 替代）
Remove-Item -Force "d:\worldSim-master\src\prompts\gm_system.py"
```

删除前先搜索确认没有其他模块依赖它们：

```powershell
# 搜索对 src/web 的引用
Select-String -Path "src\**\*.py" -Pattern "src\.web|from src\.web" -Recurse

# 搜索对 src/admin 的引用
Select-String -Path "src\**\*.py" -Pattern "src\.admin|from src\.admin" -Recurse

# 搜索对 gm_system 的引用
Select-String -Path "src\**\*.py" -Pattern "gm_system" -Recurse
```

如果发现引用，先修复引用再删除。

**4.1.3 清理其他 V1 遗留引用**

```powershell
# 搜索可能遗留的旧接口引用
cd d:\worldSim-master
Select-String -Path "src\**\*.py" -Pattern "chat_with_tools|process_stream|TOOL_REGISTRY" -Recurse
```

如果发现：
- `chat_with_tools` 调用 → 确认已改为 `stream()` 或删除
- `process_stream` 调用 → 确认已改为 `handle_event()`
- `TOOL_REGISTRY` 引用 → 确认已删除（P0 已清理）

**4.1.4 清理废弃测试**

```powershell
cd d:\worldSim-master
uv run pytest tests/ --collect-only -q 2>&1 | Select-Object -Last 5
```

如果有测试因为 import 错误而无法收集，修复或删除它们。

**验收**: `uv run pytest tests/ -v --tb=short` 全部通过，0 失败

---

### 步骤 4.2 - TextAdapter 命令行模式

**目的**: 实现 MUD 交互入口，验证完整 Agent 流程可通过命令行使用

**设计参考**: `docs/engine_adapter.md` 第 4 节

**执行**:
创建 `src/cli_v2.py`：

**完整代码**:

```python
"""
V2 命令行入口 — MUD 文字游戏模式。
通过 TextAdapter 连接 SQLite 引擎，启动事件驱动的 Agent 循环。
"""
from __future__ import annotations

import asyncio
import logging
import sys

from src.adapters.text_adapter import TextAdapter
from src.adapters.base import EngineEvent
from src.agent.game_master import GameMaster
from src.agent.event_handler import EventHandler
from src.memory.manager import MemoryManager
from src.skills.loader import SkillLoader
from src.services.llm_client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 配置
WORLD_ID = "w1"
PLAYER_ID = "p1"
WORKSPACE_PATH = "./workspace"
SKILLS_PATH = "./skills"
SYSTEM_PROMPT_PATH = "./prompts/system_prompt.md"


async def run_text_mode():
    """启动 MUD 文字游戏模式"""

    # 1. 初始化 LLM
    logger.info("初始化 LLM 客户端...")
    llm_client = LLMClient()

    # 2. 初始化记忆和 Skill
    logger.info("初始化记忆系统...")
    memory_manager = MemoryManager(WORKSPACE_PATH)

    logger.info("初始化 Skill 系统...")
    skill_loader = SkillLoader(SKILLS_PATH)

    # 3. 初始化引擎适配器
    logger.info("连接游戏引擎...")
    adapter = TextAdapter.from_world_id(WORLD_ID)
    await adapter.connect()

    # 4. 初始化 GameMaster
    logger.info("初始化 Game Master Agent...")
    game_master = GameMaster(
        llm_client=llm_client,
        memory_manager=memory_manager,
        skill_loader=skill_loader,
        engine_adapter=adapter,
        system_prompt_path=SYSTEM_PROMPT_PATH,
    )

    # 5. 初始化 EventHandler
    event_handler = EventHandler(
        game_master=game_master,
        engine_adapter=adapter,
    )

    # 6. 注册 SSE 回调（命令行模式只打印关键事件）
    async def print_sse(event_name: str, data: dict):
        if event_name == "turn_start":
            print("\n--- 回合开始 ---")
        elif event_name == "command":
            intent = data.get("intent", "")
            if intent != "no_op":
                print(f"  [指令] {intent}")
        elif event_name == "turn_end":
            stats = data.get("stats", {})
            print(f"--- 回合结束 (tokens: {stats.get('tokens_used', 0)}) ---\n")

    event_handler.register_sse_callback(print_sse)

    # 7. 交互循环
    print("=" * 50)
    print("  Game Master Agent V2 — MUD 模式")
    print(f"  世界: {WORLD_ID} | 玩家: {PLAYER_ID}")
    print("  输入 'quit' 退出, 'status' 查看状态")
    print("=" * 50)

    # 获取初始游戏状态
    player = await adapter.query_state("player", {"player_id": PLAYER_ID})
    location = player.get("location", "未知") if player else "未知"
    print(f"\n你当前在: {location}\n")

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        if user_input.lower() == "status":
            status = {
                "回合": game_master.turn_count,
                "总 Token": game_master.total_tokens,
                "历史长度": len(game_master.history),
            }
            for k, v in status.items():
                print(f"  {k}: {v}")
            continue

        if user_input.lower() == "help":
            print("  可用命令:")
            print("  quit/exit — 退出")
            print("  status — 查看状态")
            print("  help — 帮助")
            print("  其他输入 — 作为玩家操作发送给 Agent")
            continue

        # 构造引擎事件
        event = EngineEvent(
            event_id=f"cli_{game_master.turn_count + 1}",
            timestamp=__import__("datetime").datetime.now().isoformat(),
            type="player_action",
            data={"raw_text": user_input, "player_id": PLAYER_ID},
            context_hints=[],
            game_state={},
        )

        # 处理事件
        try:
            response = await event_handler.handle_event(event)
            print(f"\n{response.get('narrative', '')}")
        except Exception as e:
            logger.error(f"处理事件失败: {e}", exc_info=True)
            print(f"\n[错误] {e}")


def main():
    """入口"""
    try:
        asyncio.run(run_text_mode())
    except KeyboardInterrupt:
        print("\n再见！")


if __name__ == "__main__":
    main()
```

**验收**: `python -c "from src.cli_v2 import main; print('OK')"` 成功

---

### 步骤 4.3 - 端到端集成测试

**目的**: 验证完整流程：启动 → 连接 → 事件 → Agent 响应 → 记忆更新 → 指令执行

**执行**:
创建 `tests/test_integration/test_full_flow.py`：

**完整代码**:

```python
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
```

**验收**: `pytest tests/test_integration/test_full_flow.py -v` 全部通过（>=5 个测试）

---

### 步骤 4.4 - 性能基准测试

**目的**: 测量单回合延迟和 token 消耗，建立性能基线

**执行**:
创建 `tests/test_integration/test_performance.py`：

**完整代码**:

```python
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
```

**验收**: `pytest tests/test_integration/test_performance.py -v` 全部通过

---

### 步骤 4.5 - 文档更新

**目的**: 更新 README 和使用说明，反映 V2 架构

**执行**:

**4.5.1 更新 README.md**

先阅读现有的 `README.md`，然后更新为 V2 版本。

**README.md 完整内容**（如果原文件不存在则创建，存在则替换）:

```markdown
# Game Master Agent V2

通用游戏驱动 Agent 服务 — 像 Trae 驱动代码一样驱动游戏。

## 架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  游戏引擎    │────▶│  Agent 服务   │────▶│  WorkBench   │
│ (TextAdapter)│◀────│ (GameMaster) │     │ (Vue 前端)   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │  DeepSeek    │
                    │  (LLM API)   │
                    └──────────────┘
```

### 核心组件

| 组件 | 路径 | 说明 |
|------|------|------|
| GameMaster | `src/agent/game_master.py` | 事件驱动主循环 |
| CommandParser | `src/agent/command_parser.py` | 4 级容错 JSON 解析 |
| PromptBuilder | `src/agent/prompt_builder.py` | Prompt 组装 |
| EventHandler | `src/agent/event_handler.py` | 事件分发 + SSE |
| MemoryManager | `src/memory/manager.py` | .md 记忆管理 |
| SkillLoader | `src/skills/loader.py` | SKILL.md 发现与加载 |
| TextAdapter | `src/adapters/text_adapter.py` | MUD 文字适配器 |
| LLMClient | `src/services/llm_client.py` | DeepSeek API (AsyncOpenAI) |

### 记忆系统

Agent 使用 `.md` 文件作为记忆，采用 YAML Front Matter + Markdown Body 双层格式：

- **YAML Front Matter**: 引擎写入的结构化数据（HP、好感度等）
- **Markdown Body**: Agent 写入的认知记录（交互历史、剧情笔记等）

### Skill 系统

基于 SKILL.md 开放标准，Agent 可加载和使用技能：

- `skills/builtin/` — 内置技能（combat, dialogue, quest, exploration, narration）
- `skills/agent_created/` — Agent 自创技能

## 快速开始

### 安装

```bash
uv sync
```

### 命令行模式 (MUD)

```bash
uv run python src/cli_v2.py
```

### API 服务

```bash
uvicorn src.api.app:app --reload --port 8000
```

API 文档: http://localhost:8000/docs

### WorkBench (管理端)

```bash
# 终端 1: 启动后端
uvicorn src.api.app:app --reload --port 8000

# 终端 2: 启动前端
cd workbench
npm install
npm run dev
```

访问 http://localhost:5173

## 测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行特定模块
uv run pytest tests/test_memory/ -v
uv run pytest tests/test_skills/ -v
uv run pytest tests/test_adapters/ -v
uv run pytest tests/test_agent/ -v
uv run pytest tests/test_api/ -v
uv run pytest tests/test_integration/ -v
```

## 项目结构

```
worldSim-master/
├── src/
│   ├── agent/           # Agent 核心
│   │   ├── game_master.py
│   │   ├── command_parser.py
│   │   ├── prompt_builder.py
│   │   └── event_handler.py
│   ├── memory/          # 记忆系统
│   │   ├── file_io.py
│   │   ├── loader.py
│   │   └── manager.py
│   ├── skills/          # Skill 系统
│   │   └── loader.py
│   ├── adapters/        # 引擎适配层
│   │   ├── base.py
│   │   └── text_adapter.py
│   ├── services/        # V1 服务（保留）
│   │   ├── llm_client.py
│   │   ├── cache.py
│   │   └── model_router.py
│   ├── models/          # SQLite 数据模型
│   └── api/             # FastAPI 路由
│       ├── app.py
│       ├── routes/
│       │   ├── workspace.py
│       │   ├── skills.py
│       │   └── agent.py
│       └── sse.py
├── prompts/
│   └── system_prompt.md
├── skills/
│   └── builtin/         # 内置 SKILL.md
├── workspace/           # Agent 记忆文件
├── workbench/           # Vue 前端
├── tests/               # 测试
└── docs/                # 设计文档
```

## 技术栈

- **后端**: Python 3.11+ / FastAPI / SQLite / DeepSeek API
- **前端**: Vue 3 / TypeScript / Naive UI / Vite / md-editor-v3
- **AI**: DeepSeek (OpenAI 兼容接口)
- **记忆**: python-frontmatter (YAML + Markdown)
```

**4.5.2 更新 docs/dev_plan_v2.md 完成状态**

在 `docs/dev_plan_v2.md` 的每个阶段标题后添加 ✅ 标记：

```
## P0: 清理冗余 + 基础设施 ✅
## P1: 核心重构 ✅
## P2: API 扩展 ✅
## P3: WorkBench ✅
## P4: 集成与清理 ✅  ← 当前
```

**验收**: README.md 存在且内容完整

---

## P4 完成检查清单

- [ ] Step 4.1: V1 遗留代码已清理（ws.py/action.py 修复或标记）
- [ ] Step 4.2: `cli_v2.py` 创建，可导入
- [ ] Step 4.3: 端到端集成测试通过 (>=5 个)
- [ ] Step 4.4: 性能基准测试通过 (>=5 个)
- [ ] Step 4.5: README.md 更新完毕
- [ ] **全部测试通过（目标 >=200 个）**
- [ ] `npm run build` 前端构建无错误

---

## V2 完成标准

当 P4 全部完成后，V2 重构即告完成：

- [ ] **功能完整**: Agent 可通过 CLI、API、WorkBench 三种方式使用
- [ ] **测试覆盖**: 全部测试通过，>=200 个
- [ ] **性能达标**: 单回合框架开销 < 200ms
- [ ] **文档齐全**: README + 设计文档 + 使用说明
- [ ] **V1 兼容**: SQLite 数据模型保留，V1 服务可用
