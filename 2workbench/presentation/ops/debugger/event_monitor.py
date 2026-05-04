# 2workbench/presentation/ops/debugger/event_monitor.py
"""EventBus 事件监视器 — 实时显示所有 EventBus 事件"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QLabel, QCheckBox,
)
from PyQt6.QtCore import Qt, QEvent

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger
from presentation.theme.manager import theme_manager
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class EventMonitor(BaseWidget):
    """EventBus 事件监视器

    使用通配符订阅捕获所有事件，不再使用 monkey-patching。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._event_count = 0
        self._filter_text = ""
        self._paused = False
        self._subscription_id: str | None = None
        self._setup_ui()
        self._subscribe_all()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("过滤事件类型...")
        self._filter_edit.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._filter_edit)

        self._btn_pause = StyledButton("⏸ 暂停", style_type="ghost")
        self._btn_pause.clicked.connect(self._toggle_pause)
        toolbar.addWidget(self._btn_pause)

        self._btn_clear = StyledButton("清空", style_type="ghost")
        self._btn_clear.clicked.connect(self.clear)
        toolbar.addWidget(self._btn_clear)

        toolbar.addStretch()

        self._count_label = QLabel("事件: 0")
        text_secondary = theme_manager.get_color("text_secondary")
        self._count_label.setStyleSheet(f"color: {text_secondary}; font-size: 11px;")
        toolbar.addWidget(self._count_label)

        layout.addLayout(toolbar)

        # 事件列表
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            "font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px;"
        )
        layout.addWidget(self._output)

    def _subscribe_all(self) -> None:
        """订阅所有事件（使用通配符 *）"""
        self._subscription_id = event_bus.subscribe("*", self._on_event)
        logger.info("EventBus 事件监视器已启动（通配符订阅）")

    def _unsubscribe_all(self) -> None:
        """取消订阅"""
        # 注意：当前 EventBus 的 subscribe 返回 None，无法取消订阅
        # 使用 _paused 标志来停止处理事件
        self._paused = True
        logger.info("EventBus 事件监视器已暂停")

    def closeEvent(self, event) -> None:
        """关闭时取消订阅"""
        self._unsubscribe_all()
        super().closeEvent(event)

    def _on_event(self, event: Event) -> None:
        """处理捕获的事件"""
        if self._paused:
            return

        if self._filter_text and self._filter_text not in event.type:
            return

        self._event_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        source = event.source or "unknown"
        data_preview = str(event.data)[:80] if event.data else "{}"

        # 根据事件类型着色
        color = theme_manager.get_color("text_primary")
        if "error" in event.type.lower():
            color = theme_manager.get_color("error")
        elif "warning" in event.type.lower():
            color = theme_manager.get_color("warning")
        elif "success" in event.type.lower() or "completed" in event.type.lower():
            color = theme_manager.get_color("success")

        # 格式化输出
        line = f'<span style="color: {color}">[{timestamp}] {event.type}</span>'
        line += f' <span style="color: gray">from {source}</span>'
        line += f'<br>  {data_preview}</br>'

        self._output.append(line)
        self._count_label.setText(f"事件: {self._event_count}")

        # 限制行数
        if self._event_count % 100 == 0:
            self._trim_output()

    def _trim_output(self) -> None:
        """限制输出行数"""
        lines = self._output.toPlainText().split("\n")
        if len(lines) > 1000:
            self._output.setPlainText("\n".join(lines[-500:]))

    def _on_filter_changed(self, text: str) -> None:
        """过滤文本变化"""
        self._filter_text = text.lower()

    def _toggle_pause(self) -> None:
        """暂停/恢复"""
        self._paused = not self._paused
        self._btn_pause.setText("▶ 继续" if self._paused else "⏸ 暂停")

    def clear(self) -> None:
        """清空显示"""
        self._output.clear()
        self._event_count = 0
        self._count_label.setText("事件: 0")
