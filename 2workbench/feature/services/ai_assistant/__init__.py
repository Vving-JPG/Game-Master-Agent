"""
AI 助手服务模块
提供任务规划、工具执行、上下文收集等功能
"""
from .models import (
    StepStatus,
    MessageRole,
    PlanStep,
    ExecutionPlan,
    ChatMessage,
    SessionState,
)
from .context import ProjectContextCollector, context_collector
from .planner import TaskPlanner, task_planner, PlanParseError
from .executor import ToolExecutor, tool_executor, SnapshotManager, DiffGenerator
from .service import AIAssistantService, ai_assistant_service, ServiceState
from .prompts import PLANNER_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
from .tools import (
    AITool,
    ToolParameter,
    ToolResult,
    ToolRegistry,
    tool_registry,
    register_all_tools,
)

__all__ = [
    # 数据模型
    "StepStatus",
    "MessageRole",
    "PlanStep",
    "ExecutionPlan",
    "ChatMessage",
    "SessionState",
    # 上下文收集
    "ProjectContextCollector",
    "context_collector",
    # 规划器
    "TaskPlanner",
    "task_planner",
    "PlanParseError",
    # 执行器
    "ToolExecutor",
    "tool_executor",
    "SnapshotManager",
    "DiffGenerator",
    # 服务
    "AIAssistantService",
    "ai_assistant_service",
    "ServiceState",
    # 提示词
    "PLANNER_SYSTEM_PROMPT",
    "CHAT_SYSTEM_PROMPT",
    # 工具
    "AITool",
    "ToolParameter",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
    "register_all_tools",
]
