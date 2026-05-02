# 2workbench/presentation/ops/knowledge/knowledge_editor.py
"""知识库编辑器 — 世界观数据可视化管理

功能:
1. NPC 编辑器（名称/性格/背景/目标/对话风格）
2. 地点编辑器（名称/描述/连接/NPC）
3. 物品编辑器（名称/类型/属性/稀有度）
4. 任务编辑器（标题/描述/前置条件/奖励）
5. 世界设定编辑器（名称/描述/规则）
6. 导入/导出（JSON/Markdown）
"""
from __future__ import annotations

import json
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QFormLayout, QLineEdit,
    QComboBox, QTextBrowser, QFileDialog, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class DataEditorMixin:
    """数据编辑器通用混入"""

    def _create_form_layout(self) -> QFormLayout:
        form = QFormLayout()
        form.setContentsMargins(8, 8, 8, 8)
        form.setSpacing(8)
        return form


class NPCEditor(QWidget):
    """NPC 编辑器"""

    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._npcs: list[dict] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 左侧: NPC 列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self._npc_list = QTableWidget()
        self._npc_list.setColumnCount(3)
        self._npc_list.setHorizontalHeaderLabels(["名称", "位置", "心情"])
        self._npc_list.horizontalHeader().setStretchLastSection(True)
        self._npc_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._npc_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._npc_list.currentCellChanged.connect(self._on_npc_selected)
        left_layout.addWidget(self._npc_list)

        self._btn_add = StyledButton("+ 添加 NPC", style_type="primary")
        self._btn_add.clicked.connect(self._add_npc)
        left_layout.addWidget(self._btn_add)

        layout.addWidget(left, 1)

        # 右侧: NPC 详情编辑
        right = QWidget()
        right.setMaximumWidth(400)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)

        form = QFormLayout()

        self._name_edit = QLineEdit()
        form.addRow("名称:", self._name_edit)

        self._mood_combo = QComboBox()
        self._mood_combo.addItems(["serene", "happy", "neutral", "sad", "angry", "fearful"])
        form.addRow("心情:", self._mood_combo)

        self._speech_edit = QLineEdit()
        self._speech_edit.setPlaceholderText("说话风格描述")
        form.addRow("说话风格:", self._speech_edit)

        self._backstory_edit = QTextEdit()
        self._backstory_edit.setMaximumHeight(100)
        self._backstory_edit.setPlaceholderText("角色背景故事")
        form.addRow("背景:", self._backstory_edit)

        self._goals_edit = QLineEdit()
        self._goals_edit.setPlaceholderText("目标1, 目标2, ...")
        form.addRow("目标:", self._goals_edit)

        right_layout.addLayout(form)

        # 性格参数
        trait_group = QLabel("性格参数 (大五人格 0.0-1.0)")
        trait_group.setStyleSheet("font-weight: bold; margin-top: 8px;")
        right_layout.addWidget(trait_group)

        trait_layout = QFormLayout()
        self._openness = QDoubleSpinBox()
        self._openness.setRange(0, 1); self._openness.setSingleStep(0.1); self._openness.setValue(0.5)
        trait_layout.addRow("开放性:", self._openness)

        self._conscientiousness = QDoubleSpinBox()
        self._conscientiousness.setRange(0, 1); self._conscientiousness.setSingleStep(0.1); self._conscientiousness.setValue(0.5)
        trait_layout.addRow("尽责性:", self._conscientiousness)

        self._extraversion = QDoubleSpinBox()
        self._extraversion.setRange(0, 1); self._extraversion.setSingleStep(0.1); self._extraversion.setValue(0.5)
        trait_layout.addRow("外向性:", self._extraversion)

        self._agreeableness = QDoubleSpinBox()
        self._agreeableness.setRange(0, 1); self._agreeableness.setSingleStep(0.1); self._agreeableness.setValue(0.5)
        trait_layout.addRow("宜人性:", self._agreeableness)

        self._neuroticism = QDoubleSpinBox()
        self._neuroticism.setRange(0, 1); self._neuroticism.setSingleStep(0.1); self._neuroticism.setValue(0.5)
        trait_layout.addRow("神经质:", self._neuroticism)

        right_layout.addLayout(trait_layout)

        self._btn_save = StyledButton("💾 保存修改", style_type="primary")
        self._btn_save.clicked.connect(self._save_npc)
        right_layout.addWidget(self._btn_save)

        right_layout.addStretch()
        layout.addWidget(right)

    def load_data(self, npcs: list[dict]) -> None:
        """加载 NPC 数据"""
        self._npcs = npcs
        self._refresh_list()

    def _refresh_list(self) -> None:
        self._npc_list.setRowCount(0)
        for npc in self._npcs:
            row = self._npc_list.rowCount()
            self._npc_list.insertRow(row)
            self._npc_list.setItem(row, 0, QTableWidgetItem(npc.get("name", "")))
            self._npc_list.setItem(row, 1, QTableWidgetItem(str(npc.get("location_id", ""))))
            self._npc_list.setItem(row, 2, QTableWidgetItem(npc.get("mood", "")))

    def _on_npc_selected(self, current_row: int, current_column: int, previous_row: int, previous_column: int) -> None:
        row = current_row
        if row < 0 or row >= len(self._npcs):
            return
        npc = self._npcs[row]
        self._name_edit.setText(npc.get("name", ""))
        idx = self._mood_combo.findText(npc.get("mood", "neutral"))
        if idx >= 0:
            self._mood_combo.setCurrentIndex(idx)
        self._speech_edit.setText(npc.get("speech_style", ""))
        self._backstory_edit.setPlainText(npc.get("backstory", ""))
        self._goals_edit.setText(", ".join(npc.get("goals", [])))
        personality = npc.get("personality", {})
        if isinstance(personality, dict):
            self._openness.setValue(personality.get("openness", 0.5))
            self._conscientiousness.setValue(personality.get("conscientiousness", 0.5))
            self._extraversion.setValue(personality.get("extraversion", 0.5))
            self._agreeableness.setValue(personality.get("agreeableness", 0.5))
            self._neuroticism.setValue(personality.get("neuroticism", 0.5))

    def _add_npc(self) -> None:
        self._npcs.append({
            "name": f"NPC_{len(self._npcs)+1}",
            "mood": "neutral",
            "personality": {},
            "goals": [],
        })
        self._refresh_list()
        self._npc_list.selectRow(len(self._npcs) - 1)

    def _save_npc(self) -> None:
        row = self._npc_list.currentRow()
        if row < 0:
            return
        self._npcs[row]["name"] = self._name_edit.text()
        self._npcs[row]["mood"] = self._mood_combo.currentText()
        self._npcs[row]["speech_style"] = self._speech_edit.text()
        self._npcs[row]["backstory"] = self._backstory_edit.toPlainText()
        self._npcs[row]["goals"] = [g.strip() for g in self._goals_edit.text().split(",") if g.strip()]
        self._npcs[row]["personality"] = {
            "openness": self._openness.value(),
            "conscientiousness": self._conscientiousness.value(),
            "extraversion": self._extraversion.value(),
            "agreeableness": self._agreeableness.value(),
            "neuroticism": self._neuroticism.value(),
        }
        self._refresh_list()
        self._npc_list.selectRow(row)
        self.data_changed.emit()
        logger.info(f"NPC 已保存: {self._npcs[row]['name']}")

    def get_data(self) -> list[dict]:
        return list(self._npcs)


class LocationEditor(QWidget):
    """地点编辑器"""

    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._locations: list[dict] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 左侧列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self._loc_list = QTableWidget()
        self._loc_list.setColumnCount(2)
        self._loc_list.setHorizontalHeaderLabels(["名称", "描述"])
        self._loc_list.horizontalHeader().setStretchLastSection(True)
        self._loc_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._loc_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._loc_list.currentCellChanged.connect(self._on_loc_selected)
        left_layout.addWidget(self._loc_list)

        self._btn_add = StyledButton("+ 添加地点", style_type="primary")
        self._btn_add.clicked.connect(self._add_location)
        left_layout.addWidget(self._btn_add)

        layout.addWidget(left, 1)

        # 右侧详情
        right = QWidget()
        right.setMaximumWidth(400)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)

        form = QFormLayout()
        self._name_edit = QLineEdit()
        form.addRow("名称:", self._name_edit)

        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(120)
        form.addRow("描述:", self._desc_edit)

        self._connections_edit = QLineEdit()
        self._connections_edit.setPlaceholderText("north:1, south:2, east:3")
        form.addRow("出口:", self._connections_edit)

        right_layout.addLayout(form)

        self._btn_save = StyledButton("💾 保存修改", style_type="primary")
        self._btn_save.clicked.connect(self._save_location)
        right_layout.addWidget(self._btn_save)

        right_layout.addStretch()
        layout.addWidget(right)

    def load_data(self, locations: list[dict]) -> None:
        self._locations = locations
        self._refresh_list()

    def _refresh_list(self) -> None:
        self._loc_list.setRowCount(0)
        for loc in self._locations:
            row = self._loc_list.rowCount()
            self._loc_list.insertRow(row)
            self._loc_list.setItem(row, 0, QTableWidgetItem(loc.get("name", "")))
            self._loc_list.setItem(row, 1, QTableWidgetItem(loc.get("description", "")[:50]))

    def _on_loc_selected(self, current_row: int, current_column: int, previous_row: int, previous_column: int) -> None:
        row = current_row
        if row < 0 or row >= len(self._locations):
            return
        loc = self._locations[row]
        self._name_edit.setText(loc.get("name", ""))
        self._desc_edit.setPlainText(loc.get("description", ""))
        connections = loc.get("connections", {})
        if isinstance(connections, dict):
            self._connections_edit.setText(", ".join(f"{k}:{v}" for k, v in connections.items()))

    def _add_location(self) -> None:
        self._locations.append({"name": f"地点_{len(self._locations)+1}", "connections": {}})
        self._refresh_list()
        self._loc_list.selectRow(len(self._locations) - 1)

    def _save_location(self) -> None:
        row = self._loc_list.currentRow()
        if row < 0:
            return
        self._locations[row]["name"] = self._name_edit.text()
        self._locations[row]["description"] = self._desc_edit.toPlainText()
        # 解析连接
        connections = {}
        for part in self._connections_edit.text().split(","):
            part = part.strip()
            if ":" in part:
                key, val = part.split(":", 1)
                try:
                    connections[key.strip()] = int(val.strip())
                except ValueError:
                    pass
        self._locations[row]["connections"] = connections
        self._refresh_list()
        self._loc_list.selectRow(row)
        self.data_changed.emit()

    def get_data(self) -> list[dict]:
        return list(self._locations)


class KnowledgeEditor(BaseWidget):
    """知识库编辑器 — 主面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        self._btn_import = StyledButton("📥 导入 JSON", style_type="secondary")
        self._btn_import.clicked.connect(self._import_data)
        toolbar.addWidget(self._btn_import)

        self._btn_export = StyledButton("📤 导出 JSON", style_type="secondary")
        self._btn_export.clicked.connect(self._export_data)
        toolbar.addWidget(self._btn_export)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 标签页
        self._tabs = QTabWidget()

        self._npc_editor = NPCEditor()
        self._tabs.addTab(self._npc_editor, "👥 NPC")

        self._loc_editor = LocationEditor()
        self._tabs.addTab(self._loc_editor, "📍 地点")

        # 物品编辑器（简化版）
        self._item_placeholder = QLabel("📦 物品编辑器\n（后续扩展）")
        self._item_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._item_placeholder.setStyleSheet("color: #858585; font-size: 14px;")
        self._tabs.addTab(self._item_placeholder, "📦 物品")

        # 任务编辑器（简化版）
        self._quest_placeholder = QLabel("📋 任务编辑器\n（后续扩展）")
        self._quest_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._quest_placeholder.setStyleSheet("color: #858585; font-size: 14px;")
        self._tabs.addTab(self._quest_placeholder, "📋 任务")

        layout.addWidget(self._tabs)

    def _import_data(self) -> None:
        """导入 JSON 数据"""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入知识库", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "npcs" in data:
                self._npc_editor.load_data(data["npcs"])
            if "locations" in data:
                self._loc_editor.load_data(data["locations"])
            logger.info(f"知识库导入成功: {path}")
        except Exception as e:
            logger.error(f"导入失败: {e}")

    def _export_data(self) -> None:
        """导出 JSON 数据"""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出知识库", "knowledge.json", "JSON (*.json)"
        )
        if not path:
            return
        try:
            data = {
                "npcs": self._npc_editor.get_data(),
                "locations": self._loc_editor.get_data(),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"知识库导出成功: {path}")
        except Exception as e:
            logger.error(f"导出失败: {e}")
