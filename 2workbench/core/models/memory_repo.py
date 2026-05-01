"""NPC记忆数据访问"""
from .core.services.database import get_db
from .core.utils.logger import get_logger

logger = get_logger(__name__)


def add_memory(npc_id: int, content: str, importance: int = 5, db_path: str | None = None) -> int:
    """添加记忆"""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO npc_memories (npc_id, content, importance) VALUES (?, ?, ?)",
            (npc_id, content, importance),
        )
        return cursor.lastrowid


def get_memories(npc_id: int, limit: int = 20, db_path: str | None = None) -> list[dict]:
    """获取NPC记忆，按重要性和时间排序"""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM npc_memories WHERE npc_id = ? ORDER BY importance DESC, created_at DESC LIMIT ?",
            (npc_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_important_memories(npc_id: int, min_importance: int = 7, limit: int = 10, db_path: str | None = None) -> list[dict]:
    """获取重要记忆"""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM npc_memories WHERE npc_id = ? AND importance >= ? ORDER BY created_at DESC LIMIT ?",
            (npc_id, min_importance, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_memory(memory_id: int, db_path: str | None = None):
    """删除记忆"""
    with get_db(db_path) as conn:
        conn.execute("DELETE FROM npc_memories WHERE id = ?", (memory_id,))


def compress_memories(npc_id: int, keep_count: int = 50, db_path: str | None = None) -> int:
    """压缩记忆：保留最重要的keep_count条，删除其余"""
    with get_db(db_path) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM npc_memories WHERE npc_id = ?", (npc_id,)
        ).fetchone()[0]
        if total <= keep_count:
            return 0
        # 删除重要性最低的
        conn.execute(
            """DELETE FROM npc_memories WHERE npc_id = ? AND id NOT IN (
                SELECT id FROM npc_memories WHERE npc_id = ?
                ORDER BY importance DESC, created_at DESC LIMIT ?
            )""",
            (npc_id, npc_id, keep_count),
        )
        return total - keep_count
