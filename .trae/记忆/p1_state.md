# P1-03: LangGraph State

> 模块: `core.state`
> 文件: `2workbench/core/state.py`

---

## AgentState 类型定义

```python
AgentState = TypedDict('AgentState', {
    # 基础信息
    'world_id': str,
    'turn_count': int,
    'execution_state': str,  # "idle" | "running" | "error"
    
    # 游戏状态
    'player': dict,
    'current_location': dict,
    'active_npcs': list[dict],
    'inventory': list[dict],
    'active_quests': list[dict],
    
    # 当前事件
    'current_event': dict,  # {type, data, context_hints}
    
    # LLM 相关
    'messages': list[dict],  # 对话历史
    'llm_response': dict,    # {content, tokens, model}
    
    # 命令处理
    'parsed_commands': list[dict],
    'command_results': list[dict],
    
    # 记忆
    'context_memories': list[str],
    'new_memories': list[dict],
})
```

---

## 创建初始状态

```python
from core.state import create_initial_state

state = create_initial_state(world_id="1")
# 返回包含默认值的 AgentState
```

---

## 状态流转

```
START
  ↓
handle_event ──▶ 设置 current_event
  ↓
build_prompt ──▶ 组装 messages
  ↓
llm_reasoning ──▶ 设置 llm_response
  ↓
parse_output ──▶ 设置 parsed_commands
  ↓
execute_commands ──▶ 设置 command_results
  ↓
update_memory ──▶ 设置 new_memories
  ↓
END
```

---

## 状态更新示例

```python
# 节点函数接收并返回状态
def node_handle_event(state: AgentState) -> AgentState:
    event = state['current_event']
    # 处理事件...
    return {
        **state,
        'execution_state': 'running',
        'turn_count': state['turn_count'] + 1,
    }
```

---

## 状态持久化

关键状态字段会保存到数据库：
- player → players 表
- active_quests → quests 表
- inventory → player_items 表
- new_memories → memories 表
