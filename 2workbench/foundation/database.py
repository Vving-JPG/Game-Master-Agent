"""数据库连接管理 — SQLite + WAL + 迁移支持

设计原则:
1. 使用 SQLite WAL 模式提升并发性能
2. 使用 Row 工厂支持字典式访问
3. 支持数据库迁移（版本号管理）
4. 初始化完成后通过 EventBus 通知
5. 线程安全（每个线程独立连接）
"""
from __future__ import annotations

import contextlib
import sqlite3
import threading
from pathlib import Path
from typing import Any, Generator

from foundation.logger import get_logger

logger = get_logger(__name__)

# 线程本地存储（每个线程独立连接）
_thread_local = threading.local()

# 当前数据库 schema 版本
SCHEMA_VERSION = 2


def get_db_path() -> Path:
    """获取数据库文件路径"""
    try:
        from foundation.config import settings
        return Path(settings.database_path)
    except Exception:
        return Path("./data/game.db")


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """创建新的数据库连接

    Args:
        db_path: 数据库文件路径，默认从 settings 读取

    Returns:
        配置好的 SQLite 连接
    """
    if db_path is None:
        db_path = get_db_path()
    else:
        db_path = Path(db_path)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    return conn


@contextlib.contextmanager
def get_db(db_path: str | Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """获取数据库连接的上下文管理器（自动 commit/rollback/close）

    用法:
        with get_db() as db:
            db.execute("INSERT INTO ...")
            # 自动 commit
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_thread_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """获取当前线程的持久连接（线程安全）

    每个线程复用同一个连接，避免频繁创建/关闭。
    注意: 调用方需要自行管理事务。

    Args:
        db_path: 数据库文件路径

    Returns:
        当前线程的 SQLite 连接
    """
    if not hasattr(_thread_local, "db_connection") or _thread_local.db_connection is None:
        _thread_local.db_connection = get_connection(db_path)
        logger.debug(f"新线程数据库连接: {threading.current_thread().name}")
    return _thread_local.db_connection


def close_thread_db() -> None:
    """关闭当前线程的数据库连接"""
    if hasattr(_thread_local, "db_connection") and _thread_local.db_connection is not None:
        try:
            _thread_local.db_connection.close()
        except Exception:
            pass
        _thread_local.db_connection = None


def init_db(
    schema_path: str | Path | None = None,
    db_path: str | Path | None = None,
) -> bool:
    """初始化数据库（执行 schema.sql）

    Args:
        schema_path: SQL schema 文件路径
        db_path: 数据库文件路径

    Returns:
        是否成功初始化
    """
    if schema_path is None:
        # 默认 schema 路径
        schema_path = Path(__file__).parent.parent / "core" / "models" / "schema.sql"
    else:
        schema_path = Path(schema_path)

    try:
        with get_db(db_path) as db:
            # 检查当前版本
            row = db.execute("PRAGMA user_version").fetchone()
            current_version = row[0] if row else 0

            # 检查 worlds 表是否存在（判断是否需要初始化）
            table_check = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worlds'").fetchone()
            needs_init = table_check is None or current_version < SCHEMA_VERSION

            if not needs_init:
                logger.info(f"数据库已是最新版本 (v{current_version})")
                return True

            # 执行 schema
            if schema_path.exists():
                sql = schema_path.read_text(encoding="utf-8")
                db.executescript(sql)
                logger.info(f"数据库 schema 已执行: {schema_path}")
            else:
                logger.warning(f"Schema 文件不存在: {schema_path}，跳过初始化")

            # 更新版本号
            db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

        logger.info(f"数据库初始化完成: {db_path or get_db_path()} (v{SCHEMA_VERSION})")

        # 通知其他模块
        try:
            from foundation.event_bus import event_bus, Event
            event_bus.emit(Event(
                type="foundation.db.initialized",
                data={"db_path": str(db_path or get_db_path()), "version": SCHEMA_VERSION},
                source="foundation.database",
            ))
        except Exception:
            pass

        return True

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False


def execute_query(
    sql: str,
    params: tuple | dict = (),
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    """执行查询并返回结果列表

    Args:
        sql: SQL 语句
        params: 参数
        db_path: 数据库路径

    Returns:
        查询结果列表（sqlite3.Row 对象，支持字典式访问）
    """
    with get_db(db_path) as db:
        cursor = db.execute(sql, params)
        return cursor.fetchall()


def execute_script(
    sql: str,
    db_path: str | Path | None = None,
) -> None:
    """执行多条 SQL 语句

    Args:
        sql: 多条 SQL 语句（分号分隔）
        db_path: 数据库路径
    """
    with get_db(db_path) as db:
        db.executescript(sql)
