# workbench/widgets/console_tabs.py
"""底部控制台 — 5 个 Tab"""
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QListWidget, QListWidgetItem,
    QComboBox, QPlainTextEdit, QSplitter, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class ExecutionCtrlPanel(QWidget):
    """Tab 1: 执行控制"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 状态显示
        status_layout = QHBoxLayout()
        self.status_badge = QLabel("IDLE")
        self.status_badge.setStyleSheet(
            "background-color: #4caf50; color: white; padding: 4px 12px; "
            "border-radius: 4px; font-weight: bold; font-size: 14px;"
        )
        status_layout.addWidget(self.status_badge)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # 控制按钮
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("▶ 运行")
        self.btn_pause = QPushButton("⏸ 暂停")
        self.btn_step = QPushButton("⏯ 单步")
        self.btn_reset = QPushButton("↺ 重置")
        for btn in [self.btn_run, self.btn_pause, self.btn_step, self.btn_reset]:
            btn.setMinimumHeight(32)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        # 日志输出
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 10))
        self.log.setPlaceholderText("Agent 执行日志将显示在这里...")
        layout.addWidget(self.log)

    def append_log(self, message: str, color: str = "#d4d4d4"):
        """追加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color:#666">[{timestamp}]</span> <span style="color:{color}">{message}</span>'
        self.log.appendHtml(html)

    def set_status(self, status: str):
        """更新状态"""
        colors = {
            "IDLE": "#4caf50",
            "RUNNING": "#2196f3",
            "PAUSED": "#ff9800",
            "STEP_WAITING": "#9c27b0",
            "ERROR": "#f44336",
        }
        color = colors.get(status, "#666")
        self.status_badge.setText(status)
        self.status_badge.setStyleSheet(
            f"background-color: {color}; color: white; padding: 4px 12px; "
            f"border-radius: 4px; font-weight: bold; font-size: 14px;"
        )


class FlowViewPanel(QWidget):
    """Tab 2: 流程视图 — 运行时高亮当前节点"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 当前节点显示
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("当前节点:"))
        self.current_node_label = QLabel("无")
        self.current_node_label.setStyleSheet("color: #2196f3; font-weight: bold;")
        info_layout.addWidget(self.current_node_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # 节点列表
        self.node_table = QTableWidget(0, 3)
        self.node_table.setHorizontalHeaderLabels(["节点ID", "类型", "状态"])
        self.node_table.horizontalHeader().setStretchLastSection(True)
        self.node_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.node_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.node_table.setColumnWidth(0, 150)
        self.node_table.setColumnWidth(1, 100)
        layout.addWidget(self.node_table)

    def set_nodes(self, nodes: list[dict]):
        """设置节点列表"""
        self.node_table.setRowCount(len(nodes))
        for i, node in enumerate(nodes):
            self.node_table.setItem(i, 0, QTableWidgetItem(node.get("id", "")))
            self.node_table.setItem(i, 1, QTableWidgetItem(node.get("type", "")))
            status_item = QTableWidgetItem(node.get("status", "等待"))
            self.node_table.setItem(i, 2, status_item)

    def highlight_node(self, node_id: str):
        """高亮当前执行节点"""
        self.current_node_label.setText(node_id)
        # 更新表格中的状态
        for row in range(self.node_table.rowCount()):
            item = self.node_table.item(row, 0)
            if item and item.text() == node_id:
                status_item = QTableWidgetItem("执行中")
                status_item.setForeground(QColor("#2196f3"))
                self.node_table.setItem(row, 2, status_item)


class TurnTimelinePanel(QWidget):
    """Tab 3: 轮次回溯"""

    turn_selected = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 左侧: 轮次列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("轮次列表:"))
        self.turn_list = QListWidget()
        self.turn_list.setMaximumWidth(250)
        self.turn_list.currentRowChanged.connect(self._on_turn_selected)
        left_layout.addWidget(self.turn_list)
        layout.addWidget(left_panel)

        # 右侧: 轮次详情
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("轮次详情:"))
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setFont(QFont("Consolas", 10))
        right_layout.addWidget(self.detail)
        layout.addWidget(right_panel)

    def _on_turn_selected(self, row: int):
        """轮次选中"""
        if row >= 0:
            self.turn_selected.emit(row)

    def add_turn(self, turn_id: int, status: str, summary: str = ""):
        """添加轮次记录"""
        colors = {
            "completed": "#4caf50",
            "failed": "#f44336",
            "paused": "#ff9800",
            "current": "#2196f3",
        }
        item = QListWidgetItem(f"回合 {turn_id} [{status}]")
        item.setForeground(QColor(colors.get(status, "#d4d4d4")))
        item.setData(Qt.ItemDataRole.UserRole, {"turn_id": turn_id, "summary": summary})
        self.turn_list.addItem(item)
        self.turn_list.setCurrentRow(self.turn_list.count() - 1)

    def show_turn_detail(self, turn_id: int, detail: str):
        """显示轮次详情"""
        self.detail.setPlainText(f"=== 回合 {turn_id} ===\n\n{detail}")

    def clear_turns(self):
        """清空轮次"""
        self.turn_list.clear()
        self.detail.clear()


class InjectPanel(QWidget):
    """Tab 4: 指令注入"""

    inject_requested = pyqtSignal(str, str)  # (level, content)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 注入级别
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("注入级别:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["system", "user", "override"])
        self.level_combo.setMinimumWidth(150)
        level_layout.addWidget(self.level_combo)
        level_layout.addStretch()
        layout.addLayout(level_layout)

        # 描述
        self.level_desc = QLabel(
            "system: 插入 system prompt 末尾\n"
            "user: 模拟玩家输入\n"
            "override: 覆盖下一轮 Prompt"
        )
        self.level_desc.setStyleSheet("color: #969696; font-size: 11px; padding: 4px;")
        layout.addWidget(self.level_desc)

        # 输入
        layout.addWidget(QLabel("指令内容:"))
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("输入指令内容...")
        self.input.setMaximumHeight(120)
        layout.addWidget(self.input)

        # 发送按钮
        btn_layout = QHBoxLayout()
        self.btn_send = QPushButton("🚀 注入指令")
        self.btn_send.setMinimumHeight(32)
        self.btn_send.clicked.connect(self._on_send)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_send)
        layout.addLayout(btn_layout)

        # 历史记录
        layout.addWidget(QLabel("注入历史:"))
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        self.history.setMaximumHeight(80)
        layout.addWidget(self.history)

    def _on_send(self):
        """发送注入"""
        level = self.level_combo.currentText()
        content = self.input.toPlainText().strip()
        if content:
            self.inject_requested.emit(level, content)
            self.history.appendPlainText(f"[{level}] {content[:50]}...")
            self.input.clear()


class ForceToolPanel(QWidget):
    """Tab 5: 强制工具"""

    tool_execute_requested = pyqtSignal(str, str)  # (tool_name, params)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 工具选择
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(QLabel("工具:"))
        self.tool_combo = QComboBox()
        self.tool_combo.addItems([
            "combat.initiate",
            "dialogue.start",
            "quest.update",
            "exploration.look",
            "narration.describe",
        ])
        self.tool_combo.setMinimumWidth(200)
        tool_layout.addWidget(self.tool_combo)
        tool_layout.addStretch()
        layout.addLayout(tool_layout)

        # 参数
        layout.addWidget(QLabel("工具参数 (JSON):"))
        self.params = QPlainTextEdit()
        self.params.setPlaceholderText('{"target": "敌人", "skill": "攻击"}')
        self.params.setMaximumHeight(80)
        layout.addWidget(self.params)

        # 执行按钮
        btn_layout = QHBoxLayout()
        self.btn_execute = QPushButton("⚡ 强制执行")
        self.btn_execute.setMinimumHeight(32)
        self.btn_execute.clicked.connect(self._on_execute)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_execute)
        layout.addLayout(btn_layout)

        # 结果
        layout.addWidget(QLabel("执行结果:"))
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        layout.addWidget(self.result)

    def _on_execute(self):
        """执行工具"""
        tool = self.tool_combo.currentText()
        params = self.params.toPlainText().strip()
        self.tool_execute_requested.emit(tool, params)
        self.result.appendPlainText(f">>> {tool}\n{params}\n")

    def show_result(self, result: str):
        """显示结果"""
        self.result.appendPlainText(f"<<< {result}\n")


class SettingsPanel(QWidget):
    """Tab 6: 设置"""

    settings_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # API 设置组
        api_group = QGroupBox("API 设置")
        api_layout = QVBoxLayout(api_group)

        # 模型选择
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "deepseek-chat",
            "deepseek-coder",
            "gpt-4",
            "gpt-3.5-turbo",
        ])
        self.model_combo.setMinimumWidth(200)
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        api_layout.addLayout(model_layout)

        # 温度设置
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("温度:"))
        self.temp_combo = QComboBox()
        self.temp_combo.addItems(["0.0", "0.3", "0.5", "0.7", "1.0"])
        self.temp_combo.setCurrentText("0.7")
        self.temp_combo.setMinimumWidth(100)
        temp_layout.addWidget(self.temp_combo)
        temp_layout.addStretch()
        api_layout.addLayout(temp_layout)

        layout.addWidget(api_group)

        # 显示设置组
        display_group = QGroupBox("显示设置")
        display_layout = QVBoxLayout(display_group)

        # 字体大小
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("字体大小:"))
        self.font_combo = QComboBox()
        self.font_combo.addItems(["12", "14", "16", "18", "20"])
        self.font_combo.setCurrentText("14")
        self.font_combo.setMinimumWidth(100)
        font_layout.addWidget(self.font_combo)
        font_layout.addStretch()
        display_layout.addLayout(font_layout)

        # 主题选择
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("主题:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["暗色", "亮色"])
        self.theme_combo.setCurrentText("暗色")
        self.theme_combo.setMinimumWidth(100)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        display_layout.addLayout(theme_layout)

        layout.addWidget(display_group)

        # Agent 设置组
        agent_group = QGroupBox("Agent 设置")
        agent_layout = QVBoxLayout(agent_group)

        # 最大轮次
        turn_layout = QHBoxLayout()
        turn_layout.addWidget(QLabel("最大轮次:"))
        self.max_turns = QComboBox()
        self.max_turns.addItems(["10", "20", "50", "100", "无限制"])
        self.max_turns.setCurrentText("50")
        self.max_turns.setMinimumWidth(100)
        turn_layout.addWidget(self.max_turns)
        turn_layout.addStretch()
        agent_layout.addLayout(turn_layout)

        # 自动保存
        self.auto_save = QComboBox()
        self.auto_save.addItems(["启用", "禁用"])
        self.auto_save.setCurrentText("启用")
        auto_save_layout = QHBoxLayout()
        auto_save_layout.addWidget(QLabel("自动保存:"))
        auto_save_layout.addWidget(self.auto_save)
        auto_save_layout.addStretch()
        agent_layout.addLayout(auto_save_layout)

        layout.addWidget(agent_group)

        # 保存按钮
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 保存设置")
        self.btn_save.setMinimumHeight(32)
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _on_save(self):
        """保存设置"""
        settings = {
            "model": self.model_combo.currentText(),
            "temperature": float(self.temp_combo.currentText()),
            "font_size": int(self.font_combo.currentText()),
            "theme": self.theme_combo.currentText(),
            "max_turns": self.max_turns.currentText(),
            "auto_save": self.auto_save.currentText() == "启用",
        }
        self.settings_changed.emit(settings)


class ConsoleTabs(QTabWidget):
    """底部控制台 — 5 个 Tab"""

    def __init__(self):
        super().__init__()
        self.exec_ctrl = ExecutionCtrlPanel()
        self.flow_view = FlowViewPanel()
        self.turn_timeline = TurnTimelinePanel()
        self.inject_panel = InjectPanel()
        self.force_tool = ForceToolPanel()

        self.addTab(self.exec_ctrl, "▶ 执行控制")
        self.addTab(self.flow_view, "🔄 流程视图")
        self.addTab(self.turn_timeline, "📜 轮次回溯")
        self.addTab(self.inject_panel, "💉 指令注入")
        self.addTab(self.force_tool, "🔧 强制工具")

        # 设置Tab图标样式
        self.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 16px;
            }
        """)
