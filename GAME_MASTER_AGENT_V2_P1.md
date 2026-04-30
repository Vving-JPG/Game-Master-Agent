# Game Master Agent V2 - P1: 核心重构

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户将 V1 的 Game Master Agent **重构为 V2 通用游戏驱动 Agent**。
- **技术栈**: Python 3.11+ / DeepSeek API / FastAPI / SQLite / python-frontmatter
- **包管理器**: uv
- **LLM**: DeepSeek（通过 OpenAI 兼容接口调用）
- **开发IDE**: Trae

### 前置条件

**P0 已完成**。以下模块已就绪：
- `src/memory/file_io.py` — 原子写入 + YAML/MD 解析
- `src/memory/loader.py` — 渐进式记忆加载（3 层）
- `src/memory/manager.py` — 记忆管理主类
- `src/skills/loader.py` — Skill 发现与加载器
- `src/adapters/base.py` — 引擎适配器抽象接口 + 数据类
- `src/adapters/text_adapter.py` — MUD 文字适配器
- `skills/builtin/` — 5 个内置 SKILL.md
- `workspace/` — Agent Workspace 目录和索引文件
- P0 全部测试通过（49 个新测试 + 126 个 V1 保留测试 = **175 个**）

### ⚠️ P1 开始前必须处理的问题

1. **`src/services/llm_client.py` 是同步的**：V1 使用 `from openai import OpenAI`（同步客户端），但 P1 的 `game_master.py` 和 `event_handler.py` 都是 `async`。**步骤 1.4 会先将 `LLMClient` 改为 `AsyncOpenAI`**，再新增 `stream()` 方法
2. **`prompts/` 目录不存在**：V1 的 system prompt 在 `src/prompts/gm_system.py` 中（Python 字符串），P1 步骤 1.3 会创建独立的 `prompts/system_prompt.md` 文件
3. **`src/agent/game_master.py` 需要整体重写**：V1 用 `while` 循环 + `chat_with_tools()`，P1 改为 `handle_event()` 事件驱动

### P1 阶段目标

1. **实现 CommandParser** — 4 级容错 JSON 解析
2. **实现 PromptBuilder** — Prompt 组装（system + skills + memory + history + event）
3. **编写 system_prompt.md** — Agent 主提示词
4. **LLMClient 新增 stream()** — 流式调用 DeepSeek API
5. **重写 game_master.py** — 事件驱动主循环（替代 V1 的 while 循环）
6. **实现 EventHandler** — 事件分发与 SSE 推送
7. **集成测试** — 端到端验证完整流程

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
   - 每个模块必须有对应的 pytest 测试文件
   - 使用 `from __future__ import annotations` 启用延迟注解
7. **不要跳步**：即使用户让你跳过，也要提醒风险后再决定
8. **V1 代码可修改**：P1 需要修改 V1 的 `llm_client.py` 和重写 `game_master.py`，这是预期行为

## 参考设计文档

以下是 V2 架构设计文档，存放在 `docs/` 目录下。

| 文档 | 内容 |
|------|------|
| `docs/architecture_v2.md` | V2 架构总览、目录结构、技术栈 |
| `docs/communication_protocol.md` | JSON 命令流格式、引擎事件格式、SSE 推送协议、DeepSeek 流式调用 |
| `docs/memory_system.md` | .md 记忆文件格式、渐进式加载、原子写入 |
| `docs/skill_system.md` | SKILL.md 标准、发现机制、加载流程、Skill 嵌入 Prompt |
| `docs/engine_adapter.md` | EngineAdapter 接口、TextAdapter 实现 |
| `docs/dev_plan_v2.md` | V2 开发计划总览 |

## V1 经验教训（必须遵守）

1. **PowerShell `&&` 语法**: Windows PowerShell 不支持 `&&`，用 `;` 分隔多条命令
2. **测试隔离**: 每个测试模块用 `teardown_module()` 清理全局状态，防止测试间污染
3. **SQLite datetime('now')**: 同一秒内多次调用返回相同时间戳，测试断言用 `>=` 而非 `==`
4. **中文括号**: 测试代码中一律用英文括号 `()`，不要用中文括号 `（）`
5. **原子写入**: 所有 .md 文件写入必须用 `atomic_write()`，不要直接 `open().write()`
6. **YAML Front Matter 格式**: 用 `python-frontmatter` 库解析，不要手写字符串拼接
7. **DeepSeek reasoning_content**: 用 `getattr(delta, 'reasoning_content', None)` 安全获取
8. **reasoning_content 必须回传**: 同一 Turn 内子请求必须包含 reasoning_content
9. **tool_call_id**: tool 消息必须包含 `tool_call_id`，从 tool_calls[i].id 获取
10. **tool_calls 增量拼接**: 流式模式下 arguments 分片返回，用 dict 按 index 累积拼接
11. **llm.chat() 返回 str**: V1 的封装返回字符串，V2 用 stream() 替代

---

## P1: 核心重构（共 10 步）

### 步骤 1.1 - 实现 src/agent/command_parser.py

**目的**: 解析 LLM 输出为标准 JSON 命令流，支持 4 级容错

**设计参考**: `docs/communication_protocol.md` 第 8.3 节

**执行**:
创建 `src/agent/command_parser.py`：

**完整代码**:

```python
"""
Agent 输出解析器。
将 LLM 的文本输出解析为标准 JSON 命令流。

容错策略:
1. 直接 JSON 解析
2. 提取 ```json ... ``` 代码块
3. 提取 { ... } JSON 对象
4. 兜底: 将整个文本作为 narrative
"""
from __future__ import annotations

import json
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CommandParser:
    """LLM 输出解析器"""

    def parse(self, raw_text: str) -> dict:
        """
        解析 LLM 输出为标准 JSON 命令流。

        返回格式:
        {
            "narrative": str,
            "commands": list[dict],
            "memory_updates": list[dict]
        }
        """
        text = raw_text.strip()
        if not text:
            return self._empty_response()

        # 策略 1: 直接 JSON 解析
        result = self._try_direct_parse(text)
        if result:
            return result

        # 策略 2: 提取 ```json ... ``` 代码块
        result = self._try_json_block(text)
        if result:
            return result

        # 策略 3: 提取最外层 { ... }
        result = self._try_brace_extract(text)
        if result:
            return result

        # 策略 4: 兜底 — 整个文本作为 narrative
        logger.warning("无法解析 LLM 输出为 JSON，将整个文本作为 narrative")
        return {"narrative": text, "commands": [], "memory_updates": []}

    def _try_direct_parse(self, text: str) -> Optional[dict]:
        """策略 1: 直接 JSON 解析"""
        try:
            result = json.loads(text)
            if isinstance(result, dict) and "narrative" in result:
                return self._normalize(result)
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def _try_json_block(self, text: str) -> Optional[dict]:
        """策略 2: 提取 ```json ... ``` 代码块"""
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if not match:
            return None
        try:
            result = json.loads(match.group(1))
            if isinstance(result, dict) and "narrative" in result:
                return self._normalize(result)
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def _try_brace_extract(self, text: str) -> Optional[dict]:
        """策略 3: 提取最外层 { ... }"""
        # 找到第一个 { 和最后一个 }
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, dict) and "narrative" in result:
                return self._normalize(result)
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def _normalize(self, result: dict) -> dict:
        """确保响应包含所有必需字段"""
        return {
            "narrative": result.get("narrative", ""),
            "commands": self._normalize_commands(result.get("commands", [])),
            "memory_updates": self._normalize_memory_updates(
                result.get("memory_updates", [])
            ),
        }

    def _normalize_commands(self, commands: list) -> list[dict]:
        """规范化 commands 列表"""
        normalized = []
        for cmd in commands:
            if isinstance(cmd, dict) and "intent" in cmd:
                normalized.append({
                    "intent": cmd["intent"],
                    "params": cmd.get("params", {}),
                })
        return normalized

    def _normalize_memory_updates(self, updates: list) -> list[dict]:
        """规范化 memory_updates 列表"""
        normalized = []
        for upd in updates:
            if isinstance(upd, dict) and "file" in upd and "action" in upd:
                entry = {"file": upd["file"], "action": upd["action"]}
                if "content" in upd:
                    entry["content"] = upd["content"]
                if "frontmatter" in upd:
                    entry["frontmatter"] = upd["frontmatter"]
                normalized.append(entry)
        return normalized

    def _empty_response(self) -> dict:
        """空响应"""
        return {"narrative": "", "commands": [], "memory_updates": []}
```

**验收**: `python -c "from src.agent.command_parser import CommandParser"` 成功

---

### 步骤 1.2 - 实现 src/agent/prompt_builder.py

**目的**: 组装 Agent 的完整 Prompt（system + skills + memory + history + event）

**设计参考**: `docs/architecture_v2.md` 第 3.2 节、`docs/skill_system.md` 第 3.4 节

**执行**:
创建 `src/agent/prompt_builder.py`：

**完整代码**:

```python
"""
Prompt 组装器。
将 system prompt、Skill、记忆、历史对话、当前事件组装为完整的 messages 列表。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.memory.manager import MemoryManager
from src.skills.loader import SkillLoader, SkillMetadata

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Prompt 组装器"""

    def __init__(
        self,
        system_prompt_path: str,
        memory_manager: MemoryManager,
        skill_loader: SkillLoader,
    ):
        self.system_prompt_path = Path(system_prompt_path)
        self.memory_manager = memory_manager
        self.skill_loader = skill_loader
        self._system_prompt_cache: Optional[str] = None

    def load_system_prompt(self) -> str:
        """加载 system prompt（带缓存）"""
        if self._system_prompt_cache is None:
            if self.system_prompt_path.exists():
                self._system_prompt_cache = self.system_prompt_path.read_text(
                    encoding="utf-8"
                )
            else:
                logger.warning(f"system prompt 文件不存在: {self.system_prompt_path}")
                self._system_prompt_cache = "你是一个游戏 GM Agent。"
        return self._system_prompt_cache

    def invalidate_system_prompt_cache(self):
        """清除 system prompt 缓存"""
        self._system_prompt_cache = None

    def build(
        self,
        event: dict,
        history: list[dict],
        memory_depth: str = "activation",
    ) -> list[dict]:
        """
        组装完整的 messages 列表。

        :param event: 引擎事件 (EngineEvent 的 data 字段)
        :param history: 历史对话消息列表 (OpenAI 格式)
        :param memory_depth: 记忆加载深度 ("index" / "activation" / "execution")
        :return: OpenAI 格式的 messages 列表
        """
        messages = []

        # 1. System prompt
        system_content = self._build_system_content(event, memory_depth)
        messages.append({"role": "system", "content": system_content})

        # 2. 历史对话
        messages.extend(history)

        # 3. 当前事件（作为 user 消息）
        user_content = self._format_event_as_user_message(event)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_system_content(self, event: dict, memory_depth: str) -> str:
        """构建 system 消息内容"""
        parts = []

        # 1. 基础 system prompt
        parts.append(self.load_system_prompt())

        # 2. 相关 Skill
        event_type = event.get("type", "")
        user_input = event.get("data", {}).get("raw_text", "")
        context_hints = event.get("context_hints", [])

        relevant_skills = self.skill_loader.get_relevant_skills(
            event_type=event_type,
            user_input=user_input,
            context_hints=context_hints,
        )

        if relevant_skills:
            skill_sections = ["\n\n## 可用能力 (Skills)\n"]
            for skill in relevant_skills:
                content = self.skill_loader.load_skill_activation(skill.name)
                if content:
                    skill_sections.append(content)
                    skill_sections.append("")
            parts.append("\n".join(skill_sections))

        # 3. 记忆上下文
        if context_hints:
            memory_text = self.memory_manager.load_context(
                context_hints, depth=memory_depth
            )
            if memory_text.strip():
                parts.append(f"\n\n## 相关记忆\n\n{memory_text}")

        # 4. 游戏状态快照
        game_state = event.get("game_state", {})
        if game_state:
            state_lines = ["\n\n## 当前游戏状态\n"]
            for key, value in game_state.items():
                state_lines.append(f"- {key}: {value}")
            parts.append("\n".join(state_lines))

        return "".join(parts)

    def _format_event_as_user_message(self, event: dict) -> str:
        """将引擎事件格式化为 user 消息"""
        event_type = event.get("type", "unknown")
        data = event.get("data", {})
        raw_text = data.get("raw_text", "")

        if raw_text:
            return f"[{event_type}] 玩家: {raw_text}"

        # 非 player_action 类型的事件
        descriptions = {
            "player_move": f"玩家移动到 {data.get('to', '未知位置')}",
            "combat_start": f"战斗开始: 对手 {data.get('enemy_id', '未知')}",
            "combat_action": f"战斗动作: {data.get('action', '未知')}",
            "combat_end": f"战斗结束: {data.get('result', '未知')}",
            "quest_update": f"任务更新: {data.get('quest_id', '未知')} - {data.get('status', '')}",
            "item_acquire": f"获得物品: {data.get('item_id', '未知')}",
            "npc_interact": f"NPC {data.get('npc_id', '')} 主动交互",
            "time_pass": f"时间流逝: {data.get('new_time', '')}",
            "system_event": f"系统事件: {data.get('message', '')}",
        }
        return f"[{event_type}] {descriptions.get(event_type, str(data))}"
```

**验收**: `python -c "from src.agent.prompt_builder import PromptBuilder"` 成功

---

### 步骤 1.3 - 编写 prompts/system_prompt.md

**目的**: 定义 Agent 的角色、输出格式、Skill 使用规则

**设计参考**: `docs/communication_protocol.md` 第 3 节、`docs/skill_system.md` 第 4.3 节

**执行**:
创建 `prompts/system_prompt.md`：

**完整内容**:

```markdown
# Game Master Agent - System Prompt

## 角色定义

你是一个游戏 Game Master Agent（GM Agent）。你的职责是：

1. **理解玩家意图** — 分析玩家输入，理解他们想做什么
2. **生成叙事** — 用生动、沉浸的文字描述游戏世界的变化
3. **发出指令** — 通过 JSON commands 请求游戏引擎执行操作
4. **管理记忆** — 通过 memory_updates 记录重要的交互和状态变化

**你不是游戏本身，而是驱动游戏运行的 Agent 服务。**

## 输出格式

你必须输出 JSON 格式的命令流：

```json
{
  "narrative": "你的叙事文本...",
  "commands": [
    {"intent": "指令名称", "params": {"参数": "值"}}
  ],
  "memory_updates": [
    {"file": "相对路径.md", "action": "append", "content": "\n[第X天] 记录内容..."}
  ]
}
```

### narrative（叙事文本）
- 使用中文自然语言，第二人称视角（"你走进..."）
- 适当使用感官描写（视觉、听觉、触觉、嗅觉）
- 对话用引号包裹
- 日常场景 100-200 字，重要场景 300-500 字，战斗紧凑有力
- **纯文本**，不包含任何指令或标记

### commands（游戏指令）
- 根据当前激活的 Skill 中定义的可用指令来发出 commands
- 每条 command 包含 `intent` 和 `params`
- 只发出 Skill 中 `allowed-tools` 允许的指令
- 如果没有需要执行的操作，发 `[{"intent": "no_op", "params": {}}]`

### memory_updates（记忆更新）
- 每回合都应该更新相关记忆文件
- `action` 类型：
  - `append`: 追加内容到 Markdown Body（最常用）
  - `create`: 创建新文件（首次遇到新实体时）
  - `update_frontmatter`: 更新 YAML 字段（较少使用，通常由引擎处理）
- 每条记录以 `[第X天 时间段]` 开头
- 记录关键信息：对话要点、状态变化、重要决策
- 不要记录琐碎细节

## 可用指令列表

| intent | params | 说明 |
|--------|--------|------|
| `update_npc_relationship` | `{npc_id, change, reason}` | 修改 NPC 好感度 |
| `update_npc_state` | `{npc_id, field, value}` | 修改 NPC 状态 |
| `offer_quest` | `{title, description, objective, reward}` | 发布任务 |
| `update_quest` | `{quest_id, status, progress}` | 更新任务状态 |
| `give_item` | `{name, type, player_id}` | 给予物品 |
| `remove_item` | `{item_id}` | 移除物品 |
| `modify_stat` | `{stat, change, reason}` | 修改玩家属性 |
| `teleport_player` | `{location_id}` | 传送玩家 |
| `show_notification` | `{message, type}` | 显示通知 |
| `play_sound` | `{sound_id}` | 播放音效 |
| `no_op` | `{}` | 空操作 |

## Skill 使用规则

1. 根据当前事件类型和玩家输入，使用下方"可用能力"中列出的 Skill
2. Skill 定义了特定领域的规则和可用指令
3. 只使用 Skill 中 `allowed-tools` 列出的指令
4. 遵循 Skill 中的叙事要求和注意事项
5. 如果没有匹配的 Skill，使用 narration Skill 的默认规则

## 记忆管理规则

1. 每回合都应该通过 memory_updates 更新记忆
2. 更新与当前交互最相关的文件（NPC、地点、剧情等）
3. 记录格式：`[第X天 时间段] 简洁描述。关键信息**加粗**。`
4. 首次遇到新实体时，用 `action: "create"` 创建新文件
5. 不要重复记录已有信息

## 创建新 Skill

当你发现以下情况时，可以创建新的 Skill 文件：

1. 你在多次对话中重复使用相同的规则或流程
2. 玩家引入了系统没有覆盖的新玩法
3. 新剧情线需要特定的规则支持

创建方式：在 memory_updates 中添加一条：
```json
{
  "file": "skills/agent_created/{skill-name}/SKILL.md",
  "action": "create",
  "content": "---\nname: {skill-name}\ndescription: ...\nversion: 1.0.0\ntriggers:\n  - keyword: [...]\nallowed-tools:\n  - ...\n---\n\n# {标题}\n\n## 核心规则\n..."
}
```

## 引擎拒绝处理

如果引擎拒绝了你的 command（返回 rejected）：
1. **不要自动重试**
2. 将拒绝信息记录到 session/current.md
3. 在下一轮中，如果相关，生成替代叙事
4. 例如：传送被拒绝 → "你试图传送，但一股神秘力量阻止了你..."
```

**验收**: 文件存在，`python -c "from pathlib import Path; print(len(Path('prompts/system_prompt.md').read_text()))"` 输出 > 1000

---

### 步骤 1.4 - LLMClient 改为异步 + 新增 stream() 方法

**目的**: 将 V1 的同步 `LLMClient` 改为异步，并新增流式调用方法

**设计参考**: `docs/communication_protocol.md` 第 7 节

**背景**: V1 的 `src/services/llm_client.py` 使用 `from openai import OpenAI`（同步客户端）。P1 的 `game_master.py` 和 `event_handler.py` 都是 `async`，整个调用链必须是异步的。

**执行**:
1. 先阅读 `src/services/llm_client.py`，理解现有代码结构
2. 将 `OpenAI` 改为 `AsyncOpenAI`：
   - `from openai import OpenAI` → `from openai import AsyncOpenAI`
   - `self.client = OpenAI(...)` → `self.client = AsyncOpenAI(...)`
3. 将现有 `chat()` 方法改为 `async def chat()`：
   - `self.client.chat.completions.create(...)` → `await self.client.chat.completions.create(...)`
   - 如果有 `self.client.models.list()` 之类的调用，也加 `await`
4. 新增 `stream()` 方法（代码如下）
5. 运行 V1 保留的 126 个测试，确认 `chat()` 改为 async 后没有破坏现有功能（如果现有测试调用了 `chat()`，需要加 `asyncio.run()` 或用 `@pytest.mark.asyncio`）

**stream() 方法完整代码**:

```python
async def stream(
    self,
    messages: list[dict],
    model: str = None,
    tools: list[dict] = None,
    temperature: float = 0.7,
    **kwargs,
):
    """
    流式调用 DeepSeek API。

    yield 事件字典:
    - {"event": "reasoning", "data": {"text": "思考内容"}}
    - {"event": "token", "data": {"text": "正式回答内容"}}
    - {"event": "llm_complete", "data": {"content": str, "reasoning_content": str, "tool_calls": list|None, "finish_reason": str|None}}

    处理要点:
    1. reasoning_content: 用 getattr(delta, 'reasoning_content', None) 获取
    2. tool_calls: 增量格式，用 dict 按 index 累积拼接
    3. arguments 分片返回，需要拼接
    """
    model = model or self.model_name
    content = ""
    reasoning = ""
    tool_calls_acc = {}  # key: index, value: {id, type, function: {name, arguments}}
    finish_reason = None

    stream = await self.client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        stream=True,
        temperature=temperature,
        **kwargs,
    )

    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        finish_reason = chunk.choices[0].finish_reason

        # 1. 思考内容 (deepseek-reasoner 或 thinking 模式)
        rc = getattr(delta, 'reasoning_content', None)
        if rc:
            reasoning += rc
            yield {"event": "reasoning", "data": {"text": rc}}

        # 2. 正式回答内容
        if delta.content:
            content += delta.content
            yield {"event": "token", "data": {"text": delta.content}}

        # 3. Tool Calls (增量拼接)
        if hasattr(delta, 'tool_calls') and delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {
                        "id": tc.id or "",
                        "type": getattr(tc, 'type', 'function'),
                        "function": {
                            "name": tc.function.name if tc.function else "",
                            "arguments": ""
                        }
                    }
                if tc.function and tc.function.arguments:
                    tool_calls_acc[idx]["function"]["arguments"] += tc.function.arguments

    # 组装最终的 tool_calls 列表
    final_tool_calls = None
    if tool_calls_acc:
        final_tool_calls = [
            {
                "id": v["id"],
                "type": v["type"],
                "function": {
                    "name": v["function"]["name"],
                    "arguments": v["function"]["arguments"]
                }
            }
            for v in sorted(tool_calls_acc.values(), key=lambda x: x["id"])
        ]

    yield {
        "event": "llm_complete",
        "data": {
            "content": content,
            "reasoning_content": reasoning,
            "tool_calls": final_tool_calls,
            "finish_reason": finish_reason,
        }
    }
```

**重要注意事项**:
- 改 `OpenAI` → `AsyncOpenAI` 后，所有调用 `self.client` 的地方都要加 `await`
- 如果 V1 有其他地方直接调用 `LLMClient.chat()`（非 async），需要同步修改那些调用方
- 如果 `chat()` 方法被 V1 测试直接调用，测试需要改为 `@pytest.mark.asyncio` + `await`
- `__init__` 中的 `self.client = AsyncOpenAI(...)` 不需要 `await`

**验收**:
1. `python -c "from src.services.llm_client import LLMClient; assert hasattr(LLMClient, 'stream')"` 成功
2. V1 保留的 126 个测试仍然全部通过

---

### 步骤 1.5 - 重写 src/agent/game_master.py

**目的**: 将 V1 的 while 循环重写为事件驱动的 `handle_event()` 方法

**设计参考**: `docs/architecture_v2.md` 第 3.2 节

**说明**: 这是 P1 的核心步骤。新的 `GameMaster` 不再包含游戏逻辑，而是：
1. 接收 `EngineEvent`
2. 通过 `PromptBuilder` 组装 Prompt
3. 通过 `LLMClient.stream()` 调用 LLM
4. 通过 `CommandParser` 解析输出
5. 通过 `MemoryManager` 更新记忆
6. 通过 `EngineAdapter` 发送指令到引擎
7. 返回完整的响应

**执行**:
重写 `src/agent/game_master.py`：

**完整代码**:

```python
"""
Game Master Agent — 事件驱动主循环。
V2 重写: 不再是游戏本身，而是驱动游戏的 Agent 服务。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from src.adapters.base import EngineAdapter, EngineEvent
from src.agent.command_parser import CommandParser
from src.agent.prompt_builder import PromptBuilder
from src.memory.manager import MemoryManager
from src.skills.loader import SkillLoader

logger = logging.getLogger(__name__)


class GameMaster:
    """Game Master Agent — 事件驱动"""

    def __init__(
        self,
        llm_client,
        memory_manager: MemoryManager,
        skill_loader: SkillLoader,
        engine_adapter: EngineAdapter,
        system_prompt_path: str = "prompts/system_prompt.md",
    ):
        self.llm_client = llm_client
        self.memory_manager = memory_manager
        self.skill_loader = skill_loader
        self.engine_adapter = engine_adapter
        self.command_parser = CommandParser()
        self.prompt_builder = PromptBuilder(
            system_prompt_path=system_prompt_path,
            memory_manager=memory_manager,
            skill_loader=skill_loader,
        )
        self.history: list[dict] = []
        self.turn_count = 0
        self.total_tokens = 0

    async def handle_event(self, event: EngineEvent) -> dict:
        """
        处理单个引擎事件，返回完整的 Agent 响应。

        流程:
        1. 组装 Prompt
        2. 流式调用 LLM
        3. 解析输出
        4. 更新记忆
        5. 发送指令到引擎
        6. 更新历史对话

        返回:
        {
            "response_id": str,
            "event_id": str,
            "narrative": str,
            "commands": list[dict],
            "memory_updates": list[dict],
            "command_results": list[dict],
            "stats": dict
        }
        """
        self.turn_count += 1
        response_id = f"resp_{uuid.uuid4().hex[:12]}"

        logger.info(f"[回合 {self.turn_count}] 处理事件: {event.type}")

        # Step 1: 组装 Prompt
        event_dict = {
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "type": event.type,
            "data": event.data,
            "context_hints": event.context_hints,
            "game_state": event.game_state,
        }
        messages = self.prompt_builder.build(
            event=event_dict,
            history=self.history,
            memory_depth="activation",
        )

        # Step 2: 流式调用 LLM
        full_content = ""
        reasoning_content = ""
        tokens_used = 0

        async for chunk in self.llm_client.stream(messages):
            event_type = chunk["event"]
            data = chunk["data"]

            if event_type == "token":
                full_content += data["text"]
            elif event_type == "reasoning":
                reasoning_content += data["text"]
            elif event_type == "llm_complete":
                tokens_used = len(full_content) + len(reasoning_content)

        self.total_tokens += tokens_used

        # Step 3: 解析输出
        response = self.command_parser.parse(full_content)
        narrative = response["narrative"]
        commands = response["commands"]
        memory_updates = response["memory_updates"]

        # Step 4: 更新记忆（Agent 侧 — Markdown Body）
        for update in memory_updates:
            try:
                self.memory_manager.apply_memory_updates([update])
            except Exception as e:
                logger.error(f"记忆更新失败: {update['file']} - {e}")

        # Step 5: 发送指令到引擎
        command_results = []
        state_changes = []
        if commands:
            try:
                results = await self.engine_adapter.send_commands(commands)
                for r in results:
                    result_dict = {
                        "intent": r.intent,
                        "status": r.status,
                    }
                    if r.new_value is not None:
                        result_dict["new_value"] = r.new_value
                    if r.reason:
                        result_dict["reason"] = r.reason
                    if r.suggestion:
                        result_dict["suggestion"] = r.suggestion
                    command_results.append(result_dict)

                    # 收集引擎状态变化
                    if r.state_changes:
                        state_changes.append(r.state_changes)
            except Exception as e:
                logger.error(f"指令执行失败: {e}")
                command_results.append({
                    "intent": "error",
                    "status": "error",
                    "reason": str(e),
                })

        # Step 5.1: 应用引擎状态变化（引擎侧 — YAML Front Matter）
        for change in state_changes:
            try:
                self.memory_manager.apply_state_changes([change])
            except Exception as e:
                logger.error(f"状态变化应用失败: {change} - {e}")

        # Step 6: 更新历史对话
        self._update_history(event_dict, response, command_results)

        # 更新会话记录
        self._update_session(event, response, command_results)

        return {
            "response_id": response_id,
            "event_id": event.event_id,
            "narrative": narrative,
            "commands": commands,
            "memory_updates": memory_updates,
            "command_results": command_results,
            "stats": {
                "turn": self.turn_count,
                "tokens_used": tokens_used,
                "total_tokens": self.total_tokens,
                "commands_sent": len(commands),
                "commands_success": sum(
                    1 for r in command_results if r["status"] == "success"
                ),
            },
        }

    def _update_history(
        self,
        event: dict,
        response: dict,
        command_results: list[dict],
    ):
        """更新对话历史（保留最近 20 轮）"""
        # User 消息
        user_text = event.get("data", {}).get("raw_text", "")
        if not user_text:
            event_type = event.get("type", "")
            user_text = f"[{event_type}] {event.get('data', {})}"
        self.history.append({"role": "user", "content": user_text})

        # Assistant 消息
        self.history.append({
            "role": "assistant",
            "content": response["narrative"],
        })

        # 如果有指令执行结果，追加为 tool 消息
        for r in command_results:
            if r["status"] in ("rejected", "error"):
                self.history.append({
                    "role": "user",
                    "content": f"[系统] 指令 {r['intent']} 执行失败: {r.get('reason', '未知错误')}",
                })

        # 保留最近 20 轮（40 条消息）
        max_messages = 40
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    def _update_session(
        self,
        event: EngineEvent,
        response: dict,
        command_results: list[dict],
    ):
        """更新会话记录文件"""
        try:
            cmd_summary = ""
            if response["commands"]:
                intents = [c["intent"] for c in response["commands"] if c["intent"] != "no_op"]
                if intents:
                    cmd_summary = f" 指令: {', '.join(intents)}"

            rejected = [r for r in command_results if r["status"] == "rejected"]
            reject_summary = ""
            if rejected:
                reject_summary = f" 拒绝: {', '.join(r['intent'] for r in rejected)}"

            self.memory_manager.apply_memory_updates([{
                "file": "session/current.md",
                "action": "append",
                "content": (
                    f"\n[回合{self.turn_count}] "
                    f"{event.type}: {event.data.get('raw_text', '')[:50]}"
                    f"{cmd_summary}{reject_summary}"
                ),
            }])
        except Exception as e:
            logger.error(f"会话记录更新失败: {e}")

    def reset(self):
        """重置 Agent 状态"""
        self.history.clear()
        self.turn_count = 0
        self.total_tokens = 0
        logger.info("Agent 状态已重置")
```

**验收**: `python -c "from src.agent.game_master import GameMaster"` 成功

---

### 步骤 1.6 - 实现 src/agent/event_handler.py

**目的**: 事件分发器，接收引擎事件，调用 GameMaster，推送 SSE

**设计参考**: `docs/communication_protocol.md` 第 5 节

**执行**:
创建 `src/agent/event_handler.py`：

**完整代码**:

```python
"""
事件处理器。
接收引擎事件，调用 GameMaster 处理，通过回调推送 SSE 事件。
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterable
from typing import Callable, Awaitable, Optional

from src.adapters.base import EngineAdapter, EngineEvent
from src.agent.game_master import GameMaster

logger = logging.getLogger(__name__)


# SSE 回调类型: 接收 event_name 和 data
SSECallback = Callable[[str, dict], Awaitable[None]]


class EventHandler:
    """事件分发与 SSE 推送"""

    def __init__(
        self,
        game_master: GameMaster,
        engine_adapter: EngineAdapter,
    ):
        self.game_master = game_master
        self.engine_adapter = engine_adapter
        self._sse_callbacks: list[SSECallback] = []
        self._processing = False
        self._current_event: Optional[EngineEvent] = None

    def register_sse_callback(self, callback: SSECallback):
        """注册 SSE 推送回调"""
        self._sse_callbacks.append(callback)

    async def _emit_sse(self, event_name: str, data: dict):
        """推送到所有 SSE 回调"""
        for cb in self._sse_callbacks:
            try:
                await cb(event_name, data)
            except Exception as e:
                logger.error(f"SSE 推送失败: {e}")

    @property
    def is_processing(self) -> bool:
        """是否正在处理事件"""
        return self._processing

    @property
    def current_event(self) -> Optional[EngineEvent]:
        """当前正在处理的事件"""
        return self._current_event

    async def handle_event(self, event: EngineEvent) -> dict:
        """
        处理引擎事件并推送 SSE。

        SSE 推送时序:
        1. turn_start
        2. reasoning / token (由 GameMaster 内部流式推送)
        3. command
        4. memory_update
        5. state_change
        6. turn_end
        """
        if self._processing:
            logger.warning("Agent 正在处理其他事件，忽略新事件")
            return {"error": "AGENT_BUSY", "message": "Agent is processing another event"}

        self._processing = True
        self._current_event = event

        try:
            # 1. 推送 turn_start
            await self._emit_sse("turn_start", {
                "event_id": event.event_id,
                "type": event.type,
            })

            # 2. 调用 GameMaster 处理
            response = await self.game_master.handle_event(event)

            # 3. 推送 commands
            for cmd in response["commands"]:
                if cmd.get("intent") != "no_op":
                    await self._emit_sse("command", cmd)

            # 4. 推送 memory_updates
            for upd in response.get("memory_updates", []):
                await self._emit_sse("memory_update", upd)

            # 5. 推送 command_results 中的 state_changes
            for r in response.get("command_results", []):
                if r.get("status") == "rejected":
                    await self._emit_sse("command_rejected", r)

            # 6. 推送 turn_end
            await self._emit_sse("turn_end", {
                "response_id": response["response_id"],
                "stats": response.get("stats", {}),
            })

            return response

        except Exception as e:
            logger.error(f"事件处理失败: {e}", exc_info=True)
            await self._emit_sse("error", {
                "message": str(e),
                "code": "EVENT_PROCESSING_ERROR",
            })
            return {"error": str(e)}

        finally:
            self._processing = False
            self._current_event = None

    async def stream_response(self, event: EngineEvent) -> AsyncIterable[dict]:
        """
        流式处理事件，yield SSE 事件字典。
        用于 FastAPI EventSourceResponse。

        yield 格式: {"event": str, "data": dict, "id": int}
        """
        event_index = 0

        # turn_start
        yield {
            "event": "turn_start",
            "data": {"event_id": event.event_id, "type": event.type},
            "id": event_index,
        }
        event_index += 1

        try:
            # 调用 GameMaster
            response = await self.game_master.handle_event(event)

            # narrative 已在 GameMaster 内流式生成
            # 这里推送最终结果
            yield {
                "event": "narrative_complete",
                "data": {"text": response["narrative"]},
                "id": event_index,
            }
            event_index += 1

            # commands
            for cmd in response["commands"]:
                if cmd.get("intent") != "no_op":
                    yield {
                        "event": "command",
                        "data": cmd,
                        "id": event_index,
                    }
                    event_index += 1

            # memory_updates
            for upd in response.get("memory_updates", []):
                yield {
                    "event": "memory_update",
                    "data": upd,
                    "id": event_index,
                }
                event_index += 1

            # command_results
            for r in response.get("command_results", []):
                if r.get("status") == "rejected":
                    yield {
                        "event": "command_rejected",
                        "data": r,
                        "id": event_index,
                    }
                    event_index += 1

            # turn_end
            yield {
                "event": "turn_end",
                "data": {
                    "response_id": response["response_id"],
                    "stats": response.get("stats", {}),
                },
                "id": event_index,
            }
            event_index += 1

        except Exception as e:
            yield {
                "event": "error",
                "data": {"message": str(e), "code": "STREAM_ERROR"},
                "id": event_index,
            }
```

**验收**: `python -c "from src.agent.event_handler import EventHandler"` 成功

---

### 步骤 1.7 - TextAdapter 集成测试

**目的**: 验证事件 → Agent → 指令 → 引擎的完整流程

**执行**:
创建 `tests/test_agent/test_game_master_integration.py`：

**完整代码**:

```python
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
    # 创建必要的子目录
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
    # 模拟 stream() 返回 JSON 命令流
    async def mock_stream(messages):
        yield {"event": "token", "data": {"text": '{"narrative': "铁匠点了点头。', "commands": [{"intent": "no_op", "params": {}}], "memory_updates": [{"file": "session/current.md", "action": "append", "content": "\\n[回合1] 测试。"}]}'}}
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

        assert len(gm.history) >= 2  # 至少 user + assistant

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
```

**验收**: `pytest tests/test_agent/test_game_master_integration.py -v` 全部通过

---

### 步骤 1.8 - 记忆更新集成测试

**目的**: 验证 Agent 输出 → memory_updates → 文件更新的完整流程

**执行**:
创建 `tests/test_agent/test_memory_integration.py`：

**完整代码**:

```python
"""记忆更新集成测试"""
import pytest
from pathlib import Path
import frontmatter
from src.memory.manager import MemoryManager
from src.agent.command_parser import CommandParser


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    for d in ["npcs", "session"]:
        (ws / d).mkdir()
    return ws


@pytest.fixture
def manager(workspace):
    return MemoryManager(str(workspace))


@pytest.fixture
def parser():
    return CommandParser()


class TestMemoryUpdateIntegration:
    """验证 CommandParser 输出 → MemoryManager 文件更新"""

    def test_append_to_existing_file(self, manager, workspace, parser):
        # 先创建 NPC 文件
        (workspace / "npcs" / "铁匠.md").write_text(
            "---\nname: 铁匠\ntype: npc\nversion: 1\n---\n## 初始印象\n[第1天] 铁匠。",
            encoding="utf-8"
        )

        # 模拟 Agent 输出
        raw = '{"narrative": "铁匠点了点头。", "commands": [], "memory_updates": [{"file": "npcs/铁匠.md", "action": "append", "content": "\\n[第2天] 玩家来买剑。"}]}'
        response = parser.parse(raw)

        # 应用 memory_updates
        manager.apply_memory_updates(response["memory_updates"])

        # 验证文件更新
        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert "第1天" in post.content
        assert "第2天" in post.content
        assert post["version"] == 2

    def test_create_new_file(self, manager, workspace, parser):
        raw = '{"narrative": "一个陌生人出现了。", "commands": [], "memory_updates": [{"file": "npcs/流浪商人.md", "action": "create", "content": "---\\nname: 流浪商人\\ntype: npc\\nversion: 1\\n---\\n## 初始印象\\n[第1天] 神秘的商人。"}]}'
        response = parser.parse(raw)

        manager.apply_memory_updates(response["memory_updates"])

        assert (workspace / "npcs" / "流浪商人.md").exists()
        post = frontmatter.load(str(workspace / "npcs" / "流浪商人.md"))
        assert post["name"] == "流浪商人"

    def test_state_changes_update_frontmatter(self, manager, workspace):
        (workspace / "npcs" / "铁匠.md").write_text(
            "---\nname: 铁匠\nhp: 80\nversion: 1\n---\n记录",
            encoding="utf-8"
        )

        manager.apply_state_changes([{
            "file": "npcs/铁匠.md",
            "frontmatter": {"hp": 75, "version": 2}
        }])

        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert post["hp"] == 75
        assert "记录" in post.content  # Body 不变
```

**验收**: `pytest tests/test_agent/test_memory_integration.py -v` 全部通过

---

### 步骤 1.9 - Skill 加载集成测试

**目的**: 验证事件 → Skill 匹配 → 嵌入 Prompt 的完整流程

**执行**:
创建 `tests/test_agent/test_skill_integration.py`：

**完整代码**:

```python
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
    # 创建 combat skill
    combat_dir = sd / "builtin" / "combat"
    combat_dir.mkdir(parents=True)
    (combat_dir / "SKILL.md").write_text(
        "---\nname: combat\ndescription: 战斗系统管理。\nversion: 1.0.0\n"
        "tags: [combat]\ntriggers:\n  - event_type: combat_start\n"
        "  - keyword: [\"战斗\", \"攻击\"]\nallowed-tools:\n  - modify_stat\n---\n\n"
        "# 战斗系统\n\n## 伤害公式\n基础伤害 = 攻击力 - 防御力 * 0.5\n",
        encoding="utf-8"
    )
    # 创建 dialogue skill
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
        # 创建 NPC 记忆文件
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
```

**验收**: `pytest tests/test_agent/test_skill_integration.py -v` 全部通过

---

### 步骤 1.10 - 全流程端到端测试

**目的**: 验证完整回合：事件 → Agent → 叙事 → 指令 → 记忆 → 状态

**执行**:
创建 `tests/test_agent/test_e2e.py`：

**完整代码**:

```python
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
    # 创建玩家档案
    (ws / "player" / "profile.md").write_text(
        "---\nname: 玩家\ntype: player\nhp: 100\nversion: 1\n---\n## 初始状态\n[第1天] 冒险开始。",
        encoding="utf-8"
    )
    # 创建 NPC 文件
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

        # 验证响应结构
        assert response["narrative"] != ""
        assert response["event_id"] == "evt_e2e_001"
        assert response["stats"]["turn"] == 1
        assert len(response["commands"]) == 1
        assert response["commands"][0]["intent"] == "update_npc_relationship"

        # 验证指令执行
        assert len(response["command_results"]) == 1
        assert response["command_results"][0]["status"] == "success"

        # 验证记忆更新
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

        # 收集 SSE 事件
        sse_events = []
        async def collect_sse(name, data):
            sse_events.append({"event": name, "data": data})

        handler.register_sse_callback(collect_sse)

        event = EngineEvent(
            event_id="evt_e2e_002", timestamp="t", type="player_action",
            data={"raw_text": "看看周围"}, context_hints=[], game_state={},
        )

        response = await handler.handle_event(event)

        # 验证 SSE 事件序列
        event_names = [e["event"] for e in sse_events]
        assert "turn_start" in event_names
        assert "turn_end" in event_names

        # 验证响应
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
        assert len(gm.history) >= 6  # 3 轮 * 2 条消息
```

**验收**: `pytest tests/test_agent/test_e2e.py -v` 全部通过

---

## P1 完成检查清单

- [ ] Step 1.1: `command_parser.py` 实现 + 测试通过
- [ ] Step 1.2: `prompt_builder.py` 实现 + 测试通过
- [ ] Step 1.3: `system_prompt.md` 创建完毕
- [ ] Step 1.4: `llm_client.stream()` 新增 + 测试通过
- [ ] Step 1.5: `game_master.py` 重写完成
- [ ] Step 1.6: `event_handler.py` 实现 + 测试通过
- [ ] Step 1.7: TextAdapter 集成测试通过 (>=3 个)
- [ ] Step 1.8: 记忆更新集成测试通过 (>=3 个)
- [ ] Step 1.9: Skill 加载集成测试通过 (>=5 个)
- [ ] Step 1.10: 端到端测试通过 (>=3 个)
- [ ] P0 全部测试仍然通过（175 个）
