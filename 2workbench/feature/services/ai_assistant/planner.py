"""
AI 任务规划器
接收用户自然语言需求 → 收集项目上下文 → 调用 LLM 生成执行计划 → 解析为结构化 Plan
"""
import json
import re
from typing import Any

from foundation.logger import get_logger
from foundation.llm.model_router import model_router
from foundation.llm.base import LLMMessage
from .context import context_collector
from .models import ExecutionPlan, PlanStep, StepStatus
from .prompts import PLANNER_SYSTEM_PROMPT

logger = get_logger(__name__)


class PlanParseError(Exception):
    """计划解析失败"""
    pass


class TaskPlanner:
    """AI 任务规划器"""

    def __init__(self):
        self._context_collector = context_collector

    async def plan(self, user_request: str, session_messages: list[dict] | None = None) -> ExecutionPlan:
        """
        根据用户请求生成执行计划

        Args:
            user_request: 用户的自然语言需求
            session_messages: 当前会话的历史消息（用于多轮对话上下文）

        Returns:
            ExecutionPlan 结构化的执行计划

        Raises:
            PlanParseError: LLM 输出无法解析为有效计划
        """
        # 1. 收集项目上下文
        logger.info(f"开始规划: {user_request[:50]}...")
        context = self._context_collector.collect()
        if "error" in context:
            raise PlanParseError(context["error"])

        # 2. 构建 LLM 消息
        messages = self._build_messages(user_request, context, session_messages)

        # 3. 调用 LLM
        try:
            client, config = model_router.route(
                content=user_request,
                event_type="ai_assistant_plan",
            )
        except Exception as e:
            logger.error(f"模型路由失败: {e}")
            raise PlanParseError(f"无法获取 LLM 客户端: {e}")

        try:
            response = await client.chat_async(
                messages=messages,
                temperature=config.get("temperature", 0.3),
                max_tokens=config.get("max_tokens", 4096),
            )
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise PlanParseError(f"LLM 调用失败: {e}")

        # 4. 提取响应文本
        response_text = self._extract_response_text(response)
        logger.debug(f"LLM 规划响应:\n{response_text[:500]}")

        # 5. 解析为 ExecutionPlan
        plan = self._parse_plan(response_text, user_request, context)

        logger.info(f"计划生成完成: {len(plan.steps)} 个步骤")
        return plan

    def _build_messages(
        self,
        user_request: str,
        context: dict,
        session_messages: list[dict] | None,
    ) -> list[LLMMessage]:
        """构建 LLM 消息列表"""

        system_content = PLANNER_SYSTEM_PROMPT.format(
            project_context=json.dumps(context, ensure_ascii=False, indent=2),
        )

        messages = [LLMMessage(role="system", content=system_content)]

        if session_messages:
            for msg in session_messages[-10:]:
                if msg.get("role") in ("user", "assistant"):
                    messages.append(LLMMessage(
                        role=msg["role"],
                        content=msg.get("content", ""),
                    ))

        messages.append(LLMMessage(role="user", content=user_request))

        return messages

    def _extract_response_text(self, response: Any) -> str:
        """从 LLM 响应中提取文本"""
        if hasattr(response, "content"):
            return response.content
        elif isinstance(response, dict):
            return response.get("content", response.get("text", str(response)))
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    def _parse_plan(
        self,
        response_text: str,
        user_request: str,
        context: dict,
    ) -> ExecutionPlan:
        """解析 LLM 输出为 ExecutionPlan"""
        json_str = self._extract_json_block(response_text)

        if not json_str:
            raise PlanParseError(
                "LLM 输出中未找到有效的 JSON 计划。"
                f"\n原始输出:\n{response_text[:1000]}"
            )

        try:
            plan_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise PlanParseError(f"JSON 解析失败: {e}\n原始 JSON:\n{json_str[:500]}")

        thinking = plan_data.get("thinking", "")
        steps_data = plan_data.get("plan", [])

        if not steps_data:
            raise PlanParseError("计划中没有步骤")

        steps = []
        for i, step_data in enumerate(steps_data):
            step = PlanStep(
                step_id=step_data.get("step", i + 1),
                tool_name=step_data.get("tool", ""),
                description=step_data.get("description", ""),
                parameters=step_data.get("parameters", {}),
                status=StepStatus.PENDING,
            )
            steps.append(step)

        return ExecutionPlan(
            goal=user_request,
            steps=steps,
            context_summary=thinking,
        )

    def _extract_json_block(self, text: str) -> str | None:
        """从 LLM 输出中提取 JSON 块"""
        # 方式 1：```json 代码块
        json_block_match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
        if json_block_match:
            return json_block_match.group(1).strip()

        # 方式 2：``` 代码块（无语言标记）
        code_block_match = re.search(r"```\s*\n(.*?)\n```", text, re.DOTALL)
        if code_block_match:
            candidate = code_block_match.group(1).strip()
            if candidate.startswith("{"):
                return candidate

        # 方式 3：直接查找 JSON 对象
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        return None

    async def refine_plan(
        self,
        plan: ExecutionPlan,
        user_feedback: str,
        session_messages: list[dict] | None = None,
    ) -> ExecutionPlan:
        """根据用户反馈修改计划"""
        context = self._context_collector.get_cached_context()
        if not context:
            context = self._context_collector.collect()

        current_plan_json = json.dumps(
            plan.to_dict(),
            ensure_ascii=False,
            indent=2,
        )

        refine_request = (
            f"当前计划：\n```json\n{current_plan_json}\n```\n\n"
            f"用户反馈：{user_feedback}\n\n"
            f"请根据用户反馈修改计划，输出完整的修改后计划（JSON 格式）。"
        )

        messages = self._build_messages(refine_request, context, session_messages)

        try:
            client, config = model_router.route(
                content=refine_request,
                event_type="ai_assistant_plan",
            )
            response = await client.chat_async(
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
            )
            response_text = self._extract_response_text(response)
            new_plan = self._parse_plan(response_text, plan.goal, context)
            return new_plan
        except Exception as e:
            logger.error(f"计划修改失败: {e}")
            raise PlanParseError(f"计划修改失败: {e}")


# 全局单例
task_planner = TaskPlanner()
