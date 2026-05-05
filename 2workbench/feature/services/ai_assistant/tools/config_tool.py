"""
配置工具 — 读取和修改项目配置
"""
from foundation.logger import get_logger
from .base import AITool, ToolParameter, ToolResult

logger = get_logger(__name__)


class ReadConfigTool(AITool):
    """读取项目配置"""

    @property
    def name(self) -> str:
        return "read_config"

    @property
    def description(self) -> str:
        return "读取当前项目的配置信息（模型、温度、最大 token 等）。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return []

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        config = project_manager.load_project_config()

        return ToolResult(
            success=True,
            message="配置加载完成",
            data=config,
        )


class UpdateConfigTool(AITool):
    """修改项目配置"""

    @property
    def name(self) -> str:
        return "update_config"

    @property
    def description(self) -> str:
        return "修改项目配置。提供要修改的配置项和值。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter("updates", "string", "要修改的配置项，JSON 格式（如 {\"temperature\": 0.8, \"max_tokens\": 4096}）"),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager
        import json

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        try:
            updates = json.loads(kwargs["updates"])
        except json.JSONDecodeError as e:
            return ToolResult(success=False, message=f"JSON 解析失败: {e}")

        config = project_manager.load_project_config()
        config.update(updates)
        project_manager.save_project_config(config)

        return ToolResult(
            success=True,
            message=f"配置已更新: {list(updates.keys())}",
            data=updates,
        )
