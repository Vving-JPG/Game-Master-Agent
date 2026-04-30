"""
记忆管理器。整合文件读写和渐进式加载。
"""
from pathlib import Path
from typing import Optional

import frontmatter

from src.memory.file_io import atomic_write, update_memory_file
from src.memory.loader import MemoryLoader


class MemoryManager:
    """Agent 记忆管理器"""

    def __init__(self, workspace_path: str, llm_client=None):
        self.workspace = Path(workspace_path)
        self.loader = MemoryLoader(workspace_path)
        self.llm_client = llm_client

    def load_context(self, context_hints: list[str], depth: str = "auto") -> str:
        """根据 context_hints 加载记忆上下文"""
        if depth == "index":
            return self.loader.load_index(context_hints)
        elif depth == "activation":
            return self.loader.load_activation(context_hints)
        elif depth == "execution":
            return self.loader.load_execution(context_hints)
        else:
            return self.loader.load_index(context_hints)

    def load_full_file(self, file_path: str) -> Optional[dict]:
        """加载完整文件，返回 {frontmatter: dict, content: str}"""
        full_path = self.workspace / file_path
        if not full_path.exists():
            return None
        post = frontmatter.load(str(full_path))
        return {"frontmatter": dict(post.metadata), "content": post.content}

    def apply_state_changes(self, state_changes: list[dict]) -> None:
        """引擎执行 commands 后，更新 YAML Front Matter"""
        for change in state_changes:
            update_memory_file(
                filepath=str(self.workspace / change["file"]),
                frontmatter_updates=change["frontmatter"]
            )

    def apply_memory_updates(self, updates: list[dict]) -> None:
        """Agent 每回合追加记忆到 Markdown Body"""
        for update in updates:
            if update["action"] == "append":
                update_memory_file(
                    filepath=str(self.workspace / update["file"]),
                    append_content=update["content"]
                )
            elif update["action"] == "create":
                atomic_write(
                    str(self.workspace / update["file"]),
                    update["content"]
                )

    def initialize_workspace(self) -> None:
        """初始化 workspace 目录结构和索引文件"""
        dirs = ["npcs", "locations", "story", "quests", "items", "player", "session"]
        for d in dirs:
            dir_path = self.workspace / d
            dir_path.mkdir(parents=True, exist_ok=True)
            index_path = dir_path / "_index.md"
            if not index_path.exists():
                atomic_write(
                    str(index_path),
                    f"---\ntype: index\ncategory: {d}\nentity_count: 0\n---\n\n## {d}\n\n(暂无)"
                )
