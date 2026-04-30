"""
工作流引擎。
读取 YAML 定义的工作流步骤，按顺序/分支执行。
支持暂停、继续、单步控制。
"""
from __future__ import annotations

import asyncio
import logging
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    PROMPT = "prompt"
    LLM_STREAM = "llm_stream"
    PARSE = "parse"
    BRANCH = "branch"
    EXECUTE = "execute"
    MEMORY = "memory"
    END = "end"


class ExecutionState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STEP_WAITING = "STEP_WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str
    type: StepType
    next: str = ""
    conditions: dict[str, str] = field(default_factory=dict)
    default: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepContext:
    """步骤执行上下文（在步骤间传递数据）"""
    event: dict = field(default_factory=dict)
    messages: list[dict] = field(default_factory=list)
    llm_output: str = ""
    parsed_response: dict = field(default_factory=dict)
    commands: list[dict] = field(default_factory=list)
    command_results: list[dict] = field(default_factory=list)
    memory_updates: list[dict] = field(default_factory=list)
    turn_id: int = 0
    error: Optional[str] = None


class WorkflowEngine:
    """工作流引擎"""

    def __init__(self):
        self.steps: dict[str, WorkflowStep] = {}
        self.start_step: str = ""
        self.state = ExecutionState.IDLE
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # 默认不暂停
        self._step_mode = False
        self._current_step_id: Optional[str] = None

        # 步骤处理器注册
        self._handlers: dict[StepType, Callable[[StepContext], Awaitable[StepContext]]] = {}

    def load_from_yaml(self, yaml_path: str) -> None:
        """从 YAML 文件加载工作流定义"""
        path = Path(yaml_path)
        if not path.exists():
            logger.warning(f"工作流文件不存在: {yaml_path}")
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self.steps.clear()
        self.start_step = data.get('start', data.get('steps', [{}])[0].get('id', ''))

        for step_data in data.get('steps', []):
            # 处理 conditions 格式转换
            raw_conditions = step_data.get('conditions', {})
            conditions_dict: dict[str, str] = {}
            if isinstance(raw_conditions, list):
                # 列表格式: [{"if": "condition", "next": "target"}]
                for item in raw_conditions:
                    if isinstance(item, dict) and 'if' in item and 'next' in item:
                        conditions_dict[item['if']] = item['next']
            elif isinstance(raw_conditions, dict):
                conditions_dict = raw_conditions

            step = WorkflowStep(
                id=step_data['id'],
                type=StepType(step_data['type']),
                next=step_data.get('next', ''),
                conditions=conditions_dict,
                default=step_data.get('default', ''),
                metadata=step_data.get('metadata', {}),
            )
            self.steps[step.id] = step

        logger.info(f"工作流加载完成: {len(self.steps)} 个步骤, 起始: {self.start_step}")

    def register_handler(
        self,
        step_type: StepType,
        handler: Callable[[StepContext], Awaitable[StepContext]],
    ) -> None:
        """注册步骤处理器"""
        self._handlers[step_type] = handler

    def pause(self) -> None:
        """暂停执行"""
        self._pause_event.clear()
        self.state = ExecutionState.PAUSED
        logger.info("工作流已暂停")

    def resume(self) -> None:
        """继续执行"""
        self._pause_event.set()
        self.state = ExecutionState.RUNNING
        logger.info("工作流已继续")

    def step_once(self) -> None:
        """单步模式：执行一步后自动暂停"""
        self._step_mode = True
        self._pause_event.set()
        logger.info("单步模式已启用")

    @property
    def current_step_id(self) -> Optional[str]:
        return self._current_step_id

    async def run(self, context: StepContext) -> StepContext:
        """执行工作流"""
        self.state = ExecutionState.RUNNING
        self._pause_event.set()
        step_id = self.start_step
        max_iterations = 50  # 防止无限循环

        try:
            for _ in range(max_iterations):
                if not step_id or step_id == 'done':
                    self.state = ExecutionState.COMPLETED
                    break

                step = self.steps.get(step_id)
                if not step:
                    logger.error(f"步骤不存在: {step_id}")
                    context.error = f"Step not found: {step_id}"
                    self.state = ExecutionState.FAILED
                    break

                # 等待暂停解除
                await self._wait_if_paused()

                self._current_step_id = step_id
                logger.info(f"执行步骤: {step_id} ({step.type.value})")

                # 执行步骤
                handler = self._handlers.get(step.type)
                if handler:
                    context = await handler(context)
                else:
                    logger.warning(f"步骤 {step_id} 没有注册处理器")

                # 检查错误
                if context.error:
                    self.state = ExecutionState.FAILED
                    break

                # 单步模式：执行一步后暂停
                if self._step_mode:
                    self._step_mode = False
                    self._pause_event.clear()
                    self.state = ExecutionState.STEP_WAITING
                    await self._wait_if_paused()

                # 确定下一步
                step_id = self._resolve_next(step, context)

        except Exception as e:
            logger.error(f"工作流执行失败: {e}", exc_info=True)
            context.error = str(e)
            self.state = ExecutionState.FAILED

        finally:
            self._current_step_id = None

        return context

    def _resolve_next(self, step: WorkflowStep, context: StepContext) -> str:
        """解析下一步"""
        if step.type == StepType.BRANCH and step.conditions:
            for condition, target in step.conditions.items():
                if self._evaluate_condition(condition, context):
                    return target
            return step.default

        if step.type == StepType.END:
            return ""

        return step.next

    def _evaluate_condition(self, condition: str, context: StepContext) -> bool:
        """简单的条件表达式求值"""
        ctx = {
            'commands': context.commands,
            'command_results': context.command_results,
            'memory_updates': context.memory_updates,
            'llm_output': context.llm_output,
            'parsed_response': context.parsed_response,
        }
        # 允许使用的内置函数
        allowed_builtins = {'len': len, 'any': any, 'all': all}
        try:
            return bool(eval(condition, {"__builtins__": allowed_builtins}, ctx))  # noqa: S307
        except Exception as e:
            logger.warning(f"条件求值失败: {condition} - {e}")
            return False

    async def _wait_if_paused(self) -> None:
        """如果暂停了，等待恢复"""
        while not self._pause_event.is_set():
            self.state = ExecutionState.PAUSED
            await asyncio.sleep(0.1)
