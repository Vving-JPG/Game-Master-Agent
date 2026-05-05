"""
AI 助手数据模型
定义计划、步骤、结果、Diff、消息、会话等核心数据结构
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    """步骤执行状态"""
    PENDING = "pending"          # 待确认
    CONFIRMED = "confirmed"      # 用户已确认，等待执行
    EXECUTING = "executing"      # 执行中
    COMPLETED = "completed"      # 执行完成
    SKIPPED = "skipped"          # 用户跳过
    FAILED = "failed"            # 执行失败
    REJECTED = "rejected"        # 用户拒绝变更


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class PlanStep:
    """执行计划的单个步骤"""
    step_id: int                          # 步骤编号（从 1 开始）
    tool_name: str                        # 要调用的工具名称
    description: str                      # 步骤描述（给用户看的）
    parameters: dict[str, Any]            # 工具参数
    status: StepStatus = StepStatus.PENDING
    result: dict[str, Any] | None = None  # 执行结果
    diff: str = ""                        # 文件变更的 diff
    error: str = ""                       # 错误信息

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "description": self.description,
            "parameters": self.parameters,
            "status": self.status.value,
            "result": self.result,
            "diff": self.diff,
            "error": self.error,
        }


@dataclass
class ExecutionPlan:
    """执行计划"""
    goal: str                             # 用户的目标描述
    steps: list[PlanStep] = field(default_factory=list)
    context_summary: str = ""             # AI 对项目现状的理解

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "context_summary": self.context_summary,
        }


@dataclass
class ChatMessage:
    """对话消息"""
    role: MessageRole
    content: str
    tool_calls: list[dict] | None = None  # LLM 的工具调用请求
    tool_results: list[dict] | None = None  # 工具执行结果
    timestamp: float = 0.0

    def to_llm_message(self) -> dict:
        """转换为 LLM API 格式"""
        msg = {"role": self.role.value, "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.tool_results:
            msg["tool_results"] = self.tool_results
        return msg


@dataclass
class SessionState:
    """会话状态"""
    session_id: str = ""
    messages: list[ChatMessage] = field(default_factory=list)
    current_plan: ExecutionPlan | None = None
    current_step_index: int = -1          # 当前正在执行的步骤索引
    is_planning: bool = False             # 是否正在规划中
    is_executing: bool = False            # 是否正在执行中
    total_steps_executed: int = 0         # 累计执行步骤数
    total_steps_succeeded: int = 0        # 累计成功步骤数
