"""Prompt 版本管理数据访问"""
from .core.services.database import get_db
from .core.utils.logger import get_logger

logger = get_logger(__name__)


def save_prompt(prompt_key: str, content: str, db_path: str | None = None) -> int:
    """保存新版本 Prompt，自动递增版本号"""
    with get_db(db_path) as conn:
        # 获取当前最大版本号
        row = conn.execute(
            "SELECT MAX(version) as max_ver FROM prompt_versions WHERE prompt_key = ?",
            (prompt_key,),
        ).fetchone()
        next_ver = (row["max_ver"] or 0) + 1

        # 将旧版本设为非活跃
        conn.execute(
            "UPDATE prompt_versions SET is_active = 0 WHERE prompt_key = ?",
            (prompt_key,),
        )

        # 插入新版本
        cursor = conn.execute(
            "INSERT INTO prompt_versions (prompt_key, content, version, is_active) VALUES (?, ?, ?, 1)",
            (prompt_key, content, next_ver),
        )
        logger.info(f"Prompt '{prompt_key}' 更新到版本 {next_ver}")
        return cursor.lastrowid


def get_active_prompt(prompt_key: str, db_path: str | None = None) -> str | None:
    """获取当前活跃版本的 Prompt"""
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT content FROM prompt_versions WHERE prompt_key = ? AND is_active = 1 ORDER BY version DESC LIMIT 1",
            (prompt_key,),
        ).fetchone()
    return row["content"] if row else None


def get_prompt_history(prompt_key: str, limit: int = 20, db_path: str | None = None) -> list[dict]:
    """获取 Prompt 版本历史"""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM prompt_versions WHERE prompt_key = ? ORDER BY version DESC LIMIT ?",
            (prompt_key, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def rollback_prompt(prompt_key: str, version: int, db_path: str | None = None) -> bool:
    """回滚到指定版本"""
    with get_db(db_path) as conn:
        conn.execute("UPDATE prompt_versions SET is_active = 0 WHERE prompt_key = ?", (prompt_key,))
        conn.execute(
            "UPDATE prompt_versions SET is_active = 1 WHERE prompt_key = ? AND version = ?",
            (prompt_key, version),
        )
    logger.info(f"Prompt '{prompt_key}' 回滚到版本 {version}")
    return True
