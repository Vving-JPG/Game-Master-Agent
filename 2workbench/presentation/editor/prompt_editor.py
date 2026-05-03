"""Prompt 管理器 — 模板编辑、版本管理、变量注入、预览测试

功能:
1. Prompt 模板列表（左侧）
2. Prompt 编辑器（中央，Markdown 高亮）
3. 变量面板（右侧，自动提取 {variable}）
4. 版本历史
5. 预览/测试面板
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QLabel, QPushButton, QFormLayout, QDialog,
    QDialogButtonBox, QComboBox, QTextBrowser,
    QMenu,
)
from PyQt6.QtCore import pyqtSignal, Qt

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton
from presentation.widgets.search_bar import SearchBar

logger = get_logger(__name__)


@dataclass
class PromptVersion:
    """Prompt 版本"""
    content: str
    timestamp: str = ""
    note: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class PromptEditorWidget(BaseWidget):
    """Prompt 管理器组件"""

    prompt_changed = pyqtSignal(str, str)  # name, content

    def __init__(self, parent=None):
        super().__init__(parent)
        self._prompts: dict[str, str] = {}  # name -> content
        self._versions: dict[str, list[PromptVersion]] = {}  # name -> versions
        self._current_prompt: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: Prompt 列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self._search = SearchBar("搜索 Prompt...")
        self._search.search_changed.connect(self._filter_prompt_table)
        left_layout.addWidget(self._search)

        self._prompt_list = QListWidget()
        self._prompt_list.currentRowChanged.connect(self._on_prompt_selected)
        self._prompt_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._prompt_list.customContextMenuRequested.connect(self._on_list_context_menu)
        left_layout.addWidget(self._prompt_list)

        self._btn_new = StyledButton("+ 新建 Prompt", style_type="primary")
        self._btn_new.clicked.connect(self._new_prompt)
        left_layout.addWidget(self._btn_new)

        splitter.addWidget(left)

        # 中央: 编辑器
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(4, 4, 4, 4)

        # Prompt 名称
        name_layout = QHBoxLayout()
        self._name_label = QLabel("Prompt: ")
        self._name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self._name_edit = QLineEdit()
        self._name_edit.setReadOnly(True)
        name_layout.addWidget(self._name_label)
        name_layout.addWidget(self._name_edit, 1)
        center_layout.addLayout(name_layout)

        # 编辑器
        self._editor = QTextEdit()
        self._editor.setPlaceholderText("在此编辑 Prompt 模板...\n\n使用 {variable} 定义变量")
        self._editor.textChanged.connect(self._on_text_changed)
        center_layout.addWidget(self._editor)

        # 底部工具栏
        toolbar = QHBoxLayout()
        self._btn_save = StyledButton("💾 保存", style_type="primary")
        self._btn_save.clicked.connect(self._save_prompt)
        toolbar.addWidget(self._btn_save)

        self._btn_preview = StyledButton("👁 预览", style_type="secondary")
        self._btn_preview.clicked.connect(self._preview_prompt)
        toolbar.addWidget(self._btn_preview)

        self._btn_history = StyledButton("📜 历史", style_type="secondary")
        self._btn_history.clicked.connect(self._show_history)
        toolbar.addWidget(self._btn_history)

        toolbar.addStretch()

        self._var_count_label = QLabel("变量: 0")
        self._var_count_label.setStyleSheet("color: #858585;")
        toolbar.addWidget(self._var_count_label)

        center_layout.addLayout(toolbar)
        splitter.addWidget(center)

        # 右侧: 变量面板
        right = QWidget()
        right.setMaximumWidth(250)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        var_label = QLabel("📋 变量列表")
        var_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        right_layout.addWidget(var_label)

        self._var_list = QListWidget()
        right_layout.addWidget(self._var_list)

        # 变量值编辑
        self._var_value_edit = QLineEdit()
        self._var_value_edit.setPlaceholderText("变量值（预览用）")
        right_layout.addWidget(self._var_value_edit)

        self._btn_set_var = StyledButton("设置变量值", style_type="ghost")
        self._btn_set_var.clicked.connect(self._set_variable_value)
        right_layout.addWidget(self._btn_set_var)

        # 预览区
        preview_label = QLabel("👁 预览")
        preview_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 8px;")
        right_layout.addWidget(preview_label)

        self._preview_browser = QTextBrowser()
        self._preview_browser.setStyleSheet("font-size: 12px;")
        right_layout.addWidget(self._preview_browser)

        splitter.addWidget(right)

        splitter.setSizes([200, 500, 250])
        layout.addWidget(splitter)

        # 变量值存储
        self._var_values: dict[str, str] = {}

    def load_prompts(self, prompts: dict[str, str]) -> None:
        """加载 Prompt 集合

        Args:
            prompts: {name: content}
        """
        self._prompts = prompts
        self._prompt_list.clear()

        for name in sorted(prompts.keys()):
            self._prompt_list.addItem(name)
            # 初始化版本
            if name not in self._versions:
                self._versions[name] = [
                    PromptVersion(content=prompts[name], note="初始版本")
                ]

        if self._prompt_list.count() > 0:
            self._prompt_list.setCurrentRow(0)

    def get_prompts(self) -> dict[str, str]:
        """获取所有 Prompt"""
        return dict(self._prompts)

    def get_prompt(self, name: str) -> str:
        """获取指定 Prompt"""
        return self._prompts.get(name, "")

    def _on_prompt_selected(self, row: int) -> None:
        """选中 Prompt"""
        if row < 0:
            return
        name = self._prompt_list.item(row).text()
        self._current_prompt = name
        self._name_edit.setText(name)
        self._editor.setPlainText(self._prompts.get(name, ""))
        self._update_variables()

    def _on_text_changed(self) -> None:
        """文本变化时更新变量列表"""
        self._update_variables()

    def _update_variables(self) -> None:
        """提取并显示变量"""
        content = self._editor.toPlainText()
        variables = set(re.findall(r'\{(\w+)\}', content))
        self._var_list.clear()
        for var in sorted(variables):
            self._var_list.addItem(var)
        self._var_count_label.setText(f"变量: {len(variables)}")

    def _save_prompt(self) -> None:
        """保存当前 Prompt 到内存 + 持久化到文件"""
        if not self._current_prompt:
            return
        content = self._editor.toPlainText()
        self._prompts[self._current_prompt] = content

        # 保存版本
        if self._current_prompt not in self._versions:
            self._versions[self._current_prompt] = []
        self._versions[self._current_prompt].append(
            PromptVersion(content=content, note="手动保存")
        )

        # === 持久化到文件 ===
        try:
            from presentation.project.manager import project_manager
            project_manager.save_prompt(self._current_prompt, content)
            logger.info(f"Prompt 已持久化: {self._current_prompt} ({len(content)} 字符)")
        except Exception as e:
            logger.error(f"Prompt 持久化失败: {e}")

        self.prompt_changed.emit(self._current_prompt, content)

    def _preview_prompt(self) -> None:
        """预览 Prompt（替换变量）"""
        content = self._editor.toPlainText()
        preview = content
        for var, value in self._var_values.items():
            preview = preview.replace(f"{{{var}}}", value)
        self._preview_browser.setPlainText(preview)

    def _set_variable_value(self) -> None:
        """设置当前选中变量的值"""
        current = self._var_list.currentItem()
        if not current:
            return
        var_name = current.text()
        value = self._var_value_edit.text()
        self._var_values[var_name] = value
        self._var_value_edit.clear()
        self._preview_prompt()

    def _new_prompt(self) -> None:
        """新建 Prompt"""
        name = f"prompt_{len(self._prompts) + 1}"
        self._prompts[name] = f"# {name}\n\n在此编写 Prompt 模板..."
        self._versions[name] = [PromptVersion(content=self._prompts[name], note="新建")]
        self._prompt_list.addItem(name)
        self._prompt_list.setCurrentRow(self._prompt_list.count() - 1)

    def _show_history(self) -> None:
        """显示版本历史"""
        if not self._current_prompt:
            return
        versions = self._versions.get(self._current_prompt, [])
        if not versions:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"版本历史 — {self._current_prompt}")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        for i, v in enumerate(reversed(versions)):
            list_widget.addItem(f"[{v.timestamp}] {v.note} ({len(v.content)} 字符)")
        layout.addWidget(list_widget)

        detail = QTextEdit()
        detail.setReadOnly(True)
        list_widget.currentRowChanged.connect(
            lambda row: detail.setPlainText(versions[len(versions) - 1 - row].content)
            if 0 <= row < len(versions) else None
        )
        layout.addWidget(detail)

        if versions:
            list_widget.setCurrentRow(0)

        dialog.exec()

    def _on_list_context_menu(self, pos) -> None:
        """右键菜单"""
        menu = QMenu()
        menu.addAction("重命名", self._rename_prompt)
        menu.addAction("删除", self._delete_prompt)
        menu.exec(self._prompt_list.mapToGlobal(pos))

    def _rename_prompt(self) -> None:
        """重命名 Prompt"""
        current = self._prompt_list.currentItem()
        if not current:
            return
        old_name = current.text()
        # 简单实现: 使用输入对话框
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=old_name)
        if ok and new_name and new_name != old_name:
            self._prompts[new_name] = self._prompts.pop(old_name)
            self._versions[new_name] = self._versions.pop(old_name, [])
            current.setText(new_name)
            self._current_prompt = new_name
            self._name_edit.setText(new_name)

    def _delete_prompt(self) -> None:
        """删除 Prompt"""
        current = self._prompt_list.currentItem()
        if not current:
            return
        name = current.text()
        self._prompts.pop(name, None)
        self._versions.pop(name, None)
        row = self._prompt_list.row(current)
        self._prompt_list.takeItem(row)
        if self._current_prompt == name:
            self._current_prompt = None
            self._editor.clear()
            self._name_edit.clear()

    def _filter_prompt_table(self, keyword: str) -> None:
        """根据关键词过滤 Prompt 列表"""
        keyword = keyword.lower()
        for i in range(self._prompt_list.count()):
            item = self._prompt_list.item(i)
            match = keyword == "" or keyword in item.text().lower()
            self._prompt_list.setItemHidden(item, not match)
