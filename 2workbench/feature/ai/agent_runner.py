"""Agent 运行管理器 — Feature 层

负责监听 UI 请求并执行 Agent 运行。
通过 EventBus 与 Presentation 层通信。
"""
from __future__ import annotations

import asyncio
from typing import Any

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger
from foundation.config import settings
from feature.project import project_manager

logger = get_logger(__name__)


class AgentRunner:
    """Agent 运行管理器

    监听 UI 发出的运行请求，执行 Agent 并返回结果。
    所有通信通过 EventBus 进行，保持与 UI 解耦。
    """

    def __init__(self):
        self._current_agent = None
        self._setup_listeners()

    def _setup_listeners(self):
        """设置 EventBus 监听器"""
        event_bus.subscribe("ui.agent.run_requested", self._on_run_requested)
        event_bus.subscribe("ui.agent.stop_requested", self._on_stop_requested)

    def _on_run_requested(self, event: Event):
        """处理运行请求

        Args:
            event: 包含 world_id, user_input 等数据
        """
        world_id = event.data.get("world_id", 1)
        user_input = event.data.get("user_input", "")
        db_path = event.data.get("db_path") or settings.database_path

        logger.info(f"收到 Agent 运行请求: world_id={world_id}")

        try:
            # 导入并创建 Agent
            from feature.ai.gm_agent import GMAgent
            agent = GMAgent(world_id=world_id, db_path=db_path)

            # 尝试加载项目编译的图
            try:
                if project_manager.is_open:
                    compiled_graph = project_manager.compile_graph()
                    agent.set_graph(compiled_graph, source="json")
                    logger.info("使用项目编译的图运行 Agent")
            except Exception as e:
                logger.warning(f"项目图编译失败，使用默认图: {e}")

            self._current_agent = agent

            # 发出 Agent 准备完成事件
            # Presentation 层应监听此事件并启动 AgentThread
            event_bus.emit(Event(
                type="feature.agent.prepared",
                data={
                    "world_id": world_id,
                    "user_input": user_input,
                    "agent_ready": True,
                },
            ))
            logger.info("Agent 准备完成，等待 UI 层启动运行")

        except Exception as e:
            logger.error(f"Agent 运行准备失败: {e}")
            event_bus.emit(Event(
                type="feature.agent.run_failed",
                data={"error": str(e)},
            ))

    def _on_stop_requested(self, event: Event):
        """处理停止请求"""
        logger.info("收到 Agent 停止请求")
        event_bus.emit(Event(type="feature.agent.stop_requested", data={}))

    def get_current_agent(self):
        """获取当前 Agent 实例（供外部使用）"""
        return self._current_agent


# 全局单例
agent_runner = AgentRunner()
