"""新建项目对话框"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QDialogButtonBox,
    QLabel,
)
from PyQt6.QtCore import Qt

from presentation.project.manager import PROJECT_TEMPLATES


class NewProjectDialog(QDialog):
    """新建 Agent 项目对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建 Agent 项目")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 表单
        form = QFormLayout()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("my_agent")
        form.addRow("项目名称:", self._name_edit)

        self._template_combo = QComboBox()
        for key, tmpl in PROJECT_TEMPLATES.items():
            self._template_combo.addItem(f"{tmpl['name']} — {tmpl['description']}", key)
        form.addRow("项目模板:", self._template_combo)

        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(80)
        self._desc_edit.setPlaceholderText("项目描述（可选）")
        form.addRow("描述:", self._desc_edit)

        layout.addLayout(form)

        # 模板预览
        self._preview_label = QLabel()
        self._preview_label.setStyleSheet("color: #858585; padding: 8px;")
        self._preview_label.setWordWrap(True)
        layout.addWidget(self._preview_label)
        self._update_preview()

        self._template_combo.currentIndexChanged.connect(self._update_preview)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_preview(self) -> None:
        """更新模板预览"""
        key = self._template_combo.currentData()
        if key and key in PROJECT_TEMPLATES:
            tmpl = PROJECT_TEMPLATES[key]
            nodes = tmpl["graph"]["nodes"]
            edges = tmpl["graph"]["edges"]
            self._preview_label.setText(
                f"模板: {tmpl['name']}\n"
                f"节点数: {len(nodes)} | 边数: {len(edges)}\n"
                f"Prompt 模板: {', '.join(tmpl['prompts'].keys())}"
            )

    def get_project_data(self) -> dict:
        """获取用户输入的项目数据"""
        return {
            "name": self._name_edit.text().strip(),
            "template": self._template_combo.currentData() or "blank",
            "description": self._desc_edit.toPlainText().strip(),
        }
