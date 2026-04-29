"""地点数据访问层"""
import json
from src.services.database import get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_location(world_id: int, name: str, description: str = "",
                    connections: dict | None = None, db_path: str | None = None) -> int:
    """创建地点

    Args:
        connections: 出口连接，如 {"north": 2, "south": 3, "east": 4}
    """
    conn_json = json.dumps(connections or {}, ensure_ascii=False)
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO locations (world_id, name, description, connections) VALUES (?, ?, ?, ?)",
            (world_id, name, description, conn_json),
        )
        loc_id = cursor.lastrowid
        logger.info(f"创建地点: {name} (id={loc_id})")
        return loc_id


def get_location(location_id: int, db_path: str | None = None) -> dict | None:
    """获取地点信息"""
    with get_db(db_path) as conn:
        row = conn.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
    if row:
        result = dict(row)
        result["connections"] = json.loads(result["connections"])
        return result
    return None


def get_locations_by_world(world_id: int, db_path: str | None = None) -> list[dict]:
    """获取世界中所有地点"""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM locations WHERE world_id = ? ORDER BY id", (world_id,)
        ).fetchall()
    return [{**dict(r), "connections": json.loads(r["connections"])} for r in rows]


def update_location(location_id: int, db_path: str | None = None, **kwargs) -> bool:
    """更新地点信息"""
    if "connections" in kwargs and isinstance(kwargs["connections"], dict):
        kwargs["connections"] = json.dumps(kwargs["connections"], ensure_ascii=False)
    if not kwargs:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [location_id]
    with get_db(db_path) as conn:
        conn.execute(f"UPDATE locations SET {set_clause} WHERE id = ?", values)
    return True
