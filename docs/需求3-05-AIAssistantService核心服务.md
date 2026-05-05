# 05 — AIAssistantService 核心服务

> 目标执行者：Trae AI
> 依赖：03（TaskPlanner）+ 04（ToolExecutor）
> 产出：`feature/services/ai_assistant/service.py` + `__init__.py`

---

## 1. 设计说明

AIAssistantService 是整个 AI 助手的**核心编排层**，位于 Feature 层，负责：

1. **接收用户请求**：从 Presentation 层通过 EventBus 接收用户消息
2. **意图判断**：判断用户是闲聊/问答还是需要执行操作
3. **任务规划**：调用 TaskPlanner 生成执行计划
4. **逐步执行**：调用 ToolExecutor 逐步执行计划
5. **会话管理**：维护对话历史和会话状态
6. **事件通知**：通过 EventBus 向 Presentation 层发送状态更新

### 架构位置

```
Presentation 层
    │  (EventBus: ai_assistant.user_message)
    ▼
Feature 层 — AIAssistantService
    ├── TaskPlanner（规划）
    ├── ToolExecutor（执行）
    └── SessionState（会话）
    │  (EventBus: ai_assistant.plan_ready / step_completed / ...)
    ▼
Foundation 层 — model_router / event_bus / logger
```

### 状态机

```
IDLE ──用户发送消息──→ ANALYZING
ANALYZING ──需要规划──→ PLANNING
ANALYZING ──闲聊/问答──→ CHATTING
PLANNING ──计划生成──→ WAITING_CONFIRM
WAITING_CONFIRM ──用户确认──→ EXECUTING
WAITING_CONFIRM ──用户修改──→ PLANNING（重新规划）
WAITING_CONFIRM ──用户取消──→ IDLE
EXECUTING ──步骤完成──→ WAITING_CONFIRM（下一步）
EXECUTING ──全部完成──→ IDLE
EXECUTING ──步骤失败──→ WAITING_CONFIRM（等待用户决定）
CHATTING ──回答完成──→ IDLE
```

---

## 2. 完整实现

**文件**：`feature/services/ai_assistant/service.py`

```python
"""
AI 助手核心服务
编排 TaskPlanner + ToolExecutor，管理会话状态，通过 EventBus 通信
"""
import asyncio
import uuid
from enum import Enum
from typing import Any

from foundation.logger import get_logger
from foundation.event_bus import event_bus, Event
from .planner import task_planner, PlanParseError
from .executor import tool_executor
from .models import (
    ExecutionPlan, PlanStep, ChatMessage, SessionState,
    MessageRole, StepStatus,
)
from .prompts import CHAT_SYSTEM_PROMPT
from .context import context_collector

logger = get_logger(__name__)


class ServiceState(str, Enum):
    """服务状态"""
    IDLE = "idle"                     # 空闲
    ANALYZING = "analyzing"           # 分析用户意图
    PLANNING = "planning"             # AI 正在规划
    WAITING_CONFIRM = "waiting_confirm"  # 等待用户确认计划
    EXECUTING = "executing"           # 正在执行步骤
    CHATTING = "chatting"             # 闲聊/问答模式


class AIAssistantService:
    """AI 助手核心服务"""

    def __init__(self):
        self._state = ServiceState.IDLE
        self._session = SessionState(session_id=str(uuid.uuid4())[:8])
        self._current_plan: ExecutionPlan | None = None
        self._current_step_index: int = -1
        self._pending_actions: asyncio.Queue | None = None

    @property
    def state(self) -> ServiceState:
        return self._state

    @property
    def session(self) -> SessionState:
        return self._session

    @property
    def current_plan(self) -> ExecutionPlan | None:
        return self._current_plan

    # ───────────────────────────────────────────
    # 初始化
    # ───────────────────────────────────────────

    def initialize(self):
        """初始化服务：注册工具、订阅事件"""
        from .tools import register_all_tools
        register_all_tools()

        # 订阅用户消息事件
        event_bus.on("ai_assistant.user_message", self._on_user_message)
        event_bus.on("ai_assistant.plan_action", self._on_plan_action)
        event_bus.on("ai_assistant.step_action", self._on_step_action)
        event_bus.on("project.closed", self._on_project_closed)

        logger.info("AI 助手服务已初始化")

    # ───────────────────────────────────────────
    # 事件处理
    # ───────────────────────────────────────────

    def _on_user_message(self, event: Event):
        """处理用户消息"""
        message = event.data.get("message", "")
        if not message.strip():
            return

        # 记录到会话历史
        self._session.messages.append(ChatMessage(
            role=MessageRole.USER,
            content=message,
            timestamp=event.timestamp,
        ))

        # 异步处理（不阻塞 EventBus）
        asyncio.create_task(self._process_user_message(message))

    async def _process_user_message(self, message: str):
        """处理用户消息的核心逻辑"""
        try:
            # 1. 分析意图
            self._set_state(ServiceState.ANALYZING)
            intent = await self._analyze_intent(message)

            if intent == "chat":
                # 2a. 闲聊/问答模式
                self._set_state(ServiceState.CHATTING)
                await self._handle_chat(message)
                self._set_state(ServiceState.IDLE)

            elif intent == "execute":
                # 2b. 执行模式
                self._set_state(ServiceState.PLANNING)
                await self._handle_plan_and_execute(message)

        except Exception as e:
            logger.error(f"处理用户消息失败: {e}")
            self._emit_error(f"处理失败: {e}")
            self._set_state(ServiceState.IDLE)

    def _on_plan_action(self, event: Event):
        """处理用户对计划的操作"""
        action = event.data.get("action", "")
        feedback = event.data.get("feedback", "")

        if action == "confirm":
            asyncio.create_task(self._execute_plan())
        elif action == "modify":
            asyncio.create_task(self._modify_plan(feedback))
        elif action == "cancel":
            self._cancel_plan()
        elif action == "confirm_all":
            asyncio.create_task(self._execute_all_steps())

    def _on_step_action(self, event: Event):
        """处理用户对步骤的操作"""
        step_id = event.data.get("step_id", 0)
        action = event.data.get("action", "")

        if action == "confirm":
            asyncio.create_task(self._execute_next_step())
        elif action == "skip":
            self._skip_step(step_id)
        elif action == "reject":
            self._reject_step(step_id)

    def _on_project_closed(self, event: Event):
        """项目关闭时清理"""
        self._reset_session()
        context_collector.invalidate_cache()
        tool_executor.clear_snapshots()

    # ───────────────────────────────────────────
    # 意图分析
    # ───────────────────────────────────────────

    async def _analyze_intent(self, message: str) -> str:
        """
        分析用户意图

        Returns:
            "chat" - 闲聊/问答
            "execute" - 需要执行操作（创建/修改/删除配置文件）
        """
        # 简单的关键词匹配（后续可替换为 LLM 判断）
        execute_keywords = [
            "创建", "新建", "添加", "生成", "修改", "编辑", "更新",
            "删除", "移除", "配置", "设置", "调整", "优化",
            "create", "add", "make", "build", "modify", "edit",
            "update", "delete", "remove", "configure", "set",
            "帮我", "请", "我要", "需要",
        ]

        message_lower = message.lower()
        for keyword in execute_keywords:
            if keyword in message_lower:
                return "execute"

        # 检查是否是追问（有当前计划时）
        if self._current_plan and self._state == ServiceState.WAITING_CONFIRM:
            return "execute"

        return "chat"

    # ───────────────────────────────────────────
    # 闲聊/问答模式
    # ───────────────────────────────────────────

    async def _handle_chat(self, message: str):
        """处理闲聊/问答"""
        from foundation.llm.model_router import model_router
        from foundation.llm.base import LLMMessage

        try:
            client, config = model_router.route(
                content=message,
                event_type="ai_assistant_chat",
            )

            # 构建消息（包含最近的历史）
            messages = [LLMMessage(role="system", content=CHAT_SYSTEM_PROMPT)]

            # 添加最近 5 条历史消息
            for msg in self._session.messages[-5:]:
                if msg.role in (MessageRole.USER, MessageRole.ASSISTANT):
                    messages.append(LLMMessage(
                        role=msg.role.value,
                        content=msg.content,
                    ))

            response = await client.chat_async(
                messages=messages,
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 2048),
            )

            response_text = self._extract_text(response)

            # 记录到会话历史
            self._session.messages.append(ChatMessage(
                role=MessageRole.ASSISTANT,
                content=response_text,
            ))

            # 发送响应事件
            event_bus.emit(Event(
                type="ai_assistant.response",
                data={
                    "content": response_text,
                    "mode": "chat",
                },
                source="AIAssistantService",
            ))

        except Exception as e:
            logger.error(f"闲聊处理失败: {e}")
            self._emit_error(f"回答失败: {e}")

    # ───────────────────────────────────────────
    # 规划与执行模式
    # ───────────────────────────────────────────

    async def _handle_plan_and_execute(self, message: str):
        """规划并执行"""
        try:
            # 1. 生成计划
            session_history = [
                msg.to_llm_message()
                for msg in self._session.messages
                if msg.role in (MessageRole.USER, MessageRole.ASSISTANT)
            ]

            plan = await task_planner.plan(message, session_history)

            if not plan.steps:
                event_bus.emit(Event(
                    type="ai_assistant.response",
                    data={
                        "content": "我分析了你的需求，但无法生成具体的执行计划。请更详细地描述你想要做什么。",
                        "mode": "chat",
                    },
                    source="AIAssistantService",
                ))
                self._set_state(ServiceState.IDLE)
                return

            # 2. 保存计划
            self._current_plan = plan
            self._current_step_index = -1
            self._session.current_plan = plan

            # 3. 发送计划就绪事件（等待用户确认）
            self._set_state(ServiceState.WAITING_CONFIRM)

            event_bus.emit(Event(
                type="ai_assistant.plan_ready",
                data={
                    "plan": plan.to_dict(),
                    "thinking": plan.context_summary,
                },
                source="AIAssistantService",
            ))

        except PlanParseError as e:
            logger.error(f"计划生成失败: {e}")
            event_bus.emit(Event(
                type="ai_assistant.response",
                data={
                    "content": f"计划生成失败：{e}\n\n请尝试更具体地描述你的需求。",
                    "mode": "error",
                },
                source="AIAssistantService",
            ))
            self._set_state(ServiceState.IDLE)

    async def _modify_plan(self, feedback: str):
        """根据用户反馈修改计划"""
        if not self._current_plan:
            return

        self._set_state(ServiceState.PLANNING)

        try:
            session_history = [
                msg.to_llm_message()
                for msg in self._session.messages
                if msg.role in (MessageRole.USER, MessageRole.ASSISTANT)
            ]

            new_plan = await task_planner.refine_plan(
                self._current_plan,
                feedback,
                session_history,
            )

            self._current_plan = new_plan
            self._current_step_index = -1
            self._session.current_plan = new_plan

            self._set_state(ServiceState.WAITING_CONFIRM)

            event_bus.emit(Event(
                type="ai_assistant.plan_ready",
                data={
                    "plan": new_plan.to_dict(),
                    "thinking": new_plan.context_summary,
                    "is_modified": True,
                },
                source="AIAssistantService",
            ))

        except PlanParseError as e:
            logger.error(f"计划修改失败: {e}")
            self._emit_error(f"计划修改失败: {e}")
            self._set_state(ServiceState.WAITING_CONFIRM)

    def _cancel_plan(self):
        """取消当前计划"""
        self._current_plan = None
        self._current_step_index = -1
        self._session.current_plan = None
        self._set_state(ServiceState.IDLE)

        event_bus.emit(Event(
            type="ai_assistant.plan_cancelled",
            data={},
            source="AIAssistantService",
        ))

    # ───────────────────────────────────────────
    # 步骤执行
    # ───────────────────────────────────────────

    async def _execute_plan(self):
        """开始执行计划（逐步确认模式）"""
        if not self._current_plan:
            return

        self._current_step_index = 0
        self._set_state(ServiceState.EXECUTING)
        await self._execute_next_step()

    async def _execute_all_steps(self):
        """执行所有步骤（一键确认模式）"""
        if not self._current_plan:
            return

        self._set_state(ServiceState.EXECUTING)

        for i, step in enumerate(self._current_plan.steps):
            if step.status in (StepStatus.SKIPPED, StepStatus.COMPLETED):
                continue

            self._current_step_index = i
            step.status = StepStatus.CONFIRMED
            await self._execute_single_step(step)

            if step.status == StepStatus.FAILED:
                # 执行失败，暂停等待用户决定
                self._set_state(ServiceState.WAITING_CONFIRM)
                event_bus.emit(Event(
                    type="ai_assistant.execution_paused",
                    data={
                        "step_id": step.step_id,
                        "error": step.error,
                        "remaining": len(self._current_plan.steps) - i - 1,
                    },
                    source="AIAssistantService",
                ))
                return

        # 全部完成
        self._finish_execution()

    async def _execute_next_step(self):
        """执行下一个待确认的步骤"""
        if not self._current_plan:
            return

        # 找到下一个 PENDING 的步骤
        next_step = None
        for i, step in enumerate(self._current_plan.steps):
            if step.status == StepStatus.PENDING:
                next_step = step
                self._current_step_index = i
                break

        if next_step is None:
            # 没有更多步骤
            self._finish_execution()
            return

        self._set_state(ServiceState.EXECUTING)
        await self._execute_single_step(next_step)

        # 执行完成后回到等待确认状态（让用户确认下一步）
        if next_step.status == StepStatus.COMPLETED:
            self._set_state(ServiceState.WAITING_CONFIRM)

            # 检查是否还有下一步
            has_next = any(
                s.status == StepStatus.PENDING
                for s in self._current_plan.steps
            )

            if has_next:
                event_bus.emit(Event(
                    type="ai_assistant.next_step_ready",
                    data={
                        "completed_step_id": next_step.step_id,
                        "next_step_id": next_step.step_id + 1,
                    },
                    source="AIAssistantService",
                ))
            else:
                self._finish_execution()

    async def _execute_single_step(self, step: PlanStep):
        """执行单个步骤"""
        step.status = StepStatus.CONFIRMED
        self._session.is_executing = True

        updated_step = await tool_executor.execute_step(step)

        # 更新会话统计
        self._session.total_steps_executed += 1
        if updated_step.status == StepStatus.COMPLETED:
            self._session.total_steps_succeeded += 1

        self._session.is_executing = False

    def _skip_step(self, step_id: int):
        """跳过指定步骤"""
        if not self._current_plan:
            return

        for step in self._current_plan.steps:
            if step.step_id == step_id:
                step.status = StepStatus.SKIPPED
                logger.info(f"步骤 {step_id} 已跳过")

                event_bus.emit(Event(
                    type="ai_assistant.step_skipped",
                    data={"step_id": step_id},
                    source="AIAssistantService",
                ))

                # 检查是否还有下一步
                has_next = any(
                    s.status == StepStatus.PENDING
                    for s in self._current_plan.steps
                )
                if not has_next:
                    self._finish_execution()
                break

    def _reject_step(self, step_id: int):
        """拒绝指定步骤的变更"""
        if not self._current_plan:
            return

        for step in self._current_plan.steps:
            if step.step_id == step_id:
                tool_executor.reject_step(step)
                break

    def _finish_execution(self):
        """执行完成"""
        if not self._current_plan:
            return

        total = len(self._current_plan.steps)
        completed = sum(
            1 for s in self._current_plan.steps
            if s.status == StepStatus.COMPLETED
        )
        failed = sum(
            1 for s in self._current_plan.steps
            if s.status == StepStatus.FAILED
        )
        skipped = sum(
            1 for s in self._current_plan.steps
            if s.status == StepStatus.SKIPPED
        )

        summary = (
            f"执行完成！共 {total} 个步骤："
            f"✅ {completed} 成功"
            + (f" | ❌ {failed} 失败" if failed else "")
            + (f" | ⏭ {skipped} 跳过" if skipped else "")
        )

        self._session.messages.append(ChatMessage(
            role=MessageRole.ASSISTANT,
            content=summary,
        ))

        event_bus.emit(Event(
            type="ai_assistant.execution_finished",
            data={
                "summary": summary,
                "total": total,
                "completed": completed,
                "failed": failed,
                "skipped": skipped,
            },
            source="AIAssistantService",
        ))

        self._set_state(ServiceState.IDLE)
        tool_executor.clear_snapshots()

    # ───────────────────────────────────────────
    # 会话管理
    # ───────────────────────────────────────────

    def _reset_session(self):
        """重置会话"""
        self._session = SessionState(session_id=str(uuid.uuid4())[:8])
        self._current_plan = None
        self._current_step_index = -1
        self._set_state(ServiceState.IDLE)

    def new_session(self):
        """创建新会话"""
        self._reset_session()
        event_bus.emit(Event(
            type="ai_assistant.session_reset",
            data={"session_id": self._session.session_id},
            source="AIAssistantService",
        ))

    def get_session_history(self) -> list[dict]:
        """获取会话历史"""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self._session.messages
        ]

    # ───────────────────────────────────────────
    # 辅助方法
    # ───────────────────────────────────────────

    def _set_state(self, state: ServiceState):
        """设置服务状态并发送事件"""
        old_state = self._state
        self._state = state
        logger.debug(f"状态变更: {old_state.value} → {state.value}")

        event_bus.emit(Event(
            type="ai_assistant.state_changed",
            data={
                "old_state": old_state.value,
                "new_state": state.value,
            },
            source="AIAssistantService",
        ))

    def _emit_error(self, message: str):
        """发送错误事件"""
        event_bus.emit(Event(
            type="ai_assistant.error",
            data={"message": message},
            source="AIAssistantService",
        ))

    def _extract_text(self, response: Any) -> str:
        """从 LLM 响应中提取文本"""
        if hasattr(response, "content"):
            return response.content
        elif isinstance(response, dict):
            return response.get("content", response.get("text", str(response)))
        elif isinstance(response, str):
            return response
        return str(response)


# 全局单例
ai_assistant_service = AIAssistantService()
```

---

## 3. 包初始化

**文件**：`feature/services/ai_assistant/__init__.py`

```python
"""
AI 助手服务包
"""
from .service import AIAssistantService, ai_assistant_service, ServiceState
from .models import (
    ExecutionPlan, PlanStep, ChatMessage, SessionState,
    StepStatus, MessageRole,
)

__all__ = [
    "AIAssistantService",
    "ai_assistant_service",
    "ServiceState",
    "ExecutionPlan",
    "PlanStep",
    "ChatMessage",
    "SessionState",
    "StepStatus",
    "MessageRole",
]
```

---

## 4. 服务注册入口

在应用启动时初始化 AI 助手服务。找到应用入口文件（通常是 `main.py` 或 `app.py`），在启动逻辑中添加：

```python
# 在应用初始化阶段
from feature.services.ai_assistant import ai_assistant_service
ai_assistant_service.initialize()
```

如果项目使用了 `feature/services/__init__.py` 来管理服务，在那里添加导出：

```python
# feature/services/__init__.py 中添加
from . import ai_assistant
```

---

## 5. 验证

创建完成后，验证以下内容：

```python
# 1. 验证服务初始化
from feature.services.ai_assistant import ai_assistant_service, ServiceState

assert ai_assistant_service.state == ServiceState.IDLE
assert ai_assistant_service.session.session_id != ""

# 2. 验证会话管理
ai_assistant_service.new_session()
assert ai_assistant_service.state == ServiceState.IDLE
history = ai_assistant_service.get_session_history()
assert history == []

# 3. 验证事件订阅（需要 EventBus 运行）
# ai_assistant_service.initialize()
# event_bus.emit(Event(
#     type="ai_assistant.user_message",
#     data={"message": "你好"},
# ))
# 等待异步处理...
```

---

## 6. 与现有代码的关系

| 现有组件 | 本文档如何使用 |
|----------|---------------|
| `foundation/llm/model_router.py` | `_handle_chat()` 中 `model_router.route()` 获取 LLM 客户端 |
| `foundation/llm/base.py` | `LLMMessage` 构建消息 |
| `foundation/event_bus.py` | 订阅 `ai_assistant.*` 事件，发送状态更新事件 |
| `feature/project/manager.py` | 项目关闭时清理会话 |
| `feature/services/ai_assistant/planner.py` | `task_planner.plan()` / `refine_plan()` |
| `feature/services/ai_assistant/executor.py` | `tool_executor.execute_step()` / `reject_step()` |
| `feature/services/ai_assistant/tools/` | `register_all_tools()` 注册所有工具 |

### 事件订阅清单

| 订阅事件 | 处理方法 |
|----------|----------|
| `ai_assistant.user_message` | `_on_user_message` → 异步处理 |
| `ai_assistant.plan_action` | `_on_plan_action` → 确认/修改/取消计划 |
| `ai_assistant.step_action` | `_on_step_action` → 确认/跳过/拒绝步骤 |
| `project.closed` | `_on_project_closed` → 清理会话 |

### 事件发送清单

| 发送事件 | 触发时机 |
|----------|----------|
| `ai_assistant.state_changed` | 服务状态变更 |
| `ai_assistant.response` | AI 响应（闲聊/错误） |
| `ai_assistant.plan_ready` | 计划生成完成，等待确认 |
| `ai_assistant.plan_cancelled` | 计划被取消 |
| `ai_assistant.next_step_ready` | 下一步准备执行 |
| `ai_assistant.execution_paused` | 执行因失败暂停 |
| `ai_assistant.execution_finished` | 全部步骤执行完成 |
| `ai_assistant.session_reset` | 会话重置 |
| `ai_assistant.error` | 错误通知 |