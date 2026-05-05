"""
图定义工具 — 读取和修改 graph.json
"""
import json

from foundation.logger import get_logger
from .base import AITool, ToolParameter, ToolResult

logger = get_logger(__name__)


class ReadGraphTool(AITool):
    """读取图定义"""

    @property
    def name(self) -> str:
        return "read_graph"

    @property
    def description(self) -> str:
        return "读取当前项目的 graph.json 文件，返回节点和边的定义。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return []

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        graph_data = project_manager.load_graph()
        if not graph_data:
            return ToolResult(success=False, message="项目没有 graph.json 文件")

        return ToolResult(
            success=True,
            message=f"图定义加载完成：{len(graph_data.get('nodes', []))} 个节点",
            data=graph_data,
        )


class UpdateGraphTool(AITool):
    """修改图定义"""

    @property
    def name(self) -> str:
        return "update_graph"

    @property
    def description(self) -> str:
        return "修改 graph.json 文件。需要提供完整的图定义 JSON。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter("graph_data", "string", "完整的图定义 JSON 字符串"),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        graph_data_str = kwargs["graph_data"]

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        try:
            graph_data = json.loads(graph_data_str)
        except json.JSONDecodeError as e:
            return ToolResult(success=False, message=f"JSON 解析失败: {e}")

        graph_file = project_manager.project_path / "graph.json"
        old_content = ""
        if graph_file.exists():
            old_content = graph_file.read_text(encoding="utf-8")

        project_manager.save_graph(graph_data)

        new_content = json.dumps(graph_data, indent=2, ensure_ascii=False)
        diff_lines = [f"--- graph.json (旧)", f"+++ graph.json (新)"]
        for line in new_content.split("\n"):
            if line not in old_content:
                diff_lines.append(f"+{line}")
        for line in old_content.split("\n"):
            if line not in new_content:
                diff_lines.append(f"-{line}")

        return ToolResult(
            success=True,
            message=f"图定义已更新：{len(graph_data.get('nodes', []))} 个节点",
            diff="\n".join(diff_lines),
            file_path=str(graph_file),
        )
