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
from foundation.event_bus import event_bus, Event
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

        # === 预处理：按 source 分组边 ===
        normal_edges = []
        conditional_groups: dict[str, dict] = {}  # source -> {"route_func": str, "branches": dict}

        for edge_data in edges:
            source = edge_data["from"]
            target = edge_data["to"]
            condition = edge_data.get("condition", "")

            actual_source = START if source in ("START", "__start__") else source
            actual_target = END if target in ("END", "__end__") else target

            if condition and condition in CONDITION_FUNCTIONS:
                key = str(actual_source)
                if key not in conditional_groups:
                    conditional_groups[key] = {"route_func": condition, "branches": {}}
                conditional_groups[key]["branches"][str(actual_target)] = actual_target
            else:
                normal_edges.append((actual_source, actual_target))

        # === 添加普通边 ===
        for source, target in normal_edges:
            # 跳过已有条件边的 source（避免 add_edge + add_conditional_edges 冲突）
            if str(source) in conditional_groups:
                logger.warning(f"跳过普通边 {source} -> {target}（该节点已有条件边）")
                continue
            graph.add_edge(source, target)
            logger.debug(f"编译边: {source} --> {target}")

        # === 添加条件边（每个 source 只调用一次）===
        for source_key, group in conditional_groups.items():
            route_func = CONDITION_FUNCTIONS.get(group["route_func"])
            if route_func is None:
                logger.warning(f"未知条件路由函数: {group['route_func']}")
                continue

            actual_source = START if source_key == str(START) else source_key
            branches = group["branches"]

            if not branches:
                logger.warning(f"条件边 {source_key} 没有分支目标，跳过")
                continue

            graph.add_conditional_edges(actual_source, route_func, branches)
            logger.debug(f"编译条件边: {source_key} --[{group['route_func']}]--> {list(branches.keys())}")

        # 编译
        compiled = graph.compile()
        node_count = len(node_ids)
        edge_count = len(edges)
        cond_group_count = len(conditional_groups)
        logger.info(f"图编译完成: {node_count} 节点, {len(normal_edges)} 普通边, {cond_group_count} 条件边组")
        return compiled


# 全局单例
graph_compiler = GraphCompiler()


def _on_graph_save_requested(event: Event) -> None:
    """处理图保存请求事件

    监听 ui.graph.save_requested 事件，编译图并发出完成通知。
    """
    graph_data = event.data.get("graph_data", {})
    if not graph_data:
        logger.warning("收到空的图数据，跳过编译")
        return

    try:
        compiled = graph_compiler.compile(graph_data)
        logger.info(f"图编译成功: {len(graph_data.get('nodes', []))} 节点")

        # 发出编译完成事件
        event_bus.emit(Event(type="feature.graph.compiled", data={
            "graph_data": graph_data,
            "compiled": compiled,
            "node_count": len(graph_data.get("nodes", [])),
            "edge_count": len(graph_data.get("edges", [])),
        }))
    except Exception as e:
        logger.error(f"图编译失败: {e}")
        event_bus.emit(Event(type="feature.graph.compile_failed", data={
            "error": str(e),
            "graph_data": graph_data,
        }))


# 注册事件监听
event_bus.subscribe("ui.graph.save_requested", _on_graph_save_requested)
