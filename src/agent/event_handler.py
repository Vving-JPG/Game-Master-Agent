"""
事件处理器。
接收引擎事件，调用 GameMaster 处理，通过回调推送 SSE 事件。
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterable
from typing import Callable, Awaitable, Optional

from src.adapters.base import EngineAdapter, EngineEvent
from src.agent.game_master import GameMaster

logger = logging.getLogger(__name__)


# SSE 回调类型: 接收 event_name 和 data
SSECallback = Callable[[str, dict], Awaitable[None]]


class EventHandler:
    """事件分发与 SSE 推送"""

    def __init__(
        self,
        game_master: GameMaster,
        engine_adapter: EngineAdapter,
    ):
        self.game_master = game_master
        self.engine_adapter = engine_adapter
        self._sse_callbacks: list[SSECallback] = []
        self._processing = False
        self._current_event: Optional[EngineEvent] = None

    def register_sse_callback(self, callback: SSECallback):
        """注册 SSE 推送回调"""
        self._sse_callbacks.append(callback)

    async def _emit_sse(self, event_name: str, data: dict):
        """推送到所有 SSE 回调"""
        for cb in self._sse_callbacks:
            try:
                await cb(event_name, data)
            except Exception as e:
                logger.error(f"SSE 推送失败: {e}")

    @property
    def is_processing(self) -> bool:
        """是否正在处理事件"""
        return self._processing

    @property
    def current_event(self) -> Optional[EngineEvent]:
        """当前正在处理的事件"""
        return self._current_event

    async def handle_event(self, event: EngineEvent) -> dict:
        """
        处理引擎事件并推送 SSE。

        SSE 推送时序:
        1. turn_start
        2. reasoning / token (由 GameMaster 内部流式推送)
        3. command
        4. memory_update
        5. state_change
        6. turn_end
        """
        if self._processing:
            logger.warning("Agent 正在处理其他事件，忽略新事件")
            return {"error": "AGENT_BUSY", "message": "Agent is processing another event"}

        self._processing = True
        self._current_event = event

        try:
            # 1. 推送 turn_start
            await self._emit_sse("turn_start", {
                "event_id": event.event_id,
                "type": event.type,
            })

            # 2. 调用 GameMaster 处理
            response = await self.game_master.handle_event(event)

            # 3. 推送 commands
            for cmd in response["commands"]:
                if cmd.get("intent") != "no_op":
                    await self._emit_sse("command", cmd)

            # 4. 推送 memory_updates
            for upd in response.get("memory_updates", []):
                await self._emit_sse("memory_update", upd)

            # 5. 推送 command_results 中的 state_changes
            for r in response.get("command_results", []):
                if r.get("status") == "rejected":
                    await self._emit_sse("command_rejected", r)

            # 6. 推送 turn_end
            await self._emit_sse("turn_end", {
                "response_id": response["response_id"],
                "stats": response.get("stats", {}),
            })

            return response

        except Exception as e:
            logger.error(f"事件处理失败: {e}", exc_info=True)
            await self._emit_sse("error", {
                "message": str(e),
                "code": "EVENT_PROCESSING_ERROR",
            })
            return {"error": str(e)}

        finally:
            self._processing = False
            self._current_event = None

    async def stream_response(self, event: EngineEvent) -> AsyncIterable[dict]:
        """
        流式处理事件，yield SSE 事件字典。
        用于 FastAPI EventSourceResponse。

        yield 格式: {"event": str, "data": dict, "id": int}
        """
        event_index = 0

        # turn_start
        yield {
            "event": "turn_start",
            "data": {"event_id": event.event_id, "type": event.type},
            "id": event_index,
        }
        event_index += 1

        try:
            # 调用 GameMaster
            response = await self.game_master.handle_event(event)

            # narrative 已在 GameMaster 内流式生成
            # 这里推送最终结果
            yield {
                "event": "narrative_complete",
                "data": {"text": response["narrative"]},
                "id": event_index,
            }
            event_index += 1

            # commands
            for cmd in response["commands"]:
                if cmd.get("intent") != "no_op":
                    yield {
                        "event": "command",
                        "data": cmd,
                        "id": event_index,
                    }
                    event_index += 1

            # memory_updates
            for upd in response.get("memory_updates", []):
                yield {
                    "event": "memory_update",
                    "data": upd,
                    "id": event_index,
                }
                event_index += 1

            # command_results
            for r in response.get("command_results", []):
                if r.get("status") == "rejected":
                    yield {
                        "event": "command_rejected",
                        "data": r,
                        "id": event_index,
                    }
                    event_index += 1

            # turn_end
            yield {
                "event": "turn_end",
                "data": {
                    "response_id": response["response_id"],
                    "stats": response.get("stats", {}),
                },
                "id": event_index,
            }
            event_index += 1

        except Exception as e:
            yield {
                "event": "error",
                "data": {"message": str(e), "code": "STREAM_ERROR"},
                "id": event_index,
            }
