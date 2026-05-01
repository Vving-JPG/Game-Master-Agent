"""Foundation 层 — 最底层基础设施

本层包含全项目依赖的工具类、全局单例、基础接口和基类。
上层（Core/Feature/Presentation）可以依赖本层，但本层绝对不能引用上层。

模块:
    event_bus: 事件总线（同层/跨层通信）
    config: 配置管理（pydantic-settings）
    logger: 日志系统（结构化日志）
    database: 数据库连接管理（SQLite + WAL）
    llm: LLM 客户端（多模型抽象 + 路由）
    save_manager: 存档管理（版本化存档）
    cache: 通用缓存（LRU + TTL）
    resource_manager: 资源管理（文件系统操作）
    base: 基类与接口（单例、核心接口）
"""
from foundation.event_bus import EventBus, event_bus
from foundation.config import Settings, settings
from foundation.logger import get_logger, setup_logging
from foundation.database import get_db_path, get_db, init_db
from foundation.save_manager import SaveManager
from foundation.cache import LRUCache
from foundation.resource_manager import ResourceManager

__all__ = [
    "EventBus", "event_bus",
    "Settings", "settings",
    "get_logger", "setup_logging",
    "get_db_path", "get_db", "init_db",
    "SaveManager",
    "LRUCache",
    "ResourceManager",
]
