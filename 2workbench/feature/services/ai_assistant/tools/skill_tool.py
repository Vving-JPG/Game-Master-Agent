"""
技能工具 — 创建/修改/列出/删除技能
"""
from pathlib import Path
from datetime import datetime

from foundation.logger import get_logger
from .base import AITool, ToolParameter, ToolResult

logger = get_logger(__name__)


class CreateSkillTool(AITool):
    """创建新技能"""

    @property
    def name(self) -> str:
        return "create_skill"

    @property
    def description(self) -> str:
        return "创建新的技能文件。技能使用 YAML Front Matter + Markdown Body 格式，保存在 skills/{name}/SKILL.md。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter("name", "string", "技能名称（英文，如 trap_detection, lock_picking）"),
            ToolParameter("description", "string", "技能描述"),
            ToolParameter("keywords", "string", "触发关键词，逗号分隔（如：陷阱,检测,感知）"),
            ToolParameter("allowed_tools", "string", "允许使用的工具列表，逗号分隔（如：check_perception,roll_dice）"),
            ToolParameter("content", "string", "技能正文内容（Markdown 格式，描述技能的具体行为和规则）"),
            ToolParameter("triggers", "string", "触发事件类型，逗号分隔（可选）", required=False, default=""),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        name = kwargs["name"]
        description = kwargs["description"]
        keywords = [k.strip() for k in kwargs["keywords"].split(",")]
        allowed_tools = [t.strip() for t in kwargs["allowed_tools"].split(",")]
        content = kwargs["content"]
        triggers = [t.strip() for t in kwargs.get("triggers", "").split(",") if t.strip()]

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        skill_dir = project_manager.project_path / "skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"

        yaml_content = "---\n"
        yaml_content += f"name: {name}\n"
        yaml_content += f"description: {description}\n"
        yaml_content += f"version: 1.0.0\n"
        yaml_content += f"created: {datetime.now().isoformat()}\n"
        yaml_content += f"keywords:\n"
        for kw in keywords:
            yaml_content += f"  - {kw}\n"
        yaml_content += f"allowed-tools:\n"
        for tool in allowed_tools:
            yaml_content += f"  - {tool}\n"
        if triggers:
            yaml_content += f"triggers:\n"
            for trigger in triggers:
                yaml_content += f"  - {trigger}\n"
        yaml_content += "---\n\n"

        full_content = yaml_content + content

        old_content = ""
        if skill_file.exists():
            old_content = skill_file.read_text(encoding="utf-8")

        skill_file.write_text(full_content, encoding="utf-8")

        diff = self._simple_diff(old_content, full_content, str(skill_file))

        return ToolResult(
            success=True,
            message=f"技能 '{name}' 已创建",
            diff=diff,
            file_path=str(skill_file),
            data={"name": name, "keywords": keywords, "allowed_tools": allowed_tools},
        )

    def _simple_diff(self, old: str, new: str, filepath: str) -> str:
        if not old:
            lines = new.split("\n")
            return f"--- /dev/null\n+++ {filepath}\n" + "\n".join(f"+{line}" for line in lines)
        old_lines = old.split("\n")
        new_lines = new.split("\n")
        diff_lines = [f"--- {filepath} (旧)", f"+++ {filepath} (新)"]
        for line in new_lines:
            if line not in old_lines:
                diff_lines.append(f"+{line}")
        for line in old_lines:
            if line not in new_lines:
                diff_lines.append(f"-{line}")
        return "\n".join(diff_lines)


class ListSkillsTool(AITool):
    """列出所有技能"""

    @property
    def name(self) -> str:
        return "list_skills"

    @property
    def description(self) -> str:
        return "列出项目中所有技能的名称和描述。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return []

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        skills_dir = project_manager.project_path / "skills"
        result = []
        if skills_dir.exists():
            for skill_dir in sorted(skills_dir.iterdir()):
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        content = skill_file.read_text(encoding="utf-8")
                        desc = ""
                        for line in content.split("\n"):
                            if line.startswith("description:"):
                                desc = line.split(":", 1)[1].strip()
                                break
                        result.append({"name": skill_dir.name, "description": desc})

        return ToolResult(
            success=True,
            message=f"共 {len(result)} 个技能",
            data={"skills": result},
        )


class EditSkillTool(AITool):
    """修改现有技能"""

    @property
    def name(self) -> str:
        return "edit_skill"

    @property
    def description(self) -> str:
        return "修改现有技能的完整内容。需要提供技能名称和新的完整 SKILL.md 内容。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter("name", "string", "要修改的技能名称"),
            ToolParameter("content", "string", "新的完整 SKILL.md 内容（包含 YAML Front Matter 和正文）"),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        name = kwargs["name"]
        content = kwargs["content"]

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        skill_file = project_manager.project_path / "skills" / name / "SKILL.md"
        if not skill_file.exists():
            return ToolResult(success=False, message=f"技能 '{name}' 不存在")

        old_content = skill_file.read_text(encoding="utf-8")
        skill_file.write_text(content, encoding="utf-8")

        diff = CreateSkillTool()._simple_diff(old_content, content, str(skill_file))

        return ToolResult(
            success=True,
            message=f"技能 '{name}' 已更新",
            diff=diff,
            file_path=str(skill_file),
        )


class DeleteSkillTool(AITool):
    """删除技能"""

    @property
    def name(self) -> str:
        return "delete_skill"

    @property
    def description(self) -> str:
        return "删除指定的技能及其目录。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter("name", "string", "要删除的技能名称"),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager
        import shutil

        name = kwargs["name"]

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        skill_dir = project_manager.project_path / "skills" / name
        if not skill_dir.exists():
            return ToolResult(success=False, message=f"技能 '{name}' 不存在")

        shutil.rmtree(skill_dir)

        return ToolResult(
            success=True,
            message=f"技能 '{name}' 已删除",
            file_path=str(skill_dir),
        )
