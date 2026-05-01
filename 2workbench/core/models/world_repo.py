"""世界数据访问层"""
from .core.services.database import get_db
from .core.utils.logger import get_logger

logger = get_logger(__name__)


def create_world(name: str, setting: str = "fantasy", db_path: str | None = None) -> int:
    """创建新世界"""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO worlds (name, setting) VALUES (?, ?)",
            (name, setting),
        )
        world_id = cursor.lastrowid
        logger.info(f"创建世界: {name} (id={world_id})")
        return world_id


def get_world(world_id: int, db_path: str | None = None) -> dict | None:
    """获取世界信息"""
    with get_db(db_path) as conn:
        row = conn.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
        return dict(row) if row else None


def list_worlds(db_path: str | None = None) -> list[dict]:
    """列出所有世界"""
    with get_db(db_path) as conn:
        rows = conn.execute("SELECT * FROM worlds ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def update_world(world_id: int, db_path: str | None = None, **kwargs) -> bool:
    """更新世界信息"""
    if not kwargs:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [world_id]
    with get_db(db_path) as conn:
        conn.execute(f"UPDATE worlds SET {set_clause}, updated_at = datetime('now') WHERE id = ?", values)
        logger.info(f"更新世界 id={world_id}: {kwargs}")
        return True


def delete_world(world_id: int, db_path: str | None = None) -> bool:
    """删除世界（级联删除关联数据）"""
    with get_db(db_path) as conn:
        conn.execute("DELETE FROM worlds WHERE id = ?", (world_id,))
        logger.info(f"删除世界 id={world_id}")
        return True
