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
