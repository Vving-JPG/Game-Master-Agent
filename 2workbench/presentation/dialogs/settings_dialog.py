"""设置对话框 — 配置 API Key 和模型参数

让用户在 GUI 中配置 AI API Key，无需修改代码。
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QLabel, QTabWidget, QMessageBox,
    QWidget, QGroupBox
)
from PyQt6.QtCore import Qt

from foundation.config import settings
from foundation.logger import get_logger

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """设置 UI"""
        layout = QVBoxLayout(self)

        # 使用 Tab 切换不同设置
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # LLM 设置 Tab
        self.llm_tab = self._create_llm_tab()
        self.tabs.addTab(self.llm_tab, "🤖 AI 模型")

        # 应用设置 Tab
        self.app_tab = self._create_app_tab()
        self.tabs.addTab(self.app_tab, "⚙️ 应用")

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _create_llm_tab(self) -> QWidget:
        """创建 LLM 设置 Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 默认提供商选择
        provider_group = QGroupBox("默认 AI 提供商")
        provider_layout = QFormLayout(provider_group)

        self.default_provider = QComboBox()
        self.default_provider.addItems(["deepseek", "openai", "anthropic"])
        provider_layout.addRow("默认提供商:", self.default_provider)

        layout.addWidget(provider_group)

        # DeepSeek 设置
        deepseek_group = QGroupBox("DeepSeek 配置")
        deepseek_layout = QFormLayout(deepseek_group)

        self.deepseek_api_key = QLineEdit()
        self.deepseek_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepseek_api_key.setPlaceholderText("申请 API Key...")
        deepseek_layout.addRow("API Key:", self.deepseek_api_key)

        self.deepseek_base_url_openai = QLineEdit()
        self.deepseek_base_url_openai.setPlaceholderText("https://api.deepseek.com")
        deepseek_layout.addRow("Base URL (OpenAI):", self.deepseek_base_url_openai)

        self.deepseek_base_url_anthropic = QLineEdit()
        self.deepseek_base_url_anthropic.setPlaceholderText("https://api.deepseek.com/anthropic")
        deepseek_layout.addRow("Base URL (Anthropic):", self.deepseek_base_url_anthropic)

        self.deepseek_model = QComboBox()
        self.deepseek_model.addItems(["deepseek-v4-flash", "deepseek-v4-pro"])
        self.deepseek_model.setEditable(True)
        deepseek_layout.addRow("模型*:", self.deepseek_model)

        self.deepseek_max_tokens = QSpinBox()
        self.deepseek_max_tokens.setRange(100, 16000)
        self.deepseek_max_tokens.setSingleStep(100)
        deepseek_layout.addRow("Max Tokens:", self.deepseek_max_tokens)

        self.deepseek_temperature = QDoubleSpinBox()
        self.deepseek_temperature.setRange(0.0, 2.0)
        self.deepseek_temperature.setSingleStep(0.1)
        self.deepseek_temperature.setDecimals(1)
        deepseek_layout.addRow("Temperature:", self.deepseek_temperature)

        layout.addWidget(deepseek_group)

        # OpenAI 设置
        openai_group = QGroupBox("OpenAI 配置")
        openai_layout = QFormLayout(openai_group)

        self.openai_api_key = QLineEdit()
        self.openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key.setPlaceholderText("sk-...")
        openai_layout.addRow("API Key:", self.openai_api_key)

        self.openai_base_url = QLineEdit()
        self.openai_base_url.setPlaceholderText("https://api.openai.com/v1")
        openai_layout.addRow("Base URL:", self.openai_base_url)

        self.openai_model = QLineEdit()
        self.openai_model.setPlaceholderText("gpt-4o")
        openai_layout.addRow("模型:", self.openai_model)

        layout.addWidget(openai_group)

        # Anthropic 设置
        anthropic_group = QGroupBox("Anthropic 配置")
        anthropic_layout = QFormLayout(anthropic_group)

        self.anthropic_api_key = QLineEdit()
        self.anthropic_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_api_key.setPlaceholderText("sk-...")
        anthropic_layout.addRow("API Key:", self.anthropic_api_key)

        self.anthropic_base_url = QLineEdit()
        self.anthropic_base_url.setPlaceholderText("https://api.anthropic.com")
        anthropic_layout.addRow("Base URL:", self.anthropic_base_url)

        self.anthropic_model = QLineEdit()
        self.anthropic_model.setPlaceholderText("claude-sonnet-4-20250514")
        anthropic_layout.addRow("模型:", self.anthropic_model)

        layout.addWidget(anthropic_group)

        layout.addStretch()
        return tab

    def _create_app_tab(self) -> QWidget:
        """创建应用设置 Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 日志设置
        log_group = QGroupBox("日志设置")
        log_layout = QFormLayout(log_group)

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_layout.addRow("日志级别:", self.log_level)

        layout.addWidget(log_group)

        # 缓存设置
        cache_group = QGroupBox("缓存设置")
        cache_layout = QFormLayout(cache_group)

        self.cache_max_size = QSpinBox()
        self.cache_max_size.setRange(10, 1000)
        self.cache_max_size.setSingleStep(10)
        cache_layout.addRow("最大缓存数:", self.cache_max_size)

        self.cache_ttl = QSpinBox()
        self.cache_ttl.setRange(60, 3600)
        self.cache_ttl.setSingleStep(60)
        cache_layout.addRow("缓存 TTL (秒):", self.cache_ttl)

        layout.addWidget(cache_group)

        layout.addStretch()
        return tab

    def _load_settings(self) -> None:
        """加载设置 - 优先从当前项目 config.json 加载"""
        try:
            from presentation.project.manager import project_manager

            if project_manager.is_open:
                # 从项目加载配置
                project_config = project_manager.load_project_config()
                if project_config:
                    self._load_from_project_config(project_config)
                    return
        except Exception as e:
            logger.warning(f"从项目加载配置失败: {e}")

        # 回退到全局设置
        self._load_from_global_settings()

    def _load_from_project_config(self, config: dict) -> None:
        """从项目配置加载"""
        # LLM 设置
        self.default_provider.setCurrentText(config.get("default_provider", "deepseek"))

        # DeepSeek
        deepseek = config.get("deepseek", {})
        self.deepseek_api_key.setText(deepseek.get("api_key", ""))
        self.deepseek_base_url_openai.setText(deepseek.get("base_url_openai", "https://api.deepseek.com"))
        self.deepseek_base_url_anthropic.setText(deepseek.get("base_url_anthropic", "https://api.deepseek.com/anthropic"))
        model = deepseek.get("model", "deepseek-v4-flash")
        self.deepseek_model.setCurrentText(model) if model in ["deepseek-v4-flash", "deepseek-v4-pro"] else self.deepseek_model.setEditText(model)
        self.deepseek_max_tokens.setValue(deepseek.get("max_tokens", 4096))
        self.deepseek_temperature.setValue(deepseek.get("temperature", 0.7))

        # OpenAI
        openai = config.get("openai", {})
        self.openai_api_key.setText(openai.get("api_key", ""))
        self.openai_base_url.setText(openai.get("base_url", "https://api.openai.com/v1"))
        self.openai_model.setText(openai.get("model", "gpt-4o"))

        # Anthropic
        anthropic = config.get("anthropic", {})
        self.anthropic_api_key.setText(anthropic.get("api_key", ""))
        self.anthropic_base_url.setText(anthropic.get("base_url", "https://api.anthropic.com"))
        self.anthropic_model.setText(anthropic.get("model", "claude-sonnet-4-20250514"))

        # 应用设置
        self.log_level.setCurrentText(config.get("log_level", "INFO"))
        cache = config.get("cache", {})
        self.cache_max_size.setValue(cache.get("max_size", 1000))
        self.cache_ttl.setValue(cache.get("ttl_seconds", 300))

    def _load_from_global_settings(self) -> None:
        """从全局设置加载"""
        # LLM 设置
        self.default_provider.setCurrentText(settings.default_provider)

        # DeepSeek
        self.deepseek_api_key.setText(settings.deepseek_api_key)
        self.deepseek_base_url_openai.setText(settings.deepseek_base_url)
        self.deepseek_base_url_anthropic.setText(getattr(settings, 'deepseek_base_url_anthropic', 'https://api.deepseek.com/anthropic'))
        model = settings.deepseek_model if settings.deepseek_model else "deepseek-v4-flash"
        self.deepseek_model.setCurrentText(model) if model in ["deepseek-v4-flash", "deepseek-v4-pro"] else self.deepseek_model.setEditText(model)
        self.deepseek_max_tokens.setValue(settings.deepseek_max_tokens)
        self.deepseek_temperature.setValue(settings.deepseek_temperature)

        # OpenAI
        self.openai_api_key.setText(settings.openai_api_key)
        self.openai_base_url.setText(settings.openai_base_url)
        self.openai_model.setText(settings.openai_model)

        # Anthropic
        self.anthropic_api_key.setText(settings.anthropic_api_key)
        self.anthropic_base_url.setText(settings.anthropic_base_url)
        self.anthropic_model.setText(settings.anthropic_model)

        # 应用设置
        self.log_level.setCurrentText(settings.log_level)
        self.cache_max_size.setValue(settings.cache_max_size)
        self.cache_ttl.setValue(settings.cache_ttl_seconds)

    def _on_save(self) -> None:
        """保存设置到当前项目并热重载"""
        try:
            # 获取当前项目路径
            from presentation.project.manager import project_manager

            if not project_manager.is_open:
                QMessageBox.warning(self, "未打开项目", "请先打开或创建一个 Agent 项目")
                return

            # 保存到项目 config.json
            config_data = self._generate_project_config()
            project_manager.save_project_config(config_data)

            # 热重载：更新运行时配置
            self._reload_config(config_data)

            project_path = project_manager.project_path
            QMessageBox.information(self, "保存成功", f"设置已保存并生效:\n{project_path}")
            self.accept()

        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存设置时出错: {e}")

    def _reload_config(self, config_data: dict) -> None:
        """热重载配置到运行时"""
        try:
            from foundation.config import settings

            # 更新默认提供商
            if "default_provider" in config_data:
                settings.default_provider = config_data["default_provider"]

            # 更新 DeepSeek 配置
            deepseek = config_data.get("deepseek", {})
            if deepseek.get("api_key"):
                settings.deepseek_api_key = deepseek["api_key"]
            if deepseek.get("base_url_openai"):
                settings.deepseek_base_url = deepseek["base_url_openai"]
            if deepseek.get("base_url_anthropic"):
                settings.deepseek_base_url_anthropic = deepseek["base_url_anthropic"]
            if deepseek.get("model"):
                settings.deepseek_model = deepseek["model"]

            # 更新 OpenAI 配置
            openai = config_data.get("openai", {})
            if openai.get("api_key"):
                settings.openai_api_key = openai["api_key"]
            if openai.get("base_url"):
                settings.openai_base_url = openai["base_url"]
            if openai.get("model"):
                settings.openai_model = openai["model"]

            # 更新 Anthropic 配置
            anthropic = config_data.get("anthropic", {})
            if anthropic.get("api_key"):
                settings.anthropic_api_key = anthropic["api_key"]
            if anthropic.get("base_url"):
                settings.anthropic_base_url = anthropic["base_url"]
            if anthropic.get("model"):
                settings.anthropic_model = anthropic["model"]

            logger.info("配置已热重载")

        except Exception as e:
            logger.warning(f"热重载配置失败: {e}")

    def _generate_project_config(self) -> dict:
        """生成项目配置数据"""
        return {
            "default_provider": self.default_provider.currentText(),
            "deepseek": {
                "api_key": self.deepseek_api_key.text(),
                "base_url_openai": self.deepseek_base_url_openai.text() or "https://api.deepseek.com",
                "base_url_anthropic": self.deepseek_base_url_anthropic.text() or "https://api.deepseek.com/anthropic",
                "model": self.deepseek_model.currentText() or "deepseek-v4-flash",
                "max_tokens": self.deepseek_max_tokens.value(),
                "temperature": self.deepseek_temperature.value(),
            },
            "openai": {
                "api_key": self.openai_api_key.text(),
                "base_url": self.openai_base_url.text() or "https://api.openai.com/v1",
                "model": self.openai_model.text() or "gpt-4o",
            },
            "anthropic": {
                "api_key": self.anthropic_api_key.text(),
                "base_url": self.anthropic_base_url.text() or "https://api.anthropic.com",
                "model": self.anthropic_model.text() or "claude-sonnet-4-20250514",
            },
            "log_level": self.log_level.currentText(),
            "cache": {
                "max_size": self.cache_max_size.value(),
                "ttl_seconds": self.cache_ttl.value(),
            },
        }
