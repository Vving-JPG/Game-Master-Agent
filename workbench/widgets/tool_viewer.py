# workbench/widgets/tool_viewer.py
"""工具查看器 (只读)"""
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout


class ToolViewer(QWidget):
    """工具定义查看器"""

    modificationChanged = None

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setPlaceholderText("工具定义查看器 (只读)")
        layout.addWidget(self.editor)

    def load(self, content: str):
        self.editor.setPlainText(content)
