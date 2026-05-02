# 2workbench/presentation/ops/logger_panel/log_viewer.py
"""日志追踪 — 运行日志查看和性能分析"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QComboBox, QCheckBox, QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class LogViewer(BaseWidget):
    """日志追踪查看器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_path: Path | None = None
        self._auto_scroll = True
        self._filters: dict[str, bool] = {
            "DEBUG": True,
            "INFO": True,
            "WARNING": True,
            "ERROR": True,
        }
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()

        self._btn_open = StyledButton("📂 打开日志", style_type="secondary")
        self._btn_open.clicked.connect(self._open_log)
        toolbar.addWidget(self._btn_open)

        toolbar.addStretch()

        # 级别过滤
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            cb = QCheckBox(level)
            cb.setChecked(True)
            cb.stateChanged.connect(lambda state, l=level: self._toggle_filter(l, state))
            toolbar.addWidget(cb)

        toolbar.addStretch()

        self._btn_auto_scroll = QCheckBox("自动滚动")
        self._btn_auto_scroll.setChecked(True)
        self._btn_auto_scroll.stateChanged.connect(lambda s: setattr(self, '_auto_scroll', bool(s)))
        toolbar.addWidget(self._btn_auto_scroll)

        self._btn_clear = StyledButton("清空", style_type="ghost")
        self._btn_clear.clicked.connect(lambda: self._output.clear())
        toolbar.addWidget(self._btn_clear)

        layout.addLayout(toolbar)

        # 日志输出
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            "font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px;"
        )
        layout.addWidget(self._output)

    def _toggle_filter(self, level: str, state) -> None:
        self._filters[level] = bool(state)

    def _open_log(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "打开日志文件", "", "日志 (*.log);;所有文件 (*)"
        )
        if path:
            self._log_path = Path(path)
            self._load_log()

    def _load_log(self) -> None:
        if not self._log_path or not self._log_path.exists():
            return
        try:
            content = self._log_path.read_text(encoding="utf-8")
            self._output.setPlainText(content)
        except Exception as e:
            logger.error(f"日志加载失败: {e}")

    def append_log(self, level: str, message: str, source: str = "") -> None:
        """追加日志条目"""
        if not self._filters.get(level, True):
            return

        color_map = {
            "DEBUG": "#858585",
            "INFO": "#cccccc",
            "WARNING": "#dcdcaa",
            "ERROR": "#f44747",
        }
        color = color_map.get(level, "#cccccc")
        timestamp = datetime.now().strftime("%H:%M:%S")

        self._output.append(
            f'<span style="color: #858585;">[{timestamp}]</span> '
            f'<span style="color: {color}; font-weight: bold;">[{level}]</span> '
            f'<span style="color: #6e6e6e;">{source}</span> '
            f'<span style="color: {color};">{message}</span>'
        )

        if self._auto_scroll:
            scrollbar = self._output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
