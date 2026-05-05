"""
工具注册中心
管理所有 AI 工具的注册、查询和分发
"""
from typing import Any

from foundation.logger import get_logger
from .base import AITool, ToolResult

logger = get_logger(__name__)


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: dict[str, AITool] = {}

    def register(self, tool: AITool):
        """注册工具"""
        if tool.name in self._tools:
            logger.warning(f"工具 '{tool.name}' 已存在，将被覆盖")
        self._tools[tool.name] = tool
        logger.debug(f"注册工具: {tool.name}")

    def get(self, name: str) -> AITool | None:
        """获取工具"""
        return self._tools.get(name)

    def get_all(self) -> dict[str, AITool]:
        """获取所有工具"""
        return dict(self._tools)

    def get_names(self) -> list[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())

    def to_llm_tools(self) -> list[dict]:
        """生成 LLM function calling 格式的工具列表"""
        return [tool.to_llm_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """执行指定工具"""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                message=f"未知工具: {tool_name}",
            )

        logger.info(f"执行工具: {tool_name}({kwargs})")
        try:
            result = await tool.execute(**kwargs)
            logger.info(f"工具执行完成: {tool_name} -> success={result.success}")
            return result
        except Exception as e:
            logger.error(f"工具执行失败: {tool_name} -> {e}")
            return ToolResult(
                success=False,
                message=f"工具执行异常: {e}",
            )


# 全局单例
tool_registry = ToolRegistry()
