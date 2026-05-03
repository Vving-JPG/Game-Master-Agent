# P1-02: Repository 数据访问

> 模块: `core.models.repository`
> 文件: `2workbench/core/models/repository.py`

---

## 基类

```python
class BaseRepository:
    def _json_loads(self, value: str | None, default: Any = None) -> Any
    def _json_dumps(self, value: Any) -> str
    def _row_to_dict(self, row) -> dict[str, Any]
```

---

## Repository 列表

| Repository | 主要方法 | 对应实体 |
|-----------|---------|---------|
| `WorldRepo` | create, get_by_id, list_all, update, delete | World |
| `LocationRepo` | create, get_by_id, get_by_world, update | Location |
| `PlayerRepo` | create, get_by_id, get_by_world, update, get_inventory, add_item, remove_item | Player |
| `NPCRepo` | create, get_by_id, get_by_location, get_by_world, update | NPC |
| `ItemRepo` | create, get_by_id, search | Item |
| `QuestRepo` | create, get_by_id, get_by_player, update_status | Quest |
| `MemoryRepo` | store, recall, search_by_tags, compress, forget | Memory |
| `LogRepo` | log, get_recent | GameLog |
| `PromptRepo` | save, get_active, get_history, rollback | PromptVersion |
| `MetricsRepo` | record, get_stats | LLMCallRecord |

---

## 使用示例

```python
from core.models import WorldRepo, PlayerRepo, NPCRepo

# World
world_repo = WorldRepo()
world = world_repo.create(World(name="幻想大陆", setting=WorldType.fantasy))
worlds = world_repo.list_all()

# Player
player_repo = PlayerRepo()
player = player_repo.get_by_world(world_id=1)
player_repo.add_item(player.id, item_id=1, quantity=5)

# NPC
npc_repo = NPCRepo()
npcs = npc_repo.get_by_world(world_id=1)
npcs_in_location = npc_repo.get_by_location(location_id=5)

# Memory
from core.models import MemoryRepo
memory_repo = MemoryRepo()
memory_repo.store(
    world_id=1,
    category=MemoryCategory.npc,
    source="npc_123",
    content="玩家帮助了张三",
    importance=8,
    tags=["帮助", "张三"]
)
memories = memory_repo.recall(world_id=1, query="张三", limit=5)
```

---

## 数据库 Schema

15 张表：worlds, locations, players, npcs, items, player_items, quests, memories, logs, prompts, metrics, etc.

详见: `2workbench/core/models/schema.sql`
