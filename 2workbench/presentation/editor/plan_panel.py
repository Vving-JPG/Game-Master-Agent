"""
AI 助手 — 计划面板
显示 AI 生成的执行计划，支持确认/修改/取消
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from foundation.logger import get_logger

logger = get_logger(__name__)

# 状态图标映射
STATUS_ICONS = {
    "pending": "⏳",
    "confirmed": "🔵",
    "executing": "🔄",
    "completed": "✅",
    "skipped": "⏭️",
    "failed": "❌",
    "rejected": "🚫",
}

# 工具名称到中文的映射
TOOL_NAMES_CN = {
    "read_project": "读取项目",
    "create_prompt": "创建提示词",
    "edit_prompt": "修改提示词",
    "list_prompts": "列出提示词",
    "delete_prompt": "删除提示词",
    "create_skill": "创建技能",
    "edit_skill": "修改技能",
    "list_skills": "列出技能",
    "delete_skill": "删除技能",
    "read_graph": "读取图定义",
    "update_graph": "修改图定义",
    "read_config": "读取配置",
    "update_config": "修改配置",
    "test_prompt": "测试提示词",
}


class StepCard(QFrame):
    """单个步骤卡片"""

    expanded = pyqtSignal(int)  # step_id

    def __init__(self, step_data: dict, parent=None):
        super().__init__(parent)
        self._step_data = step_data
        self._is_expanded = False
        self._setup_ui()

    def _setup_ui(self):
        step_id = self._step_data.get("step_id", 0)
        tool = self._step_data.get("tool_name", "")
        description = self._step_data.get("description", "")
        status = self._step_data.get("status", "pending")
        parameters = self._step_data.get("parameters", {})

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 第一行：状态图标 + 步骤编号 + 描述
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        icon = STATUS_ICONS.get(status, "⏳")
        self._status_label = QLabel(icon)
        self._status_label.setFixedSize(24, 24)
        self._status_label.setStyleSheet("font-size: 16px; border: none;")
        header_layout.addWidget(self._status_label)

        step_label = QLabel(f"步骤 {step_id}: {description}")
        step_label.setFont(QFont("Microsoft YaHei", 11))
        step_label.setStyleSheet("border: none;")
        header_layout.addWidget(step_label)

        header_layout.addStretch()

        # 展开/收起按钮（仅在有参数时显示）
        if parameters:
            self._expand_btn = QPushButton("▼")
            self._expand_btn.setFixedSize(24, 24)
            self._expand_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    color: #888;
                    font-size: 12px;
                }
                QPushButton:hover {
                    color: #333;
                }
            """)
            self._expand_btn.clicked.connect(self._toggle_expand)
            header_layout.addWidget(self._expand_btn)

        layout.addLayout(header_layout)

        # 第二行：工具名称
        tool_cn = TOOL_NAMES_CN.get(tool, tool)
        tool_label = QLabel(f"工具: {tool_cn}")
        tool_label.setStyleSheet("color: #888; font-size: 11px; border: none; margin-left: 32px;")
        layout.addWidget(tool_label)

        # 参数详情（默认隐藏）
        self._detail_widget = QWidget()
        detail_layout = QVBoxLayout(self._detail_widget)
        detail_layout.setContentsMargins(32, 4, 0, 0)
        detail_layout.setSpacing(2)

        for key, value in parameters.items():
            # 截断过长的值
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."

            param_label = QLabel(f"  {key}: {value_str}")
            param_label.setStyleSheet(
                "color: #666; font-size: 11px; "
                "font-family: 'Consolas', 'Courier New', monospace; "
                "border: none;"
            )
            param_label.setWordWrap(True)
            detail_layout.addWidget(param_label)

        self._detail_widget.hide()
        layout.addWidget(self._detail_widget)

        # 样式
        self._update_style(status)

    def _toggle_expand(self):
        """展开/收起参数详情"""
        self._is_expanded = not self._is_expanded
        self._detail_widget.setVisible(self._is_expanded)
        self._expand_btn.setText("▲" if self._is_expanded else "▼")

    def update_status(self, status: str):
        """更新步骤状态"""
        self._step_data["status"] = status
        icon = STATUS_ICONS.get(status, "⏳")
        self._status_label.setText(icon)
        self._update_style(status)

    def _update_style(self, status: str):
        """根据状态更新样式"""
        base_style = """
            StepCard {{
                border-radius: 8px;
                margin: 2px 0;
            }}
        """

        if status == "completed":
            self.setStyleSheet(base_style + "StepCard { background: #e8f5e9; }")
        elif status == "failed":
            self.setStyleSheet(base_style + "StepCard { background: #ffebee; }")
        elif status == "executing":
            self.setStyleSheet(base_style + "StepCard { background: #e3f2fd; }")
        elif status == "skipped":
            self.setStyleSheet(base_style + "StepCard { background: #f5f5f5; color: #999; }")
        elif status == "rejected":
            self.setStyleSheet(base_style + "StepCard { background: #fff3e0; }")
        else:
            self.setStyleSheet(base_style + "StepCard { background: white; border: 1px solid #e0e0e0; }")


class PlanPanel(QFrame):
    """计划面板"""

    plan_action = pyqtSignal(str, str)  # action, feedback

    def __init__(self, plan_data: dict, parent=None):
        super().__init__(parent)
        self._plan_data = plan_data
        self._step_cards: list[StepCard] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 面板容器
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(16, 12, 16, 12)
        container_layout.setSpacing(8)

        # 标题
        title = QLabel("📋 执行计划")
        title.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
        title.setStyleSheet("border: none;")
        container_layout.addWidget(title)

        # 目标描述
        goal = self._plan_data.get("goal", "")
        if goal:
            goal_label = QLabel(f"目标: {goal}")
            goal_label.setStyleSheet("color: #666; font-size: 12px; border: none;")
            goal_label.setWordWrap(True)
            container_layout.addWidget(goal_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #eee;")
        container_layout.addWidget(line)

        # 步骤列表
        steps = self._plan_data.get("steps", [])
        for step_data in steps:
            card = StepCard(step_data)
            self._step_cards.append(card)
            container_layout.addWidget(card)

        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #eee;")
        container_layout.addWidget(line2)

        # 操作按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        # 确认全部按钮
        confirm_all_btn = QPushButton("✅ 确认全部执行")
        confirm_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #43a047; }
            QPushButton:pressed { background-color: #388e3c; }
        """)
        confirm_all_btn.clicked.connect(
            lambda: self.plan_action.emit("confirm_all", "")
        )
        btn_layout.addWidget(confirm_all_btn)

        # 修改计划按钮
        modify_btn = QPushButton("✏️ 修改计划")
        modify_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        modify_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #fb8c00; }
            QPushButton:pressed { background-color: #f57c00; }
        """)
        modify_btn.clicked.connect(self._on_modify)
        btn_layout.addWidget(modify_btn)

        btn_layout.addStretch()

        # 取消按钮
        cancel_btn = QPushButton("❌ 取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #666;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #eeeeee; }
        """)
        cancel_btn.clicked.connect(
            lambda: self.plan_action.emit("cancel", "")
        )
        btn_layout.addWidget(cancel_btn)

        container_layout.addLayout(btn_layout)

        # 修改输入框（默认隐藏）
        self._modify_input = QTextEdit()
        self._modify_input.setPlaceholderText("描述你希望如何修改计划...")
        self._modify_input.setMaximumHeight(80)
        self._modify_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
            }
        """)
        self._modify_input.hide()
        container_layout.addWidget(self._modify_input)

        # 修改确认按钮（默认隐藏）
        self._modify_confirm_layout = QHBoxLayout()
        self._modify_confirm_layout.setSpacing(8)

        submit_modify_btn = QPushButton("提交修改")
        submit_modify_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #fb8c00; }
        """)
        submit_modify_btn.clicked.connect(self._submit_modify)
        self._modify_confirm_layout.addWidget(submit_modify_btn)

        cancel_modify_btn = QPushButton("取消修改")
        cancel_modify_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
        """)
        cancel_modify_btn.clicked.connect(self._cancel_modify)
        self._modify_confirm_layout.addWidget(cancel_modify_btn)

        self._modify_confirm_layout.addStretch()
        container_layout.addLayout(self._modify_confirm_layout)
        self._modify_confirm_layout.setParent(None)  # 隐藏

        layout.addWidget(container)

    def _on_modify(self):
        """显示修改输入框"""
        self._modify_input.show()
        self._modify_input.setFocus()
        # 重新添加确认按钮
        container = self.findChild(QFrame)
        if container:
            container.layout().addItem(self._modify_confirm_layout)

    def _submit_modify(self):
        """提交修改意见"""
        feedback = self._modify_input.toPlainText().strip()
        if feedback:
            self.plan_action.emit("modify", feedback)
        self._cancel_modify()

    def _cancel_modify(self):
        """取消修改"""
        self._modify_input.hide()
        self._modify_input.clear()
        self._modify_confirm_layout.setParent(None)

    def update_step_status(self, step_id: int, status: str):
        """更新指定步骤的状态"""
        for card in self._step_cards:
            if card._step_data.get("step_id") == step_id:
                card.update_status(status)
                break
