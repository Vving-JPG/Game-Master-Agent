"""Prompt 管理器 — 管理项目的所有提示词

界面布局（三栏）:
├── 左侧: 提示词列表
│   ├── system.md — 系统提示词
│   ├── user_template.md — 用户消息模板
│   └── + 新建提示词
├── 中间: Markdown 编辑器 + 变量插入按钮
└── 右侧: 参数面板
    ├── temperature 滑块
    ├── max_tokens 输入
    ├── model 选择
    └── 是否启用此提示词（开关）

使用方式:
    manager = PromptEditorWidget()
    manager.load_prompts()  # 从项目加载
    manager.show()
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QLabel, QPushButton, QFormLayout, QDialog,
    QDialogButtonBox, QComboBox, QTextBrowser,
    QMenu, QSlider, QSpinBox, QCheckBox, QGroupBox,
    QMessageBox, QInputDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton
from presentation.widgets.search_bar import SearchBar
from feature.project import project_manager

logger = get_logger(__name__)


@dataclass
class PromptItem:
    """提示词项"""
    name: str
    content: str = ""
    variables: list[str] = field(default_factory=list)
    # 参数配置
    temperature: float = 0.7
    max_tokens: int = 4096
    model: str = "deepseek-chat"
    enabled: bool = True


class PromptEditorWidget(BaseWidget):
    """提示词管理器 — 管理项目的所有提示词"""

    prompt_changed = pyqtSignal(str, str)  # name, content
    prompt_test_requested = pyqtSignal(str)  # prompt_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._prompts: dict[str, PromptItem] = {}
        self._current_prompt: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置三栏布局 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧: 提示词列表
        self._setup_left_panel()
        layout.addWidget(self.left_panel, 0)

        # 中间: 编辑器
        self._setup_center_panel()
        layout.addWidget(self.center_panel, 1)

        # 右侧: 参数面板
        self._setup_right_panel()
        layout.addWidget(self.right_panel, 0)

        # 设置面板宽度
        self.left_panel.setMinimumWidth(180)
        self.left_panel.setMaximumWidth(280)
        self.right_panel.setMinimumWidth(220)
        self.right_panel.setMaximumWidth(300)

    def _setup_left_panel(self):
        """设置左侧面板 - 提示词列表"""
        self.left_panel = QGroupBox("提示词列表")
        layout = QVBoxLayout(self.left_panel)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(8)

        # 搜索框
        self._search = SearchBar("搜索提示词...")
        self._search.search_changed.connect(self._filter_prompt_list)
        layout.addWidget(self._search)

        # 提示词列表
        self._prompt_list = QListWidget()
        self._prompt_list.currentItemChanged.connect(self._on_prompt_selected)
        self._prompt_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._prompt_list.customContextMenuRequested.connect(self._on_list_context_menu)
        layout.addWidget(self._prompt_list)

        # 新建按钮
        self._btn_new = StyledButton("➕ 新建提示词", style_type="primary")
        self._btn_new.clicked.connect(self._new_prompt)
        layout.addWidget(self._btn_new)

    def _setup_center_panel(self):
        """设置中间面板 - Markdown 编辑器"""
        self.center_panel = QGroupBox("编辑器")
        layout = QVBoxLayout(self.center_panel)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(8)

        # 提示词名称
        name_layout = QHBoxLayout()
        self._name_label = QLabel("名称:")
        self._name_edit = QLineEdit()
        self._name_edit.setReadOnly(True)
        name_layout.addWidget(self._name_label)
        name_layout.addWidget(self._name_edit, 1)
        layout.addLayout(name_layout)

        # Markdown 编辑器
        self._editor = QTextEdit()
        self._editor.setPlaceholderText(
            "在此编辑 Prompt 模板...\n\n"
            "使用 {{variable}} 定义变量，例如：\n"
            "- {{world_name}} — 世界名称\n"
            "- {{player_name}} — 玩家名称\n"
            "- {{npc_name}} — NPC 名称"
        )
        self._editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._editor)

        # 变量插入按钮
        var_buttons_layout = QHBoxLayout()
        var_buttons_layout.addWidget(QLabel("插入变量:"))

        common_vars = ["world_name", "player_name", "npc_name", "location", "context"]
        for var in common_vars:
            btn = QPushButton(f"{{{{{var}}}}}")
            btn.setFlat(True)
            btn.clicked.connect(lambda checked, v=var: self._insert_variable(v))
            var_buttons_layout.addWidget(btn)

        var_buttons_layout.addStretch()
        layout.addLayout(var_buttons_layout)

        # 底部工具栏
        toolbar = QHBoxLayout()

        self._btn_save = StyledButton("💾 保存", style_type="primary")
        self._btn_save.clicked.connect(self._save_prompt)
        toolbar.addWidget(self._btn_save)

        self._btn_test = StyledButton("🧪 测试", style_type="secondary")
        self._btn_test.clicked.connect(self._test_prompt)
        toolbar.addWidget(self._btn_test)

        toolbar.addStretch()

        self._var_count_label = QLabel("变量: 0")
        toolbar.addWidget(self._var_count_label)

        layout.addLayout(toolbar)

    def _setup_right_panel(self):
        """设置右侧面板 - 参数配置"""
        self.right_panel = QGroupBox("参数配置")
        layout = QVBoxLayout(self.right_panel)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(12)

        # 启用开关
        self._enabled_check = QCheckBox("启用此提示词")
        self._enabled_check.setChecked(True)
        layout.addWidget(self._enabled_check)

        layout.addSpacing(8)

        # 模型选择
        model_label = QLabel("模型:")
        self._model_combo = QComboBox()
        self._model_combo.addItems([
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4",
            "gpt-4o",
            "gpt-3.5-turbo",
            "claude-3-opus",
            "claude-3-sonnet",
        ])
        self._model_combo.setEditable(True)
        layout.addWidget(model_label)
        layout.addWidget(self._model_combo)

        # Temperature
        temp_label = QLabel("Temperature:")
        self._temp_slider = QSlider(Qt.Orientation.Horizontal)
        self._temp_slider.setRange(0, 200)
        self._temp_slider.setValue(70)
        self._temp_value = QLabel("0.70")
        self._temp_slider.valueChanged.connect(self._on_temp_changed)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self._temp_slider)
        temp_layout.addWidget(self._temp_value)
        layout.addWidget(temp_label)
        layout.addLayout(temp_layout)

        # Max Tokens
        tokens_label = QLabel("Max Tokens:")
        self._tokens_spin = QSpinBox()
        self._tokens_spin.setRange(100, 16000)
        self._tokens_spin.setValue(4096)
        self._tokens_spin.setSingleStep(100)
        layout.addWidget(tokens_label)
        layout.addWidget(self._tokens_spin)

        layout.addStretch()

        # 变量列表
        var_group = QGroupBox("检测到的变量")
        var_layout = QVBoxLayout(var_group)
        self._var_list = QListWidget()
        var_layout.addWidget(self._var_list)
        layout.addWidget(var_group)

    def _on_temp_changed(self, value: int):
        """Temperature 滑块变化"""
        temp = value / 100.0
        self._temp_value.setText(f"{temp:.2f}")

    def _insert_variable(self, var_name: str):
        """插入变量到编辑器"""
        cursor = self._editor.textCursor()
        cursor.insertText(f"{{{{{var_name}}}}}")
        self._editor.setTextCursor(cursor)
        self._editor.setFocus()

    def _on_text_changed(self):
        """文本变化时更新变量列表"""
        self._update_variables()

    def _update_variables(self):
        """提取并显示变量"""
        content = self._editor.toPlainText()
        # 匹配 {{variable}} 格式
        variables = set(re.findall(r'\{\{(\w+)\}\}', content))
        self._var_list.clear()
        for var in sorted(variables):
            self._var_list.addItem(var)
        self._var_count_label.setText(f"变量: {len(variables)}")

    def load_prompts(self, prompts: dict[str, str] | None = None) -> None:
        """加载提示词

        Args:
            prompts: {name: content}，为 None 时从项目加载
        """
        self._prompts.clear()
        self._prompt_list.clear()

        if prompts is None:
            # 从项目加载
            if not project_manager.is_open:
                logger.warning("没有打开的项目，无法加载提示词")
                return
            prompts = {}
            for name in project_manager.list_prompts():
                prompts[name] = project_manager.load_prompt(name)

        for name, content in prompts.items():
            # 提取变量
            variables = list(set(re.findall(r'\{\{(\w+)\}\}', content)))
            self._prompts[name] = PromptItem(
                name=name,
                content=content,
                variables=variables,
            )
            self._prompt_list.addItem(f"📋 {name}")

        if self._prompt_list.count() > 0:
            self._prompt_list.setCurrentRow(0)

        logger.info(f"已加载 {len(self._prompts)} 个提示词")

    def get_prompts(self) -> dict[str, PromptItem]:
        """获取所有提示词"""
        return dict(self._prompts)

    def get_prompt(self, name: str) -> PromptItem | None:
        """获取指定提示词"""
        return self._prompts.get(name)

    def _on_prompt_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """选中提示词"""
        if current is None:
            return

        # 移除图标前缀
        name = current.text().replace("📋 ", "")
        self._current_prompt = name

        prompt_item = self._prompts.get(name)
        if prompt_item:
            self._name_edit.setText(name)
            self._editor.setPlainText(prompt_item.content)
            self._enabled_check.setChecked(prompt_item.enabled)
            self._model_combo.setEditText(prompt_item.model)
            self._temp_slider.setValue(int(prompt_item.temperature * 100))
            self._tokens_spin.setValue(prompt_item.max_tokens)
            self._update_variables()

    def _save_prompt(self) -> None:
        """保存当前提示词"""
        if not self._current_prompt:
            QMessageBox.information(self, "提示", "请先选择一个提示词")
            return

        content = self._editor.toPlainText()
        variables = list(set(re.findall(r'\{\{(\w+)\}\}', content)))

        # 更新内存中的提示词
        self._prompts[self._current_prompt] = PromptItem(
            name=self._current_prompt,
            content=content,
            variables=variables,
            temperature=self._temp_slider.value() / 100.0,
            max_tokens=self._tokens_spin.value(),
            model=self._model_combo.currentText(),
            enabled=self._enabled_check.isChecked(),
        )

        # 持久化到文件
        try:
            if project_manager.is_open:
                project_manager.save_prompt(self._current_prompt, content)
                logger.info(f"提示词已保存: {self._current_prompt}")
                self.prompt_changed.emit(self._current_prompt, content)
                QMessageBox.information(self, "成功", f"提示词 '{self._current_prompt}' 已保存")
        except Exception as e:
            logger.error(f"保存提示词失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def _test_prompt(self) -> None:
        """测试当前提示词 - 流式输出到对话框"""
        if not self._current_prompt:
            QMessageBox.information(self, "提示", "请先选择一个提示词")
            return

        content = self._editor.toPlainText()
        if not content.strip():
            QMessageBox.information(self, "提示", "提示词内容为空")
            return

        # 获取当前配置
        model = self._model_combo.currentText()
        temperature = self._temp_slider.value() / 100.0
        max_tokens = self._tokens_spin.value()

        # 显示输入对话框获取测试消息
        from PyQt6.QtWidgets import QInputDialog
        test_message, ok = QInputDialog.getText(
            self, "测试提示词", "输入测试消息:",
            text="你好，请介绍一下自己。"
        )
        if not ok or not test_message:
            return

        # 禁用测试按钮
        self._btn_test.setEnabled(False)
        self._btn_test.setText("⏳ 测试中...")

        # 先创建并显示结果对话框
        self._create_stream_dialog()

        # 在后台线程中执行流式测试
        from PyQt6.QtCore import QThread, pyqtSignal

        class StreamThread(QThread):
            token_received = pyqtSignal(str)  # token
            stream_finished = pyqtSignal(str)  # error or empty

            def __init__(self, model, temperature, max_tokens, system_prompt, user_message):
                super().__init__()
                self.model = model
                self.temperature = temperature
                self.max_tokens = max_tokens
                self.system_prompt = system_prompt
                self.user_message = user_message

            def run(self):
                try:
                    import asyncio
                    from foundation.llm.model_router import model_router
                    from foundation.llm.base import LLMMessage

                    provider = self.model.split("-")[0] if "-" in self.model else self.model
                    client, config = model_router.route(
                        provider=provider,
                        model=self.model
                    )
                    if not client:
                        self.stream_finished.emit(f"无法获取模型客户端: {self.model}")
                        return

                    messages = [
                        LLMMessage(role="system", content=self.system_prompt),
                        LLMMessage(role="user", content=self.user_message)
                    ]

                    async def _async_stream():
                        async for event in client.stream(
                            messages=messages,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        ):
                            if event.type == "token":
                                self.token_received.emit(event.content)
                            elif event.type == "error":
                                self.stream_finished.emit(event.content)
                                return
                        self.stream_finished.emit("")

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(_async_stream())
                    finally:
                        loop.close()
                except Exception as e:
                    self.stream_finished.emit(str(e))

        self._stream_thread = StreamThread(model, temperature, max_tokens, content, test_message)
        self._stream_thread.token_received.connect(self._on_stream_token)
        self._stream_thread.stream_finished.connect(self._on_stream_finished)
        self._stream_thread.start()

    def _create_stream_dialog(self):
        """创建流式输出对话框"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel

        self._stream_dialog = QDialog(self)
        self._stream_dialog.setWindowTitle("测试输出 - 流式")
        self._stream_dialog.setMinimumSize(700, 500)

        layout = QVBoxLayout(self._stream_dialog)

        # 状态标签
        self._stream_status = QLabel("🔄 正在生成...")
        layout.addWidget(self._stream_status)

        # 文本显示区
        self._stream_text = QTextEdit()
        self._stream_text.setReadOnly(True)
        self._stream_text.setPlaceholderText("等待响应...")
        layout.addWidget(self._stream_text)

        # 关闭按钮
        self._stream_close_btn = QPushButton("停止")
        self._stream_close_btn.clicked.connect(self._stop_stream)
        layout.addWidget(self._stream_close_btn)

        self._stream_dialog.show()

    def _on_stream_token(self, token: str):
        """接收流式 token - 在主线程更新UI"""
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        if hasattr(self, '_stream_text') and self._stream_text and not self._stream_text.isDestroyed():
            # 使用 invokeMethod 确保在主线程执行
            self._stream_text.insertPlainText(token)
            # 滚动到底部
            scrollbar = self._stream_text.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())

    def _on_stream_finished(self, error: str):
        """流式输出结束"""
        self._btn_test.setEnabled(True)
        self._btn_test.setText("🧪 测试")

        if error:
            if hasattr(self, '_stream_status') and self._stream_status and not self._stream_status.isDestroyed():
                self._stream_status.setText(f"❌ 错误: {error}")
            QMessageBox.critical(self, "测试失败", f"请求出错:\n{error}")
        else:
            if hasattr(self, '_stream_status') and self._stream_status and not self._stream_status.isDestroyed():
                self._stream_status.setText("✅ 完成")
            if hasattr(self, '_stream_close_btn') and self._stream_close_btn and not self._stream_close_btn.isDestroyed():
                self._stream_close_btn.setText("关闭")
                try:
                    self._stream_close_btn.clicked.disconnect()
                except:
                    pass
                self._stream_close_btn.clicked.connect(self._stream_dialog.close)

    def _stop_stream(self):
        """停止流式输出"""
        if hasattr(self, '_stream_thread') and self._stream_thread.isRunning():
            self._stream_thread.terminate()
            self._stream_thread.wait()
        self._btn_test.setEnabled(True)
        self._btn_test.setText("🧪 测试")
        if hasattr(self, '_stream_dialog'):
            self._stream_dialog.close()

    def _new_prompt(self) -> None:
        """新建提示词"""
        name, ok = QInputDialog.getText(self, "新建提示词", "提示词名称:")
        if not ok or not name:
            return

        # 检查是否已存在
        if name in self._prompts:
            QMessageBox.warning(self, "错误", f"提示词 '{name}' 已存在")
            return

        # 创建新提示词
        default_content = f"# {name}\n\n在此编写提示词模板...\n\n使用 {{{{variable}}}} 定义变量。"
        self._prompts[name] = PromptItem(
            name=name,
            content=default_content,
        )

        # 保存到文件
        if project_manager.is_open:
            project_manager.save_prompt(name, default_content)

        # 添加到列表并选中
        self._prompt_list.addItem(f"📋 {name}")
        self._prompt_list.setCurrentRow(self._prompt_list.count() - 1)

        logger.info(f"新建提示词: {name}")

    def _on_list_context_menu(self, pos) -> None:
        """右键菜单"""
        menu = QMenu()
        menu.addAction("重命名", self._rename_prompt)
        menu.addAction("删除", self._delete_prompt)
        menu.exec(self._prompt_list.mapToGlobal(pos))

    def _rename_prompt(self) -> None:
        """重命名提示词"""
        if not self._current_prompt:
            return

        new_name, ok = QInputDialog.getText(
            self, "重命名", "新名称:", text=self._current_prompt
        )
        if not ok or not new_name or new_name == self._current_prompt:
            return

        if new_name in self._prompts:
            QMessageBox.warning(self, "错误", f"提示词 '{new_name}' 已存在")
            return

        # 重命名文件
        if project_manager.is_open:
            try:
                old_path = project_manager.project_path / "prompts" / f"{self._current_prompt}.md"
                new_path = project_manager.project_path / "prompts" / f"{new_name}.md"
                if old_path.exists():
                    old_path.rename(new_path)
            except Exception as e:
                logger.error(f"重命名文件失败: {e}")

        # 更新内存
        self._prompts[new_name] = self._prompts.pop(self._current_prompt)
        self._prompts[new_name].name = new_name
        self._current_prompt = new_name

        # 更新列表
        current_item = self._prompt_list.currentItem()
        if current_item:
            current_item.setText(f"📋 {new_name}")

        self._name_edit.setText(new_name)
        logger.info(f"重命名提示词: {self._current_prompt} -> {new_name}")

    def _delete_prompt(self) -> None:
        """删除提示词"""
        if not self._current_prompt:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除提示词 '{self._current_prompt}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 删除文件
        if project_manager.is_open:
            try:
                prompt_path = project_manager.project_path / "prompts" / f"{self._current_prompt}.md"
                if prompt_path.exists():
                    prompt_path.unlink()
            except Exception as e:
                logger.error(f"删除文件失败: {e}")

        # 从列表中移除
        row = self._prompt_list.currentRow()
        self._prompt_list.takeItem(row)

        # 清理内存
        del self._prompts[self._current_prompt]
        self._current_prompt = None
        self._editor.clear()
        self._name_edit.clear()

        logger.info("提示词已删除")

    def _filter_prompt_list(self, keyword: str) -> None:
        """过滤提示词列表"""
        keyword = keyword.lower()
        for i in range(self._prompt_list.count()):
            item = self._prompt_list.item(i)
            text = item.text().lower()
            match = keyword == "" or keyword in text
            self._prompt_list.setItemHidden(item, not match)

    def get_current_prompt_config(self) -> dict[str, Any] | None:
        """获取当前提示词的完整配置"""
        if not self._current_prompt:
            return None

        prompt = self._prompts.get(self._current_prompt)
        if not prompt:
            return None

        return {
            "name": prompt.name,
            "content": prompt.content,
            "variables": prompt.variables,
            "temperature": prompt.temperature,
            "max_tokens": prompt.max_tokens,
            "model": prompt.model,
            "enabled": prompt.enabled,
        }
