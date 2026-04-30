"""项目配置模块 - 从.env文件读取配置"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，自动从.env文件加载"""

    # DeepSeek API 配置
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 数据库配置
    database_path: str = "./data/game.db"

    # 日志配置
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# 全局单例
settings = Settings()
