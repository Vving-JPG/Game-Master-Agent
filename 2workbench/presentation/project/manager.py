"""Agent 项目管理器 — 项目的 CRUD 操作

职责:
1. 创建新 Agent 项目（初始化目录结构和默认文件）
2. 打开已有项目（加载 project.json）
3. 保存项目（序列化当前状态）
4. 关闭项目（清理资源）
5. 项目模板选择
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentProjectConfig:
    """Agent 项目配置"""
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    created_at: str = ""
    updated_at: str = ""
    template: str = "blank"  # blank / trpg / chatbot / workflow
    graph_file: str = "graph.json"
    config_file: str = "config.json"

    # 运行配置
    default_model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
    stream_enabled: bool = True

    # 功能开关
    features: dict[str, bool] = field(default_factory=lambda: {
        "battle": True,
        "dialogue": True,
        "quest": True,
        "item": True,
        "exploration": True,
        "narration": True,
    })


# 项目模板
PROJECT_TEMPLATES = {
    "blank": {
        "name": "空白项目",
        "description": "从零开始创建 Agent",
        "graph": {
            "nodes": [
                {"id": "input", "type": "input", "label": "用户输入", "position": {"x": 100, "y": 200}},
                {"id": "reasoning", "type": "llm", "label": "LLM 推理", "position": {"x": 400, "y": 200}},
                {"id": "output", "type": "output", "label": "输出", "position": {"x": 700, "y": 200}},
            ],
            "edges": [
                {"from": "input", "to": "reasoning"},
                {"from": "reasoning", "to": "output"},
            ],
        },
        "prompts": {
            "system": "你是一个 AI 助手。请根据用户输入提供帮助。",
        },
        "config": {
            "default_model": "deepseek-chat",
            "temperature": 0.7,
        },
    },
    "trpg": {
        "name": "TRPG 游戏",
        "description": "桌面角色扮演游戏 Agent",
        "graph": {
            "nodes": [
                {"id": "handle_event", "type": "event", "label": "事件处理", "position": {"x": 100, "y": 200}},
                {"id": "build_prompt", "type": "prompt", "label": "Prompt 组装", "position": {"x": 300, "y": 200}},
                {"id": "llm_reasoning", "type": "llm", "label": "LLM 推理", "position": {"x": 500, "y": 200}},
                {"id": "parse_output", "type": "parser", "label": "命令解析", "position": {"x": 700, "y": 150}},
                {"id": "execute_commands", "type": "executor", "label": "命令执行", "position": {"x": 700, "y": 250}},
                {"id": "update_memory", "type": "memory", "label": "记忆更新", "position": {"x": 900, "y": 200}},
            ],
            "edges": [
                {"from": "__start__", "to": "handle_event"},
                {"from": "handle_event", "to": "build_prompt"},
                {"from": "build_prompt", "to": "llm_reasoning"},
                {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"},
                {"from": "llm_reasoning", "to": "execute_commands"},
                {"from": "parse_output", "to": "execute_commands", "condition": "route_after_parse"},
                {"from": "parse_output", "to": "update_memory"},
                {"from": "execute_commands", "to": "update_memory"},
                {"from": "update_memory", "to": "__end__"},
            ],
        },
        "prompts": {
            "system": "你是一位经验丰富的游戏主持人（Game Master）。你负责引导玩家在一个奇幻世界中冒险。\n\n## 世界观\n{world_description}\n\n## 玩家信息\n{player_info}\n\n## 当前场景\n{current_scene}\n\n## 规则\n1. 保持沉浸感，用第二人称描述\n2. 每次回复控制在 200 字以内\n3. 遇到战斗时使用 JSON 格式发出战斗指令",
            "narrative": "请根据以下游戏状态生成叙事描述：\n\n{context}",
            "combat": "战斗叙事生成规则：\n1. 描述要生动有力\n2. 突出关键动作\n3. 包含伤害数值",
        },
        "config": {
            "default_model": "deepseek-chat",
            "temperature": 0.8,
            "features": {
                "battle": True,
                "dialogue": True,
                "quest": True,
                "item": True,
                "exploration": True,
                "narration": True,
            },
        },
    },
    "chatbot": {
        "name": "对话机器人",
        "description": "通用对话 Agent",
        "graph": {
            "nodes": [
                {"id": "input", "type": "input", "label": "用户输入", "position": {"x": 100, "y": 200}},
                {"id": "context", "type": "memory", "label": "上下文检索", "position": {"x": 300, "y": 200}},
                {"id": "llm", "type": "llm", "label": "LLM 生成", "position": {"x": 500, "y": 200}},
                {"id": "output", "type": "output", "label": "回复输出", "position": {"x": 700, "y": 200}},
            ],
            "edges": [
                {"from": "input", "to": "context"},
                {"from": "context", "to": "llm"},
                {"from": "llm", "to": "output"},
            ],
        },
        "prompts": {
            "system": "你是一个友好的 AI 助手。请用简洁清晰的方式回答用户问题。",
        },
        "config": {
            "default_model": "deepseek-chat",
            "temperature": 0.7,
        },
    },
}


class ProjectManager:
    """Agent 项目管理器"""

    def __init__(self, workspace_dir: str | Path | None = None):
        self._workspace = Path(workspace_dir) if workspace_dir else Path.cwd()
        self._current_project: AgentProjectConfig | None = None
        self._project_path: Path | None = None

    @property
    def current_project(self) -> AgentProjectConfig | None:
        return self._current_project

    @property
    def project_path(self) -> Path | None:
        return self._project_path

    @property
    def is_open(self) -> bool:
        return self._current_project is not None

    def create_project(
        self,
        name: str,
        template: str = "blank",
        directory: str | Path | None = None,
        **overrides,
    ) -> Path:
        """创建新 Agent 项目

        Args:
            name: 项目名称
            template: 模板名称（blank/trpg/chatbot）
            directory: 创建目录（默认 workspace）

        Returns:
            项目路径
        """
        if template not in PROJECT_TEMPLATES:
            raise ValueError(f"未知模板: {template}，可选: {list(PROJECT_TEMPLATES.keys())}")

        base_dir = Path(directory) if directory else self._workspace
        project_dir = base_dir / f"{name}.agent"

        if project_dir.exists():
            raise FileExistsError(f"项目已存在: {project_dir}")

        # 创建目录结构
        project_dir.mkdir(parents=True)
        (project_dir / "prompts").mkdir()
        (project_dir / "tools").mkdir()
        (project_dir / "knowledge").mkdir()
        (project_dir / "saves").mkdir()
        (project_dir / "logs").mkdir()

        # 获取模板
        tmpl = PROJECT_TEMPLATES[template]
        now = datetime.now().isoformat()

        # 创建 project.json
        # 从 overrides 中提取有效字段，避免重复传递 description
        valid_overrides = {k: v for k, v in overrides.items() 
                          if k in AgentProjectConfig.__dataclass_fields__ and k != "description"}
        config = AgentProjectConfig(
            name=name,
            description=overrides.get("description", tmpl["description"]),
            created_at=now,
            updated_at=now,
            template=template,
            **valid_overrides,
        )

        # 合并模板配置
        tmpl_config = tmpl.get("config", {})
        if "default_model" in tmpl_config:
            config.default_model = tmpl_config["default_model"]
        if "temperature" in tmpl_config:
            config.temperature = tmpl_config["temperature"]
        if "features" in tmpl_config:
            config.features = tmpl_config["features"]

        self._save_project_json(project_dir, config)

        # 创建 graph.json
        graph_path = project_dir / "graph.json"
        graph_path.write_text(
            json.dumps(tmpl["graph"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 创建 Prompt 文件
        prompts = tmpl.get("prompts", {})
        for prompt_name, content in prompts.items():
            prompt_path = project_dir / "prompts" / f"{prompt_name}.md"
            prompt_path.write_text(content, encoding="utf-8")

        # 创建 config.json
        config_path = project_dir / "config.json"
        config_path.write_text(
            json.dumps({
                "default_model": config.default_model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "stream_enabled": config.stream_enabled,
                "features": config.features,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info(f"项目创建成功: {project_dir}")
        event_bus.emit(Event(type="ui.project.created", data={"path": str(project_dir), "name": name}))

        return project_dir

    def open_project(self, path: str | Path) -> AgentProjectConfig:
        """打开项目

        Args:
            path: project.json 路径或项目目录

        Returns:
            项目配置
        """
        project_dir = Path(path)
        if project_dir.is_file():
            project_dir = project_dir.parent

        project_json = project_dir / "project.json"
        if not project_json.exists():
            raise FileNotFoundError(f"项目文件不存在: {project_json}")

        config = self._load_project_json(project_json)
        self._current_project = config
        self._project_path = project_dir

        logger.info(f"项目已打开: {project_dir} ({config.name})")
        event_bus.emit(Event(type="ui.project.opened", data={
            "path": str(project_dir),
            "name": config.name,
            "template": config.template,
        }))

        return config

    def save_project(self) -> None:
        """保存当前项目"""
        if not self._current_project or not self._project_path:
            raise RuntimeError("没有打开的项目")

        self._current_project.updated_at = datetime.now().isoformat()
        self._save_project_json(self._project_path, self._current_project)

        logger.info(f"项目已保存: {self._project_path}")
        event_bus.emit(Event(type="ui.project.saved", data={
            "path": str(self._project_path),
            "name": self._current_project.name,
        }))

    def close_project(self) -> None:
        """关闭当前项目"""
        if self._current_project:
            name = self._current_project.name
            event_bus.emit(Event(type="ui.project.closing", data={"name": name}))

        self._current_project = None
        self._project_path = None

        logger.info("项目已关闭")
        event_bus.emit(Event(type="ui.project.closed", data={}))

    def load_graph(self) -> dict:
        """加载 LangGraph 图定义"""
        if not self._project_path:
            return {}
        graph_path = self._project_path / "graph.json"
        if not graph_path.exists():
            return {}
        return json.loads(graph_path.read_text(encoding="utf-8"))

    def save_graph(self, graph_data: dict) -> None:
        """保存 LangGraph 图定义"""
        if not self._project_path:
            raise RuntimeError("没有打开的项目")
        graph_path = self._project_path / "graph.json"
        graph_path.write_text(
            json.dumps(graph_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def compile_graph(self) -> Any:
        """编译当前项目的 graph.json 为 StateGraph

        Returns:
            编译好的 CompiledGraph

        Raises:
            RuntimeError: 没有打开的项目
            ValueError: graph.json 无效
        """
        if not self._project_path:
            raise RuntimeError("没有打开的项目")

        graph_data = self.load_graph()
        if not graph_data:
            raise ValueError("graph.json 为空或不存在")

        from feature.ai.graph_compiler import graph_compiler
        compiled = graph_compiler.compile(graph_data)
        logger.info(f"项目图编译成功: {self._current_project.name}")
        return compiled

    def load_prompt(self, name: str) -> str:
        """加载 Prompt 模板"""
        if not self._project_path:
            return ""
        prompt_path = self._project_path / "prompts" / f"{name}.md"
        if not prompt_path.exists():
            return ""
        return prompt_path.read_text(encoding="utf-8")

    def save_prompt(self, name: str, content: str) -> None:
        """保存 Prompt 模板"""
        if not self._project_path:
            raise RuntimeError("没有打开的项目")
        prompt_path = self._project_path / "prompts" / f"{name}.md"
        prompt_path.write_text(content, encoding="utf-8")

    def list_prompts(self) -> list[str]:
        """列出所有 Prompt 模板"""
        if not self._project_path:
            return []
        prompts_dir = self._project_path / "prompts"
        if not prompts_dir.exists():
            return []
        return [p.stem for p in prompts_dir.glob("*.md")]

    def _save_project_json(self, project_dir: Path, config: AgentProjectConfig) -> None:
        """保存 project.json"""
        project_json = project_dir / "project.json"
        project_json.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_project_json(self, path: Path) -> AgentProjectConfig:
        """加载 project.json"""
        data = json.loads(path.read_text(encoding="utf-8"))
        return AgentProjectConfig(**data)


# 全局单例
project_manager = ProjectManager()
