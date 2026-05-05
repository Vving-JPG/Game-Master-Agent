"""Checkpoint 配置 — 短期记忆持久化

使用 langgraph-checkpoint-sqlite 实现自动状态保存和恢复。
每个项目拥有独立的 checkpoint 数据库。
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from foundation.logger import get_logger

if TYPE_CHECKING:
    from langgraph.checkpoint.sqlite import SqliteSaver

logger = get_logger(__name__)

# 缓存 checkpointer 实例（每个项目一个）
_checkpointer_cache: dict[str, "SqliteSaver"] = {}


def get_checkpointer(project_path: str | Path) -> "SqliteSaver":
    """为每个项目创建独立的 checkpointer

    Args:
        project_path: 项目根目录路径

    Returns:
        SqliteSaver 实例
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    project_path = Path(project_path)
    cache_key = str(project_path.resolve())

    # 检查缓存
    if cache_key in _checkpointer_cache:
        return _checkpointer_cache[cache_key]

    # 创建数据库目录
    db_path = project_path / "data" / "checkpoint.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"创建 checkpoint 数据库: {db_path}")

    # 创建 checkpointer
    checkpointer = SqliteSaver.from_conn_string(str(db_path))

    # 缓存实例
    _checkpointer_cache[cache_key] = checkpointer

    return checkpointer


def clear_checkpointer_cache(project_path: str | Path | None = None) -> None:
    """清除 checkpointer 缓存

    Args:
        project_path: 指定项目路径则清除该项目，None 则清除所有
    """
    global _checkpointer_cache

    if project_path is None:
        _checkpointer_cache.clear()
        logger.info("已清除所有 checkpointer 缓存")
    else:
        cache_key = str(Path(project_path).resolve())
        if cache_key in _checkpointer_cache:
            del _checkpointer_cache[cache_key]
            logger.info(f"已清除项目 checkpoint 缓存: {cache_key}")


def get_checkpointer_sync(project_path: str | Path) -> "SqliteSaver":
    """同步获取 checkpointer（用于非异步上下文）

    Args:
        project_path: 项目根目录路径

    Returns:
        SqliteSaver 实例
    """
    return get_checkpointer(project_path)
