# 2workbench/presentation/ops/safety/safety_panel.py
"""安全护栏面板 — 内容过滤规则配置

功能:
1. 敏感词管理（添加/删除/分类）
2. 输出过滤规则（正则表达式）
3. 内容审核模式（严格/标准/宽松）
4. 实时过滤预览
5. 规则导入/导出
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QLabel, QListWidget, QListWidgetItem,
    QTabWidget, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QFileDialog, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class SafetyLevel(Enum):
    """安全级别"""
    STRICT = "strict"      # 严格: 所有规则启用
    STANDARD = "standard"  # 标准: 大部分规则启用
    RELAXED = "relaxed"    # 宽松: 仅关键规则启用


@dataclass
class FilterRule:
    """过滤规则"""
    id: str = ""
    name: str = ""
    pattern: str = ""       # 正则表达式
    category: str = "custom"  # violence / sexual / political / custom
    level: str = "standard"   # strict / standard / relaxed
    enabled: bool = True
    replacement: str = "***"  # 替换文本


# 默认过滤规则
DEFAULT_RULES = [
    FilterRule(id="r1", name="暴力内容", pattern=r"(杀|砍|斩|刺|血腥)", category="violence", level="strict"),
    FilterRule(id="r2", name="色情内容", pattern=r"(裸|性|色情)", category="sexual", level="strict"),
    FilterRule(id="r3", name="政治敏感", pattern=r"(政治|敏感|领导人)", category="political", level="standard"),
]


class SafetyPanel(BaseWidget):
    """安全护栏面板"""

    rules_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[FilterRule] = list(DEFAULT_RULES)
        self._safety_level = SafetyLevel.STANDARD
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 安全级别选择
        level_bar = QHBoxLayout()
        level_bar.addWidget(QLabel("🔒 安全级别:"))
        self._level_combo = QComboBox()
        self._level_combo.addItems(["严格", "标准", "宽松"])
        self._level_combo.setCurrentText("标准")
        self._level_combo.currentTextChanged.connect(self._on_level_changed)
        level_bar.addWidget(self._level_combo)

        level_bar.addStretch()

        self._btn_import = StyledButton("📥 导入规则", style_type="ghost")
        self._btn_import.clicked.connect(self._import_rules)
        level_bar.addWidget(self._btn_import)

        self._btn_export = StyledButton("📤 导出规则", style_type="ghost")
        self._btn_export.clicked.connect(self._export_rules)
        level_bar.addWidget(self._btn_export)

        layout.addLayout(level_bar)

        # 主内容
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: 规则列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self._rule_list = QListWidget()
        self._rule_list.currentRowChanged.connect(self._on_rule_selected)
        left_layout.addWidget(self._rule_list)

        rule_toolbar = QHBoxLayout()
        self._btn_add = StyledButton("+ 添加规则", style_type="primary")
        self._btn_add.clicked.connect(self._add_rule)
        rule_toolbar.addWidget(self._btn_add)

        self._btn_delete = StyledButton("删除", style_type="danger")
        self._btn_delete.clicked.connect(self._delete_rule)
        rule_toolbar.addWidget(self._btn_delete)

        left_layout.addLayout(rule_toolbar)
        splitter.addWidget(left)

        # 右侧: 规则编辑 + 预览
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)

        # 规则编辑
        edit_group = QGroupBox("规则编辑")
        edit_layout = QFormLayout(edit_group)

        self._name_edit = QLineEdit()
        edit_layout.addRow("名称:", self._name_edit)

        self._pattern_edit = QLineEdit()
        self._pattern_edit.setPlaceholderText("正则表达式，如 (暴力|血腥)")
        edit_layout.addRow("匹配模式:", self._pattern_edit)

        self._category_combo = QComboBox()
        self._category_combo.addItems(["violence", "sexual", "political", "custom"])
        edit_layout.addRow("分类:", self._category_combo)

        self._rule_level_combo = QComboBox()
        self._rule_level_combo.addItems(["strict", "standard", "relaxed"])
        edit_layout.addRow("级别:", self._rule_level_combo)

        self._replacement_edit = QLineEdit()
        self._replacement_edit.setText("***")
        edit_layout.addRow("替换为:", self._replacement_edit)

        self._enabled_check = QCheckBox("启用")
        self._enabled_check.setChecked(True)
        edit_layout.addRow("状态:", self._enabled_check)

        self._btn_save_rule = StyledButton("💾 保存规则", style_type="primary")
        self._btn_save_rule.clicked.connect(self._save_rule)
        edit_layout.addRow(self._btn_save_rule)

        right_layout.addWidget(edit_group)

        # 过滤预览
        preview_group = QGroupBox("过滤预览")
        preview_layout = QVBoxLayout(preview_group)

        self._preview_input = QTextEdit()
        self._preview_input.setMaximumHeight(80)
        self._preview_input.setPlaceholderText("输入测试文本...")
        preview_layout.addWidget(self._preview_input)

        self._btn_filter = StyledButton("🔍 测试过滤", style_type="secondary")
        self._btn_filter.clicked.connect(self._test_filter)
        preview_layout.addWidget(self._btn_filter)

        self._preview_output = QTextEdit()
        self._preview_output.setReadOnly(True)
        self._preview_output.setMaximumHeight(80)
        preview_layout.addWidget(self._preview_output)

        right_layout.addWidget(preview_group)
        right_layout.addStretch()

        splitter.addWidget(right)
        splitter.setSizes([250, 350])
        layout.addWidget(splitter)

        self._refresh_list()

    def _refresh_list(self) -> None:
        self._rule_list.clear()
        for rule in self._rules:
            status = "✅" if rule.enabled else "❌"
            self._rule_list.addItem(f"{status} [{rule.category}] {rule.name}")

    def _on_rule_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._rules):
            return
        rule = self._rules[row]
        self._name_edit.setText(rule.name)
        self._pattern_edit.setText(rule.pattern)
        idx = self._category_combo.findText(rule.category)
        if idx >= 0:
            self._category_combo.setCurrentIndex(idx)
        idx = self._rule_level_combo.findText(rule.level)
        if idx >= 0:
            self._rule_level_combo.setCurrentIndex(idx)
        self._replacement_edit.setText(rule.replacement)
        self._enabled_check.setChecked(rule.enabled)

    def _add_rule(self) -> None:
        rule = FilterRule(
            id=f"r_{len(self._rules)+1}",
            name=f"新规则_{len(self._rules)+1}",
            category="custom",
        )
        self._rules.append(rule)
        self._refresh_list()
        self._rule_list.setCurrentRow(len(self._rules) - 1)

    def _delete_rule(self) -> None:
        row = self._rule_list.currentRow()
        if row < 0:
            return
        self._rules.pop(row)
        self._refresh_list()

    def _save_rule(self) -> None:
        row = self._rule_list.currentRow()
        if row < 0:
            return
        rule = self._rules[row]
        rule.name = self._name_edit.text()
        rule.pattern = self._pattern_edit.text()
        rule.category = self._category_combo.currentText()
        rule.level = self._rule_level_combo.currentText()
        rule.replacement = self._replacement_edit.text()
        rule.enabled = self._enabled_check.isChecked()
        self._refresh_list()
        self._rule_list.setCurrentRow(row)
        self.rules_changed.emit()
        logger.info(f"规则已保存: {rule.name}")

    def _on_level_changed(self, text: str) -> None:
        level_map = {"严格": SafetyLevel.STRICT, "标准": SafetyLevel.STANDARD, "宽松": SafetyLevel.RELAXED}
        self._safety_level = level_map.get(text, SafetyLevel.STANDARD)

    def _test_filter(self) -> None:
        """测试过滤"""
        text = self._preview_input.toPlainText()
        filtered = self.filter_text(text)
        self._preview_output.setPlainText(filtered)

    def filter_text(self, text: str) -> str:
        """应用过滤规则"""
        result = text
        for rule in self._rules:
            if not rule.enabled:
                continue
            # 根据安全级别决定是否应用
            if self._safety_level == SafetyLevel.RELAXED and rule.level == "strict":
                continue
            if self._safety_level == SafetyLevel.STANDARD and rule.level == "strict":
                # 标准模式下也应用 strict 规则
                pass
            try:
                result = re.sub(rule.pattern, rule.replacement, result)
            except re.error:
                pass
        return result

    def _import_rules(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "导入规则", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                self._rules.append(FilterRule(**item))
            self._refresh_list()
        except Exception as e:
            logger.error(f"导入失败: {e}")

    def _export_rules(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出规则", "safety_rules.json", "JSON (*.json)")
        if not path:
            return
        try:
            data = [
                {"id": r.id, "name": r.name, "pattern": r.pattern,
                 "category": r.category, "level": r.level,
                 "enabled": r.enabled, "replacement": r.replacement}
                for r in self._rules
            ]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"导出失败: {e}")

    def get_active_rules(self) -> list[FilterRule]:
        """获取当前级别下的活跃规则"""
        active = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if self._safety_level == SafetyLevel.RELAXED and rule.level == "strict":
                continue
            active.append(rule)
        return active
