"""
Game Master Agent — 事件驱动主循环。
V2 重写: 不再是游戏本身，而是驱动游戏的 Agent 服务。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from src.adapters.base import EngineAdapter, EngineEvent
from src.agent.command_parser import CommandParser
from src.agent.prompt_builder import PromptBuilder
from src.memory.manager import MemoryManager
from src.skills.loader import SkillLoader

logger = logging.getLogger(__name__)


class GameMaster:
    """Game Master Agent — 事件驱动"""

    def __init__(
        self,
        llm_client,
        memory_manager: MemoryManager,
        skill_loader: SkillLoader,
        engine_adapter: EngineAdapter,
        system_prompt_path: str = "prompts/system_prompt.md",
    ):
        self.llm_client = llm_client
        self.memory_manager = memory_manager
        self.skill_loader = skill_loader
        self.engine_adapter = engine_adapter
        self.command_parser = CommandParser()
        self.prompt_builder = PromptBuilder(
            system_prompt_path=system_prompt_path,
            memory_manager=memory_manager,
            skill_loader=skill_loader,
        )
        self.history: list[dict] = []
        self.turn_count = 0
        self.total_tokens = 0

    async def handle_event(self, event: EngineEvent) -> dict:
        """
        处理单个引擎事件，返回完整的 Agent 响应。

        流程:
        1. 组装 Prompt
        2. 流式调用 LLM
        3. 解析输出
        4. 更新记忆
        5. 发送指令到引擎
        6. 更新历史对话

        返回:
        {
            "response_id": str,
            "event_id": str,
            "narrative": str,
            "commands": list[dict],
            "memory_updates": list[dict],
            "command_results": list[dict],
            "stats": dict
        }
        """
        self.turn_count += 1
        response_id = f"resp_{uuid.uuid4().hex[:12]}"

        logger.info(f"[回合 {self.turn_count}] 处理事件: {event.type}")

        # Step 1: 组装 Prompt
        event_dict = {
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "type": event.type,
            "data": event.data,
            "context_hints": event.context_hints,
            "game_state": event.game_state,
        }
        messages = self.prompt_builder.build(
            event=event_dict,
            history=self.history,
            memory_depth="activation",
        )

        # Step 2: 流式调用 LLM
        full_content = ""
        reasoning_content = ""
        tokens_used = 0

        async for chunk in self.llm_client.stream(messages):
            event_type = chunk["event"]
            data = chunk["data"]

            if event_type == "token":
                full_content += data["text"]
            elif event_type == "reasoning":
                reasoning_content += data["text"]
            elif event_type == "llm_complete":
                tokens_used = len(full_content) + len(reasoning_content)

        self.total_tokens += tokens_used

        # Step 3: 解析输出
        response = self.command_parser.parse(full_content)
        narrative = response["narrative"]
        commands = response["commands"]
        memory_updates = response["memory_updates"]

        # Step 4: 更新记忆（Agent 侧 — Markdown Body）
        for update in memory_updates:
            try:
                self.memory_manager.apply_memory_updates([update])
            except Exception as e:
                logger.error(f"记忆更新失败: {update['file']} - {e}")

        # Step 5: 发送指令到引擎
        command_results = []
        state_changes = []
        if commands:
            try:
                results = await self.engine_adapter.send_commands(commands)
                for r in results:
                    result_dict = {
                        "intent": r.intent,
                        "status": r.status,
                    }
                    if r.new_value is not None:
                        result_dict["new_value"] = r.new_value
                    if r.reason:
                        result_dict["reason"] = r.reason
                    if r.suggestion:
                        result_dict["suggestion"] = r.suggestion
                    command_results.append(result_dict)

                    # 收集引擎状态变化
                    if r.state_changes:
                        state_changes.append(r.state_changes)
            except Exception as e:
                logger.error(f"指令执行失败: {e}")
                command_results.append({
                    "intent": "error",
                    "status": "error",
                    "reason": str(e),
                })

        # Step 5.1: 应用引擎状态变化（引擎侧 — YAML Front Matter）
        for change in state_changes:
            try:
                self.memory_manager.apply_state_changes([change])
            except Exception as e:
                logger.error(f"状态变化应用失败: {change} - {e}")

        # Step 6: 更新历史对话
        self._update_history(event_dict, response, command_results)

        # 更新会话记录
        self._update_session(event, response, command_results)

        return {
            "response_id": response_id,
            "event_id": event.event_id,
            "narrative": narrative,
            "commands": commands,
            "memory_updates": memory_updates,
            "command_results": command_results,
            "stats": {
                "turn": self.turn_count,
                "tokens_used": tokens_used,
                "total_tokens": self.total_tokens,
                "commands_sent": len(commands),
                "commands_success": sum(
                    1 for r in command_results if r["status"] == "success"
                ),
            },
        }

    def _update_history(
        self,
        event: dict,
        response: dict,
        command_results: list[dict],
    ):
        """更新对话历史（保留最近 20 轮）"""
        # User 消息
        user_text = event.get("data", {}).get("raw_text", "")
        if not user_text:
            event_type = event.get("type", "")
            user_text = f"[{event_type}] {event.get('data', {})}"
        self.history.append({"role": "user", "content": user_text})

        # Assistant 消息
        self.history.append({
            "role": "assistant",
            "content": response["narrative"],
        })

        # 如果有指令执行结果，追加为 tool 消息
        for r in command_results:
            if r["status"] in ("rejected", "error"):
                self.history.append({
                    "role": "user",
                    "content": f"[系统] 指令 {r['intent']} 执行失败: {r.get('reason', '未知错误')}",
                })

        # 保留最近 20 轮（40 条消息）
        max_messages = 40
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    def _update_session(
        self,
        event: EngineEvent,
        response: dict,
        command_results: list[dict],
    ):
        """更新会话记录文件"""
        try:
            cmd_summary = ""
            if response["commands"]:
                intents = [c["intent"] for c in response["commands"] if c["intent"] != "no_op"]
                if intents:
                    cmd_summary = f" 指令: {', '.join(intents)}"

            rejected = [r for r in command_results if r["status"] == "rejected"]
            reject_summary = ""
            if rejected:
                reject_summary = f" 拒绝: {', '.join(r['intent'] for r in rejected)}"

            self.memory_manager.apply_memory_updates([{
                "file": "session/current.md",
                "action": "append",
                "content": (
                    f"\n[回合{self.turn_count}] "
                    f"{event.type}: {event.data.get('raw_text', '')[:50]}"
                    f"{cmd_summary}{reject_summary}"
                ),
            }])
        except Exception as e:
            logger.error(f"会话记录更新失败: {e}")

    def reset(self):
        """重置 Agent 状态"""
        self.history.clear()
        self.turn_count = 0
        self.total_tokens = 0
        logger.info("Agent 状态已重置")
