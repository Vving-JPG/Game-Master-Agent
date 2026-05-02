"""Feature 模块基类 — 定义通用接口和生命周期

所有 Feature 模块（Battle/Dialogue/Quest/...）继承此基类。
通过 EventBus 与其他模块通信，禁止直接依赖。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger


class BaseFeature(ABC):
    """Feature 模块基类

    生命周期:
    1. __init__ — 初始化（注册 EventBus 订阅）
    2. on_enable — 启用（加载资源、初始化状态）
    3. on_disable — 禁用（释放资源）
    4. on_event — 处理 EventBus 事件

    使用方式:
        class BattleSystem(BaseFeature):
            name = "battle"

            def handle_combat_start(self, event: Event):
                ...

            def on_enable(self):
                self.subscribe("feature.battle.start", self.handle_combat_start)
    """

    name: str = ""  # 子类必须设置

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path
        self._enabled = False
        self._subscriptions: list[tuple[str, Any]] = []
        self._logger = get_logger(f"feature.{self.name}")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def on_enable(self) -> None:
        """启用 Feature（子类重写以注册 EventBus 订阅）"""
        self._enabled = True
        self._logger.info(f"[{self.name}] 已启用")

    def on_disable(self) -> None:
        """禁用 Feature（子类重写以清理资源）"""
        self._enabled = False
        # 取消所有订阅
        for event_type, handler in self._subscriptions:
            event_bus.unsubscribe(event_type, handler)
        self._subscriptions.clear()
        self._logger.info(f"[{self.name}] 已禁用")

    def subscribe(self, event_type: str, handler) -> None:
        """订阅 EventBus 事件（记录以便清理）"""
        event_bus.subscribe(event_type, handler)
        self._subscriptions.append((event_type, handler))

    def emit(self, event_type: str, data: dict | None = None) -> list:
        """发出 EventBus 事件"""
        event = Event(
            type=event_type,
            data=data or {},
            source=f"feature.{self.name}",
        )
        return event_bus.emit(event)

    async def emit_async(self, event_type: str, data: dict | None = None) -> list:
        """异步发出 EventBus 事件"""
        event = Event(
            type=event_type,
            data=data or {},
            source=f"feature.{self.name}",
        )
        return await event_bus.emit_async(event)

    def get_state(self) -> dict[str, Any]:
        """获取 Feature 状态（用于 UI 展示）"""
        return {"name": self.name, "enabled": self._enabled}
