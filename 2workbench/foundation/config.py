"""配置管理 — 多模型 + 全局配置

从 .env 文件和环境变量加载配置，支持多 LLM 供应商配置。
配置变更时通过 EventBus 通知。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from foundation.logger import get_logger

logger = get_logger(__name__)


class LLMProviderConfig(BaseSettings):
    """单个 LLM 供应商配置"""
    model_config = SettingsConfigDict(env_prefix="")

    api_key: str = ""
    base_url: str = ""
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    max_retries: int = 3


class Settings(BaseSettings):
    """全局配置

    环境变量映射:
        DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
        OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
        ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL

    .env 文件格式:
        DEEPSEEK_API_KEY=sk-xxx
        DEEPSEEK_BASE_URL=https://api.deepseek.com
        DEEPSEEK_MODEL=deepseek-chat
        OPENAI_API_KEY=sk-xxx
        OPENAI_MODEL=gpt-4o
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 应用 ----
    app_name: str = "Game Master Agent"
    app_version: str = "3.0"
    debug: bool = False

    # ---- 数据库 ----
    database_path: str = "./data/default.db"
    database_wal_mode: bool = True

    # ---- 日志 ----
    log_level: str = "INFO"
    log_file: str = "./data/logs/app.log"
    log_max_size_mb: int = 10
    log_backup_count: int = 5

    # ---- LLM 供应商 ----
    # DeepSeek（默认）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_base_url_anthropic: str = "https://api.deepseek.com/anthropic"
    deepseek_model: str = "deepseek-chat"
    deepseek_max_tokens: int = 4096
    deepseek_temperature: float = 0.7

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.7

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096
    anthropic_temperature: float = 0.7

    # ---- 默认模型 ----
    default_provider: Literal["deepseek", "openai", "anthropic"] = "deepseek"

    # ---- 缓存 ----
    cache_max_size: int = 200
    cache_ttl_seconds: int = 600

    # ---- 存档 ----
    save_directory: str = "./saves"
    max_save_slots: int = 10

    # ---- HTTP 服务 ----
    http_host: str = "127.0.0.1"
    http_port: int = 18080

    # ---- UI ----
    ui_theme: str = "dark"
    ui_font_size: int = 13
    ui_language: str = "zh-CN"

    def get_provider_config(self, provider: str | None = None) -> LLMProviderConfig:
        """获取指定供应商的配置

        Args:
            provider: 供应商名称（deepseek/openai/anthropic），默认使用 default_provider

        Returns:
            LLMProviderConfig 实例
        """
        provider = provider or self.default_provider
        configs = {
            "deepseek": LLMProviderConfig(
                api_key=self.deepseek_api_key,
                base_url=self.deepseek_base_url,
                model=self.deepseek_model,
                max_tokens=self.deepseek_max_tokens,
                temperature=self.deepseek_temperature,
            ),
            "openai": LLMProviderConfig(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url,
                model=self.openai_model,
                max_tokens=self.openai_max_tokens,
                temperature=self.openai_temperature,
            ),
            "anthropic": LLMProviderConfig(
                api_key=self.anthropic_api_key,
                base_url=self.anthropic_base_url,
                model=self.anthropic_model,
                max_tokens=self.anthropic_max_tokens,
                temperature=self.anthropic_temperature,
            ),
        }
        if provider not in configs:
            raise ValueError(f"未知 LLM 供应商: {provider}，可用: {list(configs.keys())}")
        return configs[provider]

    def get_available_providers(self) -> list[str]:
        """获取已配置 API Key 的可用供应商列表"""
        providers = []
        if self.deepseek_api_key:
            providers.append("deepseek")
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic")
        return providers or [self.default_provider]

    def load_from_project_config(self, config_path: Path | str) -> None:
        """从项目 config.json 加载配置并覆盖当前配置

        Args:
            config_path: 项目 config.json 文件路径
        """
        import json
        config_file = Path(config_path)
        if not config_file.exists():
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 映射 config.json 到 Settings 字段
            # config.json 格式: {"deepseek": {"api_key": "...", ...}}
            for provider, provider_config in config.items():
                if provider == "deepseek":
                    if "api_key" in provider_config:
                        self.deepseek_api_key = provider_config["api_key"]
                    if "base_url" in provider_config:
                        self.deepseek_base_url = provider_config["base_url"]
                    if "model" in provider_config:
                        self.deepseek_model = provider_config["model"]
                elif provider == "openai":
                    if "api_key" in provider_config:
                        self.openai_api_key = provider_config["api_key"]
                    if "base_url" in provider_config:
                        self.openai_base_url = provider_config["base_url"]
                    if "model" in provider_config:
                        self.openai_model = provider_config["model"]
                elif provider == "anthropic":
                    if "api_key" in provider_config:
                        self.anthropic_api_key = provider_config["api_key"]
                    if "base_url" in provider_config:
                        self.anthropic_base_url = provider_config["base_url"]
                    if "model" in provider_config:
                        self.anthropic_model = provider_config["model"]

            logger.info(f"已从项目配置加载: {config_file}")
        except Exception as e:
            logger.warning(f"加载项目配置失败: {e}")


# 全局单例
settings = Settings()
