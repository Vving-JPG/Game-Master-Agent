# workbench/widgets/md_editor.py
"""Markdown 编辑器 — 支持 YAML Front Matter"""
from PyQt6.QtWidgets import (
    QPlainTextEdit, QWidget, QVBoxLayout, QLabel,
)
from PyQt6.QtCore import Qt
from pathlib import Path
import frontmatter


class MarkdownEditor(QWidget):
    """Markdown 编辑器，顶部显示 YAML Front Matter"""

    modificationChanged = None  # 由内部 editor 发射

    def __init__(self):
        super().__init__()
        self.current_file: str | None = None
        self._original_content: str = ""
        self._frontmatter: dict = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # FM 显示区
        self.fm_label = QLabel("")
        self.fm_label.setStyleSheet(
            "background-color: #2d2d2d; padding: 8px; color: #ce9178; "
            "border-bottom: 1px solid #3e3e3e; font-family: Consolas, monospace;"
        )
        self.fm_label.setWordWrap(True)
        self.fm_label.setVisible(False)
        layout.addWidget(self.fm_label)

        # 编辑区
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Markdown 编辑器")
        layout.addWidget(self.editor)

        # 转发信号
        self.modificationChanged = self.editor.modificationChanged

    def load(self, content: str, path: str):
        """加载文件"""
        self.current_file = path
        try:
            post = frontmatter.loads(content)
            self._frontmatter = dict(post.metadata)
            self._original_content = post.content

            if self._frontmatter:
                fm_lines = ["[YAML Front Matter]"]
                for k, v in self._frontmatter.items():
                    fm_lines.append(f"  {k}: {v}")
                self.fm_label.setText("\n".join(fm_lines))
                self.fm_label.setVisible(True)
            else:
                self.fm_label.setVisible(False)

            self.editor.setPlainText(post.content or "")
            self.editor.setModified(False)
        except Exception as e:
            self.fm_label.setVisible(False)
            self.editor.setPlainText(f"# 加载失败\n\n{e}")

    def save(self):
        """保存文件"""
        if not self.current_file:
            return
        content = self.editor.toPlainText()
        post = frontmatter.Post(content=content)
        post.metadata = self._frontmatter
        post["version"] = post.get("version", 0) + 1
        Path(self.current_file).write_text(frontmatter.dumps(post), encoding="utf-8")
        self._original_content = content
        self.editor.setModified(False)

    def toPlainText(self):
        return self.editor.toPlainText()

    def setPlainText(self, text: str):
        self.editor.setPlainText(text)
