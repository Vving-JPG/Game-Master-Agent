"""
提示词工具 — 创建/修改/列出/删除提示词
"""
from pathlib import Path
from datetime import datetime

from foundation.logger import get_logger
from .base import AITool, ToolParameter, ToolResult

logger = get_logger(__name__)


class CreatePromptTool(AITool):
    """创建新提示词"""

    @property
    def name(self) -> str:
        return "create_prompt"

    @property
    def description(self) -> str:
        return "创建新的提示词文件。提示词保存为 .md 格式，包含 YAML Front Matter（category, created）和 Markdown 正文。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter("name", "string", "提示词名称（英文，如 system, user_template, dungeon_exploration）"),
            ToolParameter("content", "string", "提示词正文内容（Markdown 格式）"),
            ToolParameter("category", "string", "提示词分类", required=False, default="scene",
                          enum=["system", "scene", "npc", "item", "quest", "rule", "custom"]),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        name = kwargs["name"]
        content = kwargs["content"]
        category = kwargs.get("category", "scene")

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        prompts_dir = project_manager.project_path / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        prompt_path = prompts_dir / f"{name}.md"

        front_matter = f"""---
category: {category}
created: {datetime.now().isoformat()}
updated: {datetime.now().isoformat()}
---

"""
        full_content = front_matter + content

        old_content = ""
        if prompt_path.exists():
            old_content = prompt_path.read_text(encoding="utf-8")

        prompt_path.write_text(full_content, encoding="utf-8")

        diff = self._generate_diff(old_content, full_content, str(prompt_path))

        return ToolResult(
            success=True,
            message=f"提示词 '{name}' 已创建",
            diff=diff,
            file_path=str(prompt_path),
            data={"name": name, "category": category, "path": str(prompt_path)},
        )

    def _generate_diff(self, old: str, new: str, filepath: str) -> str:
        if not old:
            lines = new.split("\n")
            return f"--- /dev/null\n+++ {filepath}\n" + "\n".join(f"+{line}" for line in lines)
        else:
            old_lines = old.split("\n")
            new_lines = new.split("\n")
            diff_lines = [f"--- {filepath} (旧)", f"+++ {filepath} (新)"]
            for line in new_lines:
                if line not in old_lines:
                    diff_lines.append(f"+{line}")
            return "\n".join(diff_lines)


class EditPromptTool(AITool):
    """修改现有提示词"""

    @property
    def name(self) -> str:
        return "edit_prompt"

    @property
    def description(self) -> str:
        return "修改现有提示词的内容。需要指定提示词名称和新的完整内容。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter("name", "string", "要修改的提示词名称"),
            ToolParameter("content", "string", "新的完整提示词内容（包含 Front Matter 和正文）"),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        name = kwargs["name"]
        content = kwargs["content"]

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        prompt_path = project_manager.project_path / "prompts" / f"{name}.md"
        if not prompt_path.exists():
            return ToolResult(success=False, message=f"提示词 '{name}' 不存在")

        old_content = prompt_path.read_text(encoding="utf-8")

        if content.startswith("---"):
            import re
            content = re.sub(
                r"updated: [^\n]+",
                f"updated: {datetime.now().isoformat()}",
                content,
                count=1,
            )

        prompt_path.write_text(content, encoding="utf-8")

        diff = CreatePromptTool()._generate_diff(old_content, content, str(prompt_path))

        return ToolResult(
            success=True,
            message=f"提示词 '{name}' 已更新",
            diff=diff,
            file_path=str(prompt_path),
        )


class ListPromptsTool(AITool):
    """列出所有提示词"""

    @property
    def name(self) -> str:
        return "list_prompts"

    @property
    def description(self) -> str:
        return "列出项目中所有提示词的名称和简要预览。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return []

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        prompts = project_manager.list_prompts()
        result = []
        for name in prompts:
            content = project_manager.load_prompt(name)
            preview = (content or "")[:100].replace("\n", " ")
            result.append({"name": name, "preview": preview})

        return ToolResult(
            success=True,
            message=f"共 {len(result)} 个提示词",
            data={"prompts": result},
        )


class DeletePromptTool(AITool):
    """删除提示词"""

    @property
    def name(self) -> str:
        return "delete_prompt"

    @property
    def description(self) -> str:
        return "删除指定的提示词文件。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter("name", "string", "要删除的提示词名称"),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager

        name = kwargs["name"]

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        prompt_path = project_manager.project_path / "prompts" / f"{name}.md"
        if not prompt_path.exists():
            return ToolResult(success=False, message=f"提示词 '{name}' 不存在")

        old_content = prompt_path.read_text(encoding="utf-8")
        prompt_path.unlink()

        diff = f"--- {prompt_path}\n+++ /dev/null\n" + "\n".join(f"-{line}" for line in old_content.split("\n"))

        return ToolResult(
            success=True,
            message=f"提示词 '{name}' 已删除",
            diff=diff,
            file_path=str(prompt_path),
        )
