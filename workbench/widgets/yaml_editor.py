# workbench/widgets/yaml_editor.py
"""YAML 编辑器"""
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout
from pathlib import Path


class YamlEditor(QWidget):
    """YAML 编辑器"""

    modificationChanged = None

    def __init__(self):
        super().__init__()
        self.current_file: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("YAML 编辑器")
        layout.addWidget(self.editor)
        self.modificationChanged = self.editor.modificationChanged

    def load(self, content: str, path: str):
        self.current_file = path
        self.editor.setPlainText(content)
        self.editor.setModified(False)

    def save(self):
        if not self.current_file:
            return
        Path(self.current_file).write_text(self.editor.toPlainText(), encoding="utf-8")
        self.editor.setModified(False)
