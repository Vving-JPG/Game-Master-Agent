"""NPC数据访问层"""
import json
from .core.services.database import get_db
from .core.utils.logger import get_logger

logger = get_logger(__name__)


def create_npc(world_id: int, name: str, location_id: int | None = None,
               personality: str | dict | None = None, backstory: str = "",
               mood: str = "neutral", goals: str | list | None = None,
               relationships: str | dict | None = None, speech_style: str = "",
               db_path: str | None = None) -> int:
    """创建NPC

    Args:
        world_id: 世界ID
        name: NPC名字
        location_id: 所在地点ID
        personality: 性格JSON字符串或字典 {"openness":0.7,...}
        backstory: 背景故事
        mood: 当前心情
        goals: 目标JSON字符串或列表 [{"description":"...","priority":1}]
        relationships: 关系JSON字符串或字典 {"npc_id": value}
        speech_style: 说话风格
        db_path: 数据库路径
    """
    # 处理各种输入格式
    if isinstance(personality, dict):
        personality = json.dumps(personality, ensure_ascii=False)
    if isinstance(goals, list):
        goals = json.dumps(goals, ensure_ascii=False)
    if isinstance(relationships, dict):
        relationships = json.dumps(relationships, ensure_ascii=False)

    with get_db(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO npcs (world_id, name, location_id, personality, backstory,
                                mood, goals, relationships, speech_style)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (world_id, name, location_id, personality or '{}', backstory,
             mood, goals or '[]', relationships or '{}', speech_style),
        )
        npc_id = cursor.lastrowid
        logger.info(f"创建NPC: {name} (id={npc_id})")
        return npc_id


def get_npc(npc_id: int, db_path: str | None = None) -> dict | None:
    """获取NPC信息"""
    with get_db(db_path) as conn:
        row = conn.execute("SELECT * FROM npcs WHERE id = ?", (npc_id,)).fetchone()
    if row:
        result = dict(row)
        result["personality"] = json.loads(result["personality"])
        result["goals"] = json.loads(result["goals"])
        result["relationships"] = json.loads(result["relationships"])
        return result
    return None


def get_npcs_by_location(location_id: int, db_path: str | None = None) -> list[dict]:
    """获取地点中的所有NPC"""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM npcs WHERE location_id = ?", (location_id,)
        ).fetchall()
    result = []
    for r in rows:
        npc = dict(r)
        npc["personality"] = json.loads(r["personality"])
        npc["goals"] = json.loads(r["goals"])
        npc["relationships"] = json.loads(r["relationships"])
        result.append(npc)
    return result


def update_npc(npc_id: int, db_path: str | None = None, **kwargs) -> bool:
    """更新NPC信息"""
    # 自动序列化JSON字段
    json_fields = ["personality", "goals", "relationships"]
    for field in json_fields:
        if field in kwargs and isinstance(kwargs[field], (dict, list)):
            kwargs[field] = json.dumps(kwargs[field], ensure_ascii=False)
    if not kwargs:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [npc_id]
    with get_db(db_path) as conn:
        conn.execute(f"UPDATE npcs SET {set_clause}, updated_at = datetime('now') WHERE id = ?", values)
    return True
