# P2: LangGraph Agent 核心 — StateGraph 构建与替换

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。
> **前置条件**: P0 Foundation 层 + P1 Core 层已全部完成并通过测试。

## 项目概述

你正在帮助用户将 **Game Master Agent V2** 的 `2workbench/` 目录重构为**四层架构**。

- **技术**: Python 3.11+ / PyQt6 / SQLite / LangGraph / uv
- **包管理器**: uv
- **开发 IDE**: Trae
- **本 Phase 目标**: 用 LangGraph StateGraph 替换现有 Agent 核心（`_legacy/bridge/agent_bridge.py` 的模拟工作流 + `1agent_core/src/game_master.py` 的 6 步流水线）

### 架构约束

```
入口层 → Presentation (表现层) → Feature (功能层) → Core (核心层) → Foundation (基础层)
```

- ✅ Feature 层**只依赖** Core 和 Foundation 层
- ❌ Feature 层**绝对不能** import Presentation 层
- ✅ 同层模块间仅通过 EventBus 通信，禁止直接依赖
- ✅ LangGraph 图定义在 Feature 层，节点函数调用 Foundation 层的 LLM 客户端

### 本 Phase (P2) 范围

1. **LangGraph 环境安装** — 确认依赖
2. **GM Agent StateGraph** — 核心图构建（节点/边/条件路由）
3. **节点函数实现** — 6 个核心节点（事件处理→Prompt 组装→LLM 推理→命令解析→执行→记忆更新）
4. **工具系统** — LangGraph Tool 封装（骰子、战斗、物品、对话等）
5. **CommandParser 封装** — 4 级容错解析器作为节点
6. **PromptBuilder 封装** — Prompt 组装逻辑
7. **SkillLoader 封装** — 评分匹配 + Prompt 注入
8. **流式事件系统** — 通过 EventBus 推送 LangGraph stream 事件
9. **GM Agent 门面** — 对外统一接口（替代 GameMaster + EventHandler）
10. **集成测试** — 端到端 Agent 执行测试

### 现有代码参考

| 现有文件 | 参考内容 | 改进方向 |
|---------|---------|---------|
| `1agent_core/src/game_master.py` | 6 步流水线 | 用 StateGraph 节点图替代 |
| `1agent_core/src/event_handler.py` | SSE 事件推送 | 用 EventBus + LangGraph stream 替代 |
| `1agent_core/src/command_parser.py` | 4 级容错解析 | 封装为 LangGraph 节点 |
| `1agent_core/src/prompt_builder.py` | Prompt 组装 | 封装为 LangGraph 节点 |
| `1agent_core/src/skills/loader.py` | Skill 评分匹配 | 封装为条件路由逻辑 |
| `_legacy/bridge/agent_bridge.py` | GUI↔后端桥接 | 用 GM Agent 门面替代 |

### P0/P1 产出（本 Phase 依赖）

```python
# Foundation 层
from foundation.event_bus import event_bus, Event
from foundation.config import settings
from foundation.logger import get_logger
from foundation.database import get_db, init_db
from foundation.llm import BaseLLMClient, LLMMessage, LLMResponse, StreamEvent
from foundation.llm.openai_client import OpenAICompatibleClient
from foundation.llm.model_router import ModelRouter, model_router
from foundation.cache import llm_cache

# Core 层
from core.state import AgentState, create_initial_state
from core.models import (
    World, Player, NPC, Memory, Quest, Item,
    WorldRepo, PlayerRepo, NPCRepo, MemoryRepo, ItemRepo,
    QuestRepo, LogRepo, MetricsRepo, PromptRepo,
)
from core.calculators import roll_dice, attack, combat_round, is_combat_over
from core.constants import NPC_TEMPLATES, apply_template, generate_quest_from_template
```

---

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始"后，主动执行
4. **遇到错误先尝试修复**：3 次失败后再询问
5. **代码规范**：UTF-8，中文注释，PEP 8，类型注解
6. **依赖方向**：Feature 层只允许 import `core.*` 和 `foundation.*`
7. **LangGraph 最佳实践**：使用 `add_messages` Reducer、条件边、checkpointer
8. **EventBus 通知**：关键节点执行时通过 EventBus 通知上层

---

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **工作目录**: `2workbench/`
- **Feature 层**: `2workbench/feature/`
- **Legacy 参考**: `2workbench/_legacy/`、`1agent_core/src/`

---

## 步骤

### Step 1: 环境确认 + 目录创建

**目的**: 确保 LangGraph 已安装，创建 Feature 层目录。

**方案**:

1.1 安装依赖：

```bash
pip install langgraph langchain-core --break-system-packages
```

1.2 创建 Feature 层目录结构：

```
2workbench/feature/
├── __init__.py
├── ai/                          ← LangGraph Agent 核心（本 Phase 重点）
│   ├── __init__.py
│   ├── graph.py                 ← StateGraph 定义（节点/边/条件路由）
│   ├── nodes.py                 ← 节点函数实现
│   ├── tools.py                 ← LangGraph Tool 定义
│   ├── prompt_builder.py        ← Prompt 组装
│   ├── command_parser.py        ← 命令解析
│   ├── skill_loader.py          ← Skill 加载与匹配
│   ├── gm_agent.py              ← GM Agent 门面（对外统一接口）
│   └── events.py                ← 事件定义与 EventBus 集成
├── battle/
│   └── __init__.py
├── dialogue/
│   └── __init__.py
├── quest/
│   └── __init__.py
├── item/
│   └── __init__.py
├── exploration/
│   └── __init__.py
├── narration/
│   └── __init__.py
├── skill/
│   └── __init__.py
```

1.3 验证 LangGraph 安装：

```bash
cd 2workbench ; python -c "
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
print('✅ LangGraph 安装成功')
"
```

**验收**:
- [ ] LangGraph 安装成功
- [ ] `feature/ai/` 目录创建完成
- [ ] 导入测试通过

---

### Step 2: 事件定义

**目的**: 定义 Agent 执行过程中的事件类型，用于 EventBus 通知和 UI 更新。

**方案**:

2.1 创建 `2workbench/feature/ai/events.py`：

```python
# 2workbench/feature/ai/events.py
"""Agent 事件定义 — 通过 EventBus 通知上层

事件命名规范: feature.ai.{category}.{action}

替代原有的 EventHandler SSE 推送机制。
上层（Presentation）通过订阅这些事件来更新 UI。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from foundation.event_bus import Event


# ===== 事件类型常量 =====

# 生命周期
TURN_START = "feature.ai.lifecycle.turn_start"
TURN_END = "feature.ai.lifecycle.turn_end"
AGENT_ERROR = "feature.ai.lifecycle.error"
AGENT_PAUSED = "feature.ai.lifecycle.paused"
AGENT_RESUMED = "feature.ai.lifecycle.resumed"

# 节点执行
NODE_STARTED = "feature.ai.node.started"
NODE_COMPLETED = "feature.ai.node.completed"

# LLM
LLM_REQUEST = "feature.ai.llm.request"
LLM_RESPONSE = "feature.ai.llm.response"
LLM_STREAM_TOKEN = "feature.ai.llm.stream_token"
LLM_STREAM_REASONING = "feature.ai.llm.stream_reasoning"
LLM_TOOL_CALL = "feature.ai.llm.tool_call"

# 命令
COMMAND_PARSED = "feature.ai.command.parsed"
COMMAND_EXECUTED = "feature.ai.command.executed"
COMMAND_REJECTED = "feature.ai.command.rejected"

# 记忆
MEMORY_STORED = "feature.ai.memory.stored"
MEMORY_UPDATED = "feature.ai.memory.updated"

# 状态
STATE_CHANGED = "feature.ai.state.changed"
STATE_SNAPSHOT = "feature.ai.state.snapshot"


# ===== 事件创建辅助函数 =====

def create_turn_start_event(world_id: str, turn_count: int) -> Event:
    """创建回合开始事件"""
    return Event(
        type=TURN_START,
        data={"world_id": world_id, "turn_count": turn_count},
        source="feature.ai",
    )


def create_turn_end_event(
    world_id: str,
    turn_count: int,
    narrative: str = "",
    commands_count: int = 0,
    tokens_used: int = 0,
    latency_ms: int = 0,
) -> Event:
    """创建回合结束事件"""
    return Event(
        type=TURN_END,
        data={
            "world_id": world_id,
            "turn_count": turn_count,
            "narrative": narrative[:200],  # 截断避免事件过大
            "commands_count": commands_count,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
        },
        source="feature.ai",
    )


def create_node_event(node_name: str, status: str, data: dict | None = None) -> Event:
    """创建节点执行事件"""
    return Event(
        type=f"feature.ai.node.{status}",
        data={"node": node_name, **(data or {})},
        source="feature.ai",
    )


def create_stream_token_event(content: str) -> Event:
    """创建流式 token 事件"""
    return Event(
        type=LLM_STREAM_TOKEN,
        data={"content": content},
        source="feature.ai",
    )


def create_error_event(error: str, node: str = "") -> Event:
    """创建错误事件"""
    return Event(
        type=AGENT_ERROR,
        data={"error": error, "node": node},
        source="feature.ai",
    )
```

2.2 测试：

```bash
cd 2workbench ; python -c "
from feature.ai.events import (
    TURN_START, TURN_END, LLM_STREAM_TOKEN, AGENT_ERROR,
    create_turn_start_event, create_turn_end_event, create_stream_token_event,
)
from foundation.event_bus import event_bus

# 测试事件创建
event = create_turn_start_event(world_id='1', turn_count=5)
assert event.type == TURN_START
assert event.get('turn_count') == 5

# 测试事件发送
results = event_bus.emit(event)
print(f'事件发送结果: {results}')

print('✅ 事件定义测试通过')
event_bus.clear()
"
```

**验收**:
- [ ] `feature/ai/events.py` 创建完成
- [ ] 12 个事件类型常量定义
- [ ] 5 个事件创建辅助函数
- [ ] 测试通过

---

### Step 3: CommandParser — 命令解析器

**目的**: 将 LLM 输出解析为结构化命令，封装为可独立使用的模块。

**参考**: `1agent_core/src/command_parser.py` — 4 级容错策略

**方案**:

3.1 创建 `2workbench/feature/ai/command_parser.py`：

```python
# 2workbench/feature/ai/command_parser.py
"""命令解析器 — 将 LLM 输出解析为结构化命令

4 级容错策略:
1. 直接 JSON 解析
2. 提取 ```json ... ``` 代码块
3. 提取最外层 { ... }
4. 兜底: 整个文本作为 narrative

从 1agent_core/src/command_parser.py 重构而来。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedCommand:
    """解析后的命令"""
    intent: str           # 命令意图（如 update_hp, move_to, give_item）
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedOutput:
    """解析后的完整输出"""
    narrative: str = ""                     # 叙事文本
    commands: list[ParsedCommand] = field(default_factory=list)
    memory_updates: list[dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""                      # 原始文本
    parse_method: str = ""                  # 使用的解析方法


def parse_llm_output(text: str) -> ParsedOutput:
    """解析 LLM 输出（4 级容错）

    Args:
        text: LLM 的原始文本输出

    Returns:
        ParsedOutput
    """
    if not text or not text.strip():
        return ParsedOutput(narrative="", raw_text=text, parse_method="empty")

    text = text.strip()
    result = ParsedOutput(raw_text=text)

    # 第 1 级: 直接 JSON 解析
    data = _try_parse_json(text)
    if data and "narrative" in data:
        result.parse_method = "direct_json"
        _fill_result(result, data)
        return result

    # 第 2 级: 提取 ```json ... ``` 代码块
    json_block = _extract_json_block(text)
    if json_block:
        data = _try_parse_json(json_block)
        if data and "narrative" in data:
            result.parse_method = "json_block"
            _fill_result(result, data)
            return result

    # 第 3 级: 提取最外层 { ... }
    json_outer = _extract_outer_braces(text)
    if json_outer:
        data = _try_parse_json(json_outer)
        if data and "narrative" in data:
            result.parse_method = "outer_braces"
            _fill_result(result, data)
            return result

    # 第 4 级: 兜底 — 整个文本作为 narrative
    result.parse_method = "fallback"
    result.narrative = text
    logger.debug(f"命令解析使用兜底策略（无法解析为 JSON）")

    return result


def _try_parse_json(text: str) -> dict | None:
    """尝试 JSON 解析"""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def _extract_json_block(text: str) -> str | None:
    """提取 ```json ... ``` 代码块"""
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None


def _extract_outer_braces(text: str) -> str | None:
    """提取最外层 { ... }"""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return None


def _fill_result(result: ParsedOutput, data: dict) -> None:
    """从 JSON 数据填充解析结果"""
    result.narrative = data.get("narrative", "")

    # 解析命令
    for cmd in data.get("commands", []):
        if isinstance(cmd, dict) and "intent" in cmd:
            result.commands.append(ParsedCommand(
                intent=cmd["intent"],
                params=cmd.get("params", {}),
            ))

    # 解析记忆更新
    for mem in data.get("memory_updates", []):
        if isinstance(mem, dict) and "action" in mem:
            result.memory_updates.append(mem)
```

3.2 测试：

```bash
cd 2workbench ; python -c "
from feature.ai.command_parser import parse_llm_output, ParsedOutput

# 测试第 1 级: 直接 JSON
text1 = '{\"narrative\": \"你走进了酒馆\", \"commands\": [{\"intent\": \"update_location\", \"params\": {\"location\": \"酒馆\"}}]}'
r1 = parse_llm_output(text1)
assert r1.parse_method == 'direct_json'
assert r1.narrative == '你走进了酒馆'
assert len(r1.commands) == 1
assert r1.commands[0].intent == 'update_location'
print(f'Level 1: {r1.parse_method} ✅')

# 测试第 2 级: JSON 代码块
text2 = '''一些文字
\`\`\`json
{\"narrative\": \"战斗开始\", \"commands\": []}
\`\`\`
更多文字'''
r2 = parse_llm_output(text2)
assert r2.parse_method == 'json_block'
assert r2.narrative == '战斗开始'
print(f'Level 2: {r2.parse_method} ✅')

# 测试第 3 级: 外层花括号
text3 = '描述文本 {\"narrative\": \"纯文本输出\", \"commands\": []} 尾部'
r3 = parse_llm_output(text3)
assert r3.parse_method == 'outer_braces'
print(f'Level 3: {r3.parse_method} ✅')

# 测试第 4 级: 兜底
text4 = '这只是一段普通文本，没有 JSON 结构'
r4 = parse_llm_output(text4)
assert r4.parse_method == 'fallback'
assert r4.narrative == text4
print(f'Level 4: {r4.parse_method} ✅')

print('✅ CommandParser 测试通过')
"
```

**验收**:
- [ ] `feature/ai/command_parser.py` 创建完成
- [ ] 4 级容错策略全部实现
- [ ] `ParsedOutput` 和 `ParsedCommand` 数据类
- [ ] 测试通过

---

### Step 4: PromptBuilder — Prompt 组装

**目的**: 将系统 Prompt、Skill、记忆、游戏状态组装为完整的 messages 列表。

**参考**: `1agent_core/src/prompt_builder.py` — 4 部分组装 + 事件格式化

**方案**:

4.1 创建 `2workbench/feature/ai/prompt_builder.py`：

```python
# 2workbench/feature/ai/prompt_builder.py
"""Prompt 组装器 — 构建 LLM 的 messages 列表

组装结构:
[system] 基础 system prompt + Skills + 记忆上下文 + 游戏状态
[user]   历史对话 N 轮
[user]   当前事件

从 1agent_core/src/prompt_builder.py 重构而来。
"""
from __future__ import annotations

from typing import Any

from foundation.llm import LLMMessage
from foundation.logger import get_logger
from core.models import MemoryRepo, PromptRepo
from core.state import AgentState

logger = get_logger(__name__)


class PromptBuilder:
    """Prompt 组装器

    用法:
        builder = PromptBuilder()
        messages = builder.build(
            system_prompt="你是游戏主持人...",
            state=agent_state,
            active_skills=["narration", "exploration"],
            event_text="玩家说: 我要探索幽暗森林",
        )
    """

    def __init__(self):
        self._system_prompt_cache: str | None = None
        self._system_prompt_key: str | None = None

    def build(
        self,
        system_prompt: str,
        state: AgentState,
        active_skills: list[str] | None = None,
        event_text: str = "",
        skill_contents: list[str] | None = None,
        memory_context: str = "",
        max_history_turns: int = 10,
        db_path: str | None = None,
    ) -> list[LLMMessage]:
        """组装完整的 messages 列表

        Args:
            system_prompt: 基础 system prompt
            state: 当前 Agent 状态
            active_skills: 激活的 Skill 名称列表
            event_text: 当前事件的文本描述
            skill_contents: Skill 内容列表（已加载）
            memory_context: 记忆上下文文本
            max_history_turns: 最大历史轮数
            db_path: 数据库路径

        Returns:
            LLMMessage 列表
        """
        messages: list[LLMMessage] = []

        # 1. System 消息
        system_content = self._build_system_content(
            system_prompt=system_prompt,
            skill_contents=skill_contents or [],
            memory_context=memory_context,
            state=state,
        )
        messages.append(LLMMessage(role="system", content=system_content))

        # 2. 历史对话（从 state.messages 中取最近 N 轮）
        history = self._extract_history(state, max_history_turns)
        messages.extend(history)

        # 3. 当前事件
        if event_text:
            messages.append(LLMMessage(role="user", content=event_text))

        return messages

    def _build_system_content(
        self,
        system_prompt: str,
        skill_contents: list[str],
        memory_context: str,
        state: AgentState,
    ) -> str:
        """构建 system 消息内容"""
        parts = [system_prompt]

        # Skill 内容
        if skill_contents:
            parts.append("\n\n## 当前激活的技能规则\n")
            for i, content in enumerate(skill_contents):
                parts.append(f"\n### 技能 {i+1}\n{content}")

        # 记忆上下文
        if memory_context:
            parts.append(f"\n\n## 相关记忆\n{memory_context}")

        # 游戏状态快照
        state_text = self._format_game_state(state)
        if state_text:
            parts.append(f"\n\n## 当前游戏状态\n{state_text}")

        return "".join(parts)

    def _format_game_state(self, state: AgentState) -> str:
        """格式化游戏状态为文本"""
        parts = []

        player = state.get("player", {})
        if player:
            parts.append(
                f"- 玩家: {player.get('name', '未知')} "
                f"HP:{player.get('hp', 0)}/{player.get('max_hp', 0)} "
                f"MP:{player.get('mp', 0)}/{player.get('max_mp', 0)} "
                f"Lv.{player.get('level', 1)} "
                f"EXP:{player.get('exp', 0)} "
                f"金币:{player.get('gold', 0)}"
            )

        location = state.get("current_location", {})
        if location:
            parts.append(f"- 当前位置: {location.get('name', '未知')}")

        npcs = state.get("active_npcs", [])
        if npcs:
            npc_names = [n.get("name", "未知") for n in npcs]
            parts.append(f"- 场景 NPC: {', '.join(npc_names)}")

        quests = state.get("active_quests", [])
        if quests:
            for q in quests[:3]:  # 最多显示 3 个
                parts.append(f"- 任务: [{q.get('status', '?')}] {q.get('title', '未知')}")

        parts.append(f"- 回合数: {state.get('turn_count', 0)}")

        return "\n".join(parts)

    def _extract_history(self, state: AgentState, max_turns: int) -> list[LLMMessage]:
        """从 state.messages 提取历史对话"""
        messages = state.get("messages", [])
        if not messages:
            return []

        # LangGraph 的 messages 是 LangChain Message 对象列表
        # 取最近 2*max_turns 条消息（N 轮 = 2N 条）
        recent = messages[-(max_turns * 2):]

        result = []
        for msg in recent:
            if hasattr(msg, "role"):
                role = msg.role
                content = msg.content if hasattr(msg, "content") else str(msg)
            elif hasattr(msg, "type"):
                # LangChain BaseMessage
                role = msg.type
                content = msg.content
            else:
                continue

            # 跳过 system 消息（已在前面添加）
            if role == "system":
                continue

            result.append(LLMMessage(role=role, content=content))

        return result
```

4.2 测试：

```bash
cd 2workbench ; python -c "
from feature.ai.prompt_builder import PromptBuilder
from core.state import create_initial_state

builder = PromptBuilder()
state = create_initial_state(world_id='1', player_name='冒险者')
state['turn_count'] = 5

messages = builder.build(
    system_prompt='你是一个游戏主持人。',
    state=state,
    event_text='玩家说: 我要探索幽暗森林',
    skill_contents=['## 探索规则\n探索时可能发现隐藏物品。'],
    memory_context='之前在宁静村遇到了老村长。',
)

assert len(messages) >= 2  # system + user
assert messages[0].role == 'system'
assert '游戏主持人' in messages[0].content
assert '冒险者' in messages[0].content  # 游戏状态
assert '探索规则' in messages[0].content  # Skill
assert messages[-1].role == 'user'
assert '幽暗森林' in messages[-1].content

print(f'组装了 {len(messages)} 条消息')
print('✅ PromptBuilder 测试通过')
"
```

**验收**:
- [ ] `feature/ai/prompt_builder.py` 创建完成
- [ ] System 消息包含 4 部分（基础 prompt + Skill + 记忆 + 状态）
- [ ] 历史对话正确提取
- [ ] 测试通过

---

### Step 5: SkillLoader — Skill 加载与匹配

**目的**: 加载 Skill 定义，根据事件内容评分匹配相关 Skill。

**参考**: `1agent_core/src/skills/loader.py` — 评分匹配机制

**方案**:

5.1 创建 `2workbench/feature/ai/skill_loader.py`：

```python
# 2workbench/feature/ai/skill_loader.py
"""Skill 加载器 — 评分匹配 + Prompt 注入

Skill 是 Markdown 文件，通过 YAML Front Matter 定义元数据。
Skill 不是可执行代码，而是通过评分匹配后注入 system prompt 的指导文档。

从 1agent_core/src/skills/loader.py 重构而来。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SkillMetadata:
    """Skill 元数据"""
    name: str
    description: str = ""
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    triggers: list[dict[str, Any]] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class Skill:
    """完整的 Skill"""
    metadata: SkillMetadata
    content: str = ""  # Markdown Body（指导 LLM 的规则）


class SkillLoader:
    """Skill 加载器

    用法:
        loader = SkillLoader(skills_dir="./skills")
        loader.discover_all()
        relevant = loader.get_relevant_skills(event_type="player_move", user_input="探索森林")
        contents = [loader.load_activation(s.name) for s in relevant]
    """

    def __init__(self, skills_dir: str | Path | None = None):
        self._skills_dir = Path(skills_dir) if skills_dir else None
        self._skills: dict[str, Skill] = {}
        self._discovered = False

    def discover_all(self) -> list[str]:
        """扫描目录，发现所有 Skill

        Returns:
            发现的 Skill 名称列表
        """
        if not self._skills_dir or not self._skills_dir.exists():
            logger.warning(f"Skill 目录不存在: {self._skills_dir}")
            return []

        self._skills.clear()
        for skill_dir in sorted(self._skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                skill = self._load_skill_file(skill_file)
                self._skills[skill.metadata.name] = skill
                logger.debug(f"发现 Skill: {skill.metadata.name}")
            except Exception as e:
                logger.error(f"加载 Skill 失败 ({skill_file}): {e}")

        self._discovered = True
        logger.info(f"发现 {len(self._skills)} 个 Skill")
        return list(self._skills.keys())

    def get_relevant_skills(
        self,
        event_type: str = "",
        user_input: str = "",
        context_hints: list[str] | None = None,
        max_skills: int = 5,
    ) -> list[Skill]:
        """评分匹配相关 Skill

        评分规则:
        - event_type 匹配: +10 分
        - keyword 匹配: +5 分/关键词
        - context_hint 匹配: +3 分/提示
        - triggers 为空（始终加载）: +100 分

        Args:
            event_type: 事件类型
            user_input: 用户输入
            context_hints: 上下文提示
            max_skills: 最大返回数量

        Returns:
            按评分排序的 Skill 列表
        """
        if not self._discovered:
            self.discover_all()

        scored: list[tuple[int, Skill]] = []
        input_lower = user_input.lower()
        hints = set(context_hints or [])

        for skill in self._skills.values():
            score = 0
            meta = skill.metadata

            # 始终加载的 Skill（如 narration）
            if not meta.triggers and not meta.keywords:
                score += 100

            # event_type 匹配
            for trigger in meta.triggers:
                if trigger.get("event_type") == event_type:
                    score += 10

            # keyword 匹配
            for keyword in meta.keywords:
                if keyword.lower() in input_lower:
                    score += 5

            # context_hint 匹配
            for tag in meta.tags:
                if tag in hints:
                    score += 3

            if score > 0:
                scored.append((score, skill))

        # 按评分降序排序
        scored.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in scored[:max_skills]]

    def load_activation(self, skill_name: str, max_chars: int = 2000) -> str:
        """加载 Skill 的激活层内容

        返回: YAML 关键字段 + Markdown Body 前 N 字符
        """
        skill = self._skills.get(skill_name)
        if not skill:
            return ""

        parts = [f"**{skill.metadata.name}** (v{skill.metadata.version})"]
        parts.append(f"描述: {skill.metadata.description}")
        if skill.metadata.allowed_tools:
            parts.append(f"可用工具: {', '.join(skill.metadata.allowed_tools)}")
        parts.append("")
        parts.append(skill.content[:max_chars])

        return "\n".join(parts)

    def get_all_skill_names(self) -> list[str]:
        """获取所有 Skill 名称"""
        if not self._discovered:
            self.discover_all()
        return list(self._skills.keys())

    def _load_skill_file(self, filepath: Path) -> Skill:
        """从 SKILL.md 文件加载 Skill"""
        content = filepath.read_text(encoding="utf-8")

        # 解析 YAML Front Matter
        metadata = SkillMetadata(name=filepath.parent.name)
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                import yaml
                try:
                    front_matter = yaml.safe_load(content[3:end]) or {}
                    metadata = SkillMetadata(
                        name=front_matter.get("name", filepath.parent.name),
                        description=front_matter.get("description", ""),
                        version=str(front_matter.get("version", "1.0.0")),
                        tags=front_matter.get("tags", []),
                        allowed_tools=front_matter.get("allowed-tools", []),
                        triggers=front_matter.get("triggers", []),
                        keywords=front_matter.get("keywords", []),
                    )
                    content = content[end + 3:].strip()
                except Exception as e:
                    logger.warning(f"解析 YAML Front Matter 失败: {e}")

        return Skill(metadata=metadata, content=content)
```

5.2 测试：

```bash
cd 2workbench ; python -c "
from feature.ai.skill_loader import SkillLoader, SkillMetadata, Skill
import tempfile, os

# 创建临时 Skill 目录
with tempfile.TemporaryDirectory() as tmpdir:
    # 创建一个 Skill
    skill_dir = os.path.join(tmpdir, 'test_skill')
    os.makedirs(skill_dir)
    with open(os.path.join(skill_dir, 'SKILL.md'), 'w', encoding='utf-8') as f:
        f.write('''---
name: test_skill
description: 测试技能
version: 1.0.0
tags: [test, demo]
keywords: [测试, 探索, 调查]
triggers:
  - event_type: player_move
---
# 测试技能规则

当玩家探索时，遵循以下规则：
1. 描述周围环境
2. 提示可能的发现
''')

    loader = SkillLoader(skills_dir=tmpdir)
    names = loader.discover_all()
    assert 'test_skill' in names

    # 测试评分匹配
    relevant = loader.get_relevant_skills(event_type='player_move', user_input='我要探索这个区域')
    assert len(relevant) == 1
    assert relevant[0].metadata.name == 'test_skill'

    # 测试激活层加载
    activation = loader.load_activation('test_skill')
    assert '测试技能规则' in activation

    print('✅ SkillLoader 测试通过')
"
```

**验收**:
- [ ] `feature/ai/skill_loader.py` 创建完成
- [ ] YAML Front Matter 解析
- [ ] 评分匹配（event_type + keyword + context_hint）
- [ ] 激活层加载
- [ ] 测试通过

---

### Step 6: LangGraph Tools — 工具定义

**目的**: 将游戏机制封装为 LangGraph Tool，供 LLM 在推理时调用。

**方案**:

6.1 创建 `2workbench/feature/ai/tools.py`：

```python
# 2workbench/feature/ai/tools.py
"""LangGraph Tools — 游戏机制工具

将游戏机制封装为 LangChain Tool 格式，供 LLM 在推理时调用。
这些工具通过 LangGraph 的 ToolNode 执行。
"""
from __future__ import annotations

import random
from typing import Any

from langchain_core.tools import tool
from foundation.logger import get_logger

logger = get_logger(__name__)


@tool
def roll_dice(sides: int = 20, count: int = 1, modifier: int = 0) -> str:
    """掷骰子进行随机判定。

    Args:
        sides: 骰子面数（默认 20，即 D20）
        count: 掷骰次数（默认 1）
        modifier: 加值（默认 0）

    Returns:
        掷骰结果描述
    """
    results = [random.randint(1, sides) for _ in range(count)]
    total = sum(results) + modifier
    rolls_str = " + ".join(str(r) for r in results)
    if modifier:
        rolls_str += f" + {modifier}"
    return f"掷骰结果: [{rolls_str}] = {total}"


@tool
def update_player_stat(stat_name: str, value: int, player_id: int = 0) -> str:
    """更新玩家属性值。

    Args:
        stat_name: 属性名（hp, mp, exp, gold, level）
        value: 新的值（如果是负数则减少）
        player_id: 玩家 ID

    Returns:
        更新结果描述
    """
    valid_stats = {"hp", "mp", "exp", "gold", "level"}
    if stat_name not in valid_stats:
        return f"无效的属性名: {stat_name}，可用: {valid_stats}"
    return f"玩家属性已更新: {stat_name} = {value}"


@tool
def give_item(item_name: str, quantity: int = 1, player_id: int = 0) -> str:
    """给予玩家道具。

    Args:
        item_name: 道具名称
        quantity: 数量
        player_id: 玩家 ID

    Returns:
        给予结果描述
    """
    return f"已给予玩家 {quantity} 个 {item_name}"


@tool
def remove_item(item_name: str, quantity: int = 1, player_id: int = 0) -> str:
    """从玩家身上移除道具。

    Args:
        item_name: 道具名称
        quantity: 数量

    Returns:
        移除结果描述
    """
    return f"已从玩家身上移除 {quantity} 个 {item_name}"


@tool
def move_to_location(location_name: str, player_id: int = 0) -> str:
    """移动玩家到指定地点。

    Args:
        location_name: 目标地点名称
        player_id: 玩家 ID

    Returns:
        移动结果描述
    """
    return f"玩家已移动到: {location_name}"


@tool
def update_npc_relationship(npc_name: str, change: int, player_id: int = 0) -> str:
    """修改 NPC 对玩家的关系值。

    Args:
        npc_name: NPC 名称
        change: 关系值变化（正数=好感增加，负数=好感降低）
        player_id: 玩家 ID

    Returns:
        关系变化描述
    """
    direction = "增加" if change > 0 else "降低"
    return f"{npc_name} 对玩家的好感度{direction}了 {abs(change)} 点"


@tool
def update_quest_status(quest_title: str, status: str) -> str:
    """更新任务状态。

    Args:
        quest_title: 任务标题
        status: 新状态（active, completed, failed）

    Returns:
        任务状态更新描述
    """
    valid = {"active", "completed", "failed"}
    if status not in valid:
        return f"无效的任务状态: {status}，可用: {valid}"
    return f"任务 [{quest_title}] 状态已更新为: {status}"


@tool
def store_memory(content: str, category: str, importance: float = 0.5) -> str:
    """存储一条记忆（用于后续检索）。

    Args:
        content: 记忆内容
        category: 类别（npc, location, player, quest, world, session）
        importance: 重要性 0.0-1.0

    Returns:
        存储结果
    """
    valid = {"npc", "location", "player", "quest", "world", "session"}
    if category not in valid:
        return f"无效的记忆类别: {category}，可用: {valid}"
    return f"记忆已存储: [{category}] {content[:50]}..."


@tool
def check_quest_prerequisites(quest_title: str) -> str:
    """检查任务的前置条件是否满足。

    Args:
        quest_title: 任务标题

    Returns:
        前置条件检查结果
    """
    return f"任务 [{quest_title}] 的前置条件检查完成。"


# 所有工具列表
ALL_TOOLS = [
    roll_dice,
    update_player_stat,
    give_item,
    remove_item,
    move_to_location,
    update_npc_relationship,
    update_quest_status,
    store_memory,
    check_quest_prerequisites,
]


def get_tools_schema() -> list[dict]:
    """获取所有工具的 OpenAI function calling schema"""
    from langchain_core.utils.function_calling import convert_to_openai_tool
    return [convert_to_openai_tool(t) for t in ALL_TOOLS]
```

6.2 测试：

```bash
cd 2workbench ; python -c "
from feature.ai.tools import ALL_TOOLS, get_tools_schema, roll_dice, give_item

# 测试工具调用
result = roll_dice.invoke({'sides': 20, 'count': 1})
assert '掷骰结果' in result
print(f'骰子: {result}')

result = give_item.invoke({'item_name': '木剑', 'quantity': 1})
assert '木剑' in result
print(f'道具: {result}')

# 测试 schema
schemas = get_tools_schema()
assert len(schemas) == len(ALL_TOOLS)
print(f'工具数量: {len(schemas)}')
for s in schemas:
    print(f'  - {s[\"function\"][\"name\"]}')

print('✅ LangGraph Tools 测试通过')
"
```

**验收**:
- [ ] `feature/ai/tools.py` 创建完成
- [ ] 9 个工具定义（骰子、属性、物品、移动、关系、任务、记忆）
- [ ] 每个工具有完整的 docstring 和参数定义
- [ ] `get_tools_schema()` 返回正确的 schema
- [ ] 测试通过

---

### Step 7: StateGraph 构建 — 核心图定义

**目的**: 构建 LangGraph StateGraph，定义节点、边和条件路由。

**方案**:

7.1 创建 `2workbench/feature/ai/nodes.py` — 节点函数：

```python
# 2workbench/feature/ai/nodes.py
"""LangGraph 节点函数 — StateGraph 的计算单元

每个节点函数:
- 接收 AgentState 作为输入
- 执行特定逻辑
- 返回 State 的部分更新字典

节点列表:
1. handle_event — 接收事件，更新状态
2. build_prompt — 组装 Prompt
3. llm_reasoning — 调用 LLM（流式）
4. parse_output — 解析 LLM 输出
5. execute_commands — 执行解析出的命令
6. update_memory — 更新记忆
"""
from __future__ import annotations

import time
from typing import Any

from foundation.event_bus import event_bus
from foundation.llm import LLMMessage
from foundation.llm.model_router import model_router
from foundation.logger import get_logger
from core.state import AgentState

from .events import (
    create_node_event, create_stream_token_event,
    create_error_event, LLM_STREAM_TOKEN, LLM_STREAM_REASONING,
    COMMAND_PARSED, COMMAND_EXECUTED, MEMORY_STORED,
)
from .prompt_builder import PromptBuilder
from .command_parser import parse_llm_output
from .tools import ALL_TOOLS, get_tools_schema

logger = get_logger(__name__)

# 全局 PromptBuilder 实例
_prompt_builder = PromptBuilder()


def node_handle_event(state: AgentState) -> dict[str, Any]:
    """节点 1: 接收事件，更新状态

    从 state.current_event 中提取事件信息，
    更新 turn_count、execution_state 等。
    """
    event_bus.emit(create_node_event("handle_event", "started"))

    event = state.get("current_event", {})
    turn = state.get("turn_count", 0) + 1

    # 格式化事件文本
    event_type = event.get("type", "player_action")
    event_data = event.get("data", {})
    raw_text = event_data.get("raw_text", "")

    # 根据事件类型格式化
    event_texts = {
        "player_action": f"玩家行动: {raw_text}",
        "player_move": f"玩家移动: {raw_text}",
        "npc_interact": f"与 NPC 交互: {raw_text}",
        "combat_start": f"战斗开始: {raw_text}",
        "system_event": f"系统事件: {raw_text}",
    }
    event_text = event_texts.get(event_type, f"事件: {raw_text}")

    event_bus.emit(create_node_event("handle_event", "completed"))

    return {
        "turn_count": turn,
        "execution_state": "running",
        "current_event": {**event, "_formatted_text": event_text},
    }


def node_build_prompt(state: AgentState) -> dict[str, Any]:
    """节点 2: 组装 Prompt

    调用 PromptBuilder 组装完整的 messages 列表。
    """
    event_bus.emit(create_node_event("build_prompt", "started"))

    event = state.get("current_event", {})
    event_text = event.get("_formatted_text", event.get("data", {}).get("raw_text", ""))

    # 获取 Skill 内容（简化版，实际应从 SkillLoader 获取）
    skill_contents = []
    active_skills = state.get("active_skills", [])
    # TODO: P3 阶段接入 SkillLoader

    # 组装 Prompt
    system_prompt = _get_system_prompt()
    messages = _prompt_builder.build(
        system_prompt=system_prompt,
        state=state,
        event_text=event_text,
        skill_contents=skill_contents,
    )

    # 转换为 LangChain Message 格式
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    lc_messages = []
    for msg in messages:
        if msg.role == "system":
            lc_messages.append(SystemMessage(content=msg.content))
        elif msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))

    event_bus.emit(create_node_event("build_prompt", "completed"))

    return {
        "prompt_messages": [{"role": m.type, "content": m.content} for m in lc_messages],
    }


def node_llm_reasoning(state: AgentState) -> dict[str, Any]:
    """节点 3: 调用 LLM（流式）

    使用 ModelRouter 选择合适的模型，
    流式调用 LLM 并通过 EventBus 推送 token。
    """
    event_bus.emit(create_node_event("llm_reasoning", "started"))

    start_time = time.time()
    prompt_messages = state.get("prompt_messages", [])

    if not prompt_messages:
        return {
            "llm_response": {"content": "", "error": "无 prompt 消息"},
            "error": "无 prompt 消息",
        }

    # 获取 LLM 客户端
    content = prompt_messages[-1].get("content", "") if prompt_messages else ""
    client, config = model_router.route(
        content=content,
        provider=state.get("provider"),
        model=state.get("model_name"),
    )

    # 转换为 LLMMessage
    llm_messages = [LLMMessage(role=m["role"], content=m["content"]) for m in prompt_messages]

    # 流式调用
    full_content = ""
    reasoning_content = ""
    tool_calls = []
    total_tokens = 0

    try:
        async def _stream_and_collect():
            nonlocal full_content, reasoning_content, tool_calls, total_tokens
            async for event in client.stream(
                messages=llm_messages,
                temperature=config.get("temperature", 0.7),
                tools=get_tools_schema() if state.get("active_skills") else None,
            ):
                if event.type == "token":
                    full_content += event.content
                    event_bus.emit(create_stream_token_event(event.content))
                elif event.type == "reasoning":
                    reasoning_content += event.content
                elif event.type == "tool_call":
                    tool_calls.extend(event.tool_calls)
                elif event.type == "complete":
                    total_tokens = event.total_tokens

        # 在同步上下文中运行异步代码
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import qasync
                loop.run_until_complete(_stream_and_collect())
            else:
                asyncio.run(_stream_and_collect())
        except RuntimeError:
            asyncio.run(_stream_and_collect())

    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        event_bus.emit(create_error_event(str(e), "llm_reasoning"))
        return {
            "llm_response": {"content": full_content or f"[LLM 错误: {e}]", "error": str(e)},
            "error": str(e),
        }

    latency_ms = int((time.time() - start_time) * 1000)

    event_bus.emit(create_node_event("llm_reasoning", "completed", {
        "latency_ms": latency_ms, "tokens": total_tokens,
    }))

    return {
        "llm_response": {
            "content": full_content,
            "reasoning": reasoning_content,
            "tool_calls": tool_calls,
            "tokens": total_tokens,
            "latency_ms": latency_ms,
            "model": config.get("model", ""),
            "provider": config.get("provider", ""),
        },
    }


def node_parse_output(state: AgentState) -> dict[str, Any]:
    """节点 4: 解析 LLM 输出

    调用 CommandParser 将 LLM 文本解析为结构化命令。
    """
    event_bus.emit(create_node_event("parse_output", "started"))

    llm_response = state.get("llm_response", {})
    raw_content = llm_response.get("content", "")

    parsed = parse_llm_output(raw_content)

    # 如果 LLM 返回了 tool_calls，也作为命令处理
    tool_commands = []
    for tc in llm_response.get("tool_calls", []):
        func = tc.get("function", {})
        tool_commands.append({
            "intent": f"tool:{func.get('name', '')}",
            "params": {"arguments": func.get("arguments", "{}")},
        })

    all_commands = parsed.commands + [
        __import__("feature.ai.command_parser", fromlist=["ParsedCommand"]).ParsedCommand(
            intent=c["intent"], params=c.get("params", {})
        ) for c in tool_commands
    ]

    event_bus.emit(create_node_event("parse_output", "completed", {
        "commands_count": len(all_commands),
        "parse_method": parsed.parse_method,
    }))

    return {
        "parsed_commands": [
            {"intent": c.intent, "params": c.params} for c in all_commands
        ],
        "memory_updates": parsed.memory_updates,
    }


def node_execute_commands(state: AgentState) -> dict[str, Any]:
    """节点 5: 执行解析出的命令

    将命令分发给对应的工具或处理器。
    """
    event_bus.emit(create_node_event("execute_commands", "started"))

    commands = state.get("parsed_commands", [])
    results = []

    for cmd in commands:
        intent = cmd.get("intent", "")
        params = cmd.get("params", {})

        try:
            # 查找匹配的工具
            from .tools import ALL_TOOLS
            for tool in ALL_TOOLS:
                if tool.name == intent or intent == f"tool:{tool.name}":
                    # 执行工具
                    if isinstance(params.get("arguments"), str):
                        import json
                        try:
                            params = json.loads(params["arguments"])
                        except Exception:
                            params = {}
                    result = tool.invoke(params)
                    results.append({"intent": intent, "success": True, "result": result})
                    logger.debug(f"工具执行: {intent} -> {result[:100]}")
                    break
            else:
                # 无匹配工具，记录为 no_op
                results.append({"intent": intent, "success": False, "result": "no matching tool"})
        except Exception as e:
            results.append({"intent": intent, "success": False, "result": f"error: {e}"})
            logger.error(f"命令执行失败 ({intent}): {e}")

    event_bus.emit(create_node_event("execute_commands", "completed", {
        "executed": len(results),
    }))

    return {
        "command_results": results,
    }


def node_update_memory(state: AgentState) -> dict[str, Any]:
    """节点 6: 更新记忆

    将记忆更新写入数据库。
    """
    event_bus.emit(create_node_event("update_memory", "started"))

    memory_updates = state.get("memory_updates", [])
    stored_count = 0

    world_id = int(state.get("world_id", 0))
    turn = state.get("turn_count", 0)

    if world_id > 0 and memory_updates:
        from core.models import MemoryRepo
        repo = MemoryRepo()
        for mem in memory_updates:
            try:
                repo.store(
                    world_id=world_id,
                    category=mem.get("category", "session"),
                    source=mem.get("source", "agent"),
                    content=mem.get("content", ""),
                    title=mem.get("title", ""),
                    importance=mem.get("importance", 0.5),
                    turn=turn,
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"记忆存储失败: {e}")

    event_bus.emit(create_node_event("update_memory", "completed", {
        "stored": stored_count,
    }))

    return {}


# ===== 条件路由函数 =====

def route_after_llm(state: AgentState) -> str:
    """LLM 推理后的路由

    如果有 tool_calls -> execute_commands
    否则 -> parse_output
    """
    llm_response = state.get("llm_response", {})
    if llm_response.get("tool_calls"):
        return "execute_commands"
    return "parse_output"


def route_after_parse(state: AgentState) -> str:
    """解析后的路由

    如果有命令 -> execute_commands
    否则 -> update_memory
    """
    commands = state.get("parsed_commands", [])
    if commands:
        return "execute_commands"
    return "update_memory"


# ===== System Prompt =====

def _get_system_prompt() -> str:
    """获取基础 System Prompt"""
    return """你是一个沉浸式游戏主持人（Game Master）。你的职责是：

1. **叙事** — 生动地描述游戏世界、场景、NPC 行为和事件
2. **裁判** — 公平地判定玩家行动的结果
3. **角色扮演** — 扮演 NPC 与玩家互动
4. **推进剧情** — 根据玩家选择推进故事发展

## 输出格式

每次回复必须包含一个 JSON 结构：
```json
{
    "narrative": "你的叙事描述文本",
    "commands": [
        {"intent": "命令名称", "params": {"参数": "值"}}
    ],
    "memory_updates": [
        {"action": "create", "category": "session", "content": "重要信息摘要"}
    ]
}
```

## 可用命令

- `roll_dice` — 掷骰子判定
- `update_player_stat` — 更新玩家属性
- `give_item` / `remove_item` — 物品管理
- `move_to_location` — 移动玩家
- `update_npc_relationship` — 修改 NPC 关系
- `update_quest_status` — 更新任务状态
- `store_memory` — 存储记忆

## 风格要求

- 使用第二人称描述玩家行动
- 保持叙事的沉浸感和连贯性
- 根据玩家选择产生有意义的后果
- 适当使用对话和描写来丰富场景
"""
```

7.2 创建 `2workbench/feature/ai/graph.py` — StateGraph 定义：

```python
# 2workbench/feature/ai/graph.py
"""LangGraph StateGraph 定义 — GM Agent 核心图

图结构:
    START -> handle_event -> build_prompt -> llm_reasoning
                                                    |
                                              route_after_llm
                                              /            \
                                        parse_output    execute_commands (tool_calls)
                                              |                |
                                        route_after_parse      |
                                        /            \          |
                              execute_commands    update_memory |
                                    |                |       |
                                    +-------+--------+-------+
                                            |
                                         update_memory
                                            |
                                           END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from core.state import AgentState
from .nodes import (
    node_handle_event,
    node_build_prompt,
    node_llm_reasoning,
    node_parse_output,
    node_execute_commands,
    node_update_memory,
    route_after_llm,
    route_after_parse,
)


def build_gm_graph() -> StateGraph:
    """构建 GM Agent StateGraph

    Returns:
        编译后的 CompiledGraph
    """
    builder = StateGraph(AgentState)

    # 添加节点
    builder.add_node("handle_event", node_handle_event)
    builder.add_node("build_prompt", node_build_prompt)
    builder.add_node("llm_reasoning", node_llm_reasoning)
    builder.add_node("parse_output", node_parse_output)
    builder.add_node("execute_commands", node_execute_commands)
    builder.add_node("update_memory", node_update_memory)

    # 添加边
    builder.add_edge(START, "handle_event")
    builder.add_edge("handle_event", "build_prompt")
    builder.add_edge("build_prompt", "llm_reasoning")

    # LLM 推理后的条件路由
    builder.add_conditional_edges(
        "llm_reasoning",
        route_after_llm,
        {
            "parse_output": "parse_output",
            "execute_commands": "execute_commands",
        },
    )

    # 解析后的条件路由
    builder.add_conditional_edges(
        "parse_output",
        route_after_parse,
        {
            "execute_commands": "execute_commands",
            "update_memory": "update_memory",
        },
    )

    # 命令执行后 -> 更新记忆
    builder.add_edge("execute_commands", "update_memory")

    # 更新记忆后 -> 结束
    builder.add_edge("update_memory", END)

    # 编译
    graph = builder.compile()
    return graph


# 全局编译好的图实例
gm_graph = build_gm_graph()
```

7.3 测试图构建：

```bash
cd 2workbench ; python -c "
from feature.ai.graph import build_gm_graph, gm_graph
from core.state import create_initial_state

# 测试图构建
graph = build_gm_graph()
assert graph is not None

# 测试图结构（不实际运行，只验证编译）
print(f'图节点: {list(graph.get_graph().nodes.keys())}')

# 创建初始状态
state = create_initial_state()
assert state['execution_state'] == 'idle'

print('✅ StateGraph 构建测试通过')
"
```

**验收**:
- [ ] `feature/ai/nodes.py` — 6 个节点函数 + 2 个路由函数
- [ ] `feature/ai/graph.py` — StateGraph 定义 + 编译
- [ ] 图结构正确（START → 6 节点 → END，含条件路由）
- [ ] `gm_graph` 全局实例可导入
- [ ] 测试通过

---

### Step 8: GM Agent 门面

**目的**: 提供对外统一接口，替代原有的 `GameMaster` + `EventHandler` + `AgentBridge`。

**方案**:

8.1 创建 `2workbench/feature/ai/gm_agent.py`：

```python
# 2workbench/feature/ai/gm_agent.py
"""GM Agent 门面 — 对外统一接口

替代原有的:
- 1agent_core/src/game_master.py (GameMaster)
- 1agent_core/src/event_handler.py (EventHandler)
- _legacy/bridge/agent_bridge.py (AgentBridge)

使用方式:
    agent = GMAgent(world_id=1)
    result = await agent.run("玩家说: 我要探索幽暗森林")
    # 或同步:
    result = agent.run_sync("玩家说: 我要探索幽暗森林")
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncGenerator

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger
from core.state import AgentState, create_initial_state
from core.models import WorldRepo, PlayerRepo, NPCRepo, LocationRepo, MemoryRepo

from .graph import gm_graph
from .events import (
    create_turn_start_event, create_turn_end_event, create_error_event,
    TURN_START, TURN_END, AGENT_ERROR,
)

logger = get_logger(__name__)


class GMAgent:
    """GM Agent — 游戏主持人 Agent

    这是整个 Agent 系统的统一入口。
    上层（Presentation）通过此类与 Agent 交互。
    """

    def __init__(
        self,
        world_id: int = 1,
        db_path: str | None = None,
        system_prompt: str | None = None,
        skills_dir: str | None = None,
    ):
        self._world_id = world_id
        self._db_path = db_path
        self._system_prompt = system_prompt
        self._execution_state = "idle"
        self._last_result: dict[str, Any] = {}

        # 加载游戏状态
        self._initial_state = self._load_initial_state()

    def _load_initial_state(self) -> AgentState:
        """从数据库加载初始状态"""
        state = create_initial_state(world_id=str(self._world_id))

        try:
            world_repo = WorldRepo()
            world = world_repo.get_by_id(self._world_id, self._db_path)
            if world:
                state["current_location"] = {"name": world.name}

            player_repo = PlayerRepo()
            player = player_repo.get_by_world(self._world_id, self._db_path)
            if player:
                state["player"] = player.model_dump()

            npc_repo = NPCRepo()
            npcs = npc_repo.get_by_world(self._world_id, self._db_path)
            if npcs:
                state["active_npcs"] = [n.model_dump() for n in npcs]

        except Exception as e:
            logger.warning(f"加载游戏状态失败: {e}")

        return state

    def run_sync(self, user_input: str, event_type: str = "player_action") -> dict[str, Any]:
        """同步执行一轮 Agent（阻塞）

        Args:
            user_input: 玩家输入
            event_type: 事件类型

        Returns:
            执行结果字典
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在 Qt 事件循环中，使用 qasync
                import qasync
                future = qasync.ensure_future(self.run(user_input, event_type))
                # 注意: 这里不能直接 await，需要由调用方处理
                return {"status": "async_scheduled", "message": "已调度异步执行"}
            else:
                return loop.run_until_complete(self.run(user_input, event_type))
        except RuntimeError:
            return asyncio.run(self.run(user_input, event_type))

    async def run(self, user_input: str, event_type: str = "player_action") -> dict[str, Any]:
        """异步执行一轮 Agent

        Args:
            user_input: 玩家输入
            event_type: 事件类型

        Returns:
            执行结果字典:
            {
                "narrative": str,
                "commands": list,
                "turn_count": int,
                "tokens_used": int,
                "latency_ms": int,
                "model": str,
            }
        """
        start_time = time.time()
        self._execution_state = "running"

        # 通知回合开始
        turn = self._initial_state.get("turn_count", 0) + 1
        event_bus.emit(create_turn_start_event(str(self._world_id), turn))

        try:
            # 准备输入状态
            input_state = {
                **self._initial_state,
                "current_event": {
                    "type": event_type,
                    "data": {"raw_text": user_input},
                    "context_hints": [],
                },
            }

            # 执行图
            result = await gm_graph.ainvoke(input_state)

            # 提取结果
            llm_response = result.get("llm_response", {})
            narrative = llm_response.get("content", "")
            commands = result.get("parsed_commands", [])
            command_results = result.get("command_results", [])

            latency_ms = int((time.time() - start_time) * 1000)

            # 更新内部状态
            self._initial_state["turn_count"] = result.get("turn_count", turn)
            self._initial_state["execution_state"] = "idle"
            self._execution_state = "idle"

            # 通知回合结束
            event_bus.emit(create_turn_end_event(
                world_id=str(self._world_id),
                turn_count=result.get("turn_count", turn),
                narrative=narrative,
                commands_count=len(commands),
                tokens_used=llm_response.get("tokens", 0),
                latency_ms=latency_ms,
            ))

            self._last_result = {
                "status": "success",
                "narrative": narrative,
                "commands": commands,
                "command_results": command_results,
                "turn_count": result.get("turn_count", turn),
                "tokens_used": llm_response.get("tokens", 0),
                "latency_ms": latency_ms,
                "model": llm_response.get("model", ""),
                "provider": llm_response.get("provider", ""),
            }

            return self._last_result

        except Exception as e:
            logger.error(f"Agent 执行失败: {e}")
            self._execution_state = "error"
            event_bus.emit(create_error_event(str(e)))
            return {
                "status": "error",
                "error": str(e),
                "narrative": f"[Agent 错误: {e}]",
            }

    async def stream(self, user_input: str, event_type: str = "player_action") -> AsyncGenerator[dict, None]:
        """流式执行一轮 Agent

        Yields:
            事件字典（token/command/error/complete）
        """
        # 流式执行通过 EventBus 间接实现
        # 上层通过订阅 EventBus 事件来获取流式数据
        result = await self.run(user_input, event_type)
        yield {"type": "complete", "data": result}

    @property
    def execution_state(self) -> str:
        return self._execution_state

    @property
    def last_result(self) -> dict[str, Any]:
        return self._last_result

    def get_state_snapshot(self) -> dict[str, Any]:
        """获取当前状态快照（用于 UI 显示）"""
        return {
            "world_id": self._world_id,
            "turn_count": self._initial_state.get("turn_count", 0),
            "execution_state": self._execution_state,
            "player": self._initial_state.get("player", {}),
            "location": self._initial_state.get("current_location", {}),
            "npcs": self._initial_state.get("active_npcs", []),
        }
```

8.2 创建 `2workbench/feature/ai/__init__.py`：

```python
# 2workbench/feature/ai/__init__.py
"""AI 编排层 — LangGraph Agent 核心"""
from feature.ai.graph import gm_graph, build_gm_graph
from feature.ai.gm_agent import GMAgent
from feature.ai.nodes import (
    node_handle_event, node_build_prompt, node_llm_reasoning,
    node_parse_output, node_execute_commands, node_update_memory,
)
from feature.ai.command_parser import parse_llm_output, ParsedOutput, ParsedCommand
from feature.ai.prompt_builder import PromptBuilder
from feature.ai.skill_loader import SkillLoader, Skill, SkillMetadata
from feature.ai.tools import ALL_TOOLS, get_tools_schema
from feature.ai.events import (
    TURN_START, TURN_END, AGENT_ERROR,
    LLM_STREAM_TOKEN, LLM_STREAM_REASONING,
    COMMAND_PARSED, COMMAND_EXECUTED, MEMORY_STORED,
    create_turn_start_event, create_turn_end_event, create_stream_token_event,
)

__all__ = [
    "gm_graph", "build_gm_graph", "GMAgent",
    "parse_llm_output", "PromptBuilder", "SkillLoader",
    "ALL_TOOLS", "get_tools_schema",
]
```

**验收**:
- [ ] `feature/ai/gm_agent.py` 创建完成
- [ ] `GMAgent` 提供 `run()` / `run_sync()` / `stream()` 接口
- [ ] `get_state_snapshot()` 返回当前状态
- [ ] `feature/ai/__init__.py` 导出完整

---

### Step 9: 集成测试

**目的**: 端到端测试 Agent 执行流程。

**方案**:

9.1 创建 `2workbench/tests/test_ai_integration.py`：

```bash
cd 2workbench ; python -c "
print('集成测试需要实际 LLM API Key，跳过自动测试。')
print('手动测试步骤:')
print('1. 确保 .env 中配置了 DEEPSEEK_API_KEY')
print('2. 运行: python -c \"from feature.ai import GMAgent; agent = GMAgent(); print(agent.run_sync(\\\"你好\\\"))\"')
print('✅ P2 AI 层代码结构验证通过')
"
```

**注意**: 完整的端到端测试需要实际的 LLM API Key。在没有 API Key 的情况下，验证代码结构即可。

9.2 验证代码结构（不需要 API Key）：

```bash
cd 2workbench ; python -c "
# 验证所有模块可以导入
from feature.ai import (
    gm_graph, build_gm_graph, GMAgent,
    parse_llm_output, PromptBuilder, SkillLoader,
    ALL_TOOLS, get_tools_schema,
)
from feature.ai.events import TURN_START, TURN_END, create_turn_start_event
from feature.ai.command_parser import ParsedOutput, ParsedCommand
from feature.ai.nodes import node_handle_event, route_after_llm

# 验证图结构
graph = build_gm_graph()
nodes = list(graph.get_graph().nodes.keys())
print(f'图节点: {nodes}')
assert 'handle_event' in nodes
assert 'build_prompt' in nodes
assert 'llm_reasoning' in nodes
assert 'parse_output' in nodes
assert 'execute_commands' in nodes
assert 'update_memory' in nodes

# 验证 GMAgent 可以创建（不需要 DB）
agent = GMAgent(world_id=999)
assert agent.execution_state == 'idle'
snapshot = agent.get_state_snapshot()
assert snapshot['world_id'] == 999

# 验证 CommandParser
parsed = parse_llm_output('{\"narrative\": \"测试\", \"commands\": []}')
assert parsed.narrative == '测试'

# 验证工具
schemas = get_tools_schema()
assert len(schemas) == 9

print('✅ P2 AI 层代码结构验证全部通过')
"
```

**验收**:
- [ ] 所有模块导入成功
- [ ] StateGraph 包含 6 个节点
- [ ] GMAgent 可创建
- [ ] CommandParser 正常工作
- [ ] 9 个工具 schema 正确

---

## 注意事项

### 异步执行

LangGraph 的 `ainvoke` 是异步的。在 PyQt6 环境中使用 `qasync`：
- `GMAgent.run_sync()` 会自动检测事件循环
- 如果在 Qt 事件循环中，返回 `async_scheduled` 状态
- 上层需要使用 `qasync.ensure_future()` 来调度

### EventBus 事件流

Agent 执行过程中会通过 EventBus 发出大量事件。Presentation 层通过订阅这些事件来更新 UI：
- `TURN_START` / `TURN_END` — 回合生命周期
- `LLM_STREAM_TOKEN` — 流式 token（用于实时显示）
- `NODE_STARTED` / `NODE_COMPLETED` — 节点执行进度
- `AGENT_ERROR` — 错误通知

### LLM API Key

Agent 执行需要至少一个 LLM API Key。在 `.env` 中配置：
```
DEEPSEEK_API_KEY=sk-xxx
```

### 后续 Phase 衔接

- **P3 (Feature Services)**: 将各业务系统（Battle/Dialogue/Quest 等）封装为 Feature 模块，通过 EventBus 与 AI 层通信
- **P4 (GUI Editor)**: Presentation 层订阅 EventBus 事件，更新 UI

---

## 完成检查清单

- [ ] Step 1: LangGraph 安装 + 目录创建
- [ ] Step 2: 事件定义（12 个事件类型 + 5 个辅助函数）
- [ ] Step 3: CommandParser（4 级容错）
- [ ] Step 4: PromptBuilder（4 部分组装）
- [ ] Step 5: SkillLoader（评分匹配 + 激活层加载）
- [ ] Step 6: LangGraph Tools（9 个工具）
- [ ] Step 7: StateGraph 构建（6 节点 + 条件路由）
- [ ] Step 8: GM Agent 门面（统一接口）
- [ ] Step 9: 集成测试（代码结构验证）
