# P5: Presentation 层 — IDE 运营工具集

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。
> **前置条件**: P0 Foundation + P1 Core + P2 LangGraph Agent + P3 Feature Services + P4 GUI Editor 已全部完成。

## 项目概述

你正在帮助用户将 **Game Master Agent V2** 的 `2workbench/` 目录重构为**四层架构**。

- **技术**: Python 3.11+ / PyQt6 / SQLite / LangGraph / uv / qasync
- **包管理器**: uv
- **开发 IDE**: Trae
- **本 Phase 目标**: 实现 Presentation 层的运营工具集，包括运行时调试器、评估工作台、知识库编辑器、安全护栏、多 Agent 编排、日志追踪和部署管理。这些是 IDE 的高级功能模块。

### 架构约束

```
入口层 → Presentation (表现层) → Feature (功能层) → Core (核心层) → Foundation (基础层)
```

- ✅ Presentation 层**只依赖** Feature、Core 和 Foundation 层
- ❌ Presentation 层**绝对不能**被下层 import
- ✅ Presentation 层通过 EventBus 订阅 Feature 层事件
- ✅ 长时间操作使用 qasync，不阻塞 UI 线程
- ❌ Presentation 层不直接操作数据库，通过 Core 层 Repository

### 本 Phase (P5) 范围

1. **运行时调试器** — Agent 运行控制、状态检查、断点、变量监视
2. **评估工作台** — Prompt 评估、批量测试、指标统计、对比分析
3. **知识库编辑器** — 世界观/角色/物品知识管理、导入导出
4. **安全护栏面板** — 内容过滤规则配置、敏感词管理、输出审核
5. **多 Agent 编排** — Agent 链配置、并行/串行编排、消息路由
6. **日志追踪** — 运行日志查看、EventBus 事件追踪、性能分析
7. **部署管理** — Agent 导出为服务、配置打包、运行状态监控

### 现有代码参考

| 现有文件（`_legacy/`） | 参考内容 | 改进方向 |
|---------|---------|---------|
| `_legacy/widgets/console_tabs.py` | 控制台输出 | 重构为运行时调试器 |
| `_legacy/server.py` | HTTP API 服务 | 重构为部署管理 |
| `_legacy/bridge/agent_bridge.py` | Agent 桥接 | 替换为运行时调试器直连 |
| `_legacy/core/services/cache.py` | LRU 缓存 | 集成到评估工作台 |

### P0-P4 产出（本 Phase 依赖）

```python
# Foundation
from foundation.event_bus import event_bus, Event
from foundation.config import settings
from foundation.logger import get_logger
from foundation.database import init_db, get_db
from foundation.llm import BaseLLMClient, LLMMessage, LLMResponse, StreamEvent
from foundation.llm.model_router import model_router
from foundation.cache import llm_cache

# Core
from core.state import AgentState, create_initial_state
from core.models import (
    World, Player, NPC, Memory, Quest, Item, Location,
    WorldRepo, PlayerRepo, NPCRepo, MemoryRepo, ItemRepo,
    QuestRepo, LogRepo, MetricsRepo, PromptRepo,
)

# Feature
from feature.base import BaseFeature
from feature.registry import feature_registry
from feature.ai import GMAgent
from feature.ai.events import (
    TURN_START, TURN_END, AGENT_ERROR,
    LLM_STREAM_TOKEN, COMMAND_PARSED, COMMAND_EXECUTED,
)

# Presentation
from presentation.main_window import MainWindow
from presentation.theme.manager import theme_manager
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton
from presentation.project.manager import project_manager, ProjectManager
from presentation.editor.graph_editor import GraphEditorWidget
from presentation.editor.prompt_editor import PromptEditorWidget
from presentation.editor.tool_manager import ToolManagerWidget
```

---

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始"后，主动执行
4. **遇到错误先尝试修复**：3 次失败后再询问
5. **代码规范**：UTF-8，中文注释，PEP 8，类型注解
6. **异步安全**：LLM 调用使用 qasync，不阻塞 UI
7. **EventBus 驱动**：UI 更新通过订阅事件触发

---

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **工作目录**: `2workbench/`
- **Presentation Ops**: `2workbench/presentation/ops/`

---

## 步骤

### Step 1: 运行时调试器

**目的**: 实现 Agent 运行控制面板，支持启动/暂停/停止、状态检查、变量监视、EventBus 事件追踪。

**参考**: `_legacy/widgets/console_tabs.py` + `_legacy/bridge/agent_bridge.py`

**方案**:

1.1 创建目录结构：

```
2workbench/presentation/ops/
├── __init__.py
├── debugger/
│   ├── __init__.py
│   ├── runtime_panel.py     # 运行控制面板
│   ├── state_inspector.py   # 状态检查器
│   └── event_monitor.py     # EventBus 事件监视器
├── evaluator/
│   ├── __init__.py
│   └── eval_workbench.py    # 评估工作台
├── knowledge/
│   ├── __init__.py
│   └── knowledge_editor.py  # 知识库编辑器
├── safety/
│   ├── __init__.py
│   └── safety_panel.py      # 安全护栏面板
├── multi_agent/
│   ├── __init__.py
│   └── orchestrator.py      # 多 Agent 编排
├── logger_panel/
│   ├── __init__.py
│   └── log_viewer.py        # 日志追踪
└── deploy/
    ├── __init__.py
    └── deploy_manager.py    # 部署管理
```

1.2 创建 `2workbench/presentation/ops/debugger/runtime_panel.py`：

```python
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

import asyncio
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

    def append_command(self, command: str, result: str) -> None:
        """命令执行记录"""
        self.append_text(f"⚡ 命令: {command} → {result}", "#dcdcaa")

    def clear(self) -> None:
        """清空输出"""
        self._output.clear()
        self._count = 0
        self._line_count.setText("行数: 0")

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

        self._auto_refresh = StyledButton("自动刷新", style_type="ghost")
        self._auto_refresh.setCheckable(True)
        toolbar.addWidget(self._auto_refresh)

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

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._turns_label = QLabel("0")
        self._turns_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #569cd6;")
        layout.addRow("🔄 总轮次:", self._turns_label)

        self._tokens_label = QLabel("0")
        self._tokens_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4ec9b0;")
        layout.addRow("📊 总 Token:", self._tokens_label)

        self._cost_label = QLabel("¥0.00")
        self._cost_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #dcdcaa;")
        layout.addRow("💰 总费用:", self._cost_label)

        self._time_label = QLabel("0ms")
        self._time_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ce9178;")
        layout.addRow("⏱ 平均响应:", self._time_label)

        self._error_label = QLabel("0")
        self._error_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #f44747;")
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
```

1.3 创建 `2workbench/presentation/ops/debugger/event_monitor.py`：

```python
# 2workbench/presentation/ops/debugger/event_monitor.py
"""EventBus 事件监视器 — 实时显示所有 EventBus 事件"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QLabel, QCheckBox,
)
from PyQt6.QtCore import Qt

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class EventMonitor(BaseWidget):
    """EventBus 事件监视器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._event_count = 0
        self._filter_text = ""
        self._paused = False
        self._setup_ui()
        self._install_hook()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("过滤事件类型...")
        self._filter_edit.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._filter_edit)

        self._btn_pause = StyledButton("⏸ 暂停", style_type="ghost")
        self._btn_pause.clicked.connect(self._toggle_pause)
        toolbar.addWidget(self._btn_pause)

        self._btn_clear = StyledButton("清空", style_type="ghost")
        self._btn_clear.clicked.connect(self.clear)
        toolbar.addWidget(self._btn_clear)

        toolbar.addStretch()

        self._count_label = QLabel("事件: 0")
        self._count_label.setStyleSheet("color: #858585; font-size: 11px;")
        toolbar.addWidget(self._count_label)

        layout.addLayout(toolbar)

        # 事件列表
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            "font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px;"
        )
        layout.addWidget(self._output)

    def _install_hook(self) -> None:
        """安装 EventBus 钩子，捕获所有事件"""
        original_emit = event_bus.emit

        def hooked_emit(event: Event) -> list:
            if not self._paused:
                self._on_event(event)
            return original_emit(event)

        event_bus.emit = hooked_emit
        self._logger.info("EventBus 钩子已安装")

    def _on_event(self, event: Event) -> None:
        """处理捕获的事件"""
        if self._filter_text and self._filter_text not in event.type:
            return

        self._event_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        source = event.source or "unknown"
        data_preview = str(event.data)[:80] if event.data else "{}"

        # 根据事件类型着色
        color = "#cccccc"
        if "error" in event.type.lower():
            color = "#f44747"
        elif "stream" in event.type.lower():
            color = "#4ec9b0"
        elif "turn" in event.type.lower():
            color = "#569cd6"
        elif "command" in event.type.lower():
            color = "#dcdcaa"

        self._output.append(
            f'<span style="color: #858585;">[{timestamp}]</span> '
            f'<span style="color: {color};">{event.type}</span> '
            f'<span style="color: #6e6e6e;">← {source}</span> '
            f'<span style="color: #858585;">{data_preview}</span>'
        )

        self._count_label.setText(f"事件: {self._event_count}")

        # 限制行数
        if self._output.document().blockCount() > 2000:
            cursor = self._output.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.KeepAnchor, 500)
            cursor.removeSelectedText()

    def _on_filter_changed(self, text: str) -> None:
        self._filter_text = text

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self._btn_pause.setText("▶ 继续" if self._paused else "⏸ 暂停")

    def clear(self) -> None:
        self._output.clear()
        self._event_count = 0
        self._count_label.setText("事件: 0")
```

1.4 创建各模块 `__init__.py`：

```python
# 2workbench/presentation/ops/__init__.py
"""Presentation 层 — IDE 运营工具集"""

# 2workbench/presentation/ops/debugger/__init__.py
"""运行时调试器"""
from presentation.ops.debugger.runtime_panel import RuntimePanel
from presentation.ops.debugger.event_monitor import EventMonitor
__all__ = ["RuntimePanel", "EventMonitor"]
```

1.5 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.ops.debugger.runtime_panel import (
    RuntimePanel, ConsoleOutput, VariableWatcher, PerformanceMetrics,
)

# 测试 ConsoleOutput
console = ConsoleOutput()
console.append_system('系统消息')
console.append_user('玩家输入')
console.append_assistant('Agent 回复')
console.append_error('错误消息')
console.append_command('start_combat', '{\"enemies\": [...]}')
assert console._count == 5
print('✅ ConsoleOutput 测试通过')

# 测试 VariableWatcher
watcher = VariableWatcher()
watcher.update_state({
    'messages': [{'role': 'user', 'content': 'hello'}],
    'turn': 5,
    'world_id': 1,
    'player_name': '冒险者',
    'active_quests': ['拯救公主', '探索洞穴'],
})
assert watcher._table.rowCount() == 5
print('✅ VariableWatcher 测试通过')

# 测试 PerformanceMetrics
metrics = PerformanceMetrics()
metrics.update_metrics({
    'total_turns': 10,
    'total_tokens': 5000,
    'total_cost': 0.15,
    'avg_response_time': 1200,
    'errors': 2,
})
assert metrics._metrics['total_turns'] == 10
print('✅ PerformanceMetrics 测试通过')

# 测试 RuntimePanel
panel = RuntimePanel()
assert not panel._running
print('✅ RuntimePanel 创建成功')

# 测试 EventMonitor
from presentation.ops.debugger.event_monitor import EventMonitor
monitor = EventMonitor()

# 触发测试事件
from foundation.event_bus import event_bus, Event
event_bus.emit(Event(type='test.event', data={'key': 'value'}))
assert monitor._event_count >= 1
print(f'✅ EventMonitor 捕获 {monitor._event_count} 个事件')

print('✅ 运行时调试器测试通过')
"
```

**验收**:
- [ ] ConsoleOutput（系统/用户/Agent/错误/命令/流式 Token）
- [ ] VariableWatcher（AgentState 表格显示）
- [ ] PerformanceMetrics（轮次/Token/费用/响应时间/错误数）
- [ ] RuntimePanel（运行控制 + 输入 + 控制台 + 变量 + 指标）
- [ ] EventMonitor（EventBus 全事件捕获 + 过滤 + 暂停）
- [ ] 测试通过

---

### Step 2: 评估工作台

**目的**: 实现 Prompt 评估工具，支持批量测试、指标统计和对比分析。

**方案**:

2.1 创建 `2workbench/presentation/ops/evaluator/eval_workbench.py`：

```python
# 2workbench/presentation/ops/evaluator/eval_workbench.py
"""评估工作台 — Prompt 评估、批量测试、指标统计、对比分析

功能:
1. 评估用例管理（导入/编辑/运行）
2. 评估指标（相关性、准确性、一致性、延迟、Token 用量）
3. 批量运行（多模型对比）
4. 结果统计和可视化
5. 历史记录
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QFormLayout, QComboBox,
    QLineEdit, QPushButton, QFileDialog, QProgressBar,
    QGroupBox, QDialog, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from foundation.event_bus import event_bus, Event
from foundation.llm import LLMMessage
from foundation.llm.model_router import model_router
from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


@dataclass
class EvalCase:
    """评估用例"""
    id: str = ""
    input_text: str = ""
    expected_output: str = ""
    actual_output: str = ""
    model: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    score: float = 0.0  # 0-10 评分
    notes: str = ""


@dataclass
class EvalResult:
    """评估结果"""
    model: str = ""
    total_cases: int = 0
    avg_score: float = 0.0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    pass_rate: float = 0.0  # score >= 6 的比例
    cases: list[EvalCase] = field(default_factory=list)


class EvalCaseEditor(QWidget):
    """评估用例编辑器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cases: list[EvalCase] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        self._btn_add = StyledButton("+ 添加用例", style_type="primary")
        self._btn_add.clicked.connect(self._add_case)
        toolbar.addWidget(self._btn_add)

        self._btn_import = StyledButton("📥 导入 JSON", style_type="secondary")
        self._btn_import.clicked.connect(self._import_cases)
        toolbar.addWidget(self._btn_import)

        self._btn_clear = StyledButton("清空", style_type="ghost")
        self._btn_clear.clicked.connect(self._clear_cases)
        toolbar.addWidget(self._btn_clear)

        toolbar.addStretch()
        self._count_label = QLabel("用例: 0")
        self._count_label.setStyleSheet("color: #858585;")
        toolbar.addWidget(self._count_label)

        layout.addLayout(toolbar)

        # 用例表格
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "ID", "输入", "期望输出", "实际输出", "评分", "延迟"
        ])
        self._table.horizontalHeader().setStretchLastSection(True)
        for i in range(5):
            self._table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.Interactive
            )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

    def _add_case(self) -> None:
        """添加空用例"""
        case = EvalCase(
            id=f"case_{len(self._cases) + 1}",
            input_text="",
            expected_output="",
        )
        self._cases.append(case)
        self._refresh_table()

    def _import_cases(self) -> None:
        """从 JSON 导入用例"""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入评估用例", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                self._cases.append(EvalCase(
                    id=item.get("id", f"case_{len(self._cases)+1}"),
                    input_text=item.get("input", ""),
                    expected_output=item.get("expected", ""),
                ))
            self._refresh_table()
            self._logger.info(f"导入 {len(data)} 个评估用例")
        except Exception as e:
            self._logger.error(f"导入失败: {e}")

    def _clear_cases(self) -> None:
        self._cases.clear()
        self._refresh_table()

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        for case in self._cases:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(case.id))
            self._table.setItem(row, 1, QTableWidgetItem(case.input_text[:50]))
            self._table.setItem(row, 2, QTableWidgetItem(case.expected_output[:50]))
            self._table.setItem(row, 3, QTableWidgetItem(case.actual_output[:50] if case.actual_output else "-"))
            score_item = QTableWidgetItem(f"{case.score:.1f}" if case.score else "-")
            self._table.setItem(row, 4, score_item)
            latency_item = QTableWidgetItem(f"{case.latency_ms:.0f}ms" if case.latency_ms else "-")
            self._table.setItem(row, 5, latency_item)
        self._count_label.setText(f"用例: {len(self._cases)}")

    def get_cases(self) -> list[EvalCase]:
        return list(self._cases)


class EvalWorkbench(BaseWidget):
    """评估工作台"""

    eval_completed = pyqtSignal(object)  # EvalResult

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: list[EvalResult] = []
        self._running = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 顶部配置
        config_bar = QHBoxLayout()

        config_bar.addWidget(QLabel("Prompt:"))
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setMaximumHeight(60)
        self._prompt_edit.setPlaceholderText("输入要评估的 Prompt 模板...")
        config_bar.addWidget(self._prompt_edit, 1)

        layout.addLayout(config_bar)

        model_bar = QHBoxLayout()
        model_bar.addWidget(QLabel("模型:"))
        self._model_combo = QComboBox()
        self._model_combo.addItems(["deepseek-chat", "deepseek-reasoner", "gpt-4o", "claude-sonnet"])
        self._model_combo.setMinimumWidth(150)
        model_bar.addWidget(self._model_combo)

        self._btn_run = StyledButton("▶ 运行评估", style_type="success")
        self._btn_run.clicked.connect(self._run_eval)
        model_bar.addWidget(self._btn_run)

        self._btn_compare = StyledButton("📊 对比分析", style_type="secondary")
        self._btn_compare.clicked.connect(self._show_comparison)
        model_bar.addWidget(self._btn_compare)

        model_bar.addStretch()

        self._progress = QProgressBar()
        self._progress.setMaximumWidth(200)
        self._progress.setVisible(False)
        model_bar.addWidget(self._progress)

        layout.addLayout(model_bar)

        # 主内容
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 用例编辑器
        self._case_editor = EvalCaseEditor()
        splitter.addWidget(self._case_editor)

        # 结果面板
        result_group = QGroupBox("评估结果")
        result_layout = QVBoxLayout(result_group)

        self._result_table = QTableWidget()
        self._result_table.setColumnCount(6)
        self._result_table.setHorizontalHeaderLabels([
            "模型", "用例数", "平均分", "通过率", "平均延迟", "总 Token"
        ])
        self._result_table.horizontalHeader().setStretchLastSection(True)
        self._result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._result_table.setAlternatingRowColors(True)
        result_layout.addWidget(self._result_table)

        splitter.addWidget(result_group)
        splitter.setSizes([400, 300])

        layout.addWidget(splitter)

    def _run_eval(self) -> None:
        """运行评估（同步模拟，实际使用 qasync）"""
        cases = self._case_editor.get_cases()
        if not cases:
            self._logger.warning("没有评估用例")
            return

        model = self._model_combo.currentText()
        prompt_template = self._prompt_edit.toPlainText()

        self._running = True
        self._btn_run.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setMaximum(len(cases))
        self._progress.setValue(0)

        # 同步模拟评估（实际应使用 qasync）
        result = EvalResult(model=model, total_cases=len(cases))
        total_score = 0.0
        total_latency = 0.0
        total_tokens = 0
        passed = 0

        for i, case in enumerate(cases):
            # 模拟评估结果
            case.model = model
            case.latency_ms = 800 + i * 100  # 模拟延迟
            case.tokens_used = 100 + i * 50
            case.score = 7.0 + (i % 3)  # 模拟评分
            case.actual_output = f"[模拟输出] 对 '{case.input_text[:20]}...' 的回复"

            total_score += case.score
            total_latency += case.latency_ms
            total_tokens += case.tokens_used
            if case.score >= 6:
                passed += 1

            self._progress.setValue(i + 1)

        result.avg_score = total_score / len(cases)
        result.avg_latency_ms = total_latency / len(cases)
        result.total_tokens = total_tokens
        result.pass_rate = passed / len(cases)
        result.cases = cases

        self._results.append(result)
        self._refresh_results()
        self._case_editor._refresh_table()

        self._running = False
        self._btn_run.setEnabled(True)
        self._progress.setVisible(False)

        self._logger.info(
            f"评估完成: {model}, 平均分={result.avg_score:.1f}, "
            f"通过率={result.pass_rate:.0%}"
        )
        self.eval_completed.emit(result)

    def _refresh_results(self) -> None:
        """刷新结果表格"""
        self._result_table.setRowCount(0)
        for result in self._results:
            row = self._result_table.rowCount()
            self._result_table.insertRow(row)
            self._result_table.setItem(row, 0, QTableWidgetItem(result.model))
            self._result_table.setItem(row, 1, QTableWidgetItem(str(result.total_cases)))
            self._result_table.setItem(row, 2, QTableWidgetItem(f"{result.avg_score:.1f}"))
            self._result_table.setItem(row, 3, QTableWidgetItem(f"{result.pass_rate:.0%}"))
            self._result_table.setItem(row, 4, QTableWidgetItem(f"{result.avg_latency_ms:.0f}ms"))
            self._result_table.setItem(row, 5, QTableWidgetItem(str(result.total_tokens)))

    def _show_comparison(self) -> None:
        """显示对比分析"""
        if len(self._results) < 2:
            self._logger.warning("至少需要 2 次评估结果才能对比")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("模型对比分析")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        comparison = QTextEdit()
        comparison.setReadOnly(True)

        lines = ["# 模型对比分析\n"]
        lines.append(f"| 指标 | " + " | ".join(r.model for r in self._results) + " |")
        lines.append("| --- | " + " | ".join("---" for _ in self._results) + " |")
        lines.append(f"| 平均分 | " + " | ".join(f"{r.avg_score:.1f}" for r in self._results) + " |")
        lines.append(f"| 通过率 | " + " | ".join(f"{r.pass_rate:.0%}" for r in self._results) + " |")
        lines.append(f"| 平均延迟 | " + " | ".join(f"{r.avg_latency_ms:.0f}ms" for r in self._results) + " |")
        lines.append(f"| 总 Token | " + " | ".join(str(r.total_tokens) for r in self._results) + " |")

        comparison.setPlainText("\n".join(lines))
        layout.addWidget(comparison)

        dialog.exec()
```

2.2 创建 `__init__.py`：

```python
# 2workbench/presentation/ops/evaluator/__init__.py
"""评估工作台"""
from presentation.ops.evaluator.eval_workbench import EvalWorkbench
__all__ = ["EvalWorkbench"]
```

2.3 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.ops.evaluator.eval_workbench import EvalWorkbench, EvalCase

bench = EvalWorkbench()

# 添加测试用例
bench._case_editor._cases = [
    EvalCase(id='c1', input_text='你好', expected_output='你好！有什么可以帮助你的？'),
    EvalCase(id='c2', input_text='掷骰子', expected_output='你掷出了 15 点'),
    EvalCase(id='c3', input_text='攻击哥布林', expected_output='你对哥布林造成了 8 点伤害'),
]
bench._case_editor._refresh_table()
assert bench._case_editor._table.rowCount() == 3
print('✅ 评估用例加载成功')

# 运行评估
bench._run_eval()
assert len(bench._results) == 1
result = bench._results[0]
assert result.total_cases == 3
assert result.avg_score > 0
print(f'✅ 评估完成: 平均分={result.avg_score:.1f}, 通过率={result.pass_rate:.0%}')

print('✅ 评估工作台测试通过')
"
```

**验收**:
- [ ] 评估用例编辑器（添加/导入/清空）
- [ ] 评估运行（模型选择 + 进度条）
- [ ] 结果统计（平均分/通过率/延迟/Token）
- [ ] 对比分析（多模型对比表格）
- [ ] 测试通过

---

### Step 3: 知识库编辑器

**目的**: 实现世界观数据的可视化编辑器，管理 NPC、地点、物品、任务等知识。

**方案**:

3.1 创建 `2workbench/presentation/ops/knowledge/knowledge_editor.py`：

```python
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
        return QFormLayout()
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
        self._npc_list.currentRowChanged.connect(self._on_npc_selected)
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

    def _on_npc_selected(self, row: int) -> None:
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
        self._npc_list.setCurrentRow(len(self._npcs) - 1)

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
        self._npc_list.setCurrentRow(row)
        self.data_changed.emit()
        self._logger.info(f"NPC 已保存: {self._npcs[row]['name']}")

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
        self._loc_list.currentRowChanged.connect(self._on_loc_selected)
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

    def _on_loc_selected(self, row: int) -> None:
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
        self._loc_list.setCurrentRow(len(self._locations) - 1)

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
        self._loc_list.setCurrentRow(row)
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
            self._logger.info(f"知识库导入成功: {path}")
        except Exception as e:
            self._logger.error(f"导入失败: {e}")

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
            self._logger.info(f"知识库导出成功: {path}")
        except Exception as e:
            self._logger.error(f"导出失败: {e}")
```

3.2 创建 `__init__.py`：

```python
# 2workbench/presentation/ops/knowledge/__init__.py
"""知识库编辑器"""
from presentation.ops.knowledge.knowledge_editor import KnowledgeEditor
__all__ = ["KnowledgeEditor"]
```

3.3 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.ops.knowledge.knowledge_editor import KnowledgeEditor

editor = KnowledgeEditor()

# 加载测试数据
editor._npc_editor.load_data([
    {'name': '老村长', 'mood': 'serene', 'speech_style': '温和', 'backstory': '守护村庄50年', 'goals': ['守护知识'], 'personality': {'openness': 0.8, 'agreeableness': 0.8}},
    {'name': '铁匠', 'mood': 'happy', 'speech_style': '豪爽', 'backstory': '退伍军人', 'goals': ['打造神兵'], 'personality': {'extraversion': 0.9}},
])
assert editor._npc_editor._npc_list.rowCount() == 2
print('✅ NPC 数据加载成功')

editor._loc_editor.load_data([
    {'name': '宁静村', 'description': '一个宁静的小村庄', 'connections': {'north': 2, 'east': 3}},
    {'name': '幽暗森林', 'description': '阴森的森林', 'connections': {'south': 1}},
])
assert editor._loc_editor._loc_list.rowCount() == 2
print('✅ 地点数据加载成功')

# 测试添加 NPC
editor._npc_editor._add_npc()
assert editor._npc_editor._npc_list.rowCount() == 3
print('✅ 添加 NPC 成功')

# 测试标签页
assert editor._tabs.count() == 4
print('✅ 标签页: NPC/地点/物品/任务')

print('✅ 知识库编辑器测试通过')
"
```

**验收**:
- [ ] NPC 编辑器（列表 + 详情 + 性格参数 + 保存）
- [ ] 地点编辑器（列表 + 详情 + 连接编辑 + 保存）
- [ ] 物品/任务占位标签页
- [ ] JSON 导入/导出
- [ ] 测试通过

---

### Step 4: 安全护栏面板

**目的**: 实现内容安全配置面板，管理敏感词、输出过滤规则和内容审核。

**方案**:

4.1 创建 `2workbench/presentation/ops/safety/safety_panel.py`：

```python
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
from PyQt6.QtCore import Qt

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
        self._logger.info(f"规则已保存: {rule.name}")

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
            self._logger.error(f"导入失败: {e}")

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
            self._logger.error(f"导出失败: {e}")

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
```

4.2 创建 `__init__.py`：

```python
# 2workbench/presentation/ops/safety/__init__.py
"""安全护栏"""
from presentation.ops.safety.safety_panel import SafetyPanel, SafetyLevel
__all__ = ["SafetyPanel", "SafetyLevel"]
```

4.3 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.ops.safety.safety_panel import SafetyPanel, SafetyLevel

panel = SafetyPanel()

# 验证默认规则
assert len(panel._rules) == 3
print(f'✅ 默认规则: {len(panel._rules)} 条')

# 测试过滤
test_text = '他拿刀砍向敌人，鲜血四溅。'
filtered = panel.filter_text(test_text)
assert '***' in filtered
print(f'✅ 过滤测试: \"{test_text}\" → \"{filtered}\"')

# 切换到宽松模式
panel._level_combo.setCurrentText('宽松')
panel._on_level_changed('宽松')
filtered_relaxed = panel.filter_text(test_text)
print(f'✅ 宽松模式: \"{filtered_relaxed}\"')

# 测试添加规则
panel._add_rule()
assert len(panel._rules) == 4
print('✅ 添加规则成功')

# 测试活跃规则
active = panel.get_active_rules()
print(f'✅ 活跃规则: {len(active)} 条')

print('✅ 安全护栏面板测试通过')
"
```

**验收**:
- [ ] 3 条默认过滤规则（暴力/色情/政治）
- [ ] 规则编辑（名称/正则/分类/级别/替换文本）
- [ ] 安全级别切换（严格/标准/宽松）
- [ ] 过滤预览测试
- [ ] 规则导入/导出
- [ ] 测试通过

---

### Step 5: 多 Agent 编排 + 日志追踪 + 部署管理

**目的**: 实现多 Agent 编排面板、日志追踪查看器和部署管理器（三个模块合并为一个 Step）。

**方案**:

5.1 创建 `2workbench/presentation/ops/multi_agent/orchestrator.py`：

```python
# 2workbench/presentation/ops/multi_agent/orchestrator.py
"""多 Agent 编排器 — Agent 链配置和消息路由

功能:
1. Agent 实例管理（创建/配置/删除）
2. 链式编排（串行/并行/条件分支）
3. 消息路由规则
4. 可视化拓扑
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QListWidget, QListWidgetItem, QTabWidget,
    QFormLayout, QLineEdit, QComboBox, QTextEdit,
    QGroupBox,
)
from PyQt6.QtCore import Qt

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


@dataclass
class AgentInstance:
    """Agent 实例定义"""
    id: str = ""
    name: str = ""
    role: str = "general"  # gm / narrator / combat / dialogue / custom
    model: str = "deepseek-chat"
    system_prompt: str = ""
    enabled: bool = True


@dataclass
class ChainStep:
    """链式步骤"""
    agent_id: str = ""
    step_type: str = "sequential"  # sequential / parallel / conditional
    condition: str = ""  # 条件表达式（conditional 时使用）
    next_agent_id: str = ""


class MultiAgentOrchestrator(BaseWidget):
    """多 Agent 编排器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._agents: list[AgentInstance] = []
        self._chain: list[ChainStep] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        self._btn_add_agent = StyledButton("+ 添加 Agent", style_type="primary")
        self._btn_add_agent.clicked.connect(self._add_agent)
        toolbar.addWidget(self._btn_add_agent)

        self._btn_add_link = StyledButton("🔗 添加连接", style_type="secondary")
        self._btn_add_link.clicked.connect(self._add_link)
        toolbar.addWidget(self._btn_add_link)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 主内容
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: Agent 列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        agent_label = QLabel("🤖 Agent 实例")
        agent_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(agent_label)

        self._agent_list = QListWidget()
        self._agent_list.currentRowChanged.connect(self._on_agent_selected)
        left_layout.addWidget(self._agent_list)

        splitter.addWidget(left)

        # 中央: Agent 配置
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(8, 8, 8, 8)

        config_group = QGroupBox("Agent 配置")
        config_layout = QFormLayout(config_group)

        self._name_edit = QLineEdit()
        config_layout.addRow("名称:", self._name_edit)

        self._role_combo = QComboBox()
        self._role_combo.addItems(["gm", "narrator", "combat", "dialogue", "custom"])
        config_layout.addRow("角色:", self._role_combo)

        self._model_combo = QComboBox()
        self._model_combo.addItems(["deepseek-chat", "deepseek-reasoner", "gpt-4o", "claude-sonnet"])
        config_layout.addRow("模型:", self._model_combo)

        self._prompt_edit = QTextEdit()
        self._prompt_edit.setMaximumHeight(120)
        self._prompt_edit.setPlaceholderText("System Prompt...")
        config_layout.addRow("System Prompt:", self._prompt_edit)

        self._btn_save_agent = StyledButton("💾 保存", style_type="primary")
        self._btn_save_agent.clicked.connect(self._save_agent)
        config_layout.addRow(self._btn_save_agent)

        center_layout.addWidget(config_group)
        splitter.addWidget(center)

        # 右侧: 链式拓扑
        right = QWidget()
        right.setMaximumWidth(250)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        chain_label = QLabel("🔗 编排链")
        chain_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(chain_label)

        self._chain_list = QListWidget()
        right_layout.addWidget(self._chain_list)

        splitter.addWidget(right)
        splitter.setSizes([200, 400, 200])
        layout.addWidget(splitter)

    def _add_agent(self) -> None:
        agent = AgentInstance(
            id=f"agent_{len(self._agents)+1}",
            name=f"Agent_{len(self._agents)+1}",
        )
        self._agents.append(agent)
        self._refresh_agent_list()
        self._agent_list.setCurrentRow(len(self._agents) - 1)

    def _on_agent_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._agents):
            return
        agent = self._agents[row]
        self._name_edit.setText(agent.name)
        idx = self._role_combo.findText(agent.role)
        if idx >= 0:
            self._role_combo.setCurrentIndex(idx)
        idx = self._model_combo.findText(agent.model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        self._prompt_edit.setPlainText(agent.system_prompt)

    def _save_agent(self) -> None:
        row = self._agent_list.currentRow()
        if row < 0:
            return
        agent = self._agents[row]
        agent.name = self._name_edit.text()
        agent.role = self._role_combo.currentText()
        agent.model = self._model_combo.currentText()
        agent.system_prompt = self._prompt_edit.toPlainText()
        self._refresh_agent_list()
        self._agent_list.setCurrentRow(row)

    def _add_link(self) -> None:
        if len(self._agents) < 2:
            self._logger.warning("至少需要 2 个 Agent 才能创建连接")
            return
        step = ChainStep(
            agent_id=self._agents[-2].id,
            next_agent_id=self._agents[-1].id,
        )
        self._chain.append(step)
        self._refresh_chain_list()

    def _refresh_agent_list(self) -> None:
        self._agent_list.clear()
        for agent in self._agents:
            status = "✅" if agent.enabled else "❌"
            self._agent_list.addItem(f"{status} {agent.name} ({agent.role})")

    def _refresh_chain_list(self) -> None:
        self._chain_list.clear()
        for step in self._chain:
            self._chain_list.addItem(f"{step.agent_id} → {step.next_agent_id} [{step.step_type}]")

    def get_config(self) -> dict:
        """导出编排配置"""
        return {
            "agents": [
                {"id": a.id, "name": a.name, "role": a.role, "model": a.model, "system_prompt": a.system_prompt}
                for a in self._agents
            ],
            "chain": [
                {"agent_id": s.agent_id, "next_agent_id": s.next_agent_id, "type": s.step_type}
                for s in self._chain
            ],
        }
```

5.2 创建 `2workbench/presentation/ops/logger_panel/log_viewer.py`：

```python
# 2workbench/presentation/ops/logger_panel/log_viewer.py
"""日志追踪 — 运行日志查看和性能分析"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QComboBox, QCheckBox, QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class LogViewer(BaseWidget):
    """日志追踪查看器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_path: Path | None = None
        self._auto_scroll = True
        self._filters: dict[str, bool] = {
            "DEBUG": True,
            "INFO": True,
            "WARNING": True,
            "ERROR": True,
        }
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()

        self._btn_open = StyledButton("📂 打开日志", style_type="secondary")
        self._btn_open.clicked.connect(self._open_log)
        toolbar.addWidget(self._btn_open)

        toolbar.addStretch()

        # 级别过滤
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            cb = QCheckBox(level)
            cb.setChecked(True)
            cb.stateChanged.connect(lambda state, l=level: self._toggle_filter(l, state))
            toolbar.addWidget(cb)

        toolbar.addStretch()

        self._btn_auto_scroll = QCheckBox("自动滚动")
        self._btn_auto_scroll.setChecked(True)
        self._btn_auto_scroll.stateChanged.connect(lambda s: setattr(self, '_auto_scroll', bool(s)))
        toolbar.addWidget(self._btn_auto_scroll)

        self._btn_clear = StyledButton("清空", style_type="ghost")
        self._btn_clear.clicked.connect(lambda: self._output.clear())
        toolbar.addWidget(self._btn_clear)

        layout.addLayout(toolbar)

        # 日志输出
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            "font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px;"
        )
        layout.addWidget(self._output)

    def _toggle_filter(self, level: str, state) -> None:
        self._filters[level] = bool(state)

    def _open_log(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "打开日志文件", "", "日志 (*.log);;所有文件 (*)"
        )
        if path:
            self._log_path = Path(path)
            self._load_log()

    def _load_log(self) -> None:
        if not self._log_path or not self._log_path.exists():
            return
        try:
            content = self._log_path.read_text(encoding="utf-8")
            self._output.setPlainText(content)
        except Exception as e:
            self._logger.error(f"日志加载失败: {e}")

    def append_log(self, level: str, message: str, source: str = "") -> None:
        """追加日志条目"""
        if not self._filters.get(level, True):
            return

        color_map = {
            "DEBUG": "#858585",
            "INFO": "#cccccc",
            "WARNING": "#dcdcaa",
            "ERROR": "#f44747",
        }
        color = color_map.get(level, "#cccccc")
        timestamp = datetime.now().strftime("%H:%M:%S")

        self._output.append(
            f'<span style="color: #858585;">[{timestamp}]</span> '
            f'<span style="color: {color}; font-weight: bold;">[{level}]</span> '
            f'<span style="color: #6e6e6e;">{source}</span> '
            f'<span style="color: {color};">{message}</span>'
        )

        if self._auto_scroll:
            scrollbar = self._output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
```

5.3 创建 `2workbench/presentation/ops/deploy/deploy_manager.py`：

```python
# 2workbench/presentation/ops/deploy/deploy_manager.py
"""部署管理器 — Agent 导出为服务、配置打包、运行状态监控

功能:
1. Agent 项目打包（包含所有配置、Prompt、工具）
2. 导出为独立服务（FastAPI/Flask）
3. 运行配置管理
4. 部署状态监控
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QLineEdit, QTextEdit,
    QGroupBox, QProgressBar, QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class DeployManager(BaseWidget):
    """部署管理器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._deploy_status = "idle"  # idle / packaging / deploying / running / error
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 状态栏
        status_bar = QHBoxLayout()
        self._status_label = QLabel("⚪ 就绪")
        self._status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_bar.addWidget(self._status_label)

        status_bar.addStretch()
        layout.addLayout(status_bar)

        # 标签页
        self._tabs = QTabWidget()

        # 打包配置
        pack_widget = QWidget()
        pack_layout = QVBoxLayout(pack_widget)

        config_group = QGroupBox("打包配置")
        config_form = QFormLayout(config_group)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("my_agent_service")
        config_form.addRow("服务名称:", self._name_edit)

        self._version_edit = QLineEdit()
        self._version_edit.setText("1.0.0")
        config_form.addRow("版本:", self._version_edit)

        self._framework_combo = QComboBox()
        self._framework_combo.addItems(["FastAPI", "Flask", "Standalone"])
        config_form.addRow("框架:", self._framework_combo)

        self._port_spin = QLineEdit()
        self._port_spin.setText("8000")
        config_form.addRow("端口:", self._port_spin)

        self._host_edit = QLineEdit()
        self._host_edit.setText("0.0.0.0")
        config_form.addRow("主机:", self._host_edit)

        pack_layout.addWidget(config_group)

        self._btn_package = StyledButton("📦 打包项目", style_type="primary")
        self._btn_package.clicked.connect(self._package_project)
        pack_layout.addWidget(self._btn_package)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        pack_layout.addWidget(self._progress)

        self._pack_log = QTextEdit()
        self._pack_log.setReadOnly(True)
        self._pack_log.setMaximumHeight(150)
        self._pack_log.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        pack_layout.addWidget(self._pack_log)

        pack_layout.addStretch()
        self._tabs.addTab(pack_widget, "📦 打包")

        # 运行监控
        monitor_widget = QWidget()
        monitor_layout = QVBoxLayout(monitor_widget)

        monitor_group = QGroupBox("运行状态")
        monitor_form = QFormLayout(monitor_group)

        self._run_status = QLabel("未运行")
        monitor_form.addRow("状态:", self._run_status)

        self._run_uptime = QLabel("0:00:00")
        monitor_form.addRow("运行时间:", self._run_uptime)

        self._run_requests = QLabel("0")
        monitor_form.addRow("请求数:", self._run_requests)

        self._run_errors = QLabel("0")
        monitor_form.addRow("错误数:", self._run_errors)

        monitor_layout.addWidget(monitor_group)

        run_toolbar = QHBoxLayout()
        self._btn_start = StyledButton("▶ 启动服务", style_type="success")
        self._btn_start.clicked.connect(self._start_service)
        run_toolbar.addWidget(self._btn_start)

        self._btn_stop = StyledButton("⏹ 停止服务", style_type="danger")
        self._btn_stop.clicked.connect(self._stop_service)
        self._btn_stop.setEnabled(False)
        run_toolbar.addWidget(self._btn_stop)

        monitor_layout.addLayout(run_toolbar)
        monitor_layout.addStretch()
        self._tabs.addTab(monitor_widget, "📊 监控")

        layout.addWidget(self._tabs)

    def _package_project(self) -> None:
        """打包项目"""
        from presentation.project.manager import project_manager

        if not project_manager.is_open:
            self._pack_log.append("❌ 没有打开的项目")
            return

        self._deploy_status = "packaging"
        self._status_label.setText("📦 打包中...")
        self._progress.setVisible(True)
        self._progress.setValue(0)

        project_path = project_manager.project_path
        if not project_path:
            return

        name = self._name_edit.text().strip() or "agent_service"
        version = self._version_edit.text().strip()

        # 模拟打包过程
        self._pack_log.append(f"📦 开始打包: {name} v{version}")
        self._pack_log.append(f"   项目路径: {project_path}")
        self._progress.setValue(20)

        # 收集文件列表
        files = list(project_path.rglob("*"))
        file_count = len([f for f in files if f.is_file()])
        self._pack_log.append(f"   文件数: {file_count}")
        self._progress.setValue(50)

        # 模拟生成服务入口
        self._pack_log.append(f"   框架: {self._framework_combo.currentText()}")
        self._pack_log.append(f"   端口: {self._port_spin.text()}")
        self._progress.setValue(80)

        self._pack_log.append(f"   生成入口文件: server.py")
        self._progress.setValue(100)

        self._deploy_status = "idle"
        self._status_label.setText("✅ 打包完成")
        self._pack_log.append(f"✅ 打包完成: {name}_v{version}")
        self._logger.info(f"项目打包完成: {name} v{version}")

    def _start_service(self) -> None:
        """启动服务"""
        self._deploy_status = "running"
        self._status_label.setText("🟢 运行中")
        self._run_status.setText("运行中")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._logger.info("服务已启动（模拟）")

    def _stop_service(self) -> None:
        """停止服务"""
        self._deploy_status = "idle"
        self._status_label.setText("⚪ 已停止")
        self._run_status.setText("已停止")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._logger.info("服务已停止")
```

5.4 创建各模块 `__init__.py`：

```python
# 2workbench/presentation/ops/multi_agent/__init__.py
"""多 Agent 编排"""
from presentation.ops.multi_agent.orchestrator import MultiAgentOrchestrator
__all__ = ["MultiAgentOrchestrator"]

# 2workbench/presentation/ops/logger_panel/__init__.py
"""日志追踪"""
from presentation.ops.logger_panel.log_viewer import LogViewer
__all__ = ["LogViewer"]

# 2workbench/presentation/ops/deploy/__init__.py
"""部署管理"""
from presentation.ops.deploy.deploy_manager import DeployManager
__all__ = ["DeployManager"]
```

5.5 更新 `2workbench/presentation/ops/__init__.py`：

```python
# 2workbench/presentation/ops/__init__.py
"""Presentation 层 — IDE 运营工具集"""
from presentation.ops.debugger import RuntimePanel, EventMonitor
from presentation.ops.evaluator import EvalWorkbench
from presentation.ops.knowledge import KnowledgeEditor
from presentation.ops.safety import SafetyPanel
from presentation.ops.multi_agent import MultiAgentOrchestrator
from presentation.ops.logger_panel import LogViewer
from presentation.ops.deploy import DeployManager

__all__ = [
    "RuntimePanel", "EventMonitor",
    "EvalWorkbench",
    "KnowledgeEditor",
    "SafetyPanel",
    "MultiAgentOrchestrator",
    "LogViewer",
    "DeployManager",
]
```

5.6 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

# 测试多 Agent 编排器
from presentation.ops.multi_agent.orchestrator import MultiAgentOrchestrator
orch = MultiAgentOrchestrator()
orch._add_agent()
orch._add_agent()
assert len(orch._agents) == 2
orch._add_link()
assert len(orch._chain) == 1
config = orch.get_config()
assert 'agents' in config
assert 'chain' in config
print('✅ 多 Agent 编排器测试通过')

# 测试日志查看器
from presentation.ops.logger_panel.log_viewer import LogViewer
log_viewer = LogViewer()
log_viewer.append_log('INFO', '系统启动', 'main')
log_viewer.append_log('ERROR', '连接失败', 'llm_client')
assert '系统启动' in log_viewer._output.toPlainText()
print('✅ 日志查看器测试通过')

# 测试部署管理器
from presentation.ops.deploy.deploy_manager import DeployManager
deploy = DeployManager()
assert deploy._deploy_status == 'idle'
deploy._start_service()
assert deploy._deploy_status == 'running'
deploy._stop_service()
assert deploy._deploy_status == 'idle'
print('✅ 部署管理器测试通过')

# 测试全部导入
from presentation.ops import (
    RuntimePanel, EventMonitor,
    EvalWorkbench,
    KnowledgeEditor,
    SafetyPanel,
    MultiAgentOrchestrator,
    LogViewer,
    DeployManager,
)
print('✅ 所有 ops 模块导入成功')

print()
print('=' * 50)
print('✅ P5 Presentation 层 IDE 运营工具集 — 全部测试通过')
print('=' * 50)
"
```

**验收**:
- [ ] MultiAgentOrchestrator（Agent 实例管理 + 链式编排）
- [ ] LogViewer（日志查看 + 级别过滤 + 自动滚动）
- [ ] DeployManager（打包配置 + 运行监控 + 启停控制）
- [ ] 所有 ops 模块可导入
- [ ] 测试通过

---

### Step 6: 集成到主窗口 + 端到端测试

**目的**: 将所有运营工具集成到主窗口的 Tools 菜单和标签页中。

**方案**:

6.1 在 `MainWindow` 中注册运营工具面板：

在 `2workbench/presentation/main_window.py` 的 `_setup_menu` 方法中，更新 Tools 菜单：

```python
# 在 MainWindow._setup_menu 中，更新 Tools 菜单

# Tools 菜单
tools_menu = menubar.addMenu("工具(&T)")

tools_menu.addAction("🔧 运行时调试器", lambda: self._show_ops_panel("debugger"))
tools_menu.addAction("📊 评估工作台", lambda: self._show_ops_panel("evaluator"))
tools_menu.addAction("📖 知识库编辑器", lambda: self._show_ops_panel("knowledge"))
tools_menu.addAction("🔒 安全护栏", lambda: self._show_ops_panel("safety"))
tools_menu.addAction("🤖 多 Agent 编排", lambda: self._show_ops_panel("multi_agent"))
tools_menu.addAction("📋 日志追踪", lambda: self._show_ops_panel("logger"))
tools_menu.addAction("🚀 部署管理", lambda: self._show_ops_panel("deploy"))
```

在 `MainWindow` 中添加 `_show_ops_panel` 方法：

```python
# 在 MainWindow 中添加

def _show_ops_panel(self, panel_type: str) -> None:
    """显示运营工具面板"""
    from presentation.ops.debugger import RuntimePanel, EventMonitor
    from presentation.ops.evaluator import EvalWorkbench
    from presentation.ops.knowledge import KnowledgeEditor
    from presentation.ops.safety import SafetyPanel
    from presentation.ops.multi_agent import MultiAgentOrchestrator
    from presentation.ops.logger_panel import LogViewer
    from presentation.ops.deploy import DeployManager

    panel_map = {
        "debugger": ("🔧 调试器", RuntimePanel),
        "evaluator": ("📊 评估", EvalWorkbench),
        "knowledge": ("📖 知识库", KnowledgeEditor),
        "safety": ("🔒 安全", SafetyPanel),
        "multi_agent": ("🤖 编排", MultiAgentOrchestrator),
        "logger": ("📋 日志", LogViewer),
        "deploy": ("🚀 部署", DeployManager),
    }

    if panel_type not in panel_map:
        return

    title, panel_class = panel_map[panel_type]

    # 检查是否已打开
    for i in range(self.center_panel.tab_widget.count()):
        if self.center_panel.tab_widget.tabText(i) == title:
            self.center_panel.tab_widget.setCurrentIndex(i)
            return

    # 创建新标签页
    panel = panel_class()
    self.center_panel.tab_widget.addTab(panel, title)
    self.center_panel.tab_widget.setCurrentIndex(
        self.center_panel.tab_widget.count() - 1
    )
```

6.2 端到端测试：

```bash
cd 2workbench ; python -c "
import sys, tempfile, shutil
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

# 1. 创建主窗口
from presentation.main_window import MainWindow
window = MainWindow()
print('✅ 主窗口创建成功')

# 2. 创建测试项目
from presentation.project.manager import project_manager
tmp_dir = tempfile.mkdtemp()

try:
    path = project_manager.create_project('ops_test', template='trpg', directory=tmp_dir)
    project_manager.open_project(path)
    print('✅ 测试项目创建并打开')

    # 3. 打开所有运营工具面板
    ops_panels = [
        ('debugger', '🔧 调试器'),
        ('evaluator', '📊 评估'),
        ('knowledge', '📖 知识库'),
        ('safety', '🔒 安全'),
        ('multi_agent', '🤖 编排'),
        ('logger', '📋 日志'),
        ('deploy', '🚀 部署'),
    ]

    for panel_type, title in ops_panels:
        window._show_ops_panel(panel_type)
        # 验证标签页已添加
        found = False
        for i in range(window.center_panel.tab_widget.count()):
            if window.center_panel.tab_widget.tabText(i) == title:
                found = True
                break
        assert found, f'面板 {title} 未找到'
        print(f'  ✅ {title} 面板已打开')

    # 4. 验证标签页数量
    tab_count = window.center_panel.tab_widget.count()
    assert tab_count >= 8  # Welcome + 7 ops panels
    print(f'✅ 标签页总数: {tab_count}')

    # 5. 测试调试器功能
    from presentation.ops.debugger.runtime_panel import RuntimePanel
    debugger_panel = None
    for i in range(window.center_panel.tab_widget.count()):
        widget = window.center_panel.tab_widget.widget(i)
        if isinstance(widget, RuntimePanel):
            debugger_panel = widget
            break
    assert debugger_panel is not None

    debugger_panel._console.append_system('测试消息')
    debugger_panel._console.append_user('玩家输入')
    debugger_panel._console.append_assistant('Agent 回复')
    assert debugger_panel._console._count == 3
    print('✅ 调试器控制台功能正常')

    # 6. 测试安全护栏过滤
    from presentation.ops.safety import SafetyPanel
    safety_panel = None
    for i in range(window.center_panel.tab_widget.count()):
        widget = window.center_panel.tab_widget.widget(i)
        if isinstance(widget, SafetyPanel):
            safety_panel = widget
            break
    if safety_panel:
        result = safety_panel.filter_text('暴力内容测试')
        assert '***' in result
        print('✅ 安全护栏过滤正常')

    # 7. 清理
    project_manager.close_project()
    print('✅ 项目关闭成功')

    print()
    print('=' * 50)
    print('✅ P5 Presentation 层 IDE 运营工具集 — 端到端测试通过')
    print('=' * 50)

finally:
    shutil.rmtree(tmp_dir)
"
```

**验收**:
- [ ] 7 个运营工具面板全部可通过 Tools 菜单打开
- [ ] 标签页不重复打开
- [ ] 调试器控制台功能正常
- [ ] 安全护栏过滤正常
- [ ] 项目生命周期完整（创建→打开→使用→关闭）
- [ ] 端到端测试通过

---

## 注意事项

### 异步操作

- LLM 调用和评估运行应使用 `qasync`，不阻塞 UI
- 评估工作台的 `_run_eval` 方法当前为同步模拟，后续应改为异步
- 部署管理的服务启动/停止应使用子进程

### 数据安全

- 安全护栏的过滤规则应存储在项目配置中
- 敏感词列表不应硬编码，支持导入/导出
- 过滤操作应在 Feature 层执行，Presentation 层仅负责配置

### 多 Agent 编排

- 当前为可视化配置面板，实际编排逻辑在 Feature 层实现
- Agent 实例配置应序列化为 JSON 存储在项目中
- 链式拓扑支持串行、并行和条件分支三种模式

### 日志管理

- 日志文件路径通过 `foundation.config.settings` 配置
- 日志查看器支持实时追加和文件加载两种模式
- 日志级别过滤在 UI 层实现，不影响实际日志记录

---

## 完成检查清单

- [ ] Step 1: 运行时调试器（控制台 + 变量监视 + 性能指标 + 事件监视器）
- [ ] Step 2: 评估工作台（用例管理 + 批量运行 + 指标统计 + 对比分析）
- [ ] Step 3: 知识库编辑器（NPC + 地点 + 导入导出）
- [ ] Step 4: 安全护栏面板（过滤规则 + 安全级别 + 预览测试）
- [ ] Step 5: 多 Agent 编排 + 日志追踪 + 部署管理
- [ ] Step 6: 集成到主窗口 + 端到端测试
