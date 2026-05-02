# P1: Core 层 — 纯数据 + 纯规则 + 数据统一

> 创建时间: 2026-05-01
> 状态: ✅ 已完成
> 依赖: P0 Foundation 层

---

## 概述

Core 层是四层架构的第二层，负责：
- **纯数据定义** — Pydantic BaseModel 实体类
- **LangGraph State** — Agent 运行时共享状态
- **统一数据访问** — 类式 Repository + SQLite
- **纯函数计算** — 战斗、结局等无副作用逻辑
- **常量定义** — NPC 模板、剧情模板

---

## 文件结构

```
2workbench/core/
├── __init__.py                 # 统一导出接口
├── state.py                    # LangGraph State 定义
├── models/
│   ├── __init__.py
│   ├── entities.py             # Pydantic 数据模型
│   ├── repository.py           # 10个类式 Repository
│   └── schema.sql              # 15张表 Schema
├── calculators/
│   ├── __init__.py
│   ├── combat.py               # 战斗纯函数
│   └── ending.py               # 结局评分纯函数
└── constants/
    ├── __init__.py
    ├── npc_templates.py        # 6种 NPC 模板
    └── story_templates.py      # 5种剧情模板
```

---

## 数据模型 (entities.py)

### 枚举类型

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

### 核心实体

| 实体 | 关键字段 | 说明 |
|-----|---------|------|
| `World` | id, name, setting, description | 游戏世界 |
| `Location` | id, world_id, connections(dict) | 地点（含方向连接） |
| `Player` | id, world_id, hp, mp, level, exp, gold | 玩家状态 |
| `NPC` | id, world_id, personality(Personality), mood, goals, relationships | NPC |
| `Item` | id, name, item_type, rarity, stats(ItemStats) | 道具模板 |
| `PlayerItem` | id, player_id, item_id, quantity, equipped | 玩家物品栏 |
| `Quest` | id, world_id, player_id, quest_type, status, rewards | 任务 |
| `Memory` | id, world_id, category, source, content, importance, tags | 统一记忆 |
| `GameLog` | id, world_id, event_type, content | 游戏日志 |
| `PromptVersion` | id, prompt_key, content, version, is_active | Prompt 版本 |
| `LLMCallRecord` | id, world_id, tokens, latency, model | LLM 调用记录 |

---

## Repository 层 (repository.py)

### 基类

```python
class BaseRepository:
    def _json_loads(self, value: str | None, default: Any = None) -> Any
    def _json_dumps(self, value: Any) -> str
    def _row_to_dict(self, row) -> dict[str, Any]
```

### 具体 Repository

| Repository | 主要方法 |
|-----------|---------|
| `WorldRepo` | create, get_by_id, list_all, update, delete |
| `LocationRepo` | create, get_by_id, get_by_world, update, _row_to_location |
| `PlayerRepo` | create, get_by_id, get_by_world, update, get_inventory, add_item, remove_item |
| `NPCRepo` | create, get_by_id, get_by_location, get_by_world, update, _row_to_npc |
| `ItemRepo` | create, get_by_id, search, _row_to_item |
| `QuestRepo` | create, get_by_id, get_by_player, update_status, _row_to_quest |
| `MemoryRepo` | store, recall, search_by_tags, update_reference, compress, forget |
| `LogRepo` | log, get_recent |
| `PromptRepo` | save, get_active, get_history, rollback |
| `MetricsRepo` | record, get_stats |

### 使用示例

```python
from core.models import WorldRepo, PlayerRepo, MemoryRepo

# 创建世界
world_repo = WorldRepo()
world = world_repo.create(name="艾泽拉斯", setting="fantasy")

# 创建玩家
player_repo = PlayerRepo()
player = player_repo.create(world_id=world.id, name="冒险者", hp=100)

# 存储记忆
mem_repo = MemoryRepo()
mem = mem_repo.store(
    world_id=world.id,
    category="npc",
    source="npc:老村长",
    content="村长讲述了古老的传说",
    importance=0.8,
    turn=1
)

# 检索记忆
memories = mem_repo.recall(world_id=world.id, category="npc", min_importance=0.5)
```

---

## LangGraph State (state.py)

```python
class AgentState(TypedDict, total=False):
    # LangGraph 消息（带 Reducer）
    messages: Annotated[list, add_messages]
    
    # 游戏世界状态
    world_id: str
    player: dict[str, Any]
    current_location: dict[str, Any]
    active_npcs: list[dict[str, Any]]
    inventory: list[dict[str, Any]]
    active_quests: list[dict[str, Any]]
    
    # Agent 运行时状态
    turn_count: int
    execution_state: str  # idle / running / paused / step_waiting / completed / error
    
    # 工作流中间数据
    current_event: dict[str, Any]
    prompt_messages: list[dict]
    llm_response: dict[str, Any]
    parsed_commands: list[dict]
    command_results: list[dict]
    memory_updates: list[dict]
    
    # 配置
    active_skills: list[str]
    model_name: str
    provider: str
    temperature: float
    
    # 错误处理
    error: str
    retry_count: int
```

### 创建初始状态

```python
from core.state import create_initial_state

state = create_initial_state(
    world_id="1",
    player_name="冒险者",
    model_name="deepseek-chat",
    provider="deepseek"
)
```

---

## 纯函数计算器

### 战斗计算 (combat.py)

```python
from core.calculators.combat import (
    Combatant, AttackResult, CombatResult,
    roll_dice, calculate_attack_bonus, calculate_ac,
    attack, combat_round, is_combat_over, calculate_rewards
)

# 创建战斗者
player = Combatant(name="冒险者", hp=100, max_hp=100, attack_bonus=3, damage_dice="1d8", ac=15)
goblin = Combatant(name="哥布林", hp=20, max_hp=20, attack_bonus=1, damage_dice="1d6", ac=12)

# 执行攻击
result = attack(player, goblin)
# AttackResult(attacker, defender, hit, is_crit, attack_roll, damage, narrative)

# 执行一轮战斗
results = combat_round(player, [goblin])

# 检查战斗结束
if is_combat_over(player, [goblin]):
    rewards = calculate_rewards([goblin])  # {exp, gold, defeated_count}
```

### 结局评分 (ending.py)

```python
from core.calculators.ending import (
    EndingScore, calculate_ending_score, determine_ending, format_ending_narrative
)

scores = calculate_ending_score(
    main_quests_completed=5,
    side_quests_completed=4,
    total_main_quests=5,
    player_hp=80,
    npc_relationships={"村长": 0.8, "铁匠": 0.6}
)
# EndingScore(hero=xx, villain=xx, neutral=xx, tragic=xx, secret=xx)

ending = determine_ending(scores)  # "hero" | "villain" | "neutral" | "tragic" | "secret"
narrative = format_ending_narrative(ending, player_name="冒险者")
```

---

## 常量定义

### NPC 模板 (npc_templates.py)

```python
from core.constants.npc_templates import apply_template, list_templates

# 可用模板
list_templates()  # ['brave_warrior', 'mysterious_mage', 'friendly_merchant', 
                  #  'sinister_villain', 'wise_elder', 'naive_villager']

# 应用模板
npc_data = apply_template('wise_elder', overrides={'name': '老村长'})
# {
#   'name': '老村长',
#   'personality': Personality(openness=0.8, conscientiousness=0.7, ...),
#   'speech_style': '温和、睿智，喜欢讲寓言和故事',
#   'mood': 'serene',
#   'common_topics': ['历史', '智慧', '传承', '命运'],
#   'goals': ['守护知识', '引导后辈', '维护和平']
# }
```

### 剧情模板 (story_templates.py)

```python
from core.constants.story_templates import generate_quest_from_template

quest = generate_quest_from_template(
    'rescue',
    target='公主',
    enemy='恶龙',
    location='龙巢'
)
# {
#   'title': '公主 被 恶龙 抓走了，需要前往...',
#   'description': '公主 被 恶龙 抓走了，需要前往 龙巢 救出 公主。',
#   'steps': [
#       {'type': 'goto', 'description': '前往 龙巢', 'completed': False},
#       {'type': 'kill', 'description': '击败 恶龙', 'completed': False},
#       {'type': 'talk', 'description': '与 公主 对话', 'completed': False}
#   ],
#   'rewards': {'exp': 100, 'gold': 50},
#   'branches': {...}
# }
```

---

## Schema 变更

### 新增表: memories

```sql
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    category TEXT DEFAULT 'session',
    source TEXT DEFAULT '',
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    importance REAL DEFAULT 0.5,
    tags TEXT DEFAULT '[]',
    metadata TEXT DEFAULT '{}',
    turn_created INTEGER DEFAULT 0,
    turn_last_referenced INTEGER DEFAULT 0,
    reference_count INTEGER DEFAULT 0,
    compressed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

-- 记忆表索引
CREATE INDEX IF NOT EXISTS idx_memories_world ON memories(world_id);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(world_id, category);
CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(world_id, source);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(world_id, importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_turn ON memories(world_id, turn_created);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(world_id, tags);
```

### 修改表: quests

```sql
-- player_id 改为可空，外键约束改为 ON DELETE SET NULL
CREATE TABLE IF NOT EXISTS quests (
    ...
    player_id INTEGER DEFAULT NULL,  -- 原为 DEFAULT 0
    ...
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE SET NULL  -- 原为 CASCADE
);
```

---

## 依赖关系

```
Core 层只允许 import:
├── foundation.*           # Foundation 层
├── typing / dataclasses / enum / json / re / random  # 标准库
├── pydantic               # 数据验证
└── langgraph.graph.message # add_messages reducer

Core 层禁止 import:
├── feature.*              # Feature 层
├── presentation.*         # Presentation 层
├── openai / tenacity      # LLM 相关（属于 Foundation）
```

---

## 测试

```bash
cd 2workbench
python tests/test_core_integration.py
```

测试覆盖:
- 完整游戏状态流程（世界→地点→玩家→NPC→物品→任务→记忆→日志→State）
- 计算器与 State 配合（战斗模拟、结局评分）
- 模板与 Repository 配合

---

## 废弃说明

- `1agent_core/src/memory/` — Markdown 文件记忆系统已废弃
- `_legacy/core/models/*.py` — 函数式 Repository 已废弃
- 统一使用 `core.models.repository.MemoryRepo` 进行记忆管理
