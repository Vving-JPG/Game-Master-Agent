# 2workbench/feature/ai/tools/context.py
"""工具上下文 — 让工具能访问数据库"""
from __future__ import annotations

import threading
from typing import Any

from foundation.config import settings
from foundation.logger import get_logger

logger = get_logger(__name__)


class ToolContext:
    """工具执行上下文"""

    def __init__(self, db_path: str, world_id: str, player_id: int):
        self.db_path = db_path
        self.world_id = world_id
        self.player_id = player_id
        self._repos: dict[str, Any] = {}

    def get_repo(self, repo_class) -> Any:
        """获取 Repository 实例（懒加载）"""
        if repo_class.__name__ not in self._repos:
            self._repos[repo_class.__name__] = repo_class(self.db_path)
        return self._repos[repo_class.__name__]


_tool_context = threading.local()


def _init_tool_context():
    """初始化线程本地存储的默认值"""
    if not hasattr(_tool_context, 'context'):
        _tool_context.context = None


def set_tool_context(ctx: ToolContext | None):
    """设置当前工具上下文"""
    _init_tool_context()
    _tool_context.context = ctx


def get_tool_context() -> ToolContext | None:
    """获取当前工具上下文"""
    _init_tool_context()
    return _tool_context.context


def _get_db_path() -> str:
    """获取数据库路径"""
    return getattr(settings, 'database_path', 'data/game.db')


def _get_world_id() -> int:
    """从工具上下文获取 world_id，默认为 1"""
    ctx = get_tool_context()
    if ctx and ctx.world_id:
        try:
            return int(ctx.world_id)
        except (ValueError, TypeError):
            return 1
    return 1
