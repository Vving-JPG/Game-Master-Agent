# 2workbench/presentation/ops/debugger/runtime_panel.py
"""运行时调试器 — Agent 运行控制 + 状态检查 + 变量监视

功能:
1. 运行控制（启动/暂停/停止/单步）
2. 控制台输出（LLM 流式输出 + 系统消息）
3. 变量监视（AgentState 实时查看）
4. 性能指标（Token 用量、响应时间、Turn 计数）

从 _legacy/widgets/console_tabs.py + _legacy/bridge/agent_bridge.py 重构。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QLabel, QPushButton, QFormLayout,
    QComboBox, QLineEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class ConsoleOutput(QWidget):
    """控制台输出组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        self._btn_clear = StyledButton("清空", style_type="ghost")
        self._btn_clear.clicked.connect(self.clear)
        toolbar.addWidget(self._btn_clear)

        self._btn_copy = StyledButton("复制全部", style_type="ghost")
        self._btn_copy.clicked.connect(self._copy_all)
        toolbar.addWidget(self._btn_copy)

        toolbar.addStretch()

        self._line_count = QLabel("行数: 0")
        self._line_count.setStyleSheet("color: #858585; font-size: 11px;")
        toolbar.addWidget(self._line_count)

        layout.addLayout(toolbar)

        # 输出区域
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            "font-family: 'Cascadia Code', 'Consolas', monospace; "
            "font-size: 13px; line-height: 1.5;"
        )
        layout.addWidget(self._output)

        self._count = 0
        self._line_count_int = 0  # 行数统计（整数）

    def append_text(self, text: str, color: str = "#cccccc") -> None:
        """追加文本"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._output.append(
            f'<span style="color: #858585;">[{timestamp}]</span> '
            f'<span style="color: {color};">{text}</span>'
        )
        self._count += 1
        self._line_count.setText(f"行数: {self._count}")
        # 自动滚动到底部
        scrollbar = self._output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_system(self, text: str) -> None:
        """系统消息（灰色）"""
        self.append_text(text, "#858585")

    def append_user(self, text: str) -> None:
        """用户输入（白色）"""
        self.append_text(f"👤 {text}", "#cccccc")

    def append_assistant(self, text: str) -> None:
        """Agent 输出（青色）"""
        self.append_text(f"🤖 {text}", "#4ec9b0")

    def append_error(self, text: str) -> None:
        """错误消息（红色）"""
        self.append_text(f"❌ {text}", "#f44747")

    def append_stream_token(self, token: str) -> None:
        """流式 Token（追加到最后一段）"""
        cursor = self._output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(token)
        self._output.setTextCursor(cursor)
        scrollbar = self._output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # 更新计数
        self._count += len(token)
        if '\n' in token:
            self._line_count_int += token.count('\n')
        self._update_stats()

    def append_command(self, command: str, result: str) -> None:
        """命令执行记录"""
        self.append_text(f"⚡ 命令: {command} → {result}", "#dcdcaa")

    def clear(self) -> None:
        """清空输出"""
        self._output.clear()
        self._count = 0
        self._line_count_int = 0
        self._line_count.setText("行数: 0")

    def _update_stats(self) -> None:
        """更新统计显示"""
        self._count_label.setText(f"字符: {self._count}")
        self._line_count.setText(f"行数: {self._line_count_int}")

    def _copy_all(self) -> None:
        """复制全部内容"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._output.toPlainText())


class VariableWatcher(QWidget):
    """变量监视器 — AgentState 实时查看"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        self._btn_refresh = StyledButton("🔄 刷新", style_type="ghost")
        self._btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(self._btn_refresh)

        self._auto_refresh_btn = StyledButton("⏯ 自动刷新", style_type="ghost")
        self._auto_refresh_btn.setCheckable(True)
        self._auto_refresh_btn.toggled.connect(self._on_auto_refresh_toggled)
        toolbar.addWidget(self._auto_refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 状态表格
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["变量名", "类型", "值"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

    def update_state(self, state: dict[str, Any]) -> None:
        """更新状态显示

        Args:
            state: AgentState 的快照字典
        """
        self._table.setRowCount(0)

        for key, value in state.items():
            row = self._table.rowCount()
            self._table.insertRow(row)

            # 变量名
            self._table.setItem(row, 0, QTableWidgetItem(str(key)))

            # 类型
            type_name = type(value).__name__
            if isinstance(value, list):
                type_name = f"list[{len(value)}]"
            elif isinstance(value, dict):
                type_name = f"dict[{len(value)}]"
            self._table.setItem(row, 1, QTableWidgetItem(type_name))

            # 值（截断长文本）
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:200] + "..."
            self._table.setItem(row, 2, QTableWidgetItem(value_str))

    def refresh(self) -> None:
        """刷新状态（从 GMAgent 获取）"""
        # 实际实现通过 EventBus 请求状态
        event_bus.emit(Event(type="ui.debugger.request_state", data={}))

    def _on_auto_refresh_toggled(self, checked: bool) -> None:
        """切换自动刷新"""
        if checked:
            self._refresh_timer = QTimer(self)
            self._refresh_timer.timeout.connect(self._refresh_metrics)
            self._refresh_timer.start(2000)  # 每 2 秒刷新
            self._auto_refresh_btn.setText("⏸ 停止刷新")
        else:
            if hasattr(self, '_refresh_timer'):
                self._refresh_timer.stop()
            self._auto_refresh_btn.setText("⏯ 自动刷新")

    def _refresh_metrics(self) -> None:
        """刷新性能指标"""
        # 从 EventBus 获取最新指标
        self.refresh()


class PerformanceMetrics(QWidget):
    """性能指标面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._metrics: dict[str, Any] = {
            "total_turns": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_response_time": 0.0,
            "errors": 0,
        }

    def _create_metric_label(self, text: str) -> QLabel:
        """创建统一样式的指标标签"""
        label = QLabel(text)
        label.setStyleSheet("font-size: 18px; font-weight: bold; color: #858585;")
        return label

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._turns_label = self._create_metric_label("0")
        layout.addRow("🔄 总轮次:", self._turns_label)

        self._tokens_label = self._create_metric_label("0")
        layout.addRow("📊 总 Token:", self._tokens_label)

        self._cost_label = self._create_metric_label("¥0.00")
        layout.addRow("💰 总费用:", self._cost_label)

        self._time_label = self._create_metric_label("0ms")
        layout.addRow("⏱ 平均响应:", self._time_label)

        self._error_label = self._create_metric_label("0")
        layout.addRow("❌ 错误数:", self._error_label)

    def update_metrics(self, metrics: dict[str, Any]) -> None:
        """更新性能指标"""
        self._metrics.update(metrics)
        self._turns_label.setText(str(self._metrics.get("total_turns", 0)))
        self._tokens_label.setText(str(self._metrics.get("total_tokens", 0)))
        cost = self._metrics.get("total_cost", 0.0)
        self._cost_label.setText(f"¥{cost:.4f}")
        avg_time = self._metrics.get("avg_response_time", 0.0)
        self._time_label.setText(f"{avg_time:.0f}ms")
        self._error_label.setText(str(self._metrics.get("errors", 0)))

    def reset(self) -> None:
        """重置指标"""
        self._metrics = {
            "total_turns": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_response_time": 0.0,
            "errors": 0,
        }
        self.update_metrics(self._metrics)


class RuntimePanel(BaseWidget):
    """运行时调试器 — 主面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._setup_ui()
        self._setup_eventbus()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 运行控制栏
        control_bar = QHBoxLayout()

        self._btn_run = StyledButton("▶ 运行", style_type="success")
        self._btn_run.clicked.connect(self._on_run)
        control_bar.addWidget(self._btn_run)

        self._btn_pause = StyledButton("⏸ 暂停", style_type="secondary")
        self._btn_pause.clicked.connect(self._on_pause)
        self._btn_pause.setEnabled(False)
        control_bar.addWidget(self._btn_pause)

        self._btn_stop = StyledButton("⏹ 停止", style_type="danger")
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_stop.setEnabled(False)
        control_bar.addWidget(self._btn_stop)

        self._btn_step = StyledButton("⏭ 单步", style_type="secondary")
        self._btn_step.clicked.connect(self._on_step)
        control_bar.addWidget(self._btn_step)

        control_bar.addStretch()

        # 模型选择
        control_bar.addWidget(QLabel("模型:"))
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(150)
        self._model_combo.addItems(["deepseek-chat", "deepseek-reasoner", "gpt-4o", "claude-sonnet"])
        control_bar.addWidget(self._model_combo)

        layout.addLayout(control_bar)

        # 用户输入栏
        input_bar = QHBoxLayout()
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("输入玩家指令（Enter 发送）...")
        self._input_edit.returnPressed.connect(self._on_send_input)
        input_bar.addWidget(self._input_edit)

        self._btn_send = StyledButton("发送", style_type="primary")
        self._btn_send.clicked.connect(self._on_send_input)
        input_bar.addWidget(self._btn_send)

        layout.addLayout(input_bar)

        # 主内容区
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 控制台
        self._console = ConsoleOutput()
        splitter.addWidget(self._console)

        # 下方标签页（变量监视 + 性能指标）
        bottom_tabs = QTabWidget()

        self._var_watcher = VariableWatcher()
        bottom_tabs.addTab(self._var_watcher, "🔍 变量监视")

        self._perf_metrics = PerformanceMetrics()
        bottom_tabs.addTab(self._perf_metrics, "📊 性能指标")

        splitter.addWidget(bottom_tabs)
        splitter.setSizes([500, 250])

        layout.addWidget(splitter)

    def _setup_eventbus(self) -> None:
        """设置 EventBus 订阅"""
        self.subscribe("feature.ai.turn_start", self._on_turn_start)
        self.subscribe("feature.ai.turn_end", self._on_turn_end)
        self.subscribe("feature.ai.agent_error", self._on_agent_error)
        self.subscribe("feature.ai.llm_stream_token", self._on_stream_token)
        self.subscribe("feature.ai.command_parsed", self._on_command_parsed)
        self.subscribe("feature.ai.command_executed", self._on_command_executed)

    # --- 运行控制 ---

    def _on_run(self) -> None:
        """启动 Agent"""
        self._running = True
        self._btn_run.setEnabled(False)
        self._btn_pause.setEnabled(True)
        self._btn_stop.setEnabled(True)
        self._console.append_system("🚀 Agent 已启动")
        self.emit_event("ui.debugger.run", {
            "model": self._model_combo.currentText(),
        })

    def _on_pause(self) -> None:
        """暂停 Agent"""
        self._running = False
        self._btn_run.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._console.append_system("⏸ Agent 已暂停")
        self.emit_event("ui.debugger.pause", {})

    def _on_stop(self) -> None:
        """停止 Agent"""
        self._running = False
        self._btn_run.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(False)
        self._console.append_system("⏹ Agent 已停止")
        self.emit_event("ui.debugger.stop", {})

    def _on_step(self) -> None:
        """单步执行"""
        self._console.append_system("⏭ 单步执行")
        self.emit_event("ui.debugger.step", {})

    def _on_send_input(self) -> None:
        """发送用户输入"""
        text = self._input_edit.text().strip()
        if not text:
            return
        self._console.append_user(text)
        self._input_edit.clear()
        self.emit_event("ui.debugger.input", {"text": text})

    # --- EventBus 回调 ---

    def _on_turn_start(self, event: Event) -> None:
        turn = event.get("turn", 0)
        self._console.append_system(f"--- Turn {turn} 开始 ---")

    def _on_turn_end(self, event: Event) -> None:
        turn = event.get("turn", 0)
        duration = event.get("duration_ms", 0)
        tokens = event.get("tokens", 0)
        self._console.append_system(
            f"--- Turn {turn} 结束 ({duration:.0f}ms, {tokens} tokens) ---"
        )

    def _on_agent_error(self, event: Event) -> None:
        error = event.get("error", "未知错误")
        self._console.append_error(str(error))

    def _on_stream_token(self, event: Event) -> None:
        token = event.get("token", "")
        self._console.append_stream_token(token)

    def _on_command_parsed(self, event: Event) -> None:
        intent = event.get("intent", "")
        params = event.get("params", {})
        self._console.append_command(f"解析意图: {intent}", str(params)[:100])

    def _on_command_executed(self, event: Event) -> None:
        result = event.get("result", {})
        self._console.append_command("执行结果", str(result)[:100])

    # --- 状态更新 ---

    def update_agent_state(self, state: dict[str, Any]) -> None:
        """更新 Agent 状态显示"""
        self._var_watcher.update_state(state)

    def update_performance(self, metrics: dict[str, Any]) -> None:
        """更新性能指标"""
        self._perf_metrics.update_metrics(metrics)
