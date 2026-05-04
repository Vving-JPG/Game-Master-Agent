"""Repository 层 — 数据访问对象

改进点（相比 _legacy 版本）:
1. 从函数式改为类式，每个 Repo 是一个类
2. 返回 Pydantic 模型而非 SQLite Row
3. 支持事务（通过传入 db 连接）
4. JSON 字段自动序列化/反序列化
5. 统一的 CRUD 接口

使用方式:
    repo = WorldRepo()
    world = repo.create(name="艾泽拉斯", setting="fantasy")
    worlds = repo.list_all()
    world = repo.get_by_id(1)
"""
from __future__ import annotations

import json
from typing import Any, Generic, TypeVar

from foundation.database import get_db
from foundation.logger import get_logger
from core.models.entities import (
    World, Location, Player, NPC, Personality,
    Item, ItemStats, PlayerItem,
    Quest, QuestStep,
    Memory, GameLog, GameMessage,
    PromptVersion, LLMCallRecord,
)

logger = get_logger(__name__)

T = TypeVar("T")  # Pydantic 模型类型


class BaseRepository:
    """Repository 基类"""

    def _json_loads(self, value: str | None, default: Any = None) -> Any:
        """JSON 反序列化"""
        if not value:
            return default if default is not None else {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default if default is not None else {}

    def _json_dumps(self, value: Any) -> str:
        """JSON 序列化"""
        return json.dumps(value, ensure_ascii=False, default=str)

    def _row_to_dict(self, row) -> dict[str, Any]:
        """SQLite Row 转字典"""
        if row is None:
            return {}
        return dict(row)


# ========== WorldRepo ==========

class WorldRepo(BaseRepository):
    """世界仓库"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def create(self, name: str, setting: str = "fantasy", description: str = "", db_path: str | None = None) -> World:
        db_path = db_path or self._db_path
        with get_db(db_path) as db:
            cursor = db.execute(
                "INSERT INTO worlds (name, setting, description) VALUES (?, ?, ?)",
                (name, setting, description),
            )
            row = db.execute("SELECT * FROM worlds WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return World(**self._row_to_dict(row))

    def get_by_id(self, world_id: int, db_path: str | None = None) -> World | None:
        db_path = db_path or self._db_path
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
            return World(**self._row_to_dict(row)) if row else None

    def list_all(self, db_path: str | None = None) -> list[World]:
        db_path = db_path or self._db_path
        with get_db(db_path) as db:
            rows = db.execute("SELECT * FROM worlds ORDER BY created_at DESC").fetchall()
            return [World(**self._row_to_dict(r)) for r in rows]

    def update(self, world_id: int, db_path: str | None = None, **kwargs) -> World | None:
        db_path = db_path or self._db_path
        if not kwargs:
            return self.get_by_id(world_id, db_path)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [world_id]
        with get_db(db_path) as db:
            db.execute(f"UPDATE worlds SET {sets}, updated_at = datetime('now') WHERE id = ?", values)
            return self.get_by_id(world_id, db_path)

    def delete(self, world_id: int, db_path: str | None = None) -> bool:
        db_path = db_path or self._db_path
        with get_db(db_path) as db:
            cursor = db.execute("DELETE FROM worlds WHERE id = ?", (world_id,))
            return cursor.rowcount > 0


# ========== LocationRepo ==========

class LocationRepo(BaseRepository):
    """地点仓库"""

    def create(self, world_id: int, name: str, description: str = "", connections: dict | None = None, db_path: str | None = None) -> Location:
        with get_db(db_path) as db:
            cursor = db.execute(
                "INSERT INTO locations (world_id, name, description, connections) VALUES (?, ?, ?, ?)",
                (world_id, name, description, self._json_dumps(connections or {})),
            )
            row = db.execute("SELECT * FROM locations WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self._row_to_location(row)

    def get_by_id(self, location_id: int, db_path: str | None = None) -> Location | None:
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
            return self._row_to_location(row) if row else None

    def get_by_world(self, world_id: int, db_path: str | None = None) -> list[Location]:
        with get_db(db_path) as db:
            rows = db.execute("SELECT * FROM locations WHERE world_id = ?", (world_id,)).fetchall()
            return [self._row_to_location(r) for r in rows]

    def _row_to_location(self, row) -> Location:
        """将 SQLite Row 转换为 Location（处理 JSON 字段）"""
        if row is None:
            return None
        d = self._row_to_dict(row)
        d["connections"] = self._json_loads(d.get("connections"), {})
        return Location(**d)

    def update(self, location_id: int, db_path: str | None = None, **kwargs) -> Location | None:
        if "connections" in kwargs and isinstance(kwargs["connections"], dict):
            kwargs["connections"] = self._json_dumps(kwargs["connections"])
        if not kwargs:
            return self.get_by_id(location_id, db_path)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [location_id]
        with get_db(db_path) as db:
            db.execute(f"UPDATE locations SET {sets}, updated_at = datetime('now') WHERE id = ?", values)
            return self.get_by_id(location_id, db_path)

    def delete(self, location_id: int, db_path: str | None = None) -> bool:
        """删除地点"""
        with get_db(db_path) as db:
            cursor = db.execute("DELETE FROM locations WHERE id = ?", (location_id,))
            return cursor.rowcount > 0


# ========== PlayerRepo ==========

class PlayerRepo(BaseRepository):
    """玩家仓库"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def create(self, world_id: int, name: str, db_path: str | None = None, **kwargs) -> Player:
        db_path = db_path or self._db_path
        defaults = {"hp": 100, "max_hp": 100, "mp": 50, "max_mp": 50, "level": 1, "exp": 0, "gold": 0, "location_id": 0}
        defaults.update(kwargs)
        with get_db(db_path) as db:
            cols = ["world_id", "name"] + list(defaults.keys())
            vals = [world_id, name] + list(defaults.values())
            placeholders = ", ".join("?" for _ in cols)
            cursor = db.execute(f"INSERT INTO players ({', '.join(cols)}) VALUES ({placeholders})", vals)
            row = db.execute("SELECT * FROM players WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return Player(**self._row_to_dict(row))

    def get_by_id(self, player_id: int, db_path: str | None = None) -> Player | None:
        db_path = db_path or self._db_path
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
            return Player(**self._row_to_dict(row)) if row else None

    def get_by_world(self, world_id: int, db_path: str | None = None) -> Player | None:
        db_path = db_path or self._db_path
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM players WHERE world_id = ? LIMIT 1", (world_id,)).fetchone()
            return Player(**self._row_to_dict(row)) if row else None

    def update(self, player_id: int, db_path: str | None = None, **kwargs) -> Player | None:
        db_path = db_path or self._db_path
        if not kwargs:
            return self.get_by_id(player_id, db_path)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [player_id]
        with get_db(db_path) as db:
            db.execute(f"UPDATE players SET {sets}, updated_at = datetime('now') WHERE id = ?", values)
            return self.get_by_id(player_id, db_path)

    def get_inventory(self, player_id: int, db_path: str | None = None) -> list[PlayerItem]:
        db_path = db_path or self._db_path
        with get_db(db_path) as db:
            rows = db.execute(
                """SELECT pi.*, i.name as item_name, i.item_type, i.rarity, i.stats, i.description
                   FROM player_items pi
                   JOIN items i ON pi.item_id = i.id
                   WHERE pi.player_id = ?
                   ORDER BY pi.equipped DESC, i.name""",
                (player_id,),
            ).fetchall()
            return [PlayerItem(**self._row_to_dict(r)) for r in rows]

    def add_item(self, player_id: int, item_id: int, quantity: int = 1, db_path: str | None = None) -> bool:
        db_path = db_path or self._db_path
        with get_db(db_path) as db:
            # 检查是否已有
            existing = db.execute(
                "SELECT id, quantity FROM player_items WHERE player_id = ? AND item_id = ?",
                (player_id, item_id),
            ).fetchone()
            if existing:
                new_qty = existing["quantity"] + quantity
                if new_qty <= 0:
                    db.execute("DELETE FROM player_items WHERE id = ?", (existing["id"],))
                else:
                    db.execute("UPDATE player_items SET quantity = ? WHERE id = ?", (new_qty, existing["id"]))
            else:
                if quantity > 0:
                    db.execute(
                        "INSERT INTO player_items (player_id, item_id, quantity) VALUES (?, ?, ?)",
                        (player_id, item_id, quantity),
                    )
            return True

    def remove_item(self, player_id: int, item_id: int, quantity: int = 1, db_path: str | None = None) -> bool:
        return self.add_item(player_id, item_id, -quantity, db_path)


# ========== NPCRepo ==========

class NPCRepo(BaseRepository):
    """NPC 仓库"""

    def create(self, world_id: int, name: str, location_id: int = 0, db_path: str | None = None, **kwargs) -> NPC:
        defaults = {"personality": {}, "backstory": "", "mood": "neutral", "goals": [], "relationships": {}, "speech_style": ""}
        defaults.update(kwargs)
        # 序列化 JSON 字段
        for key in ("personality", "goals", "relationships"):
            if isinstance(defaults.get(key), (dict, list)):
                defaults[key] = self._json_dumps(defaults[key])
        with get_db(db_path) as db:
            cols = ["world_id", "name", "location_id"] + list(defaults.keys())
            vals = [world_id, name, location_id] + list(defaults.values())
            placeholders = ", ".join("?" for _ in cols)
            cursor = db.execute(f"INSERT INTO npcs ({', '.join(cols)}) VALUES ({placeholders})", vals)
            row = db.execute("SELECT * FROM npcs WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self._row_to_npc(row)

    def get_by_id(self, npc_id: int, db_path: str | None = None) -> NPC | None:
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM npcs WHERE id = ?", (npc_id,)).fetchone()
            return self._row_to_npc(row) if row else None

    def get_by_location(self, location_id: int, db_path: str | None = None) -> list[NPC]:
        with get_db(db_path) as db:
            rows = db.execute("SELECT * FROM npcs WHERE location_id = ?", (location_id,)).fetchall()
            return [self._row_to_npc(r) for r in rows]

    def get_by_world(self, world_id: int, db_path: str | None = None) -> list[NPC]:
        with get_db(db_path) as db:
            rows = db.execute("SELECT * FROM npcs WHERE world_id = ?", (world_id,)).fetchall()
            return [self._row_to_npc(r) for r in rows]

    def update(self, npc_id: int, db_path: str | None = None, **kwargs) -> NPC | None:
        for key in ("personality", "goals", "relationships"):
            if key in kwargs and isinstance(kwargs[key], (dict, list)):
                kwargs[key] = self._json_dumps(kwargs[key])
        if not kwargs:
            return self.get_by_id(npc_id, db_path)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [npc_id]
        with get_db(db_path) as db:
            db.execute(f"UPDATE npcs SET {sets}, updated_at = datetime('now') WHERE id = ?", values)
            return self.get_by_id(npc_id, db_path)

    def delete(self, npc_id: int, db_path: str | None = None) -> bool:
        """删除 NPC"""
        with get_db(db_path) as db:
            cursor = db.execute("DELETE FROM npcs WHERE id = ?", (npc_id,))
            return cursor.rowcount > 0

    def _row_to_npc(self, row) -> NPC:
        """将 SQLite Row 转换为 NPC（处理 JSON 字段）"""
        if row is None:
            return None
        d = self._row_to_dict(row)
        d["personality"] = Personality(**self._json_loads(d.get("personality"), {}))
        d["goals"] = self._json_loads(d.get("goals"), [])
        d["relationships"] = self._json_loads(d.get("relationships"), {})
        return NPC(**d)


# ========== ItemRepo ==========

class ItemRepo(BaseRepository):
    """道具仓库"""

    def create(self, name: str, item_type: str = "misc", db_path: str | None = None, **kwargs) -> Item:
        defaults = {"rarity": "common", "slot": "", "stats": {}, "description": "", "level_req": 1, "stackable": False, "usable": False}
        defaults.update(kwargs)
        if isinstance(defaults.get("stats"), dict):
            defaults["stats"] = self._json_dumps(defaults["stats"])
        with get_db(db_path) as db:
            cols = ["name", "item_type"] + list(defaults.keys())
            vals = [name, item_type] + list(defaults.values())
            placeholders = ", ".join("?" for _ in cols)
            cursor = db.execute(f"INSERT INTO items ({', '.join(cols)}) VALUES ({placeholders})", vals)
            row = db.execute("SELECT * FROM items WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self._row_to_item(row)

    def get_by_id(self, item_id: int, db_path: str | None = None) -> Item | None:
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            return self._row_to_item(row) if row else None

    def search(self, name: str, db_path: str | None = None) -> list[Item]:
        with get_db(db_path) as db:
            rows = db.execute("SELECT * FROM items WHERE name LIKE ?", (f"%{name}%",)).fetchall()
            return [self._row_to_item(r) for r in rows]

    def update(self, item_id: int, db_path: str | None = None, **kwargs) -> Item | None:
        """更新道具"""
        with get_db(db_path) as db:
            item = self.get_by_id(item_id, db_path)
            if not item:
                return None
            sets = []
            values = []
            for key, value in kwargs.items():
                if hasattr(item, key):
                    sets.append(f"{key} = ?")
                    values.append(value)
            if not sets:
                return item
            values.append(item_id)
            db.execute(f"UPDATE items SET {', '.join(sets)} WHERE id = ?", values)
            return self.get_by_id(item_id, db_path)

    def delete(self, item_id: int, db_path: str | None = None) -> bool:
        """删除道具"""
        with get_db(db_path) as db:
            cursor = db.execute("DELETE FROM items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    def list_all(self, db_path: str | None = None) -> list[Item]:
        """列出所有道具"""
        with get_db(db_path) as db:
            rows = db.execute("SELECT * FROM items ORDER BY id").fetchall()
            return [self._row_to_item(r) for r in rows]

    def _row_to_item(self, row) -> Item:
        if row is None:
            return None
        d = self._row_to_dict(row)
        d["stats"] = ItemStats(**self._json_loads(d.get("stats"), {}))
        return Item(**d)


# ========== QuestRepo ==========

class QuestRepo(BaseRepository):
    """任务仓库"""

    def create(self, world_id: int, title: str, db_path: str | None = None, **kwargs) -> Quest:
        defaults = {"description": "", "quest_type": "side", "status": "not_started", "rewards": {}, "prerequisites": {}, "branches": {}}
        defaults.update(kwargs)
        for key in ("rewards", "prerequisites", "branches"):
            if isinstance(defaults.get(key), dict):
                defaults[key] = self._json_dumps(defaults[key])
        with get_db(db_path) as db:
            cols = ["world_id", "title"] + list(defaults.keys())
            vals = [world_id, title] + list(defaults.values())
            placeholders = ", ".join("?" for _ in cols)
            cursor = db.execute(f"INSERT INTO quests ({', '.join(cols)}) VALUES ({placeholders})", vals)
            row = db.execute("SELECT * FROM quests WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self._row_to_quest(row)

    def get_by_id(self, quest_id: int, db_path: str | None = None) -> Quest | None:
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM quests WHERE id = ?", (quest_id,)).fetchone()
            return self._row_to_quest(row) if row else None

    def get_by_player(self, player_id: int, db_path: str | None = None) -> list[Quest]:
        with get_db(db_path) as db:
            rows = db.execute("SELECT * FROM quests WHERE player_id = ?", (player_id,)).fetchall()
            return [self._row_to_quest(r) for r in rows]

    def list_all(self, db_path: str | None = None) -> list[Quest]:
        with get_db(db_path) as db:
            rows = db.execute("SELECT * FROM quests ORDER BY created_at DESC").fetchall()
            return [self._row_to_quest(r) for r in rows]

    def update_status(self, quest_id: int, status: str, db_path: str | None = None) -> bool:
        if status not in ("active", "completed", "failed", "not_started", "abandoned"):
            return False
        with get_db(db_path) as db:
            db.execute("UPDATE quests SET status = ?, updated_at = datetime('now') WHERE id = ?", (status, quest_id))
            return True

    def delete(self, quest_id: int, db_path: str | None = None) -> bool:
        """删除任务及其步骤"""
        with get_db(db_path) as db:
            db.execute("DELETE FROM quest_steps WHERE quest_id = ?", (quest_id,))
            cursor = db.execute("DELETE FROM quests WHERE id = ?", (quest_id,))
            return cursor.rowcount > 0

    def update(self, quest_id: int, db_path: str | None = None, **kwargs) -> Quest | None:
        """通用更新任务"""
        with get_db(db_path) as db:
            quest = self.get_by_id(quest_id, db_path)
            if not quest:
                return None
            sets = []
            values = []
            for key, value in kwargs.items():
                if hasattr(quest, key):
                    sets.append(f"{key} = ?")
                    values.append(value)
            if not sets:
                return quest
            values.append(quest_id)
            db.execute(f"UPDATE quests SET {', '.join(sets)} WHERE id = ?", values)
            return self.get_by_id(quest_id, db_path)

    def _row_to_quest(self, row) -> Quest:
        if row is None:
            return None
        d = self._row_to_dict(row)
        for key in ("rewards", "prerequisites", "branches"):
            d[key] = self._json_loads(d.get(key), {})
        return Quest(**d)


# ========== MemoryRepo（统一记忆） ==========

class MemoryRepo(BaseRepository):
    """统一记忆仓库 — 替代 Markdown 文件记忆

    支持按类别、来源、重要性、标签检索。
    支持记忆压缩（保留最重要的 N 条）。
    """

    def store(
        self,
        world_id: int,
        category: str,
        source: str,
        content: str,
        title: str = "",
        importance: float = 0.5,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        turn: int = 0,
        db_path: str | None = None,
    ) -> Memory:
        """存储记忆"""
        with get_db(db_path) as db:
            cursor = db.execute(
                """INSERT INTO memories
                   (world_id, category, source, title, content, importance, tags, metadata, turn_created)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (world_id, category, source, title, content, importance,
                 self._json_dumps(tags or []), self._json_dumps(metadata or {}), turn),
            )
            row = db.execute("SELECT * FROM memories WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self._row_to_memory(row)

    def recall(
        self,
        world_id: int,
        category: str | None = None,
        source: str | None = None,
        min_importance: float = 0.0,
        limit: int = 20,
        db_path: str | None = None,
    ) -> list[Memory]:
        """检索记忆（按重要性 + 时间排序）"""
        conditions = ["world_id = ?"]
        params: list[Any] = [world_id]
        if category:
            conditions.append("category = ?")
            params.append(category)
        if source:
            conditions.append("source = ?")
            params.append(source)
        if min_importance > 0:
            conditions.append("importance >= ?")
            params.append(min_importance)

        where = " AND ".join(conditions)
        params.append(limit)

        with get_db(db_path) as db:
            rows = db.execute(
                f"""SELECT * FROM memories WHERE {where}
                    ORDER BY importance DESC, turn_created DESC
                    LIMIT ?""",
                params,
            ).fetchall()
            return [self._row_to_memory(r) for r in rows]

    def search_by_tags(
        self, world_id: int, tags: list[str], limit: int = 20, db_path: str | None = None,
    ) -> list[Memory]:
        """按标签搜索记忆"""
        with get_db(db_path) as db:
            conditions = " OR ".join(f"tags LIKE ?" for _ in tags)
            params = [f"%{t}%" for t in tags] + [world_id, limit]
            rows = db.execute(
                f"""SELECT * FROM memories
                    WHERE ({conditions}) AND world_id = ?
                    ORDER BY importance DESC LIMIT ?""",
                params,
            ).fetchall()
            return [self._row_to_memory(r) for r in rows]

    def update_reference(self, memory_id: int, turn: int = 0, db_path: str | None = None) -> bool:
        """更新引用计数和最后引用回合"""
        with get_db(db_path) as db:
            db.execute(
                """UPDATE memories SET
                    reference_count = reference_count + 1,
                    turn_last_referenced = ?,
                    updated_at = datetime('now')
                   WHERE id = ?""",
                (turn, memory_id),
            )
            return True

    def compress(self, world_id: int, keep_count: int = 50, db_path: str | None = None) -> int:
        """记忆压缩 — 保留最重要的 N 条，标记其余为已压缩"""
        with get_db(db_path) as db:
            # 获取总记忆数
            total = db.execute("SELECT COUNT(*) as cnt FROM memories WHERE world_id = ? AND compressed = 0", (world_id,)).fetchone()["cnt"]
            if total <= keep_count:
                return 0

            # 标记低重要性的为已压缩
            delete_count = total - keep_count
            db.execute(
                """UPDATE memories SET compressed = 1, updated_at = datetime('now')
                   WHERE id IN (
                       SELECT id FROM memories
                       WHERE world_id = ? AND compressed = 0
                       ORDER BY importance ASC, reference_count ASC
                       LIMIT ?
                   )""",
                (world_id, delete_count),
            )
            logger.info(f"记忆压缩: world_id={world_id}, 压缩 {delete_count} 条, 保留 {keep_count} 条")
            return delete_count

    def forget(self, memory_id: int, db_path: str | None = None) -> bool:
        """删除记忆"""
        with get_db(db_path) as db:
            cursor = db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def _row_to_memory(self, row) -> Memory:
        if row is None:
            return None
        d = self._row_to_dict(row)
        d["tags"] = self._json_loads(d.get("tags"), [])
        d["metadata"] = self._json_loads(d.get("metadata"), {})
        return Memory(**d)


# ========== LogRepo ==========

class LogRepo(BaseRepository):
    """日志仓库"""

    VALID_EVENT_TYPES = {"dialog", "combat", "quest", "discovery", "system", "death", "trade"}

    def log(self, world_id: int, event_type: str, content: str, db_path: str | None = None) -> int:
        if event_type not in self.VALID_EVENT_TYPES:
            event_type = "system"
        with get_db(db_path) as db:
            cursor = db.execute(
                "INSERT INTO game_logs (world_id, event_type, content) VALUES (?, ?, ?)",
                (world_id, event_type, content),
            )
            return cursor.lastrowid

    def get_recent(self, world_id: int, limit: int = 50, db_path: str | None = None) -> list[GameLog]:
        with get_db(db_path) as db:
            rows = db.execute(
                "SELECT * FROM game_logs WHERE world_id = ? ORDER BY timestamp DESC LIMIT ?",
                (world_id, limit),
            ).fetchall()
            return [GameLog(**self._row_to_dict(r)) for r in rows]


# ========== PromptRepo ==========

class PromptRepo(BaseRepository):
    """Prompt 版本仓库"""

    def save(self, prompt_key: str, content: str, description: str = "", db_path: str | None = None) -> PromptVersion:
        with get_db(db_path) as db:
            # 将旧版本设为非活跃
            db.execute(
                "UPDATE prompt_versions SET is_active = 0 WHERE prompt_key = ?",
                (prompt_key,),
            )
            # 获取下一个版本号
            row = db.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 as next_ver FROM prompt_versions WHERE prompt_key = ?",
                (prompt_key,),
            ).fetchone()
            next_ver = row["next_ver"]
            # 插入新版本
            cursor = db.execute(
                "INSERT INTO prompt_versions (prompt_key, content, version, is_active, description) VALUES (?, ?, ?, 1, ?)",
                (prompt_key, content, next_ver, description),
            )
            row = db.execute("SELECT * FROM prompt_versions WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return PromptVersion(**self._row_to_dict(row))

    def get_active(self, prompt_key: str, db_path: str | None = None) -> PromptVersion | None:
        with get_db(db_path) as db:
            row = db.execute(
                "SELECT * FROM prompt_versions WHERE prompt_key = ? AND is_active = 1 ORDER BY version DESC LIMIT 1",
                (prompt_key,),
            ).fetchone()
            return PromptVersion(**self._row_to_dict(row)) if row else None

    def get_history(self, prompt_key: str, db_path: str | None = None) -> list[PromptVersion]:
        with get_db(db_path) as db:
            rows = db.execute(
                "SELECT * FROM prompt_versions WHERE prompt_key = ? ORDER BY version DESC",
                (prompt_key,),
            ).fetchall()
            return [PromptVersion(**self._row_to_dict(r)) for r in rows]

    def rollback(self, prompt_key: str, version: int, db_path: str | None = None) -> bool:
        with get_db(db_path) as db:
            db.execute("UPDATE prompt_versions SET is_active = 0 WHERE prompt_key = ?", (prompt_key,))
            db.execute(
                "UPDATE prompt_versions SET is_active = 1 WHERE prompt_key = ? AND version = ?",
                (prompt_key, version),
            )
            return True


# ========== MetricsRepo ==========

class MetricsRepo(BaseRepository):
    """LLM 指标仓库"""

    def record(self, world_id: int, call_type: str, prompt_tokens: int, completion_tokens: int,
               latency_ms: int, model: str = "", tool_calls_count: int = 0,
               tool_names: list[str] | None = None, error: str = "", db_path: str | None = None) -> int:
        with get_db(db_path) as db:
            cursor = db.execute(
                """INSERT INTO llm_calls
                   (world_id, call_type, prompt_tokens, completion_tokens, total_tokens,
                    latency_ms, model, tool_calls_count, tool_names, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (world_id, call_type, prompt_tokens, completion_tokens,
                 prompt_tokens + completion_tokens, latency_ms, model,
                 tool_calls_count, self._json_dumps(tool_names or []), error),
            )
            return cursor.lastrowid

    def get_stats(self, world_id: int = 0, db_path: str | None = None) -> dict[str, Any]:
        with get_db(db_path) as db:
            if world_id:
                row = db.execute(
                    """SELECT COUNT(*) as total_calls,
                              COALESCE(SUM(total_tokens), 0) as total_tokens,
                              COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                              COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                              COALESCE(AVG(latency_ms), 0) as avg_latency,
                              SUM(CASE WHEN error != '' THEN 1 ELSE 0 END) as error_count
                       FROM llm_calls WHERE world_id = ?""",
                    (world_id,),
                ).fetchone()
            else:
                row = db.execute(
                    """SELECT COUNT(*) as total_calls,
                              COALESCE(SUM(total_tokens), 0) as total_tokens,
                              COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                              COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                              COALESCE(AVG(latency_ms), 0) as avg_latency,
                              SUM(CASE WHEN error != '' THEN 1 ELSE 0 END) as error_count
                       FROM llm_calls"""
                ).fetchone()
            return dict(row)
