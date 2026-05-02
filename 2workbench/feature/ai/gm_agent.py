# 2workbench/feature/ai/gm_agent.py
"""GM Agent 门面 — 对外统一接口

替代原有的:
- 1agent_core/src/game_master.py (GameMaster)
- 1agent_core/src/event_handler.py (EventHandler)
- _legacy/bridge/agent_bridge.py (AgentBridge)

使用方式:
    agent = GMAgent(world_id=1)
    result = await agent.run("玩家说: 我要探索幽暗森林")
    # 或同步:
    result = agent.run_sync("玩家说: 我要探索幽暗森林")
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncGenerator

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger
from core.state import AgentState, create_initial_state
from core.models import WorldRepo, PlayerRepo, NPCRepo, LocationRepo, MemoryRepo

# Repository 实例复用（无状态，可安全共享）
_world_repo = WorldRepo()
_player_repo = PlayerRepo()
_npc_repo = NPCRepo()

from .graph import gm_graph
from .events import (
    create_turn_start_event, create_turn_end_event, create_error_event,
    TURN_START, TURN_END, AGENT_ERROR,
)

logger = get_logger(__name__)


class GMAgent:
    """GM Agent — 游戏主持人 Agent

    这是整个 Agent 系统的统一入口。
    上层（Presentation）通过此类与 Agent 交互。
    """

    def __init__(
        self,
        world_id: int = 1,
        db_path: str | None = None,
        system_prompt: str | None = None,
        skills_dir: str | None = None,
    ):
        self._world_id = world_id
        self._db_path = db_path
        self._system_prompt = system_prompt
        self._execution_state = "idle"
        self._last_result: dict[str, Any] = {}

        # 加载游戏状态
        self._initial_state = self._load_initial_state()

    def _load_initial_state(self) -> AgentState:
        """从数据库加载初始状态"""
        state = create_initial_state(world_id=str(self._world_id))

        try:
            world = _world_repo.get_by_id(self._world_id, self._db_path)
            if world:
                state["current_location"] = {"name": world.name}

            player = _player_repo.get_by_world(self._world_id, self._db_path)
            if player:
                state["player"] = player.model_dump()

            npcs = _npc_repo.get_by_world(self._world_id, self._db_path)
            if npcs:
                state["active_npcs"] = [n.model_dump() for n in npcs]

        except Exception as e:
            logger.warning(f"加载游戏状态失败: {e}")

        return state

    def run_sync(self, user_input: str, event_type: str = "player_action") -> dict[str, Any]:
        """同步执行一轮 Agent（阻塞）

        Args:
            user_input: 玩家输入
            event_type: 事件类型

        Returns:
            执行结果字典
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在 Qt 事件循环中，使用 qasync
                import qasync
                future = qasync.ensure_future(self.run(user_input, event_type))
                # 注意: 这里不能直接 await，需要由调用方处理
                return {"status": "async_scheduled", "message": "已调度异步执行"}
            else:
                return loop.run_until_complete(self.run(user_input, event_type))
        except RuntimeError:
            return asyncio.run(self.run(user_input, event_type))

    async def run(self, user_input: str, event_type: str = "player_action") -> dict[str, Any]:
        """异步执行一轮 Agent

        Args:
            user_input: 玩家输入
            event_type: 事件类型

        Returns:
            执行结果字典:
            {
                "narrative": str,
                "commands": list,
                "turn_count": int,
                "tokens_used": int,
                "latency_ms": int,
                "model": str,
            }
        """
        start_time = time.time()
        self._execution_state = "running"

        # 通知回合开始
        turn = self._initial_state.get("turn_count", 0) + 1
        event_bus.emit(create_turn_start_event(str(self._world_id), turn))

        try:
            # 准备输入状态
            input_state = {
                **self._initial_state,
                "current_event": {
                    "type": event_type,
                    "data": {"raw_text": user_input},
                    "context_hints": [],
                },
            }

            # 执行图
            result = await gm_graph.ainvoke(input_state)

            # 提取结果
            llm_response = result.get("llm_response", {})
            narrative = llm_response.get("content", "")
            commands = result.get("parsed_commands", [])
            command_results = result.get("command_results", [])

            latency_ms = int((time.time() - start_time) * 1000)

            # 更新内部状态
            self._initial_state["turn_count"] = result.get("turn_count", turn)
            self._initial_state["execution_state"] = "idle"
            self._execution_state = "idle"

            # 通知回合结束
            event_bus.emit(create_turn_end_event(
                world_id=str(self._world_id),
                turn_count=result.get("turn_count", turn),
                narrative=narrative,
                commands_count=len(commands),
                tokens_used=llm_response.get("tokens", 0),
                latency_ms=latency_ms,
            ))

            self._last_result = {
                "status": "success",
                "narrative": narrative,
                "commands": commands,
                "command_results": command_results,
                "turn_count": result.get("turn_count", turn),
                "tokens_used": llm_response.get("tokens", 0),
                "latency_ms": latency_ms,
                "model": llm_response.get("model", ""),
                "provider": llm_response.get("provider", ""),
            }

            return self._last_result

        except Exception as e:
            logger.error(f"Agent 执行失败: {e}")
            self._execution_state = "error"
            event_bus.emit(create_error_event(str(e)))
            return {
                "status": "error",
                "error": str(e),
                "narrative": f"[Agent 错误: {e}]",
            }

    async def stream(self, user_input: str, event_type: str = "player_action") -> AsyncGenerator[dict, None]:
        """流式执行一轮 Agent

        Yields:
            事件字典（token/command/error/complete）
        """
        # 流式执行通过 EventBus 间接实现
        # 上层通过订阅 EventBus 事件来获取流式数据
        result = await self.run(user_input, event_type)
        yield {"type": "complete", "data": result}

    @property
    def execution_state(self) -> str:
        return self._execution_state

    @property
    def last_result(self) -> dict[str, Any]:
        return self._last_result

    def get_state_snapshot(self) -> dict[str, Any]:
        """获取当前状态快照（用于 UI 显示）"""
        return {
            "world_id": self._world_id,
            "turn_count": self._initial_state.get("turn_count", 0),
            "execution_state": self._execution_state,
            "player": self._initial_state.get("player", {}),
            "location": self._initial_state.get("current_location", {}),
            "npcs": self._initial_state.get("active_npcs", []),
        }
