"""工具/插件管理器 — LangGraph Tool 管理

功能:
1. 内置工具列表（骰子、战斗、物品、对话等）
2. 自定义工具注册
3. 工具配置编辑
4. 工具测试面板
5. 工具启用/禁用
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QLabel, QFormLayout, QDialog, QDialogButtonBox,
    QComboBox, QCheckBox, QGroupBox, QTextBrowser,
    QPushButton,
)
from PyQt6.QtCore import pyqtSignal, Qt

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton
from presentation.widgets.search_bar import SearchBar

logger = get_logger(__name__)


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str = ""
    category: str = "custom"  # builtin / custom
    enabled: bool = True
    parameters: dict = field(default_factory=dict)  # JSON Schema
    source_file: str = ""  # 自定义工具的文件路径


# 内置工具定义
BUILTIN_TOOLS = [
    ToolDefinition(
        name="roll_dice",
        description="掷骰子（支持 XdY 格式，如 2d6、1d20）",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "notation": {"type": "string", "description": "骰子表示法，如 2d6"},
            },
            "required": ["notation"],
        },
    ),
    ToolDefinition(
        name="start_combat",
        description="开始战斗",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "enemies": {"type": "array", "description": "敌人列表"},
                "player_id": {"type": "integer", "description": "玩家 ID"},
            },
            "required": ["enemies"],
        },
    ),
    ToolDefinition(
        name="give_item",
        description="给予玩家物品",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "物品名称"},
                "quantity": {"type": "integer", "description": "数量", "default": 1},
                "player_id": {"type": "integer", "description": "玩家 ID"},
            },
            "required": ["item_name"],
        },
    ),
    ToolDefinition(
        name="npc_talk",
        description="与 NPC 对话",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "npc_name": {"type": "string", "description": "NPC 名称"},
                "message": {"type": "string", "description": "对话内容"},
            },
            "required": ["npc_name", "message"],
        },
    ),
    ToolDefinition(
        name="update_quest",
        description="更新任务状态",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "quest_id": {"type": "integer", "description": "任务 ID"},
                "status": {"type": "string", "description": "新状态", "enum": ["active", "completed", "failed"]},
            },
            "required": ["quest_id", "status"],
        },
    ),
    ToolDefinition(
        name="move_to",
        description="移动到指定地点",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "location_name": {"type": "string", "description": "目标地点"},
            },
            "required": ["location_name"],
        },
    ),
    ToolDefinition(
        name="check_skill",
        description="进行技能检定",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "skill": {"type": "string", "description": "技能名称"},
                "difficulty": {"type": "integer", "description": "难度等级", "default": 15},
            },
            "required": ["skill"],
        },
    ),
    ToolDefinition(
        name="search_area",
        description="搜索当前区域",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "搜索目标"},
            },
        },
    ),
    ToolDefinition(
        name="use_item",
        description="使用物品",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "物品名称"},
                "target": {"type": "string", "description": "使用目标"},
            },
            "required": ["item_name"],
        },
    ),
]


class ToolManagerWidget(BaseWidget):
    """工具/插件管理器组件"""

    tools_changed = pyqtSignal(list)  # List[ToolDefinition]
    tool_selected = pyqtSignal(dict)  # 选中工具时发送工具数据

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tools: list[ToolDefinition] = list(BUILTIN_TOOLS)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: 工具列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        list_label = QLabel("🔧 工具列表")
        list_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        left_layout.addWidget(list_label)

        # 搜索框
        self._search = SearchBar("搜索工具...")
        self._search.search_changed.connect(self._filter_tool_table)
        left_layout.addWidget(self._search)

        self._tool_list = QListWidget()
        self._tool_list.currentRowChanged.connect(self._on_tool_selected)
        left_layout.addWidget(self._tool_list)

        # 筛选
        filter_layout = QHBoxLayout()
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["全部", "内置", "自定义"])
        self._filter_combo.currentTextChanged.connect(self._filter_tools)
        filter_layout.addWidget(QLabel("筛选:"))
        filter_layout.addWidget(self._filter_combo)
        left_layout.addLayout(filter_layout)

        self._btn_add = StyledButton("+ 添加自定义工具", style_type="primary")
        self._btn_add.clicked.connect(self._add_tool_dialog)
        left_layout.addWidget(self._btn_add)

        splitter.addWidget(left)

        # 右侧: 工具详情 + 测试
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        # 工具信息
        info_group = QGroupBox("工具信息")
        info_layout = QFormLayout(info_group)

        self._name_edit = QLineEdit()
        self._name_edit.setReadOnly(True)
        info_layout.addRow("名称:", self._name_edit)

        self._desc_edit = QLineEdit()
        self._desc_edit.setReadOnly(True)
        info_layout.addRow("描述:", self._desc_edit)

        self._category_label = QLabel()
        info_layout.addRow("类别:", self._category_label)

        self._enabled_check = QCheckBox("启用")
        self._enabled_check.stateChanged.connect(self._on_enabled_changed)
        info_layout.addRow("状态:", self._enabled_check)

        right_layout.addWidget(info_group)

        # 参数 Schema
        schema_group = QGroupBox("参数 Schema (JSON)")
        schema_layout = QVBoxLayout(schema_group)

        self._schema_edit = QTextEdit()
        self._schema_edit.setReadOnly(True)
        self._schema_edit.setMaximumHeight(150)
        self._schema_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        schema_layout.addWidget(self._schema_edit)

        right_layout.addWidget(schema_group)

        # 测试面板
        test_group = QGroupBox("测试")
        test_layout = QVBoxLayout(test_group)

        self._test_input = QTextEdit()
        self._test_input.setPlaceholderText('输入测试参数 (JSON):\n{"notation": "2d6"}')
        self._test_input.setMaximumHeight(100)
        self._test_input.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        test_layout.addWidget(self._test_input)

        self._btn_test = StyledButton("▶ 执行测试", style_type="success")
        self._btn_test.clicked.connect(self._run_test)
        test_layout.addWidget(self._btn_test)

        self._test_result = QTextBrowser()
        self._test_result.setMaximumHeight(120)
        self._test_result.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        test_layout.addWidget(self._test_result)

        right_layout.addWidget(test_group)
        right_layout.addStretch()

        splitter.addWidget(right)
        splitter.setSizes([250, 400])
        layout.addWidget(splitter)

        # 初始化列表
        self._refresh_list()

    def _refresh_list(self) -> None:
        """刷新工具列表"""
        self._tool_list.clear()
        for tool in self._tools:
            icon = "🔧" if tool.category == "builtin" else "🔌"
            status = "✅" if tool.enabled else "❌"
            self._tool_list.addItem(f"{status} {icon} {tool.name}")

    def _filter_tools(self, filter_text: str) -> None:
        """筛选工具"""
        self._tool_list.clear()
        for tool in self._tools:
            if filter_text == "全部":
                show = True
            elif filter_text == "内置":
                show = tool.category == "builtin"
            else:
                show = tool.category == "custom"
            if show:
                icon = "🔧" if tool.category == "builtin" else "🔌"
                status = "✅" if tool.enabled else "❌"
                self._tool_list.addItem(f"{status} {icon} {tool.name}")

    def _filter_tool_table(self, keyword: str) -> None:
        """根据关键词过滤工具列表"""
        keyword = keyword.lower()
        self._tool_list.clear()
        for tool in self._tools:
            # 搜索名称和描述
            match = (keyword == "" or
                     keyword in tool.name.lower() or
                     keyword in tool.description.lower())
            if match:
                icon = "🔧" if tool.category == "builtin" else "🔌"
                status = "✅" if tool.enabled else "❌"
                self._tool_list.addItem(f"{status} {icon} {tool.name}")

    def _on_tool_selected(self, row: int) -> None:
        """选中工具"""
        if row < 0 or row >= len(self._tools):
            return
        tool = self._tools[row]
        self._name_edit.setText(tool.name)
        self._desc_edit.setText(tool.description)
        self._category_label.setText(tool.category)
        self._enabled_check.setChecked(tool.enabled)
        self._schema_edit.setPlainText(
            json.dumps(tool.parameters, ensure_ascii=False, indent=2)
        )
        
        # 发送信号到右侧面板显示属性
        tool_data = {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "enabled": tool.enabled,
            "parameters": tool.parameters,
        }
        self.tool_selected.emit(tool_data)

    def _on_enabled_changed(self, state) -> None:
        """启用/禁用工具"""
        row = self._tool_list.currentRow()
        if row < 0:
            return
        self._tools[row].enabled = bool(state)
        self._refresh_list()
        self._tool_list.setCurrentRow(row)
        self.tools_changed.emit(self._tools)

    def _add_tool_dialog(self) -> None:
        """添加自定义工具对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加自定义工具")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("tool_name")
        layout.addRow("工具名称:", name_edit)

        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("工具描述")
        layout.addRow("描述:", desc_edit)

        schema_edit = QTextEdit()
        schema_edit.setPlaceholderText('参数 JSON Schema:\n{"type": "object", "properties": {...}}')
        schema_edit.setMaximumHeight(120)
        layout.addRow("参数 Schema:", schema_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec():
            name = name_edit.text().strip()
            if not name:
                return
            try:
                params = json.loads(schema_edit.toPlainText()) if schema_edit.toPlainText() else {}
            except json.JSONDecodeError:
                params = {}
            tool = ToolDefinition(
                name=name,
                description=desc_edit.text().strip(),
                category="custom",
                parameters=params,
            )
            self._tools.append(tool)
            self._refresh_list()
            self.tools_changed.emit(self._tools)
            self._logger.info(f"自定义工具添加: {name}")

            # === 注册到 Agent 工具集 ===
            self._register_tool_to_agent(tool)

    def _register_tool_to_agent(self, tool: ToolDefinition) -> None:
        """注册工具到 Agent 工具集"""
        try:
            from feature.ai.tools import register_tool

            # 创建默认 handler（实际项目中可能需要更复杂的逻辑）
            def handler(**kwargs):
                return f"工具 {tool.name} 执行: {kwargs}"

            register_tool(
                name=tool.name,
                description=tool.description,
                parameters_schema=tool.parameters,
                handler=handler,
            )
            self._logger.info(f"工具已注册到 Agent: {tool.name}")
        except Exception as e:
            self._logger.error(f"工具注册到 Agent 失败: {e}")

    def _run_test(self) -> None:
        """真实调用选中的工具"""
        row = self._tool_list.currentRow()
        if row < 0:
            self._test_result.setPlainText("请先选择一个工具")
            return

        tool = self._tools[row]

        try:
            params = json.loads(self._test_input.toPlainText() or "{}")
        except json.JSONDecodeError as e:
            self._test_result.setPlainText(f"❌ JSON 格式错误: {e}")
            return

        self._test_result.setPlainText(f"⏳ 调用 {tool.name}...\n参数: {json.dumps(params, ensure_ascii=False)}")

        # === 真实调用工具 ===
        try:
            from feature.ai.tools import get_all_tools, set_tool_context, ToolContext
            from foundation.config import settings

            # 设置临时工具上下文
            ctx = ToolContext(
                db_path=settings.database_path,
                world_id="test",
                player_id=1,
            )
            set_tool_context(ctx)

            # 查找匹配的工具
            all_tools = get_all_tools()
            for t in all_tools:
                if t.name == tool.name:
                    result = t.invoke(params)
                    self._test_result.append(f"\n✅ 调用成功:\n{result}")
                    return

            self._test_result.append(f"\n❌ 未找到工具: {tool.name}")

        except Exception as e:
            self._test_result.append(f"\n❌ 调用失败: {e}")
        finally:
            set_tool_context(None)

    def get_enabled_tools(self) -> list[ToolDefinition]:
        """获取已启用的工具"""
        return [t for t in self._tools if t.enabled]

    def get_all_tools(self) -> list[ToolDefinition]:
        """获取所有工具"""
        return list(self._tools)
