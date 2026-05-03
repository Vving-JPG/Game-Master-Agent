# P2-06: Graph StateGraph 定义

> 模块: `feature.ai.graph`
> 文件: `2workbench/feature/ai/graph.py`

---

## 图结构

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

---

## 核心函数

```python
def build_gm_graph() -> StateGraph:
    """
    构建 GM Agent StateGraph
    
    Returns:
        编译后的 CompiledGraph
    """

# 全局编译好的图实例
gm_graph = build_gm_graph()
```

---

## 图定义代码

```python
from langgraph.graph import StateGraph, START, END
from core.state import AgentState
from feature.ai.nodes import (
    node_handle_event, node_build_prompt, node_llm_reasoning,
    node_parse_output, node_execute_commands, node_update_memory,
    route_after_llm, route_after_parse
)

def build_gm_graph() -> StateGraph:
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
    
    # 条件路由
    builder.add_conditional_edges(
        "llm_reasoning",
        route_after_llm,
        {
            "parse_output": "parse_output",
            "execute_commands": "execute_commands",
        }
    )
    
    builder.add_conditional_edges(
        "parse_output",
        route_after_parse,
        {
            "execute_commands": "execute_commands",
            "update_memory": "update_memory",
        }
    )
    
    builder.add_edge("execute_commands", "update_memory")
    builder.add_edge("update_memory", END)
    
    return builder.compile()
```

---

## 使用全局图

```python
from feature.ai.graph import gm_graph

# 执行图
result = await gm_graph.ainvoke(initial_state)
```

---

## 可视化图结构

```python
# 获取 Mermaid 图
mermaid_code = gm_graph.get_graph().draw_mermaid()
print(mermaid_code)
```
