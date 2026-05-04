# 2workbench/presentation/editor/prompt_tester.py
"""提示词测试面板 — 单段/多段提示词测试

核心功能:
- 配置区: 模型选择、temperature、max_tokens
- 对话区: 多轮对话测试
- 控制按钮: 发送、重置、保存测试用例
- 信息区: Token用量、延迟、费用

使用方式:
    tester = PromptTesterWidget()
    tester.set_system_prompt("你是游戏主持人...")
    tester.show()
"""
from __future__ import annotations

import asyncio
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QComboBox, QSlider, QLabel, QPushButton, QGroupBox,
    QSpinBox, QSplitter, QFrame, QMessageBox, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot

from foundation.llm import LLMMessage
from foundation.llm.model_router import model_router
from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.theme.manager import theme_manager

logger = get_logger(__name__)


class LLMWorker(QThread):
    """LLM 调用工作线程（避免阻塞 UI）"""

    response_ready = pyqtSignal(str, dict)  # content, metadata
    error_occurred = pyqtSignal(str)
    token_received = pyqtSignal(str)  # 流式 token

    def __init__(self, messages: list[LLMMessage], model: str, temperature: float, max_tokens: int):
        super().__init__()
        self.messages = messages
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._is_running = True

    def run(self):
        """在线程中执行 LLM 调用"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._call_llm())
            loop.close()

            if self._is_running:
                self.response_ready.emit(result["content"], result["metadata"])
        except Exception as e:
            if self._is_running:
                self.error_occurred.emit(str(e))

    async def _call_llm(self) -> dict:
        """调用 LLM"""
        client, config = model_router.route(
            content=self.messages[-1].content if self.messages else "",
            model=self.model,
        )

        full_content = ""
        total_tokens = 0
        latency_ms = 0

        import time
        start_time = time.time()

        async for event in client.stream(
            messages=self.messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        ):
            if not self._is_running:
                break

            if event.type == "token":
                full_content += event.content
                self.token_received.emit(event.content)
            elif event.type == "complete":
                total_tokens = event.total_tokens

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "content": full_content,
            "metadata": {
                "tokens": total_tokens,
                "latency_ms": latency_ms,
                "model": config.get("model", self.model),
            }
        }

    def stop(self):
        """停止工作线程"""
        self._is_running = False
        self.wait(1000)


class PromptTesterWidget(BaseWidget):
    """提示词测试面板 — 单段/多段提示词测试"""

    # 信号：测试用例被保存
    test_case_saved = pyqtSignal(str, dict)  # name, test_case_data

    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages: list[dict] = []  # 对话历史
        self._system_prompt: str = ""
        self._worker: LLMWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        """设置 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 左侧：配置区
        self._setup_config_panel()
        layout.addWidget(self.config_panel, 0)

        # 中间：对话区
        self._setup_chat_panel()
        layout.addWidget(self.chat_panel, 1)

        # 右侧：信息区
        self._setup_info_panel()
        layout.addWidget(self.info_panel, 0)

        # 设置面板宽度比例
        layout.setStretchFactor(self.config_panel, 0)
        layout.setStretchFactor(self.chat_panel, 1)
        layout.setStretchFactor(self.info_panel, 0)

    def _setup_config_panel(self):
        """设置配置面板"""
        self.config_panel = QGroupBox("配置")
        layout = QVBoxLayout(self.config_panel)
        layout.setSpacing(12)

        # 模型选择
        model_label = QLabel("模型:")
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4",
            "gpt-4o",
            "gpt-3.5-turbo",
            "claude-3-opus",
            "claude-3-sonnet",
        ])
        self.model_combo.setEditable(True)
        layout.addWidget(model_label)
        layout.addWidget(self.model_combo)

        # Temperature
        temp_label = QLabel("Temperature:")
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 200)
        self.temp_slider.setValue(70)
        self.temp_value = QLabel("0.7")
        self.temp_slider.valueChanged.connect(self._on_temp_changed)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(self.temp_value)
        layout.addWidget(temp_label)
        layout.addLayout(temp_layout)

        # Max Tokens
        tokens_label = QLabel("Max Tokens:")
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(100, 16000)
        self.tokens_spin.setValue(4096)
        self.tokens_spin.setSingleStep(100)
        layout.addWidget(tokens_label)
        layout.addWidget(self.tokens_spin)

        # 系统提示词编辑
        system_label = QLabel("系统提示词:")
        self.system_edit = QTextEdit()
        self.system_edit.setPlaceholderText("输入系统提示词...")
        self.system_edit.setMaximumHeight(200)
        layout.addWidget(system_label)
        layout.addWidget(self.system_edit)

        layout.addStretch()

    def _setup_chat_panel(self):
        """设置对话面板"""
        self.chat_panel = QGroupBox("对话测试")
        layout = QVBoxLayout(self.chat_panel)
        layout.setSpacing(12)

        # 对话显示区
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("对话将显示在这里...")
        layout.addWidget(self.chat_display)

        # 输入区
        input_layout = QHBoxLayout()

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("输入测试消息...")
        self.input_box.setMaximumHeight(80)
        self.input_box.keyPressEvent = self._on_input_key_press

        self.send_btn = QPushButton("🚀 发送")
        self.send_btn.setMinimumHeight(80)
        self.send_btn.clicked.connect(self._on_send)

        input_layout.addWidget(self.input_box, 1)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        # 控制按钮
        btn_layout = QHBoxLayout()

        self.reset_btn = QPushButton("🔄 重置对话")
        self.reset_btn.clicked.connect(self._on_reset)

        self.save_btn = QPushButton("💾 保存测试用例")
        self.save_btn.clicked.connect(self._on_save_test_case)

        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)

        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

    def _setup_info_panel(self):
        """设置信息面板"""
        self.info_panel = QGroupBox("运行信息")
        layout = QVBoxLayout(self.info_panel)
        layout.setSpacing(12)

        # Token 用量
        token_group = QGroupBox("Token 用量")
        token_layout = QVBoxLayout(token_group)
        self.token_prompt_label = QLabel("Prompt: 0")
        self.token_completion_label = QLabel("Completion: 0")
        self.token_total_label = QLabel("Total: 0")
        token_layout.addWidget(self.token_prompt_label)
        token_layout.addWidget(self.token_completion_label)
        token_layout.addWidget(self.token_total_label)
        layout.addWidget(token_group)

        # 延迟
        latency_group = QGroupBox("延迟")
        latency_layout = QVBoxLayout(latency_group)
        self.latency_label = QLabel("0 ms")
        latency_layout.addWidget(self.latency_label)
        layout.addWidget(latency_group)

        # 费用估算
        cost_group = QGroupBox("费用估算")
        cost_layout = QVBoxLayout(cost_group)
        self.cost_label = QLabel("¥0.00")
        cost_layout.addWidget(self.cost_label)
        layout.addWidget(cost_group)

        layout.addStretch()

    def _on_temp_changed(self, value: int):
        """Temperature 滑块变化"""
        temp = value / 100.0
        self.temp_value.setText(f"{temp:.2f}")

    def _on_input_key_press(self, event):
        """输入框键盘事件（Ctrl+Enter 发送）"""
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._on_send()
        else:
            QTextEdit.keyPressEvent(self.input_box, event)

    def _on_send(self):
        """发送消息"""
        user_input = self.input_box.toPlainText().strip()
        if not user_input:
            return

        # 添加到对话历史
        self._messages.append({"role": "user", "content": user_input})
        self._update_chat_display()
        self.input_box.clear()

        # 准备 LLM 消息
        llm_messages = []

        # 系统提示词
        system_prompt = self.system_edit.toPlainText().strip()
        if system_prompt:
            llm_messages.append(LLMMessage(role="system", content=system_prompt))

        # 对话历史
        for msg in self._messages:
            llm_messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        # 禁用发送按钮，启用停止按钮
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 启动工作线程
        model = self.model_combo.currentText()
        temperature = self.temp_slider.value() / 100.0
        max_tokens = self.tokens_spin.value()

        self._worker = LLMWorker(llm_messages, model, temperature, max_tokens)
        self._worker.response_ready.connect(self._on_response_ready)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.token_received.connect(self._on_stream_token)
        self._worker.start()

    def _on_stream_token(self, token: str):
        """接收流式 token"""
        # 更新当前正在生成的 AI 回复
        if self._messages and self._messages[-1]["role"] == "assistant":
            self._messages[-1]["content"] += token
        else:
            self._messages.append({"role": "assistant", "content": token})
        self._update_chat_display(live=True)

    def _on_response_ready(self, content: str, metadata: dict):
        """LLM 响应完成"""
        # 确保最后一条消息是完整的 AI 回复
        if self._messages and self._messages[-1]["role"] == "assistant":
            self._messages[-1]["content"] = content
        else:
            self._messages.append({"role": "assistant", "content": content})

        self._update_chat_display()
        self._update_info(metadata)

        # 恢复按钮状态
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._worker = None

    def _on_error(self, error_msg: str):
        """处理错误"""
        self.chat_display.append(f"\n[错误] {error_msg}\n")

        # 恢复按钮状态
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._worker = None

    def _on_stop(self):
        """停止生成"""
        if self._worker:
            self._worker.stop()
            self._worker = None

        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_reset(self):
        """重置对话"""
        self._messages.clear()
        self.chat_display.clear()
        self._clear_info()

    def _on_save_test_case(self):
        """保存测试用例"""
        if not self._messages:
            QMessageBox.information(self, "提示", "没有可保存的对话")
            return

        name, ok = QLineEdit.getText(self, "保存测试用例", "测试用例名称:")
        if not ok or not name:
            return

        test_case = {
            "name": name,
            "system_prompt": self.system_edit.toPlainText(),
            "model": self.model_combo.currentText(),
            "temperature": self.temp_slider.value() / 100.0,
            "max_tokens": self.tokens_spin.value(),
            "messages": self._messages.copy(),
        }

        self.test_case_saved.emit(name, test_case)
        QMessageBox.information(self, "成功", f"测试用例 '{name}' 已保存")

    def _update_chat_display(self, live: bool = False):
        """更新对话显示"""
        if not live:
            self.chat_display.clear()

        html_parts = []
        for msg in self._messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                continue  # 不显示系统消息

            if role == "user":
                html_parts.append(f'<p><b style="color: #4a9eff;">[用户]</b> {self._escape_html(content)}</p>')
            elif role == "assistant":
                html_parts.append(f'<p><b style="color: #4caf50;">[AI]</b> {self._escape_html(content)}</p>')

        self.chat_display.setHtml("".join(html_parts))

        # 滚动到底部
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _escape_html(self, text: str) -> str:
        """转义 HTML 特殊字符"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("\n", "<br>"))

    def _update_info(self, metadata: dict):
        """更新运行信息"""
        tokens = metadata.get("tokens", 0)
        latency_ms = metadata.get("latency_ms", 0)

        # 估算 prompt/completion tokens（简化计算）
        prompt_tokens = sum(len(m["content"]) // 4 for m in self._messages if m["role"] != "assistant")
        completion_tokens = tokens - prompt_tokens if tokens > prompt_tokens else tokens // 2

        self.token_prompt_label.setText(f"Prompt: {prompt_tokens}")
        self.token_completion_label.setText(f"Completion: {completion_tokens}")
        self.token_total_label.setText(f"Total: {tokens}")

        self.latency_label.setText(f"{latency_ms} ms")

        # 估算费用（简化）
        cost = (tokens / 1000) * 0.01  # 假设 0.01元/1K tokens
        self.cost_label.setText(f"¥{cost:.4f}")

    def _clear_info(self):
        """清空信息面板"""
        self.token_prompt_label.setText("Prompt: 0")
        self.token_completion_label.setText("Completion: 0")
        self.token_total_label.setText("Total: 0")
        self.latency_label.setText("0 ms")
        self.cost_label.setText("¥0.00")

    def set_system_prompt(self, prompt: str):
        """设置系统提示词"""
        self._system_prompt = prompt
        self.system_edit.setPlainText(prompt)

    def set_model(self, model: str):
        """设置模型"""
        index = self.model_combo.findText(model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        else:
            self.model_combo.setEditText(model)

    def load_test_case(self, test_case: dict):
        """加载测试用例"""
        self._messages = test_case.get("messages", []).copy()
        self.set_system_prompt(test_case.get("system_prompt", ""))
        self.set_model(test_case.get("model", "deepseek-chat"))
        self.temp_slider.setValue(int(test_case.get("temperature", 0.7) * 100))
        self.tokens_spin.setValue(test_case.get("max_tokens", 4096))
        self._update_chat_display()
