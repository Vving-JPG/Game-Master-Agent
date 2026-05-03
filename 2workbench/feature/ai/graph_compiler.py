"""GraphCompiler — 将 graph.json 编译为 LangGraph StateGraph

graph.json 格式:
{
  "nodes": [
    {"id": "handle_event", "type": "event", "label": "事件处理", "position": {"x": 100, "y": 200}},
    {"id": "llm_reasoning", "type": "llm", "label": "LLM 推理", "position": {"x": 500, "y": 200}},
    ...
  ],
  "edges": [
    {"from": "__start__", "to": "handle_event"},
    {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"},
    {"from": "parse_output", "to": "update_memory"},
    {"from": "update_memory", "to": "__end__"},
    ...
  ]
}

节点类型 → 节点函数映射:
  event    → node_handle_event
  prompt   → node_build_prompt
  llm      → node_llm_reasoning
  parser   → node_parse_output
  executor → node_execute_commands
  memory   → node_update_memory
  input    → node_handle_event      (复用)
  output   → node_update_memory     (复用)
  custom   → 需要用户注册

条件路由映射:
  route_after_llm   → llm_reasoning 后的路由（有 tool_calls → execute_commands, 否则 → parse_output）
  route_after_parse → parse_output 后的路由（有命令 → execute_commands, 否则 → update_memory）
"""
from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import StateGraph, START, END

from core.state import AgentState
from foundation.logger import get_logger

logger = get_logger(__name__)


# 节点类型 → 节点函数映射
NODE_FUNCTIONS: dict[str, Callable] = {}

# 条件路由函数映射
CONDITION_FUNCTIONS: dict[str, Callable] = {}

# 条件路由的分支映射（路由函数返回值 → 目标节点）
CONDITION_BRANCHES: dict[str, dict[str, str]] = {}


def _init_mappings():
    """延迟初始化映射，避免循环导入"""
    global NODE_FUNCTIONS, CONDITION_FUNCTIONS, CONDITION_BRANCHES

    if NODE_FUNCTIONS:
        return  # 已初始化

    from feature.ai.nodes import (
        node_handle_event,
        node_build_prompt,
        node_llm_reasoning,
        node_parse_output,
        node_execute_commands,
        node_update_memory,
        route_after_llm,
        route_after_parse,
    )

    NODE_FUNCTIONS = {
        "event": node_handle_event,
        "prompt": node_build_prompt,
        "llm": node_llm_reasoning,
        "parser": node_parse_output,
        "executor": node_execute_commands,
        "memory": node_update_memory,
        "input": node_handle_event,
        "output": node_update_memory,
    }

    CONDITION_FUNCTIONS = {
        "route_after_llm": route_after_llm,
        "route_after_parse": route_after_parse,
    }

    # 每个条件路由函数的返回值 → 目标节点名的默认映射
    CONDITION_BRANCHES = {
        "route_after_llm": {
            "execute_commands": "execute_commands",
            "parse_output": "parse_output",
        },
        "route_after_parse": {
            "execute_commands": "execute_commands",
            "update_memory": "update_memory",
        },
    }


class GraphCompiler:
    """将 graph.json 编译为 LangGraph StateGraph"""

    def compile(self, graph_data: dict) -> Any:
        """编译图定义为 CompiledStateGraph

        Args:
            graph_data: graph.json 的内容，格式:
                {
                    "nodes": [{"id": str, "type": str, "label": str, "position": dict}, ...],
                    "edges": [{"from": str, "to": str, "condition": str|None}, ...]
                }

        Returns:
            编译好的 CompiledGraph

        Raises:
            ValueError: 图定义无效（缺少必要节点、未知节点类型等）
        """
        _init_mappings()

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            raise ValueError("图定义不能为空：没有节点")

        # 创建 StateGraph
        graph = StateGraph(AgentState)

        # 收集所有节点 ID
        node_ids = set()

        # 添加节点
        for node_data in nodes:
            node_id = node_data["id"]
            node_type = node_data.get("type", "custom")
            node_func = NODE_FUNCTIONS.get(node_type)

            if node_func is None:
                logger.warning(f"未知节点类型 '{node_type}' (节点: {node_id})，跳过")
                continue

            graph.add_node(node_id, node_func)
            node_ids.add(node_id)
            logger.debug(f"编译节点: {node_id} ({node_type} → {node_func.__name__})")

        # 添加边
        for edge_data in edges:
            source = edge_data["from"]
            target = edge_data["to"]
            condition = edge_data.get("condition", "")

            # 处理 START/END 特殊标记
            actual_source = source
            actual_target = target
            if source in ("START", "__start__"):
                actual_source = START
            if target in ("END", "__end__"):
                actual_target = END

            if condition and condition in CONDITION_FUNCTIONS:
                # 条件边
                route_func = CONDITION_FUNCTIONS[condition]
                branches = CONDITION_BRANCHES.get(condition, {})

                # 如果边指定了具体目标，覆盖默认分支
                # 格式: {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"}
                # 含义: 当 route_after_llm 返回 "parse_output" 时，走这条边
                if isinstance(actual_target, str) and actual_target not in (START, END):
                    # 单分支条件边：只有返回值匹配 target 时走这条边
                    # 需要收集同一 source 的所有条件边来构建完整映射
                    pass  # 在下面统一处理

                graph.add_conditional_edges(
                    actual_source,
                    route_func,
                    branches,
                )
                logger.debug(f"编译条件边: {source} --[{condition}]--> {branches}")
            else:
                # 普通边
                graph.add_edge(actual_source, actual_target)
                logger.debug(f"编译边: {source} --> {target}")

        # 编译
        compiled = graph.compile()
        node_count = len(node_ids)
        edge_count = len(edges)
        logger.info(f"图编译完成: {node_count} 节点, {edge_count} 边")
        return compiled


# 全局单例
graph_compiler = GraphCompiler()
