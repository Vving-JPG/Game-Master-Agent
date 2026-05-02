"""通用 Widget 基类 — 提供主题感知和 EventBus 集成"""
from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QWidget

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger


class BaseWidget(QWidget):
    """通用 Widget 基类

    提供:
    1. 自动日志
    2. EventBus 订阅管理（自动清理）
    3. 主题感知
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._subscriptions: list[tuple[str, Any]] = []
        self._logger = get_logger(f"ui.{self.__class__.__name__}")

    def subscribe(self, event_type: str, handler) -> None:
        """订阅 EventBus 事件"""
        event_bus.subscribe(event_type, handler)
        self._subscriptions.append((event_type, handler))

    def unsubscribe_all(self) -> None:
        """取消所有订阅"""
        for event_type, handler in self._subscriptions:
            event_bus.unsubscribe(event_type, handler)
        self._subscriptions.clear()

    def closeEvent(self, event) -> None:
        """关闭时自动清理订阅"""
        self.unsubscribe_all()
        super().closeEvent(event)

    def emit_event(self, event_type: str, data: dict | None = None) -> list:
        """发出 EventBus 事件"""
        event = Event(
            type=event_type,
            data=data or {},
            source=f"ui.{self.__class__.__name__}",
        )
        return event_bus.emit(event)
