"""工具注册服务 — 通过 EventBus 处理工具注册请求

将 Presentation 层的工具注册请求转换为实际的工具注册。
"""
from __future__ import annotations

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger

logger = get_logger(__name__)


class ToolRegistrationService:
    """工具注册服务

    监听 UI 发出的工具注册请求，执行实际的工具注册。
    所有通信通过 EventBus 进行，保持与 UI 解耦。
    """

    def __init__(self):
        self._setup_listeners()

    def _setup_listeners(self):
        """设置 EventBus 监听器"""
        event_bus.subscribe("ui.tool.register_requested", self._on_register_requested)

    def _on_register_requested(self, event: Event):
        """处理工具注册请求

        Args:
            event: 包含 name, description, parameters_schema 等数据
        """
        name = event.data.get("name", "")
        description = event.data.get("description", "")
        parameters_schema = event.data.get("parameters_schema", {})

        if not name:
            logger.error("工具注册请求缺少名称")
            event_bus.emit(Event(
                type="feature.tool.register_failed",
                data={"error": "工具名称不能为空"},
            ))
            return

        try:
            from feature.ai.tools.registry import register_tool

            # 创建默认 handler（实际项目中可能需要更复杂的逻辑）
            def handler(**kwargs):
                return f"工具 {name} 执行: {kwargs}"

            register_tool(
                name=name,
                description=description,
                parameters_schema=parameters_schema,
                handler=handler,
            )

            logger.info(f"工具注册成功: {name}")
            event_bus.emit(Event(
                type="feature.tool.registered",
                data={"name": name, "success": True},
            ))

        except Exception as e:
            logger.error(f"工具注册失败: {e}")
            event_bus.emit(Event(
                type="feature.tool.register_failed",
                data={"name": name, "error": str(e)},
            ))


# 全局单例
tool_registration_service = ToolRegistrationService()
