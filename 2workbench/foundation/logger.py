"""日志系统 — 结构化日志 + 文件轮转 + 彩色控制台

使用方式:
    from foundation.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Agent 启动", extra={"world_id": "1", "turn": 5})
    logger.error("LLM 调用失败", exc_info=True)
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class ColoredFormatter(logging.Formatter):
    """彩色控制台日志格式器"""

    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """结构化日志格式器（用于文件输出）"""

    def format(self, record: logging.LogRecord) -> str:
        # 添加结构化字段
        record.struct = {
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # 附加 extra 字段
        for key in ("world_id", "turn", "player_id", "npc_id",
                     "model", "tokens", "latency_ms", "event_type"):
            if hasattr(record, key):
                record.struct[key] = getattr(record, key)
        return super().format(record)


_initialized = False


def setup_logging(level: str | None = None, log_file: str | None = None) -> None:
    """初始化日志系统

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR），默认从 settings 读取
        log_file: 日志文件路径，默认从 settings 读取
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    # 延迟导入避免循环依赖
    try:
        from foundation.config import settings
        _level = level or settings.log_level
        _log_file = log_file or settings.log_file
        _max_bytes = settings.log_max_size_mb * 1024 * 1024
        _backup_count = settings.log_backup_count
    except Exception:
        _level = level or "INFO"
        _log_file = log_file or "./data/logs/app.log"
        _max_bytes = 10 * 1024 * 1024
        _backup_count = 5

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, _level.upper(), logging.INFO))

    # 控制台处理器（彩色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_fmt = ColoredFormatter(
        fmt="%(asctime)s │ %(levelname)s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # 文件处理器（结构化 + 轮转）
    if _log_file:
        log_path = Path(_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            _log_file,
            maxBytes=_max_bytes,
            backupCount=_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = StructuredFormatter(
            fmt="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        root_logger.addHandler(file_handler)

    # 降低第三方库日志级别
    for lib in ("httpx", "httpcore", "openai", "anthropic", "urllib3"):
        logging.getLogger(lib).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取 logger 实例

    Args:
        name: 通常传入 __name__

    Returns:
        配置好的 Logger 实例
    """
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)
