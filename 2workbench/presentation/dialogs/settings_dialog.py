"""设置对话框 — 配置 API Key 和模型参数

让用户在 GUI 中配置 AI API Key，无需修改代码。
"""
from __future__ import annotations

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
        self.deepseek_api_key.setPlaceholderText("sk-...")
        deepseek_layout.addRow("API Key:", self.deepseek_api_key)

        self.deepseek_base_url = QLineEdit()
        self.deepseek_base_url.setPlaceholderText("https://api.deepseek.com")
        deepseek_layout.addRow("Base URL:", self.deepseek_base_url)

        self.deepseek_model = QLineEdit()
        self.deepseek_model.setPlaceholderText("deepseek-chat")
        deepseek_layout.addRow("模型:", self.deepseek_model)

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
        """加载当前设置"""
        # LLM 设置
        self.default_provider.setCurrentText(settings.default_provider)

        # DeepSeek
        self.deepseek_api_key.setText(settings.deepseek_api_key)
        self.deepseek_base_url.setText(settings.deepseek_base_url)
        self.deepseek_model.setText(settings.deepseek_model)
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
        """保存设置"""
        try:
            # 保存到 .env 文件
            env_content = self._generate_env_content()
            env_path = Path(".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_content)

            QMessageBox.information(self, "保存成功", f"设置已保存到 {env_path.absolute()}")
            self.accept()

        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存设置时出错: {e}")

    def _generate_env_content(self) -> str:
        """生成 .env 文件内容"""
        lines = [
            "# Game Master Agent V3 配置",
            "# 由设置对话框生成",
            "",
            "# ---- 默认提供商 ----",
            f"DEFAULT_PROVIDER={self.default_provider.currentText()}",
            "",
            "# ---- DeepSeek ----",
            f"DEEPSEEK_API_KEY={self.deepseek_api_key.text()}",
            f"DEEPSEEK_BASE_URL={self.deepseek_base_url.text() or 'https://api.deepseek.com'}",
            f"DEEPSEEK_MODEL={self.deepseek_model.text() or 'deepseek-chat'}",
            f"DEEPSEEK_MAX_TOKENS={self.deepseek_max_tokens.value()}",
            f"DEEPSEEK_TEMPERATURE={self.deepseek_temperature.value()}",
            "",
            "# ---- OpenAI ----",
            f"OPENAI_API_KEY={self.openai_api_key.text()}",
            f"OPENAI_BASE_URL={self.openai_base_url.text() or 'https://api.openai.com/v1'}",
            f"OPENAI_MODEL={self.openai_model.text() or 'gpt-4o'}",
            "",
            "# ---- Anthropic ----",
            f"ANTHROPIC_API_KEY={self.anthropic_api_key.text()}",
            f"ANTHROPIC_BASE_URL={self.anthropic_base_url.text() or 'https://api.anthropic.com'}",
            f"ANTHROPIC_MODEL={self.anthropic_model.text() or 'claude-sonnet-4-20250514'}",
            "",
            "# ---- 日志 ----",
            f"LOG_LEVEL={self.log_level.currentText()}",
            "",
            "# ---- 缓存 ----",
            f"CACHE_MAX_SIZE={self.cache_max_size.value()}",
            f"CACHE_TTL_SECONDS={self.cache_ttl.value()}",
        ]
        return "\n".join(lines)
