"""道具数据访问层"""
import json
from .core.services.database import get_db
from .core.utils.logger import get_logger

logger = get_logger(__name__)


def create_item(name: str, item_type: str = "misc", rarity: str = "common",
                stats: dict | None = None, description: str = "",
                level_req: int = 1, stackable: bool = False, usable: bool = False,
                slot: str | None = None, db_path: str | None = None) -> int:
    """创建道具模板"""
    stats_json = json.dumps(stats or {}, ensure_ascii=False)
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO items (name, item_type, rarity, slot, stats, description, level_req, stackable, usable)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, item_type, rarity, slot, stats_json, description, level_req, int(stackable), int(usable)),
        )
        item_id = cursor.lastrowid
        logger.info(f"创建道具: {name} (id={item_id}, rarity={rarity})")
        return item_id


def get_item(item_id: int, db_path: str | None = None) -> dict | None:
    """获取道具信息"""
    with get_db(db_path) as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if row:
        result = dict(row)
        result["stats"] = json.loads(result["stats"])
        return result
    return None


def search_items(name_pattern: str, db_path: str | None = None) -> list[dict]:
    """按名称模糊搜索道具"""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM items WHERE name LIKE ?", (f"%{name_pattern}%",)
        ).fetchall()
    return [{**dict(r), "stats": json.loads(r["stats"])} for r in rows]


def update_item(item_id: int, db_path: str | None = None, **kwargs) -> bool:
    """更新道具信息"""
    if "stats" in kwargs and isinstance(kwargs["stats"], dict):
        kwargs["stats"] = json.dumps(kwargs["stats"], ensure_ascii=False)
    if not kwargs:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [item_id]
    with get_db(db_path) as conn:
        conn.execute(f"UPDATE items SET {set_clause} WHERE id = ?", values)
    return True
