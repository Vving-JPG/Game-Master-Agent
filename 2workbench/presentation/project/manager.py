"""Agent 项目管理器 — 兼容层

⚠️ 已弃用: 此模块已移至 feature.project 模块。
请使用: from feature.project import project_manager

保留此文件仅用于向后兼容，将在未来版本中移除。
"""
from __future__ import annotations

import warnings

# 从 Feature 层重新导出所有内容
from feature.project import (
    AgentProjectConfig,
    ProjectManager,
    RecentProjectsManager,
    PROJECT_TEMPLATES,
    project_manager,
    recent_projects_manager,
)

# 发出弃用警告
warnings.warn(
    "presentation.project.manager 已弃用，请使用 feature.project 模块。",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "AgentProjectConfig",
    "ProjectManager",
    "RecentProjectsManager",
    "PROJECT_TEMPLATES",
    "project_manager",
    "recent_projects_manager",
]
