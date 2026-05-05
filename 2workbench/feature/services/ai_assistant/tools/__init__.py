from .base import AITool, ToolParameter, ToolResult
from .registry import ToolRegistry, tool_registry

# 导入所有工具
from .project_tool import ReadProjectTool
from .prompt_tool import CreatePromptTool, EditPromptTool, ListPromptsTool, DeletePromptTool
from .skill_tool import CreateSkillTool, EditSkillTool, ListSkillsTool, DeleteSkillTool
from .graph_tool import ReadGraphTool, UpdateGraphTool
from .config_tool import ReadConfigTool, UpdateConfigTool
from .test_tool import TestPromptTool


def register_all_tools():
    """注册所有 AI 助手工具"""
    tools = [
        ReadProjectTool(),
        CreatePromptTool(),
        EditPromptTool(),
        ListPromptsTool(),
        DeletePromptTool(),
        CreateSkillTool(),
        EditSkillTool(),
        ListSkillsTool(),
        DeleteSkillTool(),
        ReadGraphTool(),
        UpdateGraphTool(),
        ReadConfigTool(),
        UpdateConfigTool(),
        TestPromptTool(),
    ]
    for tool in tools:
        tool_registry.register(tool)
    return tool_registry


__all__ = [
    "AITool", "ToolParameter", "ToolResult",
    "ToolRegistry", "tool_registry",
    "register_all_tools",
]
