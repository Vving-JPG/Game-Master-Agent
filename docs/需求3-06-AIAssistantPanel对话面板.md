# 06 — AIAssistantPanel 对话面板

> 目标执行者：Trae AI
> 依赖：无
> 产出：`presentation/editor/ai_assistant.py`

---

## 1. 设计说明

AIAssistantPanel 是 AI 助手的主界面，包含：

1. **消息列表**：显示对话历史（用户消息 + AI 响应），支持 Markdown 渲染
2. **输入框**：用户输入区域，支持多行文本和快捷键发送
3. **状态指示器**：显示当前 AI 状态（思考中/规划中/执行中）
4. **内嵌面板**：PlanPanel（计划面板）和 DiffViewer（变更预览）作为子组件嵌入
5. **工具栏**：新建会话、清空历史等操作

### 布局结构

```
┌─────────────────────────────────────┐
│  🤖 AI 助手                    [新会话] │  ← 顶部工具栏
├─────────────────────────────────────┤
│                                     │
│  [用户消息气泡]                      │
│                                     │
│  [AI 响应气泡 - Markdown 渲染]       │
│                                     │
│  ┌─ PlanPanel ──────────────────┐   │  ← 内嵌计划面板
│  │ 步骤 1: 读取项目信息    ✅    │   │
│  │ 步骤 2: 创建提示词      ⏳    │   │
│  │ [确认全部] [修改] [取消]      │   │
│  └───────────────────────────────┘   │
│                                     │
│  ┌─ DiffViewer ─────────────────┐   │  ← 内嵌变更预览
│  │ --- old.md                    │   │
│  │ +++ new.md                    │   │
│  │ + 新增内容                    │   │
│  │ [确认] [拒绝]                 │   │
│  └───────────────────────────────┘   │
│                                     │
├─────────────────────────────────────┤
│  [输入框...]                    [发送] │  ← 底部输入区
└─────────────────────────────────────┘
```

---

## 2. 完整实现

**文件**：`presentation/editor/ai_assistant.py`

```python
"""
AI 助手对话面板
主界面：消息列表 + 输入框 + 内嵌计划面板和变更预览
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QFrame, QSplitter,
    QSizePolicy, QToolButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor, QPalette

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger

logger = get_logger(__name__)


class MessageBubble(QFrame):
    """消息气泡组件"""

    def __init__(self, role: str, content: str, parent=None):
        super().__init__(parent)
        self.role = role
        self._setup_ui(content)

    def _setup_ui(self, content: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 角色标签
        role_label = QLabel(
            "🧑 你" if self.role == "user" else "🤖 AI 助手"
        )
        role_label.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
        role_label.setStyleSheet("color: #888; border: none;")
        layout.addWidget(role_label)

        # 内容区域
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        content_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        if self.role == "user":
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #e3f2fd;
                    border-radius: 12px;
                    margin: 4px 40px 4px 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #f5f5f5;
                    border-radius: 12px;
                    margin: 4px 8px 4px 40px;
                }
            """)

        layout.addWidget(content_label)


class TypingIndicator(QWidget):
    """AI 正在输入的动画指示器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dots = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_dots)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        self._label = QLabel("AI 正在思考")
        self._label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self._label)

    def start(self):
        self._dots = 0
        self._timer.start(500)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _update_dots(self):
        self._dots = (self._dots + 1) % 4
        self._label.setText(f"AI 正在思考{'.' * self._dots}")


class AIAssistantPanel(QWidget):
    """AI 助手对话面板"""

    # 信号（通过 EventBus 转发，不直接调用 Feature 层）
    message_sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_eventbus()

    def _setup_ui(self):
        """构建 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 顶部工具栏 ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 8, 12, 8)

        title = QLabel("🤖 AI 助手")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        toolbar.addWidget(title)

        toolbar.addStretch()

        # 新建会话按钮
        new_chat_btn = QToolButton()
        new_chat_btn.setText("🔄 新会话")
        new_chat_btn.setStyleSheet("""
            QToolButton {
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 4px 12px;
                background: white;
            }
            QToolButton:hover {
                background: #f0f0f0;
                border-color: #999;
            }
        """)
        new_chat_btn.clicked.connect(self._on_new_chat)
        toolbar.addWidget(new_chat_btn)

        main_layout.addLayout(toolbar)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        main_layout.addWidget(line)

        # ── 消息滚动区域 ──
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #fafafa;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                border-radius: 4px;
                min-height: 30px;
            }
        """)

        # 消息容器
        self._message_container = QWidget()
        self._message_layout = QVBoxLayout(self._message_container)
        self._message_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._message_layout.setSpacing(4)
        self._message_layout.setContentsMargins(8, 8, 8, 8)

        # 添加弹性空间，使消息从顶部开始
        self._message_layout.addStretch()

        self._scroll_area.setWidget(self._message_container)
        main_layout.addWidget(self._scroll_area, 1)

        # ── 内嵌面板区域（PlanPanel / DiffViewer）──
        self._panel_container = QWidget()
        self._panel_layout = QVBoxLayout(self._panel_container)
        self._panel_layout.setContentsMargins(0, 0, 0, 0)
        self._panel_layout.setSpacing(0)
        self._panel_container.hide()

        # PlanPanel 占位（07 号文档实现）
        self._plan_panel = None
        # DiffViewer 占位（08 号文档实现）
        self._diff_viewer = None

        main_layout.addWidget(self._panel_container)

        # ── 输入区域 ──
        input_container = QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background: white;
                border-top: 1px solid #e0e0e0;
            }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(12, 8, 12, 12)
        input_layout.setSpacing(8)

        # 输入框
        self._input_box = QTextEdit()
        self._input_box.setPlaceholderText("描述你想要创建或修改的内容...")
        self._input_box.setMaximumHeight(120)
        self._input_box.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                background: #f9f9f9;
            }
            QTextEdit:focus {
                border-color: #4a90d9;
                background: white;
            }
        """)
        self._input_box.installEventFilter(self)
        input_layout.addWidget(self._input_box)

        # 发送按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        hint_label = QLabel("Enter 发送，Shift+Enter 换行")
        hint_label.setStyleSheet("color: #aaa; font-size: 11px;")
        btn_layout.addWidget(hint_label)

        btn_layout.addStretch()

        self._send_btn = QPushButton("发送")
        self._send_btn.setFixedSize(80, 32)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a6aad;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self._send_btn.clicked.connect(self._on_send)
        btn_layout.addWidget(self._send_btn)

        input_layout.addLayout(btn_layout)
        main_layout.addWidget(input_container)

        # ── 输入指示器 ──
        self._typing_indicator = TypingIndicator()
        self._message_layout.insertWidget(
            self._message_layout.count() - 1,
            self._typing_indicator,
        )
        self._typing_indicator.hide()

    def _setup_eventbus(self):
        """订阅 EventBus 事件"""
        event_bus.on("ai_assistant.response", self._on_response)
        event_bus.on("ai_assistant.state_changed", self._on_state_changed)
        event_bus.on("ai_assistant.plan_ready", self._on_plan_ready)
        event_bus.on("ai_assistant.plan_cancelled", self._on_plan_cancelled)
        event_bus.on("ai_assistant.execution_finished", self._on_execution_finished)
        event_bus.on("ai_assistant.error", self._on_error)
        event_bus.on("ai_assistant.session_reset", self._on_session_reset)

    # ───────────────────────────────────────────
    # 事件处理
    # ───────────────────────────────────────────

    def _on_send(self):
        """发送消息"""
        text = self._input_box.toPlainText().strip()
        if not text:
            return

        self._input_box.clear()

        # 显示用户消息
        self._add_message("user", text)

        # 通过 EventBus 发送到 Feature 层
        event_bus.emit(Event(
            type="ai_assistant.user_message",
            data={"message": text},
            source="AIAssistantPanel",
        ))

    def _on_response(self, event: Event):
        """处理 AI 响应"""
        content = event.data.get("content", "")
        mode = event.data.get("mode", "chat")

        self._typing_indicator.stop()

        if mode == "error":
            self._add_message("assistant", f"⚠️ {content}")
        else:
            self._add_message("assistant", content)

        self._scroll_to_bottom()

    def _on_state_changed(self, event: Event):
        """处理状态变更"""
        new_state = event.data.get("new_state", "")

        if new_state in ("analyzing", "planning", "chatting"):
            self._typing_indicator.start()
            self._send_btn.setEnabled(False)
        elif new_state == "executing":
            self._typing_indicator.stop()
            self._send_btn.setEnabled(False)
        else:
            self._typing_indicator.stop()
            self._send_btn.setEnabled(True)

    def _on_plan_ready(self, event: Event):
        """计划就绪，显示 PlanPanel"""
        self._typing_indicator.stop()
        plan_data = event.data.get("plan", {})
        thinking = event.data.get("thinking", "")

        # 显示 AI 的规划思路
        if thinking:
            self._add_message("assistant", f"📋 **规划思路：**\n\n{thinking}")

        # 显示 PlanPanel
        self._show_plan_panel(plan_data)

    def _on_plan_cancelled(self, event: Event):
        """计划取消"""
        self._hide_plan_panel()
        self._add_message("assistant", "计划已取消。")

    def _on_execution_finished(self, event: Event):
        """执行完成"""
        summary = event.data.get("summary", "执行完成")
        self._add_message("assistant", summary)
        self._scroll_to_bottom()

    def _on_error(self, event: Event):
        """错误处理"""
        message = event.data.get("message", "未知错误")
        self._typing_indicator.stop()
        self._send_btn.setEnabled(True)
        self._add_message("assistant", f"❌ {message}")

    def _on_session_reset(self, event: Event):
        """会话重置"""
        self._clear_messages()
        self._hide_plan_panel()

    def _on_new_chat(self):
        """新建会话"""
        event_bus.emit(Event(
            type="ai_assistant.new_session",
            data={},
            source="AIAssistantPanel",
        ))

    # ───────────────────────────────────────────
    # UI 操作
    # ───────────────────────────────────────────

    def _add_message(self, role: str, content: str):
        """添加消息气泡"""
        bubble = MessageBubble(role, content)
        self._message_layout.insertWidget(
            self._message_layout.count() - 1,  # 在 stretch 之前插入
            bubble,
        )
        self._scroll_to_bottom()

    def _clear_messages(self):
        """清空所有消息"""
        while self._message_layout.count() > 1:  # 保留 stretch
            item = self._message_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _scroll_to_bottom(self):
        """滚动到底部"""
        QTimer.singleShot(100, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))

    def _show_plan_panel(self, plan_data: dict):
        """显示计划面板"""
        # 延迟导入，避免循环依赖
        from .plan_panel import PlanPanel

        if self._plan_panel:
            self._plan_panel.deleteLater()

        self._plan_panel = PlanPanel(plan_data)
        self._plan_panel.plan_action.connect(self._on_plan_panel_action)

        self._panel_layout.addWidget(self._plan_panel)
        self._panel_container.show()
        self._scroll_to_bottom()

    def _hide_plan_panel(self):
        """隐藏计划面板"""
        if self._plan_panel:
            self._plan_panel.deleteLater()
            self._plan_panel = None
        self._panel_container.hide()

    def _show_diff_viewer(self, diff_text: str, file_path: str, step_id: int):
        """显示变更预览"""
        from .diff_viewer import DiffViewer

        if self._diff_viewer:
            self._diff_viewer.deleteLater()

        self._diff_viewer = DiffViewer(diff_text, file_path, step_id)
        self._diff_viewer.diff_action.connect(self._on_diff_action)

        self._panel_layout.addWidget(self._diff_viewer)
        self._panel_container.show()
        self._scroll_to_bottom()

    def _hide_diff_viewer(self):
        """隐藏变更预览"""
        if self._diff_viewer:
            self._diff_viewer.deleteLater()
            self._diff_viewer = None
        if self._plan_panel:
            # PlanPanel 还在，保持显示
            pass
        else:
            self._panel_container.hide()

    def _on_plan_panel_action(self, action: str, feedback: str = ""):
        """处理计划面板的操作"""
        event_bus.emit(Event(
            type="ai_assistant.plan_action",
            data={"action": action, "feedback": feedback},
            source="AIAssistantPanel",
        ))

        if action in ("confirm", "confirm_all"):
            self._hide_plan_panel()
        elif action == "cancel":
            self._hide_plan_panel()

    def _on_diff_action(self, action: str, step_id: int):
        """处理变更预览的操作"""
        event_bus.emit(Event(
            type="ai_assistant.step_action",
            data={"action": action, "step_id": step_id},
            source="AIAssistantPanel",
        ))

        if action in ("confirm", "reject"):
            self._hide_diff_viewer()

    # ───────────────────────────────────────────
    # 事件过滤器
    # ───────────────────────────────────────────

    def eventFilter(self, obj, event):
        """拦截 Enter 键发送消息"""
        if obj == self._input_box:
            if event.type() == event.Type.KeyPress:
                if event.key() == Qt.Key.Key_Return:
                    if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                        # Shift+Enter：换行
                        return False
                    else:
                        # Enter：发送
                        self._on_send()
                        return True
        return super().eventFilter(obj, event)
```

---

## 3. 验证

创建完成后，验证以下内容：

```python
# 1. 基本实例化
from presentation.editor.ai_assistant import AIAssistantPanel

panel = AIAssistantPanel()
assert panel is not None

# 2. 消息添加
panel._add_message("user", "测试消息")
panel._add_message("assistant", "AI 回复")
assert panel._message_layout.count() >= 3  # 2 messages + stretch + typing

# 3. 清空消息
panel._clear_messages()
```

---

## 4. 注意事项

1. **Markdown 渲染**：当前实现使用 QLabel 显示纯文本。如需 Markdown 渲染，后续可替换为 `QTextBrowser` 或第三方库（如 `markdown2` + `QTextDocument`）
2. **PlanPanel / DiffViewer**：本文件通过延迟导入引用，避免循环依赖。实际实现在 07、08 号文档
3. **样式表**：使用 QSS 内联样式，与项目现有风格保持一致。如项目有全局样式表，应改用全局样式
4. **事件过滤器**：拦截 Enter 键实现发送，Shift+Enter 实现换行