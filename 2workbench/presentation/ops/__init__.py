# 2workbench/presentation/ops/__init__.py
"""Presentation 层 — IDE 运营工具集（扁平化结构）

注意: EvalWorkbench, KnowledgeEditor, SafetyPanel, MultiAgentOrchestrator, DeployManager
已在管理器改造中移除。保留 RuntimePanel, EventMonitor, LogViewer。
"""
from presentation.ops.debugger import RuntimePanel, EventMonitor
from presentation.ops.log_viewer import LogViewer

__all__ = [
    "RuntimePanel", "EventMonitor",
    "LogViewer",
]
