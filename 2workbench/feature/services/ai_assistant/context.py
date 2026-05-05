"""
项目上下文收集器
在 AI 规划前收集项目当前状态，作为 LLM 的背景信息
"""
import json
from pathlib import Path

from foundation.logger import get_logger

logger = get_logger(__name__)


class ProjectContextCollector:
    """收集项目上下文信息"""

    def __init__(self):
        self._context_cache: dict | None = None

    def collect(self) -> dict:
        """
        收集当前项目的完整上下文

        Returns:
            包含项目结构、提示词、技能、图定义、配置的字典
        """
        from feature.project import project_manager

        if not project_manager.is_open:
            return {"error": "没有打开的项目"}

        project_path = project_manager.project_path
        project_name = project_manager.current_project.name

        context = {
            "project_name": project_name,
            "project_path": str(project_path),
            "prompts": self._collect_prompts(project_path),
            "skills": self._collect_skills(project_path),
            "graph": self._collect_graph(project_path),
            "config": self._collect_config(),
        }

        self._context_cache = context
        logger.info(f"上下文收集完成: {project_name}")
        return context

    def _collect_prompts(self, project_path: Path) -> list[dict]:
        """收集提示词信息"""
        prompts = []
        prompts_dir = project_path / "prompts"
        if prompts_dir.exists():
            for f in sorted(prompts_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                prompts.append({
                    "name": f.stem,
                    "size": len(content),
                    "preview": content[:300].replace("\n", "\\n"),
                })
        return prompts

    def _collect_skills(self, project_path: Path) -> list[dict]:
        """收集技能信息"""
        skills = []
        skills_dir = project_path / "skills"
        if skills_dir.exists():
            for skill_dir in sorted(skills_dir.iterdir()):
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        content = skill_file.read_text(encoding="utf-8")
                        metadata = self._parse_yaml_frontmatter(content)
                        skills.append({
                            "name": skill_dir.name,
                            "description": metadata.get("description", ""),
                            "keywords": metadata.get("keywords", []),
                            "allowed_tools": metadata.get("allowed-tools", []),
                            "size": len(content),
                            "preview": content[:200].replace("\n", "\\n"),
                        })
        return skills

    def _collect_graph(self, project_path: Path) -> dict:
        """收集图定义信息"""
        graph_file = project_path / "graph.json"
        if not graph_file.exists():
            return {"exists": False}

        try:
            graph_data = json.loads(graph_file.read_text(encoding="utf-8"))
            return {
                "exists": True,
                "node_count": len(graph_data.get("nodes", [])),
                "edge_count": len(graph_data.get("edges", [])),
                "nodes": [
                    {
                        "id": n.get("id", ""),
                        "type": n.get("type", ""),
                        "label": n.get("data", {}).get("label", ""),
                    }
                    for n in graph_data.get("nodes", [])
                ],
                "edges": [
                    {
                        "source": e.get("source", ""),
                        "target": e.get("target", ""),
                        "label": e.get("label", ""),
                    }
                    for e in graph_data.get("edges", [])
                ],
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"图定义解析失败: {e}")
            return {"exists": True, "error": str(e)}

    def _collect_config(self) -> dict:
        """收集项目配置"""
        from feature.project import project_manager

        try:
            config = project_manager.load_project_config()
            return config or {}
        except Exception as e:
            logger.warning(f"配置加载失败: {e}")
            return {}

    def _parse_yaml_frontmatter(self, content: str) -> dict:
        """简易解析 YAML Front Matter（不依赖 PyYAML）"""
        metadata = {}
        if not content.startswith("---"):
            return metadata

        lines = content.split("\n")
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            line = lines[i]
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if value.startswith("[") and value.endswith("]"):
                    import ast
                    try:
                        metadata[key] = ast.literal_eval(value)
                    except (ValueError, SyntaxError):
                        metadata[key] = value
                else:
                    metadata[key] = value
            i += 1

        return metadata

    def invalidate_cache(self):
        """清除上下文缓存（项目切换时调用）"""
        self._context_cache = None

    def get_cached_context(self) -> dict | None:
        """获取缓存的上下文"""
        return self._context_cache


# 全局单例
context_collector = ProjectContextCollector()
