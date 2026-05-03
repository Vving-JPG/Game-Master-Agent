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
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class EventMonitor(BaseWidget):
    """EventBus 事件监视器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._event_count = 0
        self._filter_text = ""
        self._paused = False
        self._original_emit = None
        self._setup_ui()
        self._install_hook()

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
        self._count_label.setStyleSheet("color: #858585; font-size: 11px;")
        toolbar.addWidget(self._count_label)

        layout.addLayout(toolbar)

        # 事件列表
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            "font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px;"
        )
        layout.addWidget(self._output)

    def _install_hook(self) -> None:
        """安装 EventBus 钩子，捕获所有事件"""
        self._original_emit = event_bus.emit
        event_bus.emit = self._hooked_emit
        logger.info("EventBus 钩子已安装")

    def _hooked_emit(self, event: Event) -> list:
        """钩子函数：捕获事件并转发"""
        if not self._paused:
            self._on_event(event)
        return self._original_emit(event)

    def _uninstall_hook(self) -> None:
        """卸载 EventBus 钩子"""
        if self._original_emit is not None:
            event_bus.emit = self._original_emit
            self._original_emit = None
            logger.info("EventBus 钩子已卸载")

    def closeEvent(self, event) -> None:
        """关闭时恢复原始 emit"""
        self._uninstall_hook()
        super().closeEvent(event)

    def _on_event(self, event: Event) -> None:
        """处理捕获的事件"""
        if self._filter_text and self._filter_text not in event.type:
            return

        self._event_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        source = event.source or "unknown"
        data_preview = str(event.data)[:80] if event.data else "{}"

        # 根据事件类型着色
        color = "#cccccc"
        if "error" in event.type.lower():
            color = "#f44747"
        elif "stream" in event.type.lower():
            color = "#4ec9b0"
        elif "turn" in event.type.lower():
            color = "#569cd6"
        elif "command" in event.type.lower():
            color = "#dcdcaa"

        self._output.append(
            f'<span style="color: #858585;">[{timestamp}]</span> '
            f'<span style="color: {color};">{event.type}</span> '
            f'<span style="color: #6e6e6e;">← {source}</span> '
            f'<span style="color: #858585;">{data_preview}</span>'
        )

        self._count_label.setText(f"事件: {self._event_count}")

        # 限制行数
        if self._output.document().blockCount() > 2000:
            cursor = self._output.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.KeepAnchor, 500)
            cursor.removeSelectedText()

    def _on_filter_changed(self, text: str) -> None:
        self._filter_text = text

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self._btn_pause.setText("▶ 继续" if self._paused else "⏸ 暂停")

    def clear(self) -> None:
        self._output.clear()
        self._event_count = 0
        self._count_label.setText("事件: 0")
