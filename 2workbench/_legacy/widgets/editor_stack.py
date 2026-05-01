# workbench/widgets/editor_stack.py
"""中间多态编辑器栈 — 根据文件类型路由"""
from PyQt6.QtWidgets import QStackedWidget, QLabel
from PyQt6.QtCore import pyqtSlot, Qt
from pathlib import Path

from .widgets.md_editor import MarkdownEditor
from .widgets.yaml_editor import YamlEditor
from .widgets.kv_editor import KeyValueEditor
from .widgets.tool_viewer import ToolViewer
from .widgets.runtime_viewer import RuntimeViewer
from .widgets.workflow_editor import WorkflowEditor


class EditorStack(QStackedWidget):
    """多态编辑器 — 根据资源类型切换"""

    def __init__(self):
        super().__init__()
        self.current_file: str | None = None
        self.is_modified: bool = False

        # 占位页
        self.placeholder = QLabel("选择左侧资源以打开文件")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.addWidget(self.placeholder)

        # 各类型编辑器
        self.md_editor = MarkdownEditor()
        self.yaml_editor = YamlEditor()
        self.kv_editor = KeyValueEditor()
        self.tool_viewer = ToolViewer()
        self.runtime_viewer = RuntimeViewer()
        self.workflow_editor = WorkflowEditor()

        self.addWidget(self.md_editor)       # index 1
        self.addWidget(self.yaml_editor)     # index 2
        self.addWidget(self.kv_editor)       # index 3
        self.addWidget(self.tool_viewer)     # index 4
        self.addWidget(self.runtime_viewer)  # index 5
        self.addWidget(self.workflow_editor) # index 6

        # 监听编辑器修改
        self.md_editor.modificationChanged.connect(self._on_modified)
        self.yaml_editor.modificationChanged.connect(self._on_modified)

    def _on_modified(self, changed: bool):
        """编辑器内容修改"""
        self.is_modified = changed

    @pyqtSlot(str, str)
    def open_file(self, path: str, resource_type: str = "unknown"):
        """打开文件"""
        # 先保存当前文件（如果有修改）
        if self.is_modified and self.current_file:
            self.save_current()

        self.current_file = path
        self.is_modified = False

        # 运行时节点特殊处理
        if path.startswith("runtime://"):
            key = path.replace("runtime://", "")
            self.runtime_viewer.load(key, "")
            self.setCurrentIndex(5)
            return

        file_path = Path(path)
        if not file_path.exists():
            self.md_editor.load(f"# 文件不存在\n\n{path}", path)
            self.setCurrentIndex(1)
            return

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.md_editor.load(f"# 读取失败\n\n{e}", path)
            self.setCurrentIndex(1)
            return

        # 工作流文件特殊处理
        if resource_type == "workflow" or (path.endswith(".yaml") and "workflow" in path.lower()):
            self.workflow_editor.load_from_file(path)
            self.setCurrentIndex(6)
        elif resource_type == "skill":
            self.tool_viewer.load(content)
            self.setCurrentIndex(4)
        elif resource_type in ("current_turn", "turn_history", "event_log"):
            self.runtime_viewer.load(resource_type, content)
            self.setCurrentIndex(5)
        elif path.endswith(".env") or path.endswith(".cfg") or resource_type == "config":
            self.kv_editor.load(content, path)
            self.setCurrentIndex(3)
        elif path.endswith(".yaml") or path.endswith(".yml"):
            self.yaml_editor.load(content, path)
            self.setCurrentIndex(2)
        elif path.endswith(".md"):
            self.md_editor.load(content, path)
            self.setCurrentIndex(1)
        else:
            # 默认使用 Markdown 编辑器
            self.md_editor.load(content, path)
            self.setCurrentIndex(1)

    def save_current(self):
        """保存当前文件"""
        idx = self.currentIndex()
        if idx == 1:
            self.md_editor.save()
        elif idx == 2:
            self.yaml_editor.save()
        elif idx == 3:
            self.kv_editor.save()
        elif idx == 6:
            self.workflow_editor._save()
        self.is_modified = False
