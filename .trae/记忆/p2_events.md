# P2-01: Events 事件系统

> 模块: `feature.ai.events`
> 文件: `2workbench/feature/ai/events.py`

---

## 事件类型常量

```python
# 生命周期事件
TURN_START = "feature.ai.lifecycle.turn_start"
TURN_END = "feature.ai.lifecycle.turn_end"
AGENT_ERROR = "feature.ai.lifecycle.error"

# 节点执行事件
NODE_STARTED = "feature.ai.node.started"
NODE_COMPLETED = "feature.ai.node.completed"

# LLM 事件
LLM_STREAM_TOKEN = "feature.ai.llm.stream_token"
LLM_TOOL_CALL = "feature.ai.llm.tool_call"

# 命令事件
COMMAND_PARSED = "feature.ai.command.parsed"
COMMAND_EXECUTED = "feature.ai.command.executed"

# 记忆事件
MEMORY_STORED = "feature.ai.memory.stored"
```

---

## 辅助函数

```python
def create_turn_start_event(world_id: str, turn_count: int) -> Event:
    """创建回合开始事件"""

def create_turn_end_event(
    world_id: str,
    turn_count: int,
    narrative: str,
    commands_count: int,
    tokens_used: int,
    latency_ms: int
) -> Event:
    """创建回合结束事件"""

def create_node_event(
    node_name: str,
    status: str,  # "started" | "completed" | "error"
    data: dict | None = None
) -> Event:
    """创建节点执行事件"""

def create_stream_token_event(content: str) -> Event:
    """创建流式 token 事件"""

def create_error_event(error: str, node: str = "") -> Event:
    """创建错误事件"""
```

---

## 使用示例

```python
from feature.ai.events import (
    event_bus, create_turn_start_event,
    TURN_START, NODE_COMPLETED
)

# 发布回合开始事件
event_bus.emit(create_turn_start_event(world_id="1", turn_count=5))

# 订阅节点完成事件
@event_bus.on(NODE_COMPLETED)
def on_node_complete(event):
    node_name = event.get("node_name")
    print(f"节点 {node_name} 执行完成")
```

---

## 事件数据结构

### TurnStartEvent

```python
{
    "type": "feature.ai.lifecycle.turn_start",
    "data": {
        "world_id": "1",
        "turn_count": 5
    },
    "source": "feature.ai.gm_agent"
}
```

### TurnEndEvent

```python
{
    "type": "feature.ai.lifecycle.turn_end",
    "data": {
        "world_id": "1",
        "turn_count": 5,
        "narrative": "你走进了森林...",
        "commands_count": 2,
        "tokens_used": 150,
        "latency_ms": 1200
    }
}
```

### NodeEvent

```python
{
    "type": "feature.ai.node.completed",
    "data": {
        "node_name": "llm_reasoning",
        "status": "completed",
        "duration_ms": 800
    }
}
```
