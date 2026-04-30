# workbench/widgets/runtime_viewer.py
"""运行时查看器 (只读)"""
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout


class RuntimeViewer(QWidget):
    """运行时数据查看器"""

    modificationChanged = None

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setPlaceholderText("运行时数据查看器 (只读)")
        layout.addWidget(self.editor)

    def load(self, key: str, content: str):
        self.editor.setPlainText(f"[{key}]\n\n{content or '(暂无数据)'}")
