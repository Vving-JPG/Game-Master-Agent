# 2workbench/presentation/ops/logger_panel/log_viewer.py
"""日志追踪 — 运行日志查看和性能分析"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QComboBox, QCheckBox, QFileDialog,
    QLineEdit, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher

from foundation.logger import get_logger
from presentation.theme.manager import theme_manager
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
        self._watcher = QFileSystemWatcher()
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()

        self._btn_open = StyledButton("📂 打开日志", style_type="secondary")
        self._btn_open.clicked.connect(self._open_log)
        toolbar.addWidget(self._btn_open)

        # 搜索框
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍 搜索日志...")
        self._search_edit.setMaximumWidth(200)
        self._search_edit.returnPressed.connect(self._search_in_log)
        toolbar.addWidget(self._search_edit)

        self._btn_search = StyledButton("查找", style_type="ghost")
        self._btn_search.clicked.connect(self._search_in_log)
        toolbar.addWidget(self._btn_search)

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
        # 切换筛选后刷新日志显示
        self._refresh_with_filters()

    def _search_in_log(self) -> None:
        """在日志中搜索关键词"""
        keyword = self._search_edit.text().strip()
        if not keyword:
            return

        cursor = self._output.textCursor()
        document = self._output.document()

        # 从当前位置开始查找
        found = document.find(keyword, cursor)
        if not found.isNull():
            self._output.setTextCursor(found)
            self._output.ensureCursorVisible()
        else:
            # 如果没找到，从头开始查找
            cursor.movePosition(cursor.MoveOperation.Start)
            found = document.find(keyword, cursor)
            if not found.isNull():
                self._output.setTextCursor(found)
                self._output.ensureCursorVisible()

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
            # 应用级别筛选
            filtered_content = self._apply_filters(content)
            self._output.setPlainText(filtered_content)
            # 添加文件监控
            if str(self._log_path) not in self._watcher.files():
                self._watcher.addPath(str(self._log_path))
        except Exception as e:
            logger.error(f"日志加载失败: {e}")

    def _apply_filters(self, content: str) -> str:
        """根据级别筛选日志内容

        Args:
            content: 原始日志内容

        Returns:
            筛选后的日志内容
        """
        lines = content.split('\n')
        filtered_lines = []

        for line in lines:
            # 检查行中包含的日志级别
            for level, enabled in self._filters.items():
                if enabled and f"│ {level}" in line:
                    filtered_lines.append(line)
                    break

        return '\n'.join(filtered_lines)

    def _refresh_with_filters(self) -> None:
        """使用当前筛选器重新加载日志"""
        if self._log_path and self._log_path.exists():
            try:
                content = self._log_path.read_text(encoding="utf-8")
                filtered_content = self._apply_filters(content)
                self._output.setPlainText(filtered_content)
            except Exception as e:
                logger.error(f"刷新日志失败: {e}")

    def _on_file_changed(self, path: str) -> None:
        """文件变化时自动刷新"""
        if self._auto_scroll and self._log_path and str(self._log_path) == path:
            try:
                if self._log_path.exists():
                    self._refresh_with_filters()
                    scrollbar = self._output.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())
                    # 重新添加监控（某些编辑器会创建新文件）
                    if str(self._log_path) not in self._watcher.files():
                        self._watcher.addPath(str(self._log_path))
            except Exception as e:
                logger.debug(f"日志文件监控异常: {e}")

    def append_log(self, level: str, message: str, source: str = "") -> None:
        """追加日志条目"""
        if not self._filters.get(level, True):
            return

        color_map = {
            "DEBUG": theme_manager.get_color("text_secondary"),
            "INFO": theme_manager.get_color("text_primary"),
            "WARNING": theme_manager.get_color("warning"),
            "ERROR": theme_manager.get_color("error"),
        }
        color = color_map.get(level, theme_manager.get_color("text_primary"))
        timestamp = datetime.now().strftime("%H:%M:%S")

        text_secondary = theme_manager.get_color("text_secondary")
        text_disabled = theme_manager.get_color("border")
        self._output.append(
            f'<span style="color: {text_secondary};">[{timestamp}]</span> '
            f'<span style="color: {color}; font-weight: bold;">[{level}]</span> '
            f'<span style="color: {text_disabled};">{source}</span> '
            f'<span style="color: {color};">{message}</span>'
        )

        if self._auto_scroll:
            scrollbar = self._output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def load_project_log(self, project_path: Path | str) -> None:
        """自动加载项目日志文件

        Args:
            project_path: 项目根目录路径
        """
        import os
        from datetime import datetime

        project_path = Path(project_path)

        # 尝试多个可能的日志路径（项目级）
        possible_paths = [
            project_path / "logs" / f"{datetime.now().strftime('%Y-%m-%d')}.log",
            project_path / "logs" / "app.log",
            project_path / "app.log",
        ]

        # 查找最新的日志文件
        log_dir = project_path / "logs"
        if log_dir.exists():
            log_files = sorted(log_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
            if log_files:
                possible_paths.insert(0, log_files[0])

        # 尝试应用级日志（2workbench/data/logs/）
        app_log_paths = [
            Path("data/logs/app.log"),
            Path("./data/logs/app.log"),
            Path(__file__).parent.parent.parent / "data/logs/app.log",
        ]
        possible_paths.extend(app_log_paths)

        for log_path in possible_paths:
            if log_path.exists():
                self._log_path = log_path
                self._load_log()
                logger.info(f"已加载日志: {log_path}")
                return

        # 如果没有找到日志文件，显示提示信息
        self._output.setPlainText("未找到日志文件。\n\n可能的位置:\n- 项目/logs/*.log\n- data/logs/app.log")
        logger.warning(f"未找到日志文件，已尝试: {[str(p) for p in possible_paths]}")
