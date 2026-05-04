# 2workbench/presentation/editor/skill_manager.py
"""Skill 管理器 — 创建/编辑/测试 Skill

Skill 文件格式:
```markdown
---
name: combat
description: 战斗相关技能
triggers:
  - event_type: combat_start
keywords: [伤害, hp, 暴击]
priority: 80
---

# 战斗系统 Skill

## 规则
1. 描述要生动有力
2. 突出关键动作
3. 包含伤害数值
```

使用方式:
    manager = SkillManagerWidget()
    manager.load_skills()
    manager.show()
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QTextEdit, QLineEdit, QLabel, QPushButton, QGroupBox,
    QSplitter, QMessageBox, QInputDialog, QFileDialog,
    QFormLayout, QSpinBox, QListWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from feature.project import project_manager
from feature.ai.skill_loader import SkillLoader, Skill, SkillMetadata

logger = get_logger(__name__)


@dataclass
class SkillItem:
    """Skill 列表项"""
    name: str
    metadata: SkillMetadata
    content: str
    file_path: Path | None = None


class SkillManagerWidget(BaseWidget):
    """Skill 管理器 — 创建/编辑/测试 Skill"""

    # 信号：Skill 被保存
    skill_saved = pyqtSignal(str)  # skill_name
    skill_deleted = pyqtSignal(str)  # skill_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._skills: dict[str, SkillItem] = {}
        self._current_skill: str | None = None
        self._setup_ui()

    def _setup_ui(self):
        """设置 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 左侧：Skill 列表
        self._setup_skill_list()
        layout.addWidget(self.skill_list_panel, 0)

        # 中间：编辑区
        self._setup_editor()
        layout.addWidget(self.editor_panel, 1)

        # 右侧：测试区
        self._setup_test_panel()
        layout.addWidget(self.test_panel, 0)

        # 设置面板宽度
        self.skill_list_panel.setMinimumWidth(200)
        self.skill_list_panel.setMaximumWidth(300)
        self.test_panel.setMinimumWidth(250)
        self.test_panel.setMaximumWidth(350)

    def _setup_skill_list(self):
        """设置 Skill 列表面板"""
        self.skill_list_panel = QGroupBox("Skill 列表")
        layout = QVBoxLayout(self.skill_list_panel)

        # Skill 列表
        self.skill_list = QListWidget()
        self.skill_list.itemClicked.connect(self._on_skill_selected)
        layout.addWidget(self.skill_list)

        # 按钮
        btn_layout = QHBoxLayout()

        self.new_btn = QPushButton("➕ 新建")
        self.new_btn.clicked.connect(self._on_new_skill)

        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.clicked.connect(self._on_delete_skill)

        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)

    def _setup_editor(self):
        """设置编辑器面板"""
        self.editor_panel = QGroupBox("Skill 编辑")
        layout = QVBoxLayout(self.editor_panel)

        # YAML Front Matter 编辑
        yaml_group = QGroupBox("YAML Front Matter")
        yaml_layout = QFormLayout(yaml_group)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Skill 名称")
        yaml_layout.addRow("名称:", self.name_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Skill 描述")
        yaml_layout.addRow("描述:", self.desc_edit)

        self.keywords_edit = QLineEdit()
        self.keywords_edit.setPlaceholderText("关键词，用逗号分隔")
        yaml_layout.addRow("关键词:", self.keywords_edit)

        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(0, 100)
        self.priority_spin.setValue(50)
        yaml_layout.addRow("优先级:", self.priority_spin)

        layout.addWidget(yaml_group)

        # Markdown Body 编辑
        content_group = QGroupBox("Markdown Body")
        content_layout = QVBoxLayout(content_group)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("输入 Skill 内容（Markdown 格式）...")
        content_layout.addWidget(self.content_edit)

        layout.addWidget(content_group)

        # 保存按钮
        self.save_btn = QPushButton("💾 保存 Skill")
        self.save_btn.clicked.connect(self._on_save_skill)
        layout.addWidget(self.save_btn)

    def _setup_test_panel(self):
        """设置测试面板"""
        self.test_panel = QGroupBox("Skill 测试")
        layout = QVBoxLayout(self.test_panel)

        # 测试输入
        test_label = QLabel("输入测试文本:")
        self.test_input = QTextEdit()
        self.test_input.setPlaceholderText("输入要测试的文本...")
        self.test_input.setMaximumHeight(100)
        layout.addWidget(test_label)
        layout.addWidget(self.test_input)

        # 测试按钮
        self.test_btn = QPushButton("🔍 测试匹配")
        self.test_btn.clicked.connect(self._on_test_match)
        layout.addWidget(self.test_btn)

        # 测试结果
        result_label = QLabel("匹配结果:")
        self.test_result = QTextEdit()
        self.test_result.setReadOnly(True)
        self.test_result.setPlaceholderText("测试结果将显示在这里...")
        layout.addWidget(result_label)
        layout.addWidget(self.test_result)

        layout.addStretch()

    def load_skills(self):
        """从项目的 skills/ 目录加载所有 Skill"""
        self._skills.clear()
        self.skill_list.clear()

        if not project_manager.is_open or not project_manager.project_path:
            logger.warning("没有打开的项目，无法加载 Skill")
            return

        skills_dir = project_manager.project_path / "skills"
        if not skills_dir.exists():
            logger.info(f"Skill 目录不存在: {skills_dir}")
            return

        try:
            loader = SkillLoader(str(skills_dir))
            skill_names = loader.discover_all()

            for name in skill_names:
                skill = loader._skills.get(name)
                if skill:
                    skill_file = skills_dir / name / "SKILL.md"
                    item = SkillItem(
                        name=name,
                        metadata=skill.metadata,
                        content=skill.content,
                        file_path=skill_file if skill_file.exists() else None,
                    )
                    self._skills[name] = item

                    # 添加到列表
                    list_item = QListWidgetItem(f"🎯 {name}")
                    list_item.setData(Qt.ItemDataRole.UserRole, name)
                    self.skill_list.addItem(list_item)

            logger.info(f"已加载 {len(self._skills)} 个 Skill")

        except Exception as e:
            logger.error(f"加载 Skill 失败: {e}")
            QMessageBox.warning(self, "错误", f"加载 Skill 失败: {e}")

    def _on_skill_selected(self, item: QListWidgetItem):
        """选择 Skill"""
        skill_name = item.data(Qt.ItemDataRole.UserRole)
        if skill_name not in self._skills:
            return

        self._current_skill = skill_name
        skill = self._skills[skill_name]

        # 更新编辑器
        self.name_edit.setText(skill.metadata.name)
        self.desc_edit.setText(skill.metadata.description)
        self.keywords_edit.setText(", ".join(skill.metadata.keywords))
        self.priority_spin.setValue(getattr(skill.metadata, 'priority', 50))
        self.content_edit.setPlainText(skill.content)

    def _on_new_skill(self):
        """新建 Skill"""
        name, ok = QInputDialog.getText(self, "新建 Skill", "Skill 名称:")
        if not ok or not name:
            return

        # 检查是否已存在
        if name in self._skills:
            QMessageBox.warning(self, "错误", f"Skill '{name}' 已存在")
            return

        # 创建新 Skill
        metadata = SkillMetadata(name=name, description="", keywords=[])
        skill = SkillItem(
            name=name,
            metadata=metadata,
            content="# 新 Skill\n\n在这里编写 Skill 内容...",
            file_path=None,
        )
        self._skills[name] = skill

        # 添加到列表
        list_item = QListWidgetItem(f"🎯 {name}")
        list_item.setData(Qt.ItemDataRole.UserRole, name)
        self.skill_list.addItem(list_item)
        self.skill_list.setCurrentItem(list_item)

        # 选中并编辑
        self._on_skill_selected(list_item)

    def _on_delete_skill(self):
        """删除 Skill"""
        if not self._current_skill:
            QMessageBox.information(self, "提示", "请先选择一个 Skill")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 Skill '{self._current_skill}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        skill = self._skills.get(self._current_skill)
        if skill and skill.file_path:
            try:
                # 删除文件
                skill.file_path.unlink()
                # 如果目录为空，删除目录
                skill_dir = skill.file_path.parent
                if skill_dir.exists() and not any(skill_dir.iterdir()):
                    skill_dir.rmdir()
            except Exception as e:
                logger.error(f"删除 Skill 文件失败: {e}")

        # 从列表中移除
        del self._skills[self._current_skill]
        self.skill_saved.emit(self._current_skill)
        self._current_skill = None

        # 刷新列表
        self.load_skills()

        # 清空编辑器
        self.name_edit.clear()
        self.desc_edit.clear()
        self.keywords_edit.clear()
        self.priority_spin.setValue(50)
        self.content_edit.clear()

    def _on_save_skill(self):
        """保存 Skill"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "Skill 名称不能为空")
            return

        if not project_manager.is_open or not project_manager.project_path:
            QMessageBox.warning(self, "错误", "没有打开的项目")
            return

        # 构建 YAML Front Matter
        metadata = {
            "name": name,
            "description": self.desc_edit.text().strip(),
            "keywords": [k.strip() for k in self.keywords_edit.text().split(",") if k.strip()],
            "priority": self.priority_spin.value(),
        }

        content = self.content_edit.toPlainText()

        # 构建完整文件内容
        yaml_content = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
        full_content = f"---\n{yaml_content}---\n\n{content}"

        # 保存到文件
        try:
            skills_dir = project_manager.project_path / "skills"
            skills_dir.mkdir(exist_ok=True)

            skill_dir = skills_dir / name
            skill_dir.mkdir(exist_ok=True)

            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(full_content, encoding="utf-8")

            # 更新内存中的 Skill
            skill_item = SkillItem(
                name=name,
                metadata=SkillMetadata(**metadata),
                content=content,
                file_path=skill_file,
            )
            self._skills[name] = skill_item
            self._current_skill = name

            self.skill_saved.emit(name)
            QMessageBox.information(self, "成功", f"Skill '{name}' 已保存")
            logger.info(f"Skill 已保存: {skill_file}")

        except Exception as e:
            logger.error(f"保存 Skill 失败: {e}")
            QMessageBox.critical(self, "错误", f"保存 Skill 失败: {e}")

    def _on_test_match(self):
        """测试 Skill 匹配"""
        test_text = self.test_input.toPlainText().strip()
        if not test_text:
            QMessageBox.information(self, "提示", "请输入测试文本")
            return

        if not project_manager.is_open or not project_manager.project_path:
            QMessageBox.warning(self, "错误", "没有打开的项目")
            return

        try:
            skills_dir = project_manager.project_path / "skills"
            if not skills_dir.exists():
                QMessageBox.information(self, "提示", "项目没有 Skill 目录")
                return

            loader = SkillLoader(str(skills_dir))
            loader.discover_all()

            results = loader.get_relevant_skills(
                user_input=test_text,
                event_type="player_action",
                max_skills=10,
            )

            # 显示结果
            if not results:
                self.test_result.setPlainText("没有匹配的 Skill")
                return

            result_text = []
            for skill in results:
                score = 0
                # 简单计算分数（实际分数在 loader 内部计算）
                for keyword in skill.metadata.keywords:
                    if keyword.lower() in test_text.lower():
                        score += 5

                result_text.append(f"🎯 {skill.metadata.name}")
                result_text.append(f"   描述: {skill.metadata.description}")
                result_text.append(f"   关键词: {', '.join(skill.metadata.keywords)}")
                result_text.append(f"   预估分数: {score}")
                result_text.append("")

            self.test_result.setPlainText("\n".join(result_text))

        except Exception as e:
            logger.error(f"测试 Skill 匹配失败: {e}")
            QMessageBox.critical(self, "错误", f"测试失败: {e}")

    def get_current_skill(self) -> SkillItem | None:
        """获取当前选中的 Skill"""
        if self._current_skill:
            return self._skills.get(self._current_skill)
        return None
