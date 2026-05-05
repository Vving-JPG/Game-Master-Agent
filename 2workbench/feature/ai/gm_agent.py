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

新特性（LangGraph Checkpoint + Store）:
- 自动状态持久化（短期记忆）
- 跨会话记忆恢复
- 支持中断和恢复
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncGenerator

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger
from core.state import AgentState, create_initial_state
from core.models import WorldRepo, PlayerRepo, NPCRepo

# Repository 实例复用（无状态，可安全共享）
_world_repo = WorldRepo()
_player_repo = PlayerRepo()
_npc_repo = NPCRepo()

# 默认硬编码图（回退用）
from .graph import gm_graph as _default_gm_graph
from .events import (
    create_turn_start_event, create_turn_end_event, create_error_event,
    TURN_START, TURN_END, AGENT_ERROR,
)

# 新记忆系统
from .checkpoint_config import get_checkpointer, clear_checkpointer_cache
from .memory_store import get_memory_store, get_memory_store_wrapper, clear_store_cache
from .memory_manager import get_memory_manager, reset_memory_manager

logger = get_logger(__name__)


class GMAgent:
    """GM Agent — 游戏主持人 Agent

    这是整个 Agent 系统的统一入口。
    上层（Presentation）通过此类与 Agent 交互。

    集成 LangGraph Checkpoint + Store:
    - 短期记忆：通过 checkpointer 自动保存/恢复对话状态
    - 长期记忆：通过 store 持久化跨会话信息
    - 智能记忆：通过 memory_manager 提取和检索重要信息
    """

    def __init__(
        self,
        world_id: int = 1,
        db_path: str | None = None,
        system_prompt: str | None = None,
        skills_dir: str | None = None,
        auto_load_project_graph: bool = True,
        project_path: str | None = None,
        thread_id: str = "main_session",
    ):
        self._world_id = world_id
        self._db_path = db_path
        self._custom_system_prompt = system_prompt
        self._skills_dir = skills_dir
        self._execution_state = "idle"
        self._last_result: dict[str, Any] = {}
        self._thread_id = thread_id

        # 项目路径（用于 checkpoint 和 store）
        self._project_path = self._resolve_project_path(project_path)

        # 初始化记忆系统组件
        self._checkpointer = None
        self._store = None
        self._memory_wrapper = None
        self._memory_manager = None

        if self._project_path:
            self._init_memory_system()

        # 初始化 SkillLoader
        self._skill_loader = None
        if skills_dir:
            try:
                from feature.ai.skill_loader import SkillLoader
                self._skill_loader = SkillLoader(skills_dir)
            except Exception as e:
                logger.warning(f"SkillLoader 初始化失败: {e}")

        # 图实例（优先使用 graph.json 编译的图）
        self._graph = _default_gm_graph
        self._graph_source = "default"  # default / json

        # 自动加载项目图
        if auto_load_project_graph:
            self._load_project_graph()

        # 编译图（注入 checkpointer 和 store）
        self._compiled_graph = None
        self._compile_graph()

        # 加载游戏状态
        self._initial_state = self._load_initial_state()

    def _resolve_project_path(self, project_path: str | None) -> str | None:
        """解析项目路径"""
        if project_path:
            return project_path

        # 尝试从 project_manager 获取
        try:
            from feature.project import project_manager
            if project_manager.is_open and project_manager.project_path:
                return project_manager.project_path
        except Exception:
            pass

        # 尝试从 db_path 推断
        if self._db_path:
            import os
            db_dir = os.path.dirname(self._db_path)
            if db_dir and os.path.exists(db_dir):
                return db_dir

        logger.warning("未找到项目路径，记忆系统功能将受限")
        return None

    def _init_memory_system(self) -> None:
        """初始化记忆系统"""
        try:
            # 短期记忆：Checkpoint
            self._checkpointer = get_checkpointer(self._project_path)

            # 长期记忆：Store
            self._store = get_memory_store(self._project_path, use_sqlite=True)
            self._memory_wrapper = get_memory_store_wrapper(
                self._project_path,
                world_id=str(self._world_id),
                use_sqlite=True,
            )

            # 智能记忆管理
            self._memory_manager = get_memory_manager()

            logger.info(f"记忆系统已初始化: project={self._project_path}")
        except Exception as e:
            logger.error(f"记忆系统初始化失败: {e}")
            self._checkpointer = None
            self._store = None

    def _compile_graph(self) -> None:
        """编译图，注入 checkpointer 和 store"""
        try:
            if self._checkpointer and self._store:
                self._compiled_graph = self._graph.compile(
                    checkpointer=self._checkpointer,
                    store=self._store,
                )
                logger.info("图已编译（带 checkpoint 和 store）")
            else:
                self._compiled_graph = self._graph.compile()
                logger.info("图已编译（无 checkpoint）")
        except Exception as e:
            logger.error(f"图编译失败: {e}")
            self._compiled_graph = self._graph

    def _load_project_graph(self) -> None:
        """从当前打开的项目加载 graph.json 并编译"""
        try:
            from feature.project import project_manager
            if project_manager.is_open and project_manager.project_path:
                graph_data = project_manager.load_graph()
                if graph_data and graph_data.get("nodes"):
                    from feature.ai.graph_compiler import graph_compiler
                    compiled = graph_compiler.compile(graph_data)
                    self._graph = compiled
                    self._graph_source = "json"
                    logger.info(f"Agent 图已从项目加载: {project_manager.current_project.name}")
                    # 重新编译以注入 checkpoint/store
                    self._compile_graph()
        except Exception as e:
            logger.warning(f"加载项目图失败，使用默认图: {e}")
            self._graph = _default_gm_graph
            self._graph_source = "default"

    def set_graph(self, compiled_graph: Any, source: str = "json") -> None:
        """设置 Agent 使用的图实例

        Args:
            compiled_graph: 编译好的 StateGraph
            source: 图来源标识（"json" 或 "default"）
        """
        self._graph = compiled_graph
        self._graph_source = source
        # 重新编译以注入 checkpoint/store
        self._compile_graph()
        logger.info(f"Agent 图已更新: source={source}")

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

        # 注入自定义 system_prompt
        if self._custom_system_prompt:
            state["system_prompt"] = self._custom_system_prompt

        return state

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

        # === 设置工具上下文 ===
        from .tools import set_tool_context, ToolContext
        from foundation.config import settings
        ctx = ToolContext(
            db_path=self._db_path or settings.database_path,
            world_id=str(self._world_id),
            player_id=self._initial_state.get("player", {}).get("id", 1),
        )
        set_tool_context(ctx)

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

            # 执行图（使用配置中的 thread_id 以支持状态恢复）
            config = {"configurable": {"thread_id": self._thread_id}}

            # 如果有 compiled_graph（带 checkpoint），使用它
            graph = self._compiled_graph if self._compiled_graph else self._graph
            result = await graph.ainvoke(input_state, config=config)

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
        finally:
            # 清理工具上下文
            set_tool_context(None)

    def run_sync(self, user_input: str, event_type: str = "player_action") -> dict[str, Any]:
        """同步执行一轮 Agent（阻塞）

        注意: 此方法在事件循环已运行时（如 Qt 应用）可能无法正常工作。
        在 Presentation 层，建议使用 AgentThread 在独立线程中运行。

        Args:
            user_input: 玩家输入
            event_type: 事件类型

        Returns:
            执行结果字典
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 事件循环已在运行，无法同步执行
                logger.warning("事件循环已在运行，run_sync 无法执行。请在独立线程中使用 asyncio.run() 或 AgentThread")
                return {
                    "status": "error",
                    "error": "事件循环已在运行，无法同步执行。请使用异步接口或在独立线程中运行。",
                }
            else:
                return loop.run_until_complete(self.run(user_input, event_type))
        except RuntimeError:
            return asyncio.run(self.run(user_input, event_type))

    async def stream(self, user_input: str, event_type: str = "player_action") -> AsyncGenerator[dict, None]:
        """流式执行一轮 Agent

        Yields:
            事件字典（token/command/error/complete）
        """
        # 流式执行通过 EventBus 间接实现
        # 上层通过订阅 EventBus 事件来获取流式数据
        result = await self.run(user_input, event_type)
        yield {"type": "complete", "data": result}

    async def run_stream(self, user_input: str, event_type: str = "player_action") -> AsyncGenerator[dict, None]:
        """流式执行 Agent（支持中断）

        Yields:
            事件字典（token/command/error/complete）
        """
        config = {"configurable": {"thread_id": self._thread_id}}
        input_state = {
            **self._initial_state,
            "current_event": {
                "type": event_type,
                "data": {"raw_text": user_input},
                "context_hints": [],
            },
        }

        graph = self._compiled_graph if self._compiled_graph else self._graph

        async for event in graph.astream_events(
            input_state,
            config=config,
            version="v2",
        ):
            yield event

    def get_state(self) -> dict[str, Any] | None:
        """获取当前状态 — 用于调试面板

        Returns:
            当前状态或 None（如果没有 checkpoint）
        """
        if not self._compiled_graph:
            return None

        try:
            config = {"configurable": {"thread_id": self._thread_id}}
            return self._compiled_graph.get_state(config)
        except Exception as e:
            logger.warning(f"获取状态失败: {e}")
            return None

    def resume(self) -> Any:
        """从断点恢复 — TRPG 长剧情非常有用

        Returns:
            恢复执行的结果
        """
        if not self._compiled_graph:
            logger.warning("没有 compiled_graph，无法恢复")
            return None

        try:
            config = {"configurable": {"thread_id": self._thread_id}}
            return self._compiled_graph.ainvoke(None, config)
        except Exception as e:
            logger.error(f"恢复执行失败: {e}")
            return None

    @property
    def execution_state(self) -> str:
        return self._execution_state

    @property
    def last_result(self) -> dict[str, Any]:
        return self._last_result

    def get_state_snapshot(self) -> dict[str, Any]:
        """获取当前状态快照（用于 UI 显示）"""
        snapshot = {
            "world_id": self._world_id,
            "turn_count": self._initial_state.get("turn_count", 0),
            "execution_state": self._execution_state,
            "graph_source": self._graph_source,
            "player": self._initial_state.get("player", {}),
            "location": self._initial_state.get("current_location", {}),
            "npcs": self._initial_state.get("active_npcs", []),
            "has_checkpoint": self._checkpointer is not None,
            "has_store": self._store is not None,
            "thread_id": self._thread_id,
        }

        # 如果有 checkpoint，获取图状态
        if self._compiled_graph:
            try:
                state = self.get_state()
                if state:
                    snapshot["checkpoint_state"] = {
                        "messages_count": len(state.get("messages", [])),
                        "execution_state": state.get("execution_state", "unknown"),
                    }
            except Exception:
                pass

        return snapshot

    def reset_memory(self) -> None:
        """重置记忆（切换项目时调用）"""
        if self._project_path:
            clear_checkpointer_cache(self._project_path)
            clear_store_cache(self._project_path)
        reset_memory_manager()
        logger.info("Agent 记忆已重置")


# 便捷函数：创建带记忆系统的 Agent
def create_agent_with_memory(
    project_path: str,
    world_id: int = 1,
    thread_id: str = "main_session",
    **kwargs,
) -> GMAgent:
    """创建带完整记忆系统的 Agent

    Args:
        project_path: 项目路径
        world_id: 世界 ID
        thread_id: 会话线程 ID
        **kwargs: 其他参数传递给 GMAgent

    Returns:
        配置好的 GMAgent 实例
    """
    return GMAgent(
        world_id=world_id,
        project_path=project_path,
        thread_id=thread_id,
        auto_load_project_graph=True,
        **kwargs,
    )
