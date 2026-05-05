"""
项目信息工具 — 读取当前项目的结构信息
"""
from pathlib import Path

from foundation.logger import get_logger
from .base import AITool, ToolParameter, ToolResult

logger = get_logger(__name__)


class ReadProjectTool(AITool):
    """读取项目信息"""

    @property
    def name(self) -> str:
        return "read_project"

    @property
    def description(self) -> str:
        return "读取当前项目的结构信息，包括提示词列表、技能列表、图定义和配置。在执行其他操作前应先调用此工具了解项目现状。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return []

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        project_path = project_manager.project_path

        # 收集提示词列表
        prompts = []
        prompts_dir = project_path / "prompts"
        if prompts_dir.exists():
            for f in sorted(prompts_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                preview = content[:200].replace("\n", " ")
                prompts.append({"name": f.stem, "preview": preview})

        # 收集技能列表
        skills = []
        skills_dir = project_path / "skills"
        if skills_dir.exists():
            for skill_dir in sorted(skills_dir.iterdir()):
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        content = skill_file.read_text(encoding="utf-8")
                        name = skill_dir.name
                        preview = content[:150].replace("\n", " ")
                        skills.append({"name": name, "preview": preview})

        # 读取图定义
        graph_data = None
        graph_file = project_path / "graph.json"
        if graph_file.exists():
            import json
            graph_data = json.loads(graph_file.read_text(encoding="utf-8"))

        # 读取配置
        config = project_manager.load_project_config()

        return ToolResult(
            success=True,
            message=f"项目 '{project_manager.current_project.name}' 信息加载完成",
            data={
                "project_name": project_manager.current_project.name,
                "project_path": str(project_path),
                "prompts": prompts,
                "skills": skills,
                "has_graph": graph_data is not None,
                "graph_nodes": len(graph_data.get("nodes", [])) if graph_data else 0,
                "config": config,
            },
        )
