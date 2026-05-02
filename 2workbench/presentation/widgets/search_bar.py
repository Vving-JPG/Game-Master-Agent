"""搜索栏 — 带图标和清除按钮的搜索输入框"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QCompleter,
)
from PyQt6.QtCore import pyqtSignal, Qt


class SearchBar(QWidget):
    """搜索栏组件"""

    search_changed = pyqtSignal(str)
    search_submitted = pyqtSignal(str)

    def __init__(self, placeholder: str = "搜索...", parent=None):
        super().__init__(parent)
        self._setup_ui(placeholder)

    def _setup_ui(self, placeholder: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText(placeholder)
        self._line_edit.setClearButtonEnabled(True)
        self._line_edit.textChanged.connect(self.search_changed.emit)
        self._line_edit.returnPressed.connect(
            lambda: self.search_submitted.emit(self._line_edit.text())
        )
        layout.addWidget(self._line_edit)

    def text(self) -> str:
        return self._line_edit.text()

    def set_text(self, text: str) -> None:
        self._line_edit.setText(text)

    def set_completer(self, completer: QCompleter) -> None:
        self._line_edit.setCompleter(completer)

    def set_placeholder(self, text: str) -> None:
        self._line_edit.setPlaceholderText(text)
