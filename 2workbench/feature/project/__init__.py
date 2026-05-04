"""项目管理模块 — Feature 层

提供项目 CRUD、模板管理、图编译等业务功能。
"""
from feature.project.manager import (
    AgentProjectConfig,
    ProjectManager,
    RecentProjectsManager,
    PROJECT_TEMPLATES,
    project_manager,
    recent_projects_manager,
)

__all__ = [
    "AgentProjectConfig",
    "ProjectManager",
    "RecentProjectsManager",
    "PROJECT_TEMPLATES",
    "project_manager",
    "recent_projects_manager",
]
