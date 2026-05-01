"""数据库连接管理模块"""
import sqlite3
import os
from contextlib import contextmanager
from .core.config import settings
from .core.utils.logger import get_logger

logger = get_logger(__name__)


def get_db_path() -> str:
    """获取数据库文件路径，确保目录存在"""
    db_dir = os.path.dirname(settings.database_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    return settings.database_path


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """获取数据库连接

    Args:
        db_path: 数据库文件路径，默认使用配置中的路径

    Returns:
        SQLite连接对象（启用外键约束）
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db(db_path: str | None = None):
    """数据库连接上下文管理器，自动关闭连接

    用法:
        with get_db() as conn:
            conn.execute("INSERT INTO ...")
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


def init_db(db_path: str | None = None) -> None:
    """初始化数据库，执行schema.sql建表

    Args:
        db_path: 数据库文件路径
    """
    path = db_path or get_db_path()
    schema_path = os.path.join(os.path.dirname(__file__), "..", "models", "schema.sql")
    schema_path = os.path.normpath(schema_path)

    logger.info(f"初始化数据库: {path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection(path)
    conn.executescript(schema_sql)
    conn.close()
    logger.info("数据库初始化完成")
