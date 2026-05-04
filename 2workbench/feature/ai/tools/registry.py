# 2workbench/feature/ai/tools/registry.py
"""工具注册表 — 管理动态注册的工具"""
from __future__ import annotations

from typing import Callable

from langchain_core.tools import tool
from foundation.logger import get_logger

from feature.ai.tools.context import get_tool_context

logger = get_logger(__name__)

# 动态注册的工具存储
_REGISTERED_TOOLS: dict[str, dict] = {}


def register_tool(
    name: str,
    description: str,
    parameters_schema: dict,
    handler: Callable,
):
    """注册一个工具

    Args:
        name: 工具名称
        description: 工具描述（会作为 LLM 的 tool description）
        parameters_schema: JSON Schema 格式的参数定义
        handler: 实际执行函数
    """
    _REGISTERED_TOOLS[name] = {
        "name": name,
        "description": description,
        "parameters_schema": parameters_schema,
        "handler": handler,
    }
    logger.info(f"工具已注册: {name}")


def _create_tool_function(name: str, tool_def: dict):
    """从注册信息动态创建 LangChain Tool"""
    handler = tool_def["handler"]

    # 创建带正确元数据的函数
    func = lambda **kwargs: handler(**kwargs)
    func.__name__ = name
    func.__doc__ = tool_def["description"]

    # 使用 @tool 装饰
    return tool(func)


def get_all_tools() -> list:
    """获取所有已注册的工具（包括内置和动态注册的）

    Returns:
        LangChain Tool 对象列表（用于 LangGraph 执行）
    """
    # 导入内置工具
    from feature.ai.tools import ALL_TOOLS

    tools = list(ALL_TOOLS)
    for name, tool_def in _REGISTERED_TOOLS.items():
        # 动态创建 @tool 装饰的函数
        func = _create_tool_function(name, tool_def)
        tools.append(func)
    return tools


def get_all_tools_info() -> list[dict]:
    """获取所有工具的元数据信息（用于工具管理器显示）

    Returns:
        工具信息字典列表，每个字典包含 name, description 等字段
    """
    from feature.ai.tools import ALL_TOOLS

    tools_info = []

    # 内置工具
    for t in ALL_TOOLS:
        tools_info.append({
            "name": t.name,
            "description": t.description or "",
            "category": "builtin",
        })

    # 动态注册的工具
    for name, tool_def in _REGISTERED_TOOLS.items():
        tools_info.append({
            "name": name,
            "description": tool_def.get("description", ""),
            "category": "custom",
        })

    return tools_info


def get_tools_schema() -> list[dict]:
    """获取所有工具的 OpenAI function calling schema"""
    from langchain_core.utils.function_calling import convert_to_openai_tool
    all_tools = get_all_tools()
    return [convert_to_openai_tool(t) for t in all_tools]
