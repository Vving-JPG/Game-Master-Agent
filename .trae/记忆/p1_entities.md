# P1-01: Entities 数据模型

> 模块: `core.models.entities`
> 文件: `2workbench/core/models/entities.py`

---

## 枚举类型

```python
WorldType: fantasy | sci_fi | modern | historical | custom
ItemType: weapon | armor | consumable | material | quest | misc
ItemRarity: common | uncommon | rare | epic | legendary
QuestStatus: active | completed | failed | not_started
QuestType: main | side | daily | hidden
EventType: player_action | combat_start | quest_update | ...
MemoryCategory: npc | location | player | quest | world | session
PersonalityTrait: openness | conscientiousness | extraversion | agreeableness | neuroticism
```

---

## 核心实体

### World 世界

```python
class World(BaseModel):
    id: int | None = None
    name: str
    setting: WorldType = WorldType.fantasy
    description: str = ""
    created_at: datetime | None = None
```

### Location 地点

```python
class Location(BaseModel):
    id: int | None = None
    world_id: int
    name: str
    description: str = ""
    connections: dict[str, int]  # 方向 -> location_id
    tags: list[str] = []
```

### Player 玩家

```python
class Player(BaseModel):
    id: int | None = None
    world_id: int
    name: str = "冒险者"
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    level: int = 1
    exp: int = 0
    gold: int = 0
    stats: PlayerStats  # 力量/敏捷/智力等
```

### NPC

```python
class NPC(BaseModel):
    id: int | None = None
    world_id: int
    location_id: int | None = None
    name: str
    description: str = ""
    personality: Personality  # 五大人格
    mood: str = "neutral"
    goals: list[str] = []
    relationships: dict[str, int]  # npc_id -> 好感度
```

### Item 物品

```python
class Item(BaseModel):
    id: int | None = None
    name: str
    description: str = ""
    item_type: ItemType
    rarity: ItemRarity = ItemRarity.common
    stats: ItemStats  # 攻击力/防御力等
    effects: list[dict] = []  # 使用效果
```

### Quest 任务

```python
class Quest(BaseModel):
    id: int | None = None
    world_id: int
    player_id: int | None = None
    name: str
    description: str = ""
    quest_type: QuestType = QuestType.side
    status: QuestStatus = QuestStatus.not_started
    objectives: list[dict] = []
    rewards: dict = {}  # exp/gold/items
```

### Memory 统一记忆

```python
class Memory(BaseModel):
    id: int | None = None
    world_id: int
    category: MemoryCategory
    source: str  # 来源ID
    content: str
    importance: int = 5  # 1-10
    tags: list[str] = []
    created_at: datetime | None = None
```

---

## 辅助模型

```python
class Personality(BaseModel):
    openness: int = 50
    conscientiousness: int = 50
    extraversion: int = 50
    agreeableness: int = 50
    neuroticism: int = 50

class PlayerStats(BaseModel):
    strength: int = 10
    agility: int = 10
    intelligence: int = 10
    vitality: int = 10

class ItemStats(BaseModel):
    attack: int = 0
    defense: int = 0
    magic_power: int = 0
```
