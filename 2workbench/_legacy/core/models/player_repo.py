"""玩家数据访问层"""
from .core.services.database import get_db
from .core.utils.logger import get_logger

logger = get_logger(__name__)


def create_player(world_id: int, name: str, db_path: str | None = None) -> int:
    """创建玩家"""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO players (world_id, name) VALUES (?, ?)",
            (world_id, name),
        )
        player_id = cursor.lastrowid
        logger.info(f"创建玩家: {name} (id={player_id})")
        return player_id


def get_player(player_id: int, db_path: str | None = None) -> dict | None:
    """获取玩家信息"""
    with get_db(db_path) as conn:
        row = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    return dict(row) if row else None


def update_player(player_id: int, db_path: str | None = None, **kwargs) -> bool:
    """更新玩家属性"""
    if not kwargs:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [player_id]
    with get_db(db_path) as conn:
        conn.execute(f"UPDATE players SET {set_clause}, updated_at = datetime('now') WHERE id = ?", values)
    return True


def get_inventory(player_id: int, db_path: str | None = None) -> list[dict]:
    """获取玩家物品栏"""
    with get_db(db_path) as conn:
        rows = conn.execute(
            """SELECT pi.*, i.name, i.item_type, i.rarity, i.description, i.stats
               FROM player_items pi JOIN items i ON pi.item_id = i.id
               WHERE pi.player_id = ?""",
            (player_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_item(player_id: int, item_id: int, quantity: int = 1, db_path: str | None = None) -> None:
    """添加物品到玩家背包"""
    with get_db(db_path) as conn:
        existing = conn.execute(
            "SELECT quantity FROM player_items WHERE player_id = ? AND item_id = ?",
            (player_id, item_id),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE player_items SET quantity = quantity + ? WHERE player_id = ? AND item_id = ?",
                (quantity, player_id, item_id),
            )
        else:
            conn.execute(
                "INSERT INTO player_items (player_id, item_id, quantity) VALUES (?, ?, ?)",
                (player_id, item_id, quantity),
            )
    logger.info(f"玩家{player_id}获得物品{item_id} x{quantity}")


def remove_item(player_id: int, item_id: int, quantity: int = 1, db_path: str | None = None) -> bool:
    """从玩家背包移除物品"""
    with get_db(db_path) as conn:
        existing = conn.execute(
            "SELECT quantity FROM player_items WHERE player_id = ? AND item_id = ?",
            (player_id, item_id),
        ).fetchone()
        if not existing:
            return False
        new_qty = existing["quantity"] - quantity
        if new_qty <= 0:
            conn.execute("DELETE FROM player_items WHERE player_id = ? AND item_id = ?", (player_id, item_id))
        else:
            conn.execute("UPDATE player_items SET quantity = ? WHERE player_id = ? AND item_id = ?", (new_qty, player_id, item_id))
    return True
