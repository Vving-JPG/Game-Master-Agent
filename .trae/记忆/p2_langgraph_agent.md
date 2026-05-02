# P2: LangGraph Agent 核心 — 记忆文档

> 本文件记录 P2 阶段 LangGraph Agent 核心的实现细节。
> **状态**: ✅ 已完成
> **日期**: 2026-05-01
> **依赖**: P0 Foundation 层 + P1 Core 层

---

## 1. 概述

### 1.1 目标
用 LangGraph StateGraph 替换原有的 Agent 核心：
- `_legacy/bridge/agent_bridge.py` 的模拟工作流
- `1agent_core/src/game_master.py` 的 6 步流水线

### 1.2 核心概念
```
┌─────────────────────────────────────────────────────────────┐
│  StateGraph: 事件驱动的节点图                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ handle_event│───▶│ build_prompt│───▶│llm_reasoning│     │
│  └─────────────┘    └─────────────┘    └──────┬──────┘     │
│                                               │            │
│                    ┌──────────────────────────┘            │
│                    ▼                                       │
│              ┌───────────┐    ┌─────────────┐             │
│              │parse_output│───▶│execute_cmds │             │
│              └───────────┘    └──────┬──────┘             │
│                                      │                     │
│                    ┌─────────────────┘                     │
│                    ▼                                       │
│              ┌─────────────┐    ┌─────────┐               │
│              │update_memory│───▶│   END   │               │
│              └─────────────┘    └─────────┘               │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 文件结构

```
2workbench/feature/ai/
├── __init__.py              # 统一导出接口
├── events.py                # 事件定义与 EventBus 集成
├── command_parser.py        # 4级容错命令解析器
├── prompt_builder.py        # Prompt 组装器
├── skill_loader.py          # Skill 评分匹配与加载
├── tools.py                 # 9个 LangGraph 工具
├── nodes.py                 # 6个节点函数 + 2个路由函数
├── graph.py                 # StateGraph 定义与编译
└── gm_agent.py              # GM Agent 门面（对外接口）
```

---

## 3. 核心组件

### 3.1 事件系统 (events.py)

**事件类型常量**:
```python
# 生命周期
TURN_START = "feature.ai.lifecycle.turn_start"
TURN_END = "feature.ai.lifecycle.turn_end"
AGENT_ERROR = "feature.ai.lifecycle.error"

# 节点执行
NODE_STARTED = "feature.ai.node.started"
NODE_COMPLETED = "feature.ai.node.completed"

# LLM
LLM_STREAM_TOKEN = "feature.ai.llm.stream_token"
LLM_TOOL_CALL = "feature.ai.llm.tool_call"

# 命令
COMMAND_PARSED = "feature.ai.command.parsed"
COMMAND_EXECUTED = "feature.ai.command.executed"

# 记忆
MEMORY_STORED = "feature.ai.memory.stored"
```

**辅助函数**:
```python
create_turn_start_event(world_id, turn_count)
create_turn_end_event(world_id, turn_count, narrative, ...)
create_node_event(node_name, status, data)
create_stream_token_event(content)
create_error_event(error, node)
```

### 3.2 命令解析器 (command_parser.py)

**4级容错策略**:
1. 直接 JSON 解析
2. 提取 ```json ... ``` 代码块
3. 提取最外层 `{ ... }`
4. 兜底：整个文本作为 narrative

**数据结构**:
```python
@dataclass
class ParsedCommand:
    intent: str
    params: dict[str, Any]

@dataclass
class ParsedOutput:
    narrative: str
    commands: list[ParsedCommand]
    memory_updates: list[dict]
    raw_text: str
    parse_method: str  # "direct_json" | "json_block" | "outer_braces" | "fallback"
```

**使用**:
```python
from feature.ai.command_parser import parse_llm_output

parsed = parse_llm_output(llm_output_text)
print(parsed.narrative)
for cmd in parsed.commands:
    print(cmd.intent, cmd.params)
```

### 3.3 Prompt 组装器 (prompt_builder.py)

**组装结构**:
```
[system] 基础 system prompt + Skills + 记忆上下文 + 游戏状态
[user]   历史对话 N 轮
[user]   当前事件
```

**使用**:
```python
from feature.ai.prompt_builder import PromptBuilder
from core.state import create_initial_state

builder = PromptBuilder()
state = create_initial_state(world_id='1', player_name='冒险者')

messages = builder.build(
    system_prompt='你是游戏主持人...',
    state=state,
    event_text='玩家说: 我要探索幽暗森林',
    skill_contents=['## 探索规则...'],
    memory_context='之前在宁静村...',
)
```

### 3.4 Skill 加载器 (skill_loader.py)

**Skill 文件格式** (SKILL.md):
```yaml
---
name: exploration
description: 探索规则
version: 1.0.0
tags: [exploration, demo]
keywords: [探索, 调查, 搜索]
triggers:
  - event_type: player_move
allowed-tools: [roll_dice, move_to_location]
---

# 探索规则

当玩家探索时...
```

**评分规则**:
- event_type 匹配: +10 分
- keyword 匹配: +5 分/关键词
- context_hint 匹配: +3 分/提示
- triggers 为空（始终加载）: +100 分

**使用**:
```python
from feature.ai.skill_loader import SkillLoader

loader = SkillLoader(skills_dir='./skills')
loader.discover_all()

relevant = loader.get_relevant_skills(
    event_type='player_move',
    user_input='我要探索森林',
    max_skills=5
)

for skill in relevant:
    content = loader.load_activation(skill.metadata.name)
    print(content)
```

### 3.5 工具系统 (tools.py)

**9个工具**:
| 工具名 | 功能 |
|--------|------|
| `roll_dice` | 掷骰子判定 |
| `update_player_stat` | 更新玩家属性 |
| `give_item` | 给予道具 |
| `remove_item` | 移除道具 |
| `move_to_location` | 移动玩家 |
| `update_npc_relationship` | 修改 NPC 关系 |
| `update_quest_status` | 更新任务状态 |
| `store_memory` | 存储记忆 |
| `check_quest_prerequisites` | 检查任务前置条件 |

**使用**:
```python
from feature.ai.tools import roll_dice, give_item, get_tools_schema

# 直接调用
result = roll_dice.invoke({'sides': 20, 'count': 1})

# 获取 schema（用于 LLM function calling）
schemas = get_tools_schema()
```

### 3.6 节点函数 (nodes.py)

**6个核心节点**:

| 节点 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `node_handle_event` | 接收事件，格式化文本 | `current_event` | `turn_count`, `_formatted_text` |
| `node_build_prompt` | 组装 Prompt | `current_event`, `player`, ... | `prompt_messages` |
| `node_llm_reasoning` | 流式调用 LLM | `prompt_messages` | `llm_response` |
| `node_parse_output` | 解析 LLM 输出 | `llm_response` | `parsed_commands`, `memory_updates` |
| `node_execute_commands` | 执行命令 | `parsed_commands` | `command_results` |
| `node_update_memory` | 更新记忆 | `memory_updates` | - |

**2个路由函数**:
```python
def route_after_llm(state) -> str:
    """LLM 后路由: tool_calls -> execute_commands, 否则 -> parse_output"""

def route_after_parse(state) -> str:
    """解析后路由: 有命令 -> execute_commands, 否则 -> update_memory"""
```

**System Prompt**:
节点文件内置完整的 System Prompt，包含：
- GM 职责说明（叙事、裁判、角色扮演、推进剧情）
- 输出格式要求（JSON 结构）
- 可用命令列表
- 风格要求

### 3.7 StateGraph (graph.py)

**图结构**:
```
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
```

**使用**:
```python
from feature.ai.graph import gm_graph, build_gm_graph

# 使用全局实例
result = await gm_graph.ainvoke(initial_state)

# 或重新构建
graph = build_gm_graph()
result = await graph.ainvoke(initial_state)
```

### 3.8 GM Agent 门面 (gm_agent.py)

**功能**:
- 对外统一接口
- 加载游戏状态（World/Player/NPC）
- 管理 Agent 生命周期
- 通过 EventBus 通知上层

**使用**:
```python
from feature.ai import GMAgent

# 创建 Agent
agent = GMAgent(world_id=1)

# 同步执行（自动检测事件循环）
result = agent.run_sync("玩家说: 我要探索幽暗森林")

# 异步执行
result = await agent.run("玩家说: 我要探索幽暗森林")

# 获取状态快照
snapshot = agent.get_state_snapshot()
# {
#     "world_id": 1,
#     "turn_count": 5,
#     "execution_state": "idle",
#     "player": {...},
#     "location": {...},
#     "npcs": [...]
# }
```

---

## 4. 集成使用

### 4.1 完整示例
```python
import asyncio
from feature.ai import GMAgent
from foundation.event_bus import event_bus

# 订阅事件
def on_token(event):
    print(event.data['content'], end='', flush=True)

event_bus.subscribe("feature.ai.llm.stream_token", on_token)

# 运行 Agent
async def main():
    agent = GMAgent(world_id=1)
    result = await agent.run("玩家说: 你好")
    print(f"\n叙事: {result['narrative']}")
    print(f"命令: {result['commands']}")
    print(f"Token: {result['tokens_used']}")
    print(f"延迟: {result['latency_ms']}ms")

asyncio.run(main())
```

### 4.2 在 PyQt6 中使用
```python
from PyQt6.QtWidgets import QApplication
from feature.ai import GMAgent
import qasync

class GameWindow:
    def __init__(self):
        self.agent = GMAgent(world_id=1)
        
    async def on_player_input(self, text):
        result = await self.agent.run(text)
        self.display_narrative(result['narrative'])
        
    def on_submit(self):
        text = self.input_box.text()
        qasync.ensure_future(self.on_player_input(text))
```

---

## 5. 依赖关系

### 5.1 内部依赖
```
feature.ai
├── foundation.event_bus
├── foundation.llm
│   ├── model_router
│   └── BaseLLMClient
├── foundation.logger
├── core.state
│   └── AgentState
└── core.models
    ├── WorldRepo, PlayerRepo, NPCRepo
    └── MemoryRepo
```

### 5.2 外部依赖
```
langgraph
langchain-core
```

---

## 6. 注意事项

### 6.1 异步执行
- LangGraph 的 `ainvoke` 是异步的
- `GMAgent.run_sync()` 自动检测事件循环
- 在 Qt 环境中使用 `qasync`

### 6.2 事件流
- Agent 执行过程中通过 EventBus 发出大量事件
- 上层通过订阅事件来更新 UI
- 关键事件：`TURN_START`, `TURN_END`, `LLM_STREAM_TOKEN`

### 6.3 LLM API Key
- 需要配置至少一个 LLM API Key
- 在 `.env` 中配置：`DEEPSEEK_API_KEY=sk-xxx`

### 6.4 数据库
- 自动从数据库加载 World/Player/NPC 状态
- 记忆更新自动写入数据库
- 数据库表不存在时会报错（不影响代码结构）

---

## 7. 后续 Phase 衔接

### 7.1 P3: Feature Services
- 将各业务系统封装为 Feature 模块
- Battle/Dialogue/Quest/Item/Exploration/Narration
- 通过 EventBus 与 AI 层通信

### 7.2 P4: GUI Editor
- Presentation 层订阅 EventBus 事件
- 实时更新 UI（流式 token、状态变化等）
- 使用 `GMAgent` 作为统一入口

---

## 8. 测试

### 8.1 单元测试
```bash
cd 2workbench

# 测试 CommandParser
python -c "from feature.ai.command_parser import parse_llm_output; ..."

# 测试 PromptBuilder
python -c "from feature.ai.prompt_builder import PromptBuilder; ..."

# 测试 SkillLoader
python -c "from feature.ai.skill_loader import SkillLoader; ..."

# 测试 Tools
python -c "from feature.ai.tools import roll_dice; ..."
```

### 8.2 集成测试
```bash
# 验证所有模块导入
python -c "from feature.ai import GMAgent, gm_graph; ..."

# 验证图结构
python -c "from feature.ai.graph import build_gm_graph; ..."
```

---

## 9. 变更记录

| 日期 | 变更 | 说明 |
|------|------|------|
| 2026-05-01 | 创建 | P2 LangGraph Agent 核心初始实现 |

---

*文档结束*
