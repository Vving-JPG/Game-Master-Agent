# P2-05: Nodes 节点函数

> 模块: `feature.ai.nodes`
> 文件: `2workbench/feature/ai/nodes.py`

---

## 6个节点函数

```python
def node_handle_event(state: AgentState) -> AgentState:
    """处理当前事件，准备上下文"""

def node_build_prompt(state: AgentState) -> AgentState:
    """构建 LLM Prompt"""

def node_llm_reasoning(state: AgentState) -> AgentState:
    """调用 LLM 进行推理"""

def node_parse_output(state: AgentState) -> AgentState:
    """解析 LLM 输出"""

def node_execute_commands(state: AgentState) -> AgentState:
    """执行解析出的命令"""

def node_update_memory(state: AgentState) -> AgentState:
    """更新记忆存储"""
```

---

## 2个路由函数

```python
def route_after_llm(state: AgentState) -> str:
    """
    LLM 推理后的路由
    
    返回: "parse_output" | "execute_commands"
    """
    if state.get("llm_response", {}).get("tool_calls"):
        return "execute_commands"
    return "parse_output"

def route_after_parse(state: AgentState) -> str:
    """
    解析后的路由
    
    返回: "execute_commands" | "update_memory"
    """
    if state.get("parsed_commands"):
        return "execute_commands"
    return "update_memory"
```

---

## 节点实现示例

```python
async def node_llm_reasoning(state: AgentState) -> AgentState:
    """LLM 推理节点"""
    from foundation.llm import model_router
    
    messages = state["messages"]
    
    # 路由选择模型
    client, config = model_router.route(
        content=messages[-1].get("content", "")
    )
    
    # 调用 LLM
    response = await client.chat_async(messages)
    
    # 更新状态
    return {
        **state,
        "llm_response": {
            "content": response.content,
            "tokens": response.tokens,
            "model": response.model,
        }
    }

def node_parse_output(state: AgentState) -> AgentState:
    """解析输出节点"""
    from feature.ai.command_parser import CommandParser
    
    parser = CommandParser()
    llm_output = state["llm_response"]["content"]
    
    result = parser.parse(llm_output)
    
    return {
        **state,
        "parsed_commands": result["commands"],
        "narrative": result["narrative"],
    }
```

---

## 节点事件

每个节点执行时会触发事件：

```python
from feature.ai.events import create_node_event, NODE_STARTED, NODE_COMPLETED

# 节点开始时
event_bus.emit(create_node_event("llm_reasoning", "started"))

# 节点完成时
event_bus.emit(create_node_event(
    "llm_reasoning",
    "completed",
    {"duration_ms": 800}
))
```
