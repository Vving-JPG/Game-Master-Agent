# Game Master Agent V2 - Code Wiki

> 生成日期: 2026-04-30
> 版本: V2.5 / WorkBench W1-W7 完成

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [核心模块详解](#3-核心模块详解)
4. [数据模型](#4-数据模型)
5. [API接口](#5-api接口)
6. [前端WorkBench](#6-前端workbench)
7. [依赖关系](#7-依赖关系)
8. [运行方式](#8-运行方式)

---

## 1. 项目概述

### 1.1 项目定位

**Game Master Agent V2** 是一个通用游戏驱动 Agent 服务，像 IDE 驱动代码一样驱动游戏。系统采用事件驱动架构，通过 LLM（DeepSeek）实现智能游戏主持人功能。

### 1.2 核心特性

| 特性 | 说明 |
|------|------|
| 事件驱动架构 | Agent 通过事件循环处理引擎输入 |
| 渐进式记忆 | 3层记忆披露（Index → Activation → Execution） |
| Skill 系统 | 基于 SKILL.md 标准的可扩展技能 |
| WorkBench | Vue3 管理端，文件浏览、MD编辑、Agent监控 |
| SSE流式推送 | 实时事件流（token、command、turn_start/end） |

### 1.3 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+ / FastAPI / SQLite / DeepSeek API |
| 前端 | Vue 3 / TypeScript / Naive UI / Vite |
| AI | DeepSeek (OpenAI 兼容接口) |
| 记忆 | python-frontmatter (YAML + Markdown) |
| 异步 | asyncio / AsyncOpenAI |

---

## 2. 整体架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          用户层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   CLI V2     │  │  WorkBench    │  │  第三方引擎   │         │
│  │ (MUD模式)     │  │  (Vue前端)    │  │              │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼─────────────────┼─────────────────┼─────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API 层 (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  /api/agent | /api/workspace | /api/skills | /api/pack   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Agent 核心 (src/agent/)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ GameMaster   │  │ CommandParser│  │ PromptBuilder│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ EventHandler │  │  Workflow    │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      服务层 (src/services/)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ LLMClient    │  │   Cache      │  │ ModelRouter  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    适配层 (src/adapters/)                        │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ EngineAdapter│  │ TextAdapter  │                             │
│  │   (抽象基类) │  │ (MUD适配器)  │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据层                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  SQLite DB   │  │  .md 记忆    │  │   Skills     │          │
│  │   (V1保留)   │  │   (V2新)     │  │   (SKILL.md) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责矩阵

| 模块 | 路径 | 职责 | 依赖 |
|------|------|------|------|
| Agent 核心 | `src/agent/` | 事件处理、LLM调用、命令解析 | memory, skills, adapters, services |
| 记忆系统 | `src/memory/` | .md文件读写、渐进式加载 | frontmatter |
| Skill系统 | `src/skills/` | SKILL.md发现与加载 | frontmatter |
| 适配器 | `src/adapters/` | 引擎接口抽象、MUD适配 | - |
| 服务层 | `src/services/` | LLM调用、缓存、模型路由 | config |
| 数据模型 | `src/models/` | SQLite Repository层 | database |
| API | `src/api/` | FastAPI路由、SSE推送 | agent, memory, skills |
| 前端 | `workbench/` | Vue3管理界面 | Naive UI, Pinia |

### 2.3 数据流

```
玩家输入 → EngineEvent → EventHandler.handle_event()
    ↓
GameMaster.handle_event()
    ├─→ PromptBuilder.build() → 组装完整Prompt
    │       ├─→ System Prompt
    │       ├─→ 相关Skills
    │       ├─→ 记忆上下文
    │       └─→ 游戏状态
    │
    ├─→ LLMClient.stream() → 流式调用DeepSeek
    │
    ├─→ CommandParser.parse() → 4级容错JSON解析
    │       ├─→ narrative (叙述文本)
    │       ├─→ commands (引擎指令)
    │       └─→ memory_updates (记忆更新)
    │
    ├─→ EngineAdapter.send_commands() → 执行指令
    │       └─→ CommandResult (状态变化)
    │
    ├─→ MemoryManager.apply_*() → 更新记忆
    │       ├─→ apply_memory_updates() (Agent侧)
    │       └─→ apply_state_changes() (引擎侧)
    │
    └─→ SSE推送 → turn_start/command/turn_end
```

---

## 3. 核心模块详解

### 3.1 Agent 核心模块 (`src/agent/`)

#### 3.1.1 GameMaster (`game_master.py`)

**类定义**: `GameMaster`

**核心职责**: 事件驱动主循环，协调各组件处理游戏事件

**关键方法**:

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `__init__` | llm_client, memory_manager, skill_loader, engine_adapter, system_prompt_path | - | 初始化所有组件 |
| `handle_event` | event: EngineEvent | dict | 处理单个引擎事件 |
| `reset` | - | - | 重置Agent状态 |
| `pause/resume` | - | - | 暂停/继续工作流 |
| `step_once` | - | - | 单步执行 |

**handle_event 返回格式**:
```python
{
    "response_id": str,           # 响应ID
    "event_id": str,               # 事件ID
    "narrative": str,              # 叙述文本
    "commands": list[dict],        # 引擎指令
    "memory_updates": list[dict],  # 记忆更新
    "command_results": list[dict], # 指令执行结果
    "stats": dict                  # 统计信息
}
```

**执行流程**:
1. 组装Prompt（PromptBuilder.build）
2. 流式调用LLM（LLMClient.stream）
3. 解析输出（CommandParser.parse）
4. 更新记忆（MemoryManager）
5. 发送指令（EngineAdapter.send_commands）
6. 更新历史对话

#### 3.1.2 CommandParser (`command_parser.py`)

**类定义**: `CommandParser`

**核心职责**: 将LLM文本输出解析为标准JSON命令流

**解析策略** (4级容错):
1. 直接JSON解析
2. 提取 ```json ... ``` 代码块
3. 提取 { ... } JSON对象
4. 兜底：整个文本作为narrative

**关键方法**:

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `parse` | raw_text: str | dict | 解析LLM输出 |
| `_try_direct_parse` | text: str | Optional[dict] | 策略1 |
| `_try_json_block` | text: str | Optional[dict] | 策略2 |
| `_try_brace_extract` | text: str | Optional[dict] | 策略3 |

**返回格式**:
```python
{
    "narrative": str,              # 叙述文本
    "commands": list[dict],        # 指令列表
    "memory_updates": list[dict]   # 记忆更新
}
```

#### 3.1.3 PromptBuilder (`prompt_builder.py`)

**类定义**: `PromptBuilder`

**核心职责**: 组装完整的messages列表

**关键方法**:

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `build` | event, history, memory_depth | list[dict] | 组装messages |
| `load_system_prompt` | - | str | 加载system prompt |
| `invalidate_system_prompt_cache` | - | - | 清除缓存 |

**build 返回的 messages 结构**:
```python
[
    {"role": "system", "content": "..."},      # 系统提示+Skills+记忆+状态
    {"role": "user", "content": "..."},        # 历史对话
    {"role": "user", "content": "..."}         # 当前事件
]
```

#### 3.1.4 EventHandler (`event_handler.py`)

**类定义**: `EventHandler`

**核心职责**: 事件分发与SSE推送

**关键方法**:

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `handle_event` | event: EngineEvent | dict | 处理事件并推送SSE |
| `stream_response` | event: EngineEvent | AsyncIterable | 流式处理 |
| `register_sse_callback` | callback | - | 注册SSE回调 |

**SSE事件时序**:
```
turn_start → (reasoning/token) → command → memory_update → turn_end
```

**SSE事件类型**:

| 事件 | data字段 | 说明 |
|------|----------|------|
| turn_start | event_id, type | 回合开始 |
| token | text | 逐token输出 |
| reasoning | text | 思考内容 |
| command | intent, params | 引擎指令 |
| memory_update | file, action, content | 记忆更新 |
| command_rejected | intent, reason | 指令被拒绝 |
| turn_end | response_id, stats | 回合结束 |
| error | message, code | 错误信息 |

#### 3.1.5 Workflow (`workflow.py`)

**类定义**: `WorkflowEngine`, `StepContext`, `StepType`, `ExecutionState`

**核心职责**: YAML定义的工作流执行引擎

**StepType枚举**:
```python
class StepType(str, Enum):
    PROMPT = "prompt"       # 组装Prompt
    LLM_STREAM = "llm_stream"  # LLM流式调用
    PARSE = "parse"         # 解析输出
    BRANCH = "branch"       # 条件分支
    EXECUTE = "execute"     # 执行指令
    MEMORY = "memory"       # 更新记忆
    END = "end"             # 结束
```

**ExecutionState枚举**:
```python
class ExecutionState(str, Enum):
    IDLE = "IDLE"           # 空闲
    RUNNING = "RUNNING"     # 运行中
    PAUSED = "PAUSED"       # 已暂停
    STEP_WAITING = "STEP_WAITING"  # 单步等待
    COMPLETED = "COMPLETED" # 已完成
    FAILED = "FAILED"       # 失败
```

**关键方法**:

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `load_from_yaml` | yaml_path: str | - | 加载YAML定义 |
| `register_handler` | step_type, handler | - | 注册处理器 |
| `run` | context: StepContext | StepContext | 执行工作流 |
| `pause/resume` | - | - | 暂停/继续 |

---

### 3.2 记忆系统 (`src/memory/`)

#### 3.2.1 MemoryManager (`manager.py`)

**类定义**: `MemoryManager`

**核心职责**: Agent记忆管理器，整合文件读写和渐进式加载

**关键方法**:

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `load_context` | context_hints, depth | str | 加载记忆上下文 |
| `load_full_file` | file_path: str | Optional[dict] | 加载完整文件 |
| `apply_state_changes` | state_changes | - | 更新YAML Front Matter |
| `apply_memory_updates` | updates | - | 追加Markdown Body |
| `initialize_workspace` | - | - | 初始化目录结构 |

#### 3.2.2 MemoryLoader (`loader.py`)

**类定义**: `MemoryLoader`

**核心职责**: 渐进式记忆加载（3层披露）

**加载层级**:

| 层级 | 方法 | 内容 | Token估算 |
|------|------|------|----------|
| Index | `load_index` | name, type, tags, version | ~100/file |
| Activation | `load_activation` | 完整YAML + 章节标题 | ~500-2000/file |
| Execution | `load_execution` | 完整文件内容 | ~2000-5000/file |

#### 3.2.3 FileIO (`file_io.py`)

**关键函数**:

| 函数 | 参数 | 说明 |
|------|------|------|
| `atomic_write` | filepath, content | 原子写入，防数据丢失 |
| `update_memory_file` | filepath, frontmatter_updates, append_content | 统一更新接口 |

**文件格式** (YAML Front Matter + Markdown Body):
```markdown
---
name: 酒馆老板
type: npc
relationship_with_player: 50
version: 3
last_modified: 2026-04-30T10:00:00
modified_by: engine
---

## 背景故事

这位老人在酒馆工作多年...

## 交互记录

[回合5] 玩家询问酒馆传闻...
[回合12] 玩家帮助老板找回丢失的钱袋...
```

---

### 3.3 Skill系统 (`src/skills/`)

#### 3.3.1 SkillLoader (`loader.py`)

**类定义**: `SkillLoader`, `SkillMetadata`

**核心职责**: SKILL.md发现与加载

**SkillMetadata结构**:
```python
@dataclass
class SkillMetadata:
    name: str              # 技能名称
    description: str       # 描述
    version: str           # 版本
    tags: list[str]       # 标签
    triggers: list[dict]   # 触发条件
    file_path: str         # 文件路径
    source: str            # 来源 (builtin/agent_created)
```

**关键方法**:

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `discover_all` | - | list[SkillMetadata] | 发现所有Skill |
| `get_relevant_skills` | event_type, user_input, context_hints | list[SkillMetadata] | 匹配相关Skill |
| `load_skill_content` | skill_name | Optional[str] | 完整内容 |
| `load_skill_activation` | skill_name | Optional[str] | 激活层内容 |

**Skill目录结构**:
```
skills/
├── builtin/           # 内置技能
│   ├── combat/
│   │   └── SKILL.md
│   ├── dialogue/
│   │   └── SKILL.md
│   ├── exploration/
│   │   └── SKILL.md
│   ├── narration/
│   │   └── SKILL.md
│   └── quest/
│       └── SKILL.md
└── agent_created/     # Agent自创技能
```

**SKILL.md格式**:
```markdown
---
name: 战斗系统
description: 处理战斗场景的技能
version: 1.0.0
tags: [combat, battle, combat_system]
triggers:
  - event_type: combat_start
    keyword: [攻击, 战斗, 打]
    memory_hint: [combat, battle_history]
allowed-tools: [give_damage, use_skill, show_notification]
---

## 战斗规则

### 伤害计算

基础伤害 = 攻击力 × (1 - 防御减伤比例)

...
```

---

### 3.4 适配器 (`src/adapters/`)

#### 3.4.1 EngineAdapter (`base.py`)

**类定义**: `EngineAdapter` (ABC), `EngineEvent`, `CommandResult`, `ConnectionStatus`

**核心职责**: 引擎适配器抽象基类

**ConnectionStatus枚举**:
```python
class ConnectionStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
```

**EngineEvent结构**:
```python
@dataclass
class EngineEvent:
    event_id: str           # 事件ID
    timestamp: str          # 时间戳
    type: str               # 事件类型
    data: dict              # 事件数据
    context_hints: list[str]  # 上下文提示
    game_state: dict        # 游戏状态
```

**CommandResult结构**:
```python
@dataclass
class CommandResult:
    intent: str                    # 指令意图
    status: str                   # success/rejected/partial/error
    new_value: Optional[any]       # 新值
    state_changes: Optional[dict]  # 状态变化
    reason: Optional[str]          # 原因
    suggestion: Optional[str]      # 建议
```

**抽象方法**:

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `name` | str | 适配器名称 |
| `connection_status` | ConnectionStatus | 连接状态 |
| `connect` | None | 连接 |
| `disconnect` | None | 断开 |
| `send_commands` | list[CommandResult] | 发送指令 |
| `subscribe_events` | None | 订阅事件 |
| `query_state` | dict | 查询状态 |

#### 3.4.2 TextAdapter (`text_adapter.py`)

**类定义**: `TextAdapter` (继承EngineAdapter)

**核心职责**: MUD文字游戏适配器，复用V1的SQLite数据层

**支持的Intent**:

| Intent | 说明 | 参数 |
|--------|------|------|
| update_npc_relationship | 更新NPC好感度 | npc_id, change |
| update_npc_state | 更新NPC状态 | npc_id, field, value |
| offer_quest | 发放任务 | title, description, objective |
| update_quest | 更新任务 | quest_id, status, progress |
| give_item | 给予物品 | name, type, player_id |
| remove_item | 移除物品 | item_id |
| modify_stat | 修改属性 | stat, change |
| teleport_player | 传送玩家 | location_id |
| show_notification | 显示通知 | message |

---

### 3.5 服务层 (`src/services/`)

#### 3.5.1 LLMClient (`llm_client.py`)

**类定义**: `LLMClient`

**核心职责**: DeepSeek API客户端封装（异步）

**关键方法**:

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `chat` | messages, model | str | 普通对话 |
| `chat_with_tools` | messages, tools | Response | 带工具调用 |
| `chat_stream` | messages | AsyncIterable[str] | 流式对话(旧) |
| `stream` | messages, tools, temperature | AsyncIterable[dict] | 流式调用(新) |
| `get_usage_stats` | - | dict | Token统计 |

**stream返回的事件**:
```python
{"event": "reasoning", "data": {"text": "..."}}
{"event": "token", "data": {"text": "..."}}
{"event": "llm_complete", "data": {
    "content": str,
    "reasoning_content": str,
    "tool_calls": list|None,
    "finish_reason": str|None
}}
```

**重试策略**: 3次重试，指数退避 (1s, 2s, 4s...)

---

## 4. 数据模型

### 4.1 数据库Schema (`src/models/schema.sql`)

**表结构概览**:

| 表名 | 主键 | 外键 | 说明 |
|------|------|------|------|
| worlds | id | - | 世界表 |
| locations | id | world_id | 地点表 |
| players | id | world_id, location_id | 玩家表 |
| npcs | id | world_id, location_id | NPC表 |
| items | id | - | 道具模板表 |
| player_items | player_id, item_id | player_id, item_id | 物品栏表 |
| quests | id | world_id, player_id | 任务表 |
| quest_steps | id | quest_id | 任务步骤表 |
| game_logs | id | world_id | 游戏日志表 |
| npc_memories | id | npc_id | NPC记忆表 |
| game_messages | id | world_id | 对话历史表 |
| prompt_versions | id | - | Prompt版本表 |
| llm_calls | id | world_id | LLM调用记录表 |

**players表字段**:
```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    world_id INTEGER REFERENCES worlds(id),
    name TEXT NOT NULL,
    hp INTEGER DEFAULT 100,
    max_hp INTEGER DEFAULT 100,
    mp INTEGER DEFAULT 50,
    max_mp INTEGER DEFAULT 50,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    gold INTEGER DEFAULT 0,
    location_id INTEGER REFERENCES locations(id)
);
```

### 4.2 Repository层 (`src/models/`)

| 文件 | 职责 |
|------|------|
| `world_repo.py` | 世界数据操作 |
| `player_repo.py` | 玩家数据操作 |
| `npc_repo.py` | NPC数据操作 |
| `location_repo.py` | 地点数据操作 |
| `item_repo.py` | 道具数据操作 |
| `quest_repo.py` | 任务数据操作 |
| `log_repo.py` | 日志数据操作 |
| `memory_repo.py` | 记忆数据操作 |
| `metrics_repo.py` | 指标数据操作 |
| `prompt_repo.py` | Prompt版本管理 |

---

## 5. API接口

### 5.1 API入口 (`src/api/app.py`)

**路由注册**:
```python
# 世界管理
app.include_router(worlds_router)          # /api/worlds

# 玩家
app.include_router(player_router)           # /api/player

# V2路由
app.include_router(workspace_router)         # /api/workspace
app.include_router(skills_router)            # /api/skills
app.include_router(agent_router)              # /api/agent
app.include_router(sse_router)                # /api/sse
app.include_router(pack_router)               # /api/pack

# 管理端路由
app.include_router(admin_prompts_router)     # /admin/prompts
app.include_router(admin_monitor_router)     # /admin/monitor
app.include_router(admin_data_router)        # /admin/data
app.include_router(admin_logs_router)        # /admin/logs
app.include_router(admin_control_router)     # /admin/control
```

### 5.2 核心API端点

#### Agent API (`/api/agent`)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /event | 发送引擎事件 |
| GET | /status | 获取Agent状态 |
| GET | /context | 获取当前上下文 |
| POST | /interrupt | 中断当前回合 |
| POST | /reset | 重置会话 |
| POST | /control | 控制执行 (pause/resume/step) |
| GET | /workflow | 获取工作流定义 |
| POST | /inject | 注入指令 |

#### Workspace API (`/api/workspace`)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /tree | 获取文件树 |
| GET | /read | 读取文件 |
| POST | /write | 写入文件 |
| POST | /delete | 删除文件 |
| GET | /index | 获取索引 |

#### Skills API (`/api/skills`)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /list | 列出所有Skill |
| GET | /{name} | 获取Skill详情 |
| GET | /{name}/content | 获取Skill内容 |

#### SSE API (`/api/sse`)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /stream | SSE事件流 |

---

## 6. 前端WorkBench

### 6.1 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5.32 | 框架 |
| TypeScript | 6.0.2 | 类型系统 |
| Vite | 8.0.10 | 构建工具 |
| Naive UI | 2.44.1 | UI组件库 |
| Pinia | 3.0.4 | 状态管理 |
| md-editor-v3 | 6.5.0 | Markdown编辑器 |
| @vue-flow/core | 1.48.2 | 流程图编辑 |
| axios | 1.15.2 | HTTP客户端 |

### 6.2 项目结构

```
workbench/
├── src/
│   ├── App.vue                 # 根组件
│   ├── main.ts                 # 入口
│   ├── api/                    # API客户端
│   │   ├── agent.ts
│   │   ├── resources.ts
│   │   └── workspace.ts
│   ├── components/             # 组件
│   │   ├── AgentStatus.vue     # Agent状态面板
│   │   ├── BottomConsole.vue   # 底部控制台
│   │   ├── ChatDebug.vue       # 对话调试
│   │   ├── EditorRouter.vue    # 编辑器路由
│   │   ├── FileTree.vue        # 文件树
│   │   ├── LeftPanel.vue       # 左侧资源导航
│   │   ├── MainEditor.vue      # 主编辑器
│   │   ├── ResourceTree.vue    # 资源树
│   │   ├── RightPanel.vue      # 右侧辅助面板
│   │   ├── SSEEventLog.vue     # SSE事件日志
│   │   ├── TopBar.vue          # 顶部栏
│   │   └── editors/            # 编辑器组件
│   │       ├── KeyValueEditor.vue
│   │       ├── MdEditor.vue
│   │       ├── RuntimeViewer.vue
│   │       ├── SkillEditor.vue
│   │       ├── ToolViewer.vue
│   │       ├── WorkflowEditor.vue
│   │       └── YamlEditor.vue
│   └── stores/                 # Pinia状态
│       ├── app.ts
│       └── index.ts
├── package.json
├── vite.config.ts
└── tsconfig.json
```

### 6.3 布局结构

```
┌────────────────────────────────────────────────────────────────┐
│ TopBar (48px)                                                  │
├──────────────┬────────────────────────────────────────────────┤
│              │                                                │
│  LeftPanel   │              MainEditor                         │
│   (260px)    │           (多态编辑器)                          │
│              │                                                │
│  - Prompts   ├────────────────────────────────────────────────┤
│  - Memory    │                                                │
│  - Config    │  RightPanel (360px)                            │
│  - Tools     │  - AgentStatus                                 │
│  - Workflow  │  - SSEEventLog                                 │
│  - Runtime   │  - ChatDebug                                   │
│              │                                                │
├──────────────┴────────────────────────────────────────────────┤
│ BottomConsole (200px)                                          │
│ - SSE事件流 / 控制台输出                                        │
└────────────────────────────────────────────────────────────────┘
```

### 6.4 全局状态 (`stores/app.ts`)

```typescript
export interface TurnRecord {
  id: number
  status: 'completed' | 'failed' | 'paused' | 'current'
  narrative: string
  commands: Array<{ intent: string; status: string }>
  tokens: number
  latency: number
  timestamp: string
}

// 状态定义
interface AppState {
  executionState: ExecutionState  // 'IDLE' | 'RUNNING' | 'PAUSED' | 'STEP_WAITING'
  currentTurn: number
  totalTokens: number
  currentLatency: number
  selectedModel: string
  temperature: number
  maxTokens: number
  selectedResource: ResourceNode | null
  expandedKeys: string[]
  turnHistory: TurnRecord[]
  sseEvents: Array<{ type: string; data: any; time: string }>
}
```

---

## 7. 依赖关系

### 7.1 Python依赖

| 包 | 版本 | 用途 |
|------|------|------|
| fastapi | >=0.136.1 | Web框架 |
| httpx | >=0.28.1 | HTTP客户端 |
| openai | >=2.32.0 | OpenAI兼容接口 |
| pydantic | >=2.13.3 | 数据验证 |
| pydantic-settings | >=2.14.0 | 配置管理 |
| pytest | >=9.0.3 | 测试框架 |
| pytest-asyncio | >=1.3.0 | 异步测试 |
| python-frontmatter | >=1.1.0 | YAML+MD解析 |
| python-multipart | >=0.0.20 | 文件上传 |
| tenacity | >=9.1.4 | 重试机制 |
| uvicorn | >=0.46.0 | ASGI服务器 |
| websockets | >=16.0 | WebSocket支持 |

### 7.2 组件依赖图

```
LLMClient
    │
    ├── Config (settings)
    │       └── .env (DEEPSEEK_API_KEY)
    │
    └── AsyncOpenAI

GameMaster
    ├── LLMClient
    ├── MemoryManager
    │       ├── MemoryLoader
    │       │       └── frontmatter
    │       └── FileIO
    │               └── frontmatter
    ├── SkillLoader
    │       └── frontmatter
    ├── CommandParser
    ├── PromptBuilder
    │       ├── MemoryLoader
    │       └── SkillLoader
    ├── EventHandler
    │       └── SSE Callbacks
    └── EngineAdapter
            └── TextAdapter (V1数据层)
                    ├── WorldService
                    ├── PlayerService
                    ├── NPCService
                    ├── ItemService
                    └── QuestService

FastAPI App
    ├── AgentRouter
    │       └── GameMaster, EventHandler
    ├── WorkspaceRouter
    │       └── MemoryManager
    ├── SkillsRouter
    │       └── SkillLoader
    ├── SSERouter
    │       └── EventHandler
    └── SSE ConnectionManager
```

---

## 8. 运行方式

### 8.1 环境配置

创建 `.env` 文件:
```bash
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

### 8.2 安装依赖

```bash
uv sync
```

### 8.3 运行模式

#### 8.3.1 CLI MUD模式

```bash
uv run python src/cli_v2.py
```

交互命令:
- `quit/exit/q` - 退出
- `status` - 查看状态
- `help` - 帮助
- 其他输入 - 作为玩家操作

#### 8.3.2 API服务

```bash
uvicorn src.api.app:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看API文档

#### 8.3.3 WorkBench前端

```bash
# 终端1: 启动后端
uvicorn src.api.app:app --reload --port 8000

# 终端2: 启动前端
cd workbench
npm install
npm run dev
```

访问 http://localhost:5173

### 8.4 测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行特定模块
uv run pytest tests/test_memory/ -v
uv run pytest tests/test_skills/ -v
uv run pytest tests/test_agent/ -v
uv run pytest tests/test_api/ -v
uv run pytest tests/test_integration/ -v
```

---

## 附录

### A. 关键文件索引

| 功能 | 文件路径 |
|------|----------|
| Agent主循环 | `src/agent/game_master.py` |
| 命令解析 | `src/agent/command_parser.py` |
| Prompt组装 | `src/agent/prompt_builder.py` |
| 事件处理 | `src/agent/event_handler.py` |
| 工作流引擎 | `src/agent/workflow.py` |
| 记忆管理 | `src/memory/manager.py` |
| 渐进加载 | `src/memory/loader.py` |
| 文件IO | `src/memory/file_io.py` |
| Skill加载 | `src/skills/loader.py` |
| LLM调用 | `src/services/llm_client.py` |
| API入口 | `src/api/app.py` |
| 数据库Schema | `src/models/schema.sql` |
| 前端入口 | `workbench/src/App.vue` |
| 前端状态 | `workbench/src/stores/app.ts` |

### B. 配置文件

| 文件 | 用途 |
|------|------|
| `.env.template` | 环境变量模板 |
| `pyproject.toml` | Python项目配置 |
| `workbench/package.json` | 前端依赖 |
| `workflow/main_loop.yaml` | 默认工作流定义 |

### C. 文档文件

| 文件 | 说明 |
|------|------|
| `README.md` | 项目说明 |
| `docs/architecture.md` | 架构设计文档 |
| `docs/api.md` | API文档 |
| `docs/api_design.md` | API设计文档 |
| `docs/contributing.md` | 贡献指南 |
| `.trae/记忆/*.md` | 开发记忆文件 |

---

*本文档由代码分析自动生成，如有疑问请参考源码或开发记忆文件*
