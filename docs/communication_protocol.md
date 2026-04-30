# V2 通信协议设计

> **版本**: v2.0-draft
> **日期**: 2026-04-28
> **前置文档**: `architecture_v2.md`
> **关联文档**: `memory_system.md`, `engine_adapter.md`

---

## 1. 协议概述

V2 的核心通信发生在三个方向：

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│  游戏引擎  │◄──────►│  Agent   │◄──────►│ WorkBench│
│          │  引擎协议 │  服务    │  HTTP   │ (Vue)    │
│          │         │          │  + SSE  │          │
└──────────┘         └──────────┘         └──────────┘
```

| 通信方向 | 协议 | 格式 | 说明 |
|----------|------|------|------|
| 引擎 → Agent | HTTP POST | JSON (EngineEvent) | 玩家操作、游戏状态变化 |
| Agent → 引擎 | HTTP POST | JSON (CommandBatch) | 叙事 + 游戏指令 |
| Agent → WorkBench | SSE | JSON (StreamEvent) | 实时流式推送 |
| WorkBench → Agent | HTTP REST | JSON | 管理、调试、文件操作 |

---

## 2. 引擎事件格式 (Engine → Agent)

### 2.1 基础事件结构

引擎通过 HTTP POST 发送事件到 Agent：

```json
{
  "event_id": "evt_20260428_001",
  "timestamp": "2026-04-28T14:30:00Z",
  "type": "player_action",
  "data": {
    "raw_text": "和铁匠聊聊哥布林的事",
    "player_id": "player_001"
  },
  "context_hints": ["npcs/铁匠", "story/哥布林_威胁"],
  "game_state": {
    "location": "locations/铁匠铺",
    "time": "第3天 上午",
    "player_hp": 85
  }
}
```

### 2.2 事件类型枚举

| type | 说明 | data 字段 | context_hints |
|------|------|-----------|---------------|
| `player_action` | 玩家输入文本 | `{raw_text, player_id}` | 相关 NPC/地点/剧情 |
| `player_move` | 玩家移动 | `{from, to, player_id}` | 目标地点 |
| `combat_start` | 战斗开始 | `{enemy_id, player_id}` | 敌方 NPC |
| `combat_action` | 战斗中操作 | `{action, target, player_id}` | 战斗 Skill |
| `combat_end` | 战斗结束 | `{result, rewards, player_id}` | 相关任务 |
| `quest_update` | 任务状态变化 | `{quest_id, status, progress}` | 任务文件 |
| `item_acquire` | 获得物品 | `{item_id, player_id}` | 物品文件 |
| `npc_interact` | NPC 主动交互 | `{npc_id, trigger, dialogue}` | NPC 文件 |
| `time_pass` | 时间流逝 | `{amount, new_time}` | 当前剧情 |
| `system_event` | 系统事件 | `{message, severity}` | 无 |

### 2.3 context_hints 设计

`context_hints` 是引擎告诉 Agent "你应该加载哪些记忆文件" 的提示列表。

**设计原则**:
- 引擎只提供**路径提示**，不提供文件内容
- 路径相对于 `workspace/` 目录
- Agent 的 MemoryManager 根据 hints 进行渐进式加载
- 如果 hints 为空或缺失，Agent 使用默认加载策略

**示例**:

```json
// 玩家在铁匠铺和铁匠对话
"context_hints": ["npcs/铁匠", "locations/铁匠铺"]

// 玩家进入新区域
"context_hints": ["locations/暗黑森林", "story/森林_秘密"]

// 战斗事件
"context_hints": ["npcs/哥布林_首领", "skills/combat"]

// 无特定提示（Agent 自行判断）
"context_hints": []
```

### 2.4 game_state 快照

`game_state` 是引擎附加的当前游戏状态快照，用于 Agent 理解上下文：

```json
{
  "game_state": {
    "location": "locations/铁匠铺",
    "time": "第3天 上午",
    "player_hp": 85,
    "player_level": 3,
    "active_quests": ["q_cave", "q_herb"],
    "party_members": []
  }
}
```

**注意**: `game_state` 是**只读参考**，Agent 不直接修改它。Agent 通过 `commands` 请求引擎修改状态。

---

## 3. Agent 响应格式 (Agent → 引擎)

### 3.1 核心响应结构

Agent 返回 JSON 命令流，包含三部分：

```json
{
  "response_id": "resp_20260428_001",
  "event_id": "evt_20260428_001",
  "narrative": "铁匠擦了擦额头上的汗水，将锤子放在铁砧上。他压低声音说道：'那些哥布林...就在北边的洞穴里。我上个月去采矿的时候看到过它们，至少有十几只。'他顿了顿，眼神变得严肃起来：'如果你打算去那里，最好带上足够的药水。'",
  "commands": [
    {
      "intent": "update_npc_relationship",
      "params": {
        "npc_id": "blacksmith",
        "target": "player",
        "change": 5,
        "reason": "玩家主动询问哥布林情报"
      }
    },
    {
      "intent": "offer_quest",
      "params": {
        "quest_id": "q_cave_goblins",
        "title": "清除洞穴哥布林",
        "description": "铁匠请求玩家清除北边洞穴中的哥布林",
        "objective": "击败至少10只哥布林",
        "reward": "铁匠特制长剑 + 200金币"
      }
    },
    {
      "intent": "update_location_detail",
      "params": {
        "location_id": "blacksmith_shop",
        "detail_key": "atmosphere",
        "detail_value": "铁匠正在谈论哥布林的事，气氛变得紧张"
      }
    }
  ],
  "memory_updates": [
    {
      "file": "npcs/铁匠.md",
      "action": "append",
      "content": "\n[第3天 上午] 玩家询问了哥布林的事。铁匠透露北边洞穴有十几只哥布林，建议玩家带足药水。关系+5。"
    },
    {
      "file": "story/哥布林_威胁.md",
      "action": "append",
      "content": "\n[第3天] 铁匠确认了哥布林的存在，地点在北边洞穴，数量约十几只。"
    },
    {
      "file": "session/current.md",
      "action": "append",
      "content": "\n[回合42] 玩家→铁匠：询问哥布林。铁匠提供了情报，触发任务 q_cave_goblins。"
    }
  ]
}
```

### 3.2 narrative 字段

叙事文本，Agent 生成的故事描述。规则：

- **纯文本**，不包含任何指令或标记
- 使用中文自然语言
- 可以包含对话（用引号）
- 长度不限，但建议控制在 200-500 字
- **流式推送**：narrative 在生成过程中通过 SSE 逐 token 推送到前端

### 3.3 commands 字段

游戏指令列表，Agent 请求引擎执行的操作。

**通用字段**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `intent` | string | 是 | 指令意图标识符 |
| `params` | object | 是 | 指令参数 |
| `priority` | int | 否 | 优先级 (默认 0，越大越先执行) |
| `condition` | string | 否 | 执行条件 (引擎端判断) |

**标准 intent 列表**:

| intent | params | 说明 |
|--------|--------|------|
| `update_npc_relationship` | `{npc_id, target, change, reason}` | 修改 NPC 好感度 |
| `update_npc_state` | `{npc_id, field, value}` | 修改 NPC 状态 (hp/location/mood) |
| `offer_quest` | `{quest_id, title, description, objective, reward}` | 发布新任务 |
| `update_quest` | `{quest_id, status, progress}` | 更新任务状态 |
| `give_item` | `{item_id, player_id, quantity}` | 给予玩家物品 |
| `remove_item` | `{item_id, player_id, quantity}` | 移除玩家物品 |
| `update_location` | `{location_id, field, value}` | 修改地点状态 |
| `teleport_player` | `{player_id, location_id}` | 传送玩家 |
| `modify_stat` | `{player_id, stat, change, reason}` | 修改玩家属性 |
| `trigger_event` | `{event_type, params}` | 触发游戏事件 |
| `spawn_npc` | `{npc_id, location_id}` | 生成 NPC |
| `despawn_npc` | `{npc_id}` | 移除 NPC |
| `show_notification` | `{message, type}` | 显示通知 |
| `play_sound` | `{sound_id}` | 播放音效 |
| `no_op` | `{}` | 空操作 (仅叙事，无指令) |

### 3.4 memory_updates 字段

记忆更新请求，Agent 请求更新自己的记忆文件。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | string | 是 | 相对于 workspace/ 的文件路径 |
| `action` | string | 是 | 操作类型: `append` / `create` / `update_frontmatter` |
| `content` | string | 条件 | append/create 时为追加/创建内容 |
| `frontmatter` | object | 条件 | update_frontmatter 时为要更新的 YAML 字段 |

**action 类型说明**:

```json
// 追加内容到 Markdown body 末尾
{"file": "npcs/铁匠.md", "action": "append", "content": "\n[第3天] 新的交互记录..."}

// 创建新文件
{"file": "npcs/流浪商人.md", "action": "create", "content": "---\nname: 流浪商人\n---\n## 初始印象\n..."}

// 更新 YAML Front Matter 字段
{"file": "npcs/铁匠.md", "action": "update_frontmatter", "frontmatter": {"relationship_with_player": 35, "version": 4}}
```

---

## 4. 引擎指令执行结果 (Engine → Agent)

引擎执行 commands 后返回结果：

```json
{
  "response_id": "resp_20260428_001",
  "results": [
    {
      "intent": "update_npc_relationship",
      "status": "success",
      "new_value": 35,
      "state_changes": {
        "file": "npcs/铁匠.md",
        "frontmatter": {
          "relationship_with_player": 35,
          "version": 4,
          "last_modified": "2026-04-28T14:30:05Z"
        }
      }
    },
    {
      "intent": "offer_quest",
      "status": "success",
      "quest_id": "q_cave_goblins",
      "state_changes": {
        "file": "quests/q_cave_goblins.md",
        "frontmatter": {
          "status": "active",
          "version": 1,
          "last_modified": "2026-04-28T14:30:05Z"
        }
      }
    },
    {
      "intent": "update_location_detail",
      "status": "rejected",
      "reason": "location_id 'blacksmith_shop' not found in current world",
      "suggestion": "Use 'locations/铁匠铺' as location_id"
    }
  ]
}
```

### 4.1 状态码

| status | 说明 | Agent 处理 |
|--------|------|-----------|
| `success` | 执行成功 | 无需处理 |
| `rejected` | 引擎拒绝执行 | Agent 应在下一轮生成替代方案 |
| `partial` | 部分成功 | Agent 根据返回的 new_value 调整 |
| `error` | 引擎内部错误 | Agent 记录错误，继续运行 |

### 4.2 引擎拒绝处理

当引擎返回 `rejected` 时，Agent **不自动重试**，而是：

1. 将拒绝信息记录到 `session/current.md`
2. 在下一轮对话中，如果相关，生成替代叙事
3. 例如：引擎拒绝 `teleport_player` → Agent 叙事"你试图传送，但一股神秘力量阻止了你..."

---

## 5. SSE 流式推送协议 (Agent → WorkBench)

### 5.1 连接方式

WorkBench 通过 SSE (Server-Sent Events) 订阅 Agent 的实时输出：

```
GET /api/agent/stream?session_id=xxx
Accept: text/event-stream
```

### 5.2 事件类型

| event | data 格式 | 说明 |
|-------|----------|------|
| `token` | `{"text": "铁"}` | 叙事文本 token (逐字推送) |
| `reasoning` | `{"text": "玩家在询问..."}` | 思考过程 token (deepseek-reasoner) |
| `command` | `{command_object}` | 单条指令 (narrative 完成后发送) |
| `memory_update` | `{update_object}` | 单条记忆更新 |
| `state_change` | `{change_object}` | 引擎状态变化 |
| `turn_start` | `{"event_id": "...", "type": "..."}` | 回合开始 |
| `turn_end` | `{"response_id": "...", "stats": {...}}` | 回合结束 |
| `error` | `{"message": "...", "code": "..."}` | 错误信息 |

### 5.3 SSE 事件流示例

```
event: turn_start
data: {"event_id": "evt_001", "type": "player_action"}

event: reasoning
data: {"text": "玩家在和铁匠对话，需要回忆铁匠之前的信息..."}

event: token
data: {"text": "铁"}

event: token
data: {"text": "匠"}

event: token
data: {"text": "擦了擦额头上的汗水"}

event: token
data: {"text": "，将锤子放在铁砧上。"}

event: token
data: {"text": "他压低声音说道："}

event: token
data: {"text": "'那些哥布林...就在北边的洞穴里。'"}

event: command
data: {"intent": "update_npc_relationship", "params": {"npc_id": "blacksmith", "target": "player", "change": 5}}

event: command
data: {"intent": "offer_quest", "params": {"quest_id": "q_cave_goblins", "title": "清除洞穴哥布林"}}

event: memory_update
data: {"file": "npcs/铁匠.md", "action": "append", "content": "\n[第3天] 玩家询问了哥布林的事..."}

event: state_change
data: {"file": "npcs/铁匠.md", "frontmatter": {"relationship_with_player": 35, "version": 4}}

event: turn_end
data: {"response_id": "resp_001", "stats": {"tokens_used": 1250, "latency_ms": 3200, "commands_sent": 2}}
```

### 5.4 FastAPI SSE 实现代码

```python
from collections.abc import AsyncIterable
from fastapi import FastAPI, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent
from typing import Optional
import asyncio

app = FastAPI()


@app.get("/api/agent/stream", response_class=EventSourceResponse)
async def agent_stream(
    session_id: str = Query(..., description="会话 ID")
) -> AsyncIterable[ServerSentEvent]:
    """
    Agent 实时输出流。

    WorkBench 通过此端点订阅 Agent 的叙事文本、指令和状态变化。
    支持 Last-Event-ID 断线重连。
    """
    event_index = 0

    # 模拟 Agent 处理过程
    yield ServerSentEvent(
        event="turn_start",
        data={"event_id": "evt_001", "type": "player_action"},
        id=str(event_index),
    )
    event_index += 1

    # 模拟流式叙事
    narrative = "铁匠擦了擦额头上的汗水，将锤子放在铁砧上。"
    for char in narrative:
        yield ServerSentEvent(
            event="token",
            data={"text": char},
            id=str(event_index),
        )
        event_index += 1
        await asyncio.sleep(0.05)  # 模拟逐字生成

    # 叙事完成后发送指令
    yield ServerSentEvent(
        event="command",
        data={
            "intent": "update_npc_relationship",
            "params": {"npc_id": "blacksmith", "change": 5}
        },
        id=str(event_index),
    )
    event_index += 1

    # 回合结束统计
    yield ServerSentEvent(
        event="turn_end",
        data={
            "response_id": "resp_001",
            "stats": {
                "tokens_used": 1250,
                "latency_ms": 3200,
                "commands_sent": 1
            }
        },
        id=str(event_index),
    )
```

### 5.5 流式推送时序

```
时间轴 ──────────────────────────────────────────────────►

Agent 收到事件
    │
    ├─► SSE: turn_start
    │
    ├─► [调用 LLM，开始流式生成]
    │       │
    │       ├─► SSE: reasoning (如果有思考模式)
    │       ├─► SSE: token "铁"
    │       ├─► SSE: token "匠"
    │       ├─► SSE: token "擦了擦..."
    │       │   ... (持续推送 narrative tokens)
    │       └─► SSE: token "。"
    │
    ├─► [narrative 生成完毕，解析 commands]
    │       │
    │       ├─► SSE: command (update_npc_relationship)
    │       ├─► SSE: command (offer_quest)
    │       │
    │       ├─► [执行 memory_updates]
    │       │       │
    │       │       ├─► SSE: memory_update (npcs/铁匠.md)
    │       │       └─► SSE: memory_update (story/哥布林_威胁.md)
    │       │
    │       └─► [发送 commands 到引擎]
    │               │
    │               └─► SSE: state_change (引擎返回的状态变化)
    │
    └─► SSE: turn_end (含统计信息)
```

**关键规则**:
1. **先推 narrative，后发 commands** — 玩家先看到故事，再看到游戏状态变化
2. **narrative 逐 token 推送** — 实时打字机效果
3. **commands 批量发送** — narrative 完成后一次性发送所有指令
4. **每个 SSE 事件都有 id** — 支持断线重连

---

## 6. WorkBench API (HTTP REST)

### 6.1 Workspace 文件操作

```python
# 获取 workspace 目录结构
GET /api/workspace/tree?path=npcs
# Response: {"children": [{"name": "铁匠.md", "type": "file", "size": 1024}, ...]}

# 读取文件内容 (YAML + MD 分离返回)
GET /api/workspace/file?path=npcs/铁匠.md
# Response: {"frontmatter": {"name": "铁匠", "hp": 80}, "content": "## 交互记录\n..."}

# 更新文件
PUT /api/workspace/file
# Body: {"path": "npcs/铁匠.md", "frontmatter": {"hp": 75}, "content": "## 交互记录\n...(新内容)"}

# 创建文件
POST /api/workspace/file
# Body: {"path": "npcs/新NPC.md", "content": "---\nname: 新NPC\n---\n## 初始印象\n..."}

# 删除文件
DELETE /api/workspace/file?path=npcs/旧NPC.md
```

### 6.2 Agent 控制端点

```python
# 手动发送事件 (调试用)
POST /api/agent/event
# Body: EngineEvent JSON

# 获取 Agent 当前状态
GET /api/agent/status
# Response: {"state": "idle|processing", "current_turn": 42, "tokens_used": 15000, ...}

# 获取当前上下文 (调试用)
GET /api/agent/context
# Response: {"system_prompt": "...", "loaded_memories": [...], "active_skills": [...]}

# 中断当前回合
POST /api/agent/interrupt

# 重置会话
POST /api/agent/reset
```

### 6.3 Skill 管理端点

```python
# 列出所有 Skill
GET /api/skills
# Response: [{"name": "combat", "description": "...", "source": "builtin|agent", ...}, ...]

# 读取 Skill 内容
GET /api/skills/{skill_name}
# Response: {"frontmatter": {...}, "content": "...", "file_path": "skills/builtin/combat/SKILL.md"}

# 创建/更新 Skill
PUT /api/skills/{skill_name}
# Body: {"content": "---\nname: combat\n---\n## 指令\n..."}

# 删除 Skill (仅限 agent_created)
DELETE /api/skills/{skill_name}
```

---

## 7. DeepSeek API 流式调用协议

### 7.1 流式 + Tool Calls 处理

Agent 调用 DeepSeek API 时，需要处理流式 chunk 中的增量 `tool_calls`。

```python
import json
from openai import OpenAI

client = OpenAI(
    api_key="sk-xxx",
    base_url="https://api.deepseek.com"
)


async def stream_llm_response(messages, tools=None):
    """
    流式调用 DeepSeek API，yield SSE 事件。

    处理三种 chunk 类型:
    1. reasoning_content (思考模式)
    2. content (正式回答)
    3. tool_calls (增量格式，需手动拼接)
    """
    stream = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        stream=True,
    )

    content = ""
    reasoning = ""
    tool_calls_acc = {}  # key: index, value: {id, name, arguments}
    finish_reason = None

    for chunk in stream:
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
        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name or "",
                            "arguments": ""
                        }
                    }
                if tc.function.arguments:
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
            for v in sorted(tool_calls_acc.values(), key=lambda x: int(x["id"].split("_")[-1]))
        ]

    yield {
        "event": "llm_complete",
        "data": {
            "content": content,
            "reasoning_content": reasoning,
            "tool_calls": final_tool_calls,
            "finish_reason": finish_reason
        }
    }
```

### 7.2 V1 踩坑记录 (必须遵守)

| 坑 | 说明 | 解决方案 |
|----|------|---------|
| `reasoning_content` 丢失 | DeepSeek 思考模式返回的字段，标准 OpenAI SDK 不识别 | 用 `getattr(delta, 'reasoning_content', None)` 安全获取 |
| `reasoning_content` 必须回传 | 同一 Turn 内子请求必须包含 reasoning_content | assistant 消息中加 `"reasoning_content": ...` |
| `tool_call_id` 缺失 | tool 消息必须包含 `tool_call_id` | 从 tool_calls[i].id 获取并传入 |
| `tool_calls` 增量格式 | 流式模式下 arguments 分片返回 | 用 dict 按 index 累积拼接 |
| `llm.chat()` 返回 str | V1 的封装返回字符串，不是对象 | V2 直接使用 openai SDK 的原始返回 |

### 7.3 多轮对话消息格式

```python
# 标准 OpenAI 格式，兼容 DeepSeek
messages = [
    # System prompt
    {"role": "system", "content": "你是一个游戏 GM..."},

    # 用户消息 (引擎事件转换而来)
    {"role": "user", "content": "玩家说：和铁匠聊聊哥布林的事"},

    # Assistant 回复 (含 tool_calls)
    {
        "role": "assistant",
        "content": "铁匠擦了擦汗...",
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "update_npc_relationship",
                    "arguments": '{"npc_id": "blacksmith", "change": 5}'
                }
            }
        ]
    },

    # Tool 执行结果 (必须有 tool_call_id)
    {
        "role": "tool",
        "tool_call_id": "call_abc123",
        "content": '{"status": "success", "new_value": 35}'
    },

    # Assistant 最终回复
    {"role": "assistant", "content": "铁匠点了点头，似乎对你的勇气表示赞赏..."},
]
```

---

## 8. 错误处理协议

### 8.1 错误响应格式

```json
{
  "error": {
    "code": "ENGINE_COMMAND_REJECTED",
    "message": "NPC not found: blacksmith",
    "details": {
      "intent": "update_npc_relationship",
      "params": {"npc_id": "blacksmith"}
    },
    "suggestion": "Check available NPC IDs via GET /api/world/npcs"
  }
}
```

### 8.2 错误码表

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|------------|
| `INVALID_EVENT_FORMAT` | 引擎事件格式错误 | 400 |
| `UNKNOWN_EVENT_TYPE` | 未知事件类型 | 400 |
| `CONTEXT_HINTS_NOT_FOUND` | context_hints 指向的文件不存在 | 404 (不阻断，仅警告) |
| `LLM_API_ERROR` | DeepSeek API 调用失败 | 502 |
| `LLM_RESPONSE_PARSE_ERROR` | Agent 输出无法解析为 JSON | 500 |
| `MEMORY_FILE_WRITE_ERROR` | 记忆文件写入失败 | 500 |
| `ENGINE_COMMAND_REJECTED` | 引擎拒绝执行指令 | 200 (在 results 中标记) |
| `ENGINE_NOT_CONNECTED` | 引擎适配器未连接 | 503 |
| `SESSION_NOT_FOUND` | 会话不存在 | 404 |
| `AGENT_BUSY` | Agent 正在处理其他回合 | 429 |

### 8.3 LLM 输出解析容错

Agent 的 LLM 输出可能不是标准 JSON，需要容错处理：

```python
import json
import re


def parse_agent_response(raw_text: str) -> dict:
    """
    解析 Agent 的 LLM 输出为标准 JSON 命令流。

    容错策略:
    1. 直接 JSON 解析
    2. 提取 ```json ... ``` 代码块
    3. 提取 { ... } JSON 对象
    4. 兜底: 将整个文本作为 narrative
    """
    text = raw_text.strip()

    # 策略 1: 直接解析
    try:
        result = json.loads(text)
        if "narrative" in result:
            return normalize_response(result)
    except json.JSONDecodeError:
        pass

    # 策略 2: 提取 ```json ... ``` 代码块
    json_block_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_block_match:
        try:
            result = json.loads(json_block_match.group(1))
            if "narrative" in result:
                return normalize_response(result)
        except json.JSONDecodeError:
            pass

    # 策略 3: 提取最外层 { ... }
    brace_match = re.search(r'\{.*\}', text, re.DOTALL)
    if brace_match:
        try:
            result = json.loads(brace_match.group(0))
            if "narrative" in result:
                return normalize_response(result)
        except json.JSONDecodeError:
            pass

    # 策略 4: 兜底 - 整个文本作为 narrative
    return {
        "narrative": text,
        "commands": [],
        "memory_updates": []
    }


def normalize_response(result: dict) -> dict:
    """确保响应包含所有必需字段"""
    return {
        "narrative": result.get("narrative", ""),
        "commands": result.get("commands", []),
        "memory_updates": result.get("memory_updates", [])
    }
```
