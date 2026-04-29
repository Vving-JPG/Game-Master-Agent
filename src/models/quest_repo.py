"""任务数据访问层"""
import json
from src.services.database import get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_quest(world_id: int, title: str, description: str = "",
                 quest_type: str = "side", player_id: int | None = None,
                 rewards: dict | str | None = None, prerequisites: list | str | None = None,
                 branches: list | str | None = None, db_path: str | None = None) -> int:
    """创建任务"""
    if isinstance(rewards, dict):
        rewards = json.dumps(rewards, ensure_ascii=False)
    if isinstance(prerequisites, list):
        prerequisites = json.dumps(prerequisites, ensure_ascii=False)
    if isinstance(branches, list):
        branches = json.dumps(branches, ensure_ascii=False)

    with get_db(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO quests (world_id, player_id, title, description, quest_type, rewards, prerequisites, branches)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (world_id, player_id, title, description, quest_type, rewards or '{}', prerequisites or '[]', branches or '[]'),
        )
        quest_id = cursor.lastrowid
        logger.info(f"创建任务: {title} (id={quest_id})")
        return quest_id


def get_quest(quest_id: int, db_path: str | None = None) -> dict | None:
    """获取任务信息"""
    with get_db(db_path) as conn:
        row = conn.execute("SELECT * FROM quests WHERE id = ?", (quest_id,)).fetchone()
    if row:
        result = dict(row)
        result["rewards"] = json.loads(result.get("rewards") or "{}")
        result["prerequisites"] = json.loads(result.get("prerequisites") or "[]")
        result["branches"] = json.loads(result.get("branches") or "[]")
        return result
    return None


def get_quests_by_player(player_id: int | None, db_path: str | None = None) -> list[dict]:
    """获取玩家的所有任务"""
    with get_db(db_path) as conn:
        if player_id is None:
            rows = conn.execute(
                "SELECT * FROM quests ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM quests WHERE player_id = ? ORDER BY created_at DESC", (player_id,)
            ).fetchall()
    result = []
    for r in rows:
        quest = dict(r)
        quest["rewards"] = json.loads(r["rewards"])
        quest["prerequisites"] = json.loads(r["prerequisites"])
        quest["branches"] = json.loads(r["branches"])
        result.append(quest)
    return result


def get_quests_by_world(world_id: int, db_path: str | None = None) -> list[dict]:
    """获取世界的所有任务"""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM quests WHERE world_id = ? ORDER BY created_at DESC", (world_id,)
        ).fetchall()
    result = []
    for r in rows:
        quest = dict(r)
        quest["rewards"] = json.loads(r["rewards"])
        quest["prerequisites"] = json.loads(r["prerequisites"])
        quest["branches"] = json.loads(r["branches"])
        result.append(quest)
    return result


def update_quest(quest_id: int, db_path: str | None = None, **kwargs) -> bool:
    """更新任务信息"""
    # 处理JSON字段
    json_fields = ["rewards", "prerequisites", "branches"]
    for field in json_fields:
        if field in kwargs:
            if isinstance(kwargs[field], (dict, list)):
                kwargs[field] = json.dumps(kwargs[field], ensure_ascii=False)

    if not kwargs:
        return False

    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [quest_id]
    with get_db(db_path) as conn:
        conn.execute(f"UPDATE quests SET {set_clause}, updated_at = datetime('now') WHERE id = ?", values)
    return True


def update_quest_status(quest_id: int, status: str, db_path: str | None = None) -> bool:
    """更新任务状态

    Args:
        status: active / completed / failed
    """
    if status not in ("active", "completed", "failed"):
        logger.warning(f"无效的任务状态: {status}")
        return False
    return update_quest(quest_id, status=status, db_path=db_path)


def assign_quest(quest_id: int, player_id: int, db_path: str | None = None) -> bool:
    """将任务分配给玩家"""
    with get_db(db_path) as conn:
        conn.execute("UPDATE quests SET player_id = ? WHERE id = ?", (player_id, quest_id))
    return True


def create_quest_step(quest_id: int, step_order: int, description: str,
                      step_type: str = "goto", target: str = "",
                      required_count: int = 1, db_path: str | None = None) -> int:
    """创建任务步骤"""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO quest_steps (quest_id, step_order, description, step_type, target, required_count)
             VALUES (?, ?, ?, ?, ?, ?)""",
            (quest_id, step_order, description, step_type, target, required_count),
        )
        return cursor.lastrowid


def get_quest_steps(quest_id: int, db_path: str | None = None) -> list[dict]:
    """获取任务的所有步骤"""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM quest_steps WHERE quest_id = ? ORDER BY step_order",
            (quest_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def update_quest_step(step_id: int, db_path: str | None = None,
                      current_count: int | None = None, completed: int | None = None) -> bool:
    """更新任务步骤"""
    kwargs = {}
    if current_count is not None:
        kwargs["current_count"] = current_count
    if completed is not None:
        kwargs["completed"] = completed

    if not kwargs:
        return False

    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [step_id]
    with get_db(db_path) as conn:
        conn.execute(f"UPDATE quest_steps SET {set_clause} WHERE id = ?", values)
    return True
