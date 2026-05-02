# P1: Core 层 — 纯数据 + 纯规则 + 数据统一

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。
> **前置条件**: P0 Foundation 层已全部完成并通过测试。

## 项目概述

你正在帮助用户将 **Game Master Agent V2** 的 `2workbench/` 目录重构为**四层架构**。

- **技术**: Python 3.11+ / PyQt6 / SQLite / LangGraph / uv
- **包管理器**: uv
- **开发 IDE**: Trae
- **本 Phase 目标**: 实现 Core 层 — 纯数据类（Pydantic）、LangGraph State 定义、统一记忆系统（SQLite）、Repository 重构、Schema 迁移

### 架构约束

```
入口层 → Presentation (表现层) → Feature (功能层) → Core (核心层) → Foundation (基础层)
```

- ✅ Core 层**只依赖** Foundation 层
- ❌ Core 层**绝对不能** import Feature / Presentation 层
- ✅ Core 层只包含：数据类、纯函数、常量、状态定义
- ❌ Core 层禁止：节点、动画、UI、输入、LLM 调用、异步 IO

### 本 Phase (P1) 范围

1. **LangGraph State 定义** — Agent 运行时的共享状态结构
2. **Pydantic 数据模型** — 替代现有 SQLite Row 的弱类型访问
3. **统一记忆系统** — SQLite 统一存储（废弃 Markdown 文件记忆）
4. **Repository 重构** — 从函数式改为类式，增加事务支持
5. **Schema 迁移** — 14 张表保留 + 新增记忆表
6. **纯函数计算器** — 战斗计算、结局评分等纯逻辑

### 现有代码参考

| 现有文件（`_legacy/` 下） | 参考内容 | 改进方向 |
|---------|---------|---------|
| `_legacy/core/models/schema.sql` | 14 张表定义 | 保留 + 新增 memories 表 |
| `_legacy/core/models/*.py` (10 个 Repo) | 函数式 CRUD | 改为类式 + 事务 + Pydantic 模型 |
| `_legacy/core/data/npc_templates.py` | NPC 性格模板 | 提取为 Core 常量 |
| `_legacy/core/data/story_templates.py` | 剧情模板 | 提取为 Core 常量 |
| `_legacy/core/data/seed_data.py` | 种子数据 | 保留为数据初始化脚本 |
| `_legacy/core/services/combat.py` | 战斗计算 | 提取纯函数到 calculators |
| `_legacy/core/services/ending_system.py` | 结局评分 | 提取纯函数到 calculators |
| `_legacy/core/services/story_coherence.py` | 剧情连贯性检查 | 提取纯函数到 calculators |
| `1agent_core/src/memory/` | Markdown 记忆系统 | **废弃**，统一为 SQLite |

### P0 产出（本 Phase 依赖）

以下模块已在 P0 中实现，可直接 import：

```python
from foundation.event_bus import EventBus, event_bus, Event
from foundation.config import Settings, settings
from foundation.logger import get_logger
from foundation.database import get_db, get_db_path, init_db, execute_query
from foundation.cache import LRUCache
from foundation.save_manager import SaveManager
from foundation.resource_manager import ResourceManager
from foundation.base.interfaces import IGameStateProvider, IMemoryStore, IToolExecutor
```

---

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始"后，主动执行
4. **遇到错误先尝试修复**：3 次失败后再询问
5. **代码规范**：UTF-8，中文注释，PEP 8，类型注解
6. **依赖方向**：Core 层**只允许** import `foundation.*`
7. **纯函数原则**：calculators 中的函数必须是纯函数（无副作用、无 IO）
8. **Pydantic 优先**：所有数据结构使用 Pydantic BaseModel 定义

---

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **工作目录**: `2workbench/`
- **Core 层**: `2workbench/core/`
- **Legacy 参考**: `2workbench/_legacy/`

---

## 步骤

### Step 1: Pydantic 数据模型

**目的**: 用 Pydantic BaseModel 定义所有核心数据结构，替代现有的 SQLite Row 弱类型访问。

**方案**:

1.1 创建 `2workbench/core/models/entities.py` — 游戏实体数据类：

```python
# 2workbench/core/models/entities.py
"""游戏实体数据模型 — Pydantic BaseModel

所有游戏实体的数据结构定义。
这些模型用于:
1. Repository 层的返回值类型
2. LangGraph State 中的字段类型
3. API 层的请求/响应模型

注意: 这些是纯数据类，不包含任何业务逻辑。
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ========== 枚举 ==========

class WorldType(StrEnum):
    """世界类型"""
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    MODERN = "modern"
    HISTORICAL = "historical"
    CUSTOM = "custom"


class ItemType(StrEnum):
    """道具类型"""
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    QUEST = "quest"
    MISC = "misc"


class ItemRarity(StrEnum):
    """道具稀有度"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class QuestStatus(StrEnum):
    """任务状态"""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_STARTED = "not_started"


class QuestType(StrEnum):
    """任务类型"""
    MAIN = "main"
    SIDE = "side"
    DAILY = "daily"
    HIDDEN = "hidden"


class EventType(StrEnum):
    """游戏事件类型"""
    PLAYER_ACTION = "player_action"
    PLAYER_MOVE = "player_move"
    COMBAT_START = "combat_start"
    COMBAT_ACTION = "combat_action"
    COMBAT_END = "combat_end"
    QUEST_UPDATE = "quest_update"
    ITEM_ACQUIRE = "item_acquire"
    NPC_INTERACT = "npc_interact"
    TIME_PASS = "time_pass"
    SYSTEM_EVENT = "system_event"


class MemoryCategory(StrEnum):
    """记忆类别"""
    NPC = "npc"
    LOCATION = "location"
    PLAYER = "player"
    QUEST = "quest"
    WORLD = "world"
    SESSION = "session"


class PersonalityTrait(StrEnum):
    """大五人格维度"""
    OPENNESS = "openness"          # 开放性
    CONSCIENTIOUSNESS = "conscientiousness"  # 尽责性
    EXTRAVERSION = "extraversion"  # 外向性
    AGREEABLENESS = "agreeableness"  # 宜人性
    NEUROTICISM = "neuroticism"    # 神经质


# ========== 世界 ==========

class World(BaseModel):
    """世界"""
    id: int = 0
    name: str = ""
    setting: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""


# ========== 地点 ==========

class Location(BaseModel):
    """地点"""
    id: int = 0
    world_id: int = 0
    name: str = ""
    description: str = ""
    connections: dict[str, int] = Field(default_factory=dict)  # {"north": 2, "south": 3}
    created_at: str = ""
    updated_at: str = ""


# ========== 玩家 ==========

class Player(BaseModel):
    """玩家"""
    id: int = 0
    world_id: int = 0
    name: str = ""
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    level: int = 1
    exp: int = 0
    gold: int = 0
    location_id: int = 0
    created_at: str = ""
    updated_at: str = ""


# ========== NPC ==========

class Personality(BaseModel):
    """大五人格"""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5


class NPC(BaseModel):
    """NPC"""
    id: int = 0
    world_id: int = 0
    location_id: int = 0
    name: str = ""
    personality: Personality = Field(default_factory=Personality)
    backstory: str = ""
    mood: str = "neutral"
    goals: list[str] = Field(default_factory=list)
    relationships: dict[str, float] = Field(default_factory=dict)  # {"player": 0.5}
    speech_style: str = ""
    created_at: str = ""
    updated_at: str = ""


# ========== 道具 ==========

class ItemStats(BaseModel):
    """道具属性"""
    attack: int = 0
    defense: int = 0
    hp_bonus: int = 0
    mp_bonus: int = 0
    speed: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)


class Item(BaseModel):
    """道具模板"""
    id: int = 0
    name: str = ""
    item_type: ItemType = ItemType.MISC
    rarity: ItemRarity = ItemRarity.COMMON
    slot: str = ""
    stats: ItemStats = Field(default_factory=ItemStats)
    description: str = ""
    level_req: int = 1
    stackable: bool = False
    usable: bool = False
    created_at: str = ""


class PlayerItem(BaseModel):
    """玩家物品栏条目"""
    id: int = 0
    player_id: int = 0
    item_id: int = 0
    quantity: int = 1
    equipped: bool = False
    item: Item | None = None  # 关联查询时填充


# ========== 任务 ==========

class QuestStep(BaseModel):
    """任务步骤"""
    id: int = 0
    quest_id: int = 0
    step_order: int = 0
    description: str = ""
    step_type: str = ""  # goto / kill / talk / collect
    target: str = ""
    required_count: int = 1
    current_count: int = 0
    completed: bool = False


class Quest(BaseModel):
    """任务"""
    id: int = 0
    world_id: int = 0
    player_id: int = 0
    title: str = ""
    description: str = ""
    quest_type: QuestType = QuestType.SIDE
    status: QuestStatus = QuestStatus.NOT_STARTED
    rewards: dict[str, Any] = Field(default_factory=dict)
    prerequisites: dict[str, Any] = Field(default_factory=dict)
    branches: dict[str, Any] = Field(default_factory=dict)
    steps: list[QuestStep] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


# ========== 记忆（统一 SQLite） ==========

class Memory(BaseModel):
    """记忆条目 — 统一存储在 SQLite 中

    替代原有的 Markdown 文件记忆系统。
    支持按类别、世界、重要性检索。
    """
    id: int = 0
    world_id: int = 0
    category: MemoryCategory = MemoryCategory.SESSION
    source: str = ""           # 来源标识（如 "npc:张三" 或 "location:酒馆"）
    title: str = ""            # 记忆标题
    content: str = ""          # 记忆内容（Markdown 格式）
    importance: float = 0.5    # 重要性 0-1
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)  # 扩展元数据
    turn_created: int = 0      # 创建时的回合数
    turn_last_referenced: int = 0  # 最后被引用的回合数
    created_at: str = ""
    updated_at: str = ""


# ========== 游戏日志 ==========

class GameLog(BaseModel):
    """游戏日志"""
    id: int = 0
    world_id: int = 0
    event_type: str = ""
    content: str = ""
    timestamp: str = ""


# ========== 对话消息 ==========

class GameMessage(BaseModel):
    """对话消息"""
    id: int = 0
    world_id: int = 0
    role: str = ""             # system / user / assistant / npc / narrator
    name: str = ""             # 说话者名称
    content: str = ""
    timestamp: str = ""


# ========== Prompt 版本 ==========

class PromptVersion(BaseModel):
    """Prompt 版本"""
    id: int = 0
    prompt_key: str = ""
    content: str = ""
    version: int = 1
    is_active: bool = True
    description: str = ""
    created_at: str = ""


# ========== LLM 调用记录 ==========

class LLMCallRecord(BaseModel):
    """LLM 调用记录"""
    id: int = 0
    world_id: int = 0
    call_type: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    model: str = ""
    tool_calls_count: int = 0
    tool_names: list[str] = Field(default_factory=list)
    error: str = ""
    timestamp: str = ""
```

1.2 创建 `2workbench/core/models/__init__.py`：

```python
# 2workbench/core/models/__init__.py
"""数据模型包"""
from core.models.entities import (
    # 枚举
    WorldType, ItemType, ItemRarity, QuestStatus, QuestType,
    EventType, MemoryCategory, PersonalityTrait,
    # 实体
    World, Location, Player, NPC, Personality,
    Item, ItemStats, PlayerItem,
    Quest, QuestStep,
    Memory, GameLog, GameMessage,
    PromptVersion, LLMCallRecord,
)

__all__ = [
    "WorldType", "ItemType", "ItemRarity", "QuestStatus", "QuestType",
    "EventType", "MemoryCategory", "PersonalityTrait",
    "World", "Location", "Player", "NPC", "Personality",
    "Item", "ItemStats", "PlayerItem",
    "Quest", "QuestStep",
    "Memory", "GameLog", "GameMessage",
    "PromptVersion", "LLMCallRecord",
]
```

1.3 测试：

```bash
cd 2workbench ; python -c "
from core.models import World, Player, NPC, Item, Quest, Memory, Personality
from core.models import QuestStatus, MemoryCategory, ItemType

# 测试创建
world = World(id=1, name='艾泽拉斯', setting='fantasy')
player = Player(id=1, name='冒险者', hp=100, max_hp=100, level=1)
npc = NPC(id=1, name='老村长', personality=Personality(openness=0.8))
memory = Memory(id=1, world_id=1, category=MemoryCategory.NPC, source='npc:老村长', content='村长讲述了古老的传说')

# 测试序列化
import json
print(json.dumps(player.model_dump(), ensure_ascii=False, indent=2))

# 测试枚举
assert QuestStatus.ACTIVE == 'active'
assert MemoryCategory.NPC == 'npc'
assert ItemType.WEAPON == 'weapon'

print('✅ 数据模型测试通过')
"
```

**验收**:
- [ ] `core/models/entities.py` 创建完成
- [ ] 所有枚举、实体类定义正确
- [ ] Pydantic 序列化/反序列化正常
- [ ] 测试通过

---

### Step 2: LangGraph State 定义

**目的**: 定义 LangGraph StateGraph 的共享状态结构。

**方案**:

2.1 创建 `2workbench/core/state.py`：

```python
# 2workbench/core/state.py
"""LangGraph State 定义 — Agent 运行时共享状态

这是 LangGraph StateGraph 的核心数据结构。
所有节点（Node）通过读写此 State 进行通信。

设计原则:
1. 使用 TypedDict 定义（LangGraph 要求）
2. 使用 Annotated + Reducer 控制字段更新策略
3. 只包含运行时数据，不包含持久化配置
4. 与 Pydantic 模型保持一致的字段名和类型
"""
from __future__ import annotations

from typing import Annotated, Any

from typing_extensions import TypedDict

# LangGraph 内置 Reducer
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """Agent 运行时状态

    这是 LangGraph StateGraph 的共享状态。
    每个节点函数接收当前 State，返回部分更新字典。

    Reducer 说明:
    - messages: 使用 add_messages reducer，新消息追加而非覆盖
    - 其他字段: 无 reducer，每次更新覆盖整个字段
    """

    # ===== LangGraph 消息（带 Reducer）=====
    messages: Annotated[list, add_messages]

    # ===== 游戏世界状态 =====
    world_id: str
    player: dict[str, Any]           # Player.model_dump()
    current_location: dict[str, Any] # Location.model_dump()
    active_npcs: list[dict[str, Any]]  # [NPC.model_dump(), ...]
    inventory: list[dict[str, Any]]    # [PlayerItem.model_dump(), ...]
    active_quests: list[dict[str, Any]]  # [Quest.model_dump(), ...]

    # ===== Agent 运行时状态 =====
    turn_count: int
    execution_state: str              # idle / running / paused / step_waiting / completed / error

    # ===== 工作流中间数据 =====
    current_event: dict[str, Any]     # 当前引擎事件
    prompt_messages: list[dict]       # 组装好的 messages（发给 LLM 的）
    llm_response: dict[str, Any]      # LLM 原始响应
    parsed_commands: list[dict]       # 解析后的命令列表
    command_results: list[dict]       # 引擎执行结果
    memory_updates: list[dict]        # 记忆更新列表

    # ===== 配置（运行时可变）=====
    active_skills: list[str]          # 当前激活的 Skill 名称列表
    model_name: str                   # 当前使用的模型
    provider: str                     # 当前供应商
    temperature: float                # 当前温度

    # ===== 错误处理 =====
    error: str                        # 错误信息
    retry_count: int                  # 重试次数


def create_initial_state(
    world_id: str = "1",
    player_name: str = "冒险者",
    model_name: str = "deepseek-chat",
    provider: str = "deepseek",
) -> AgentState:
    """创建初始 Agent 状态

    Args:
        world_id: 世界 ID
        player_name: 玩家名称
        model_name: 模型名称
        provider: 供应商

    Returns:
        初始 AgentState
    """
    return AgentState(
        messages=[],
        world_id=world_id,
        player={
            "id": 0,
            "name": player_name,
            "hp": 100,
            "max_hp": 100,
            "mp": 50,
            "max_mp": 50,
            "level": 1,
            "exp": 0,
            "gold": 0,
            "location_id": 0,
        },
        current_location={},
        active_npcs=[],
        inventory=[],
        active_quests=[],
        turn_count=0,
        execution_state="idle",
        current_event={},
        prompt_messages=[],
        llm_response={},
        parsed_commands=[],
        command_results=[],
        memory_updates=[],
        active_skills=[],
        model_name=model_name,
        provider=provider,
        temperature=0.7,
        error="",
        retry_count=0,
    )
```

2.2 测试：

```bash
cd 2workbench ; python -c "
from core.state import AgentState, create_initial_state

# 测试创建初始状态
state = create_initial_state(world_id='1', player_name='测试玩家')
assert state['world_id'] == '1'
assert state['player']['name'] == '测试玩家'
assert state['turn_count'] == 0
assert state['execution_state'] == 'idle'
assert state['messages'] == []

# 测试部分更新（模拟节点返回）
update = {'turn_count': 1, 'execution_state': 'running'}
# TypedDict 的更新方式
new_state = {**state, **update}
assert new_state['turn_count'] == 1
assert new_state['player']['name'] == '测试玩家'  # 未被覆盖

print('✅ LangGraph State 测试通过')
"
```

**验收**:
- [ ] `core/state.py` 创建完成
- [ ] `AgentState` 使用 TypedDict 定义
- [ ] `messages` 字段使用 `add_messages` Reducer
- [ ] `create_initial_state()` 返回正确的初始状态
- [ ] 测试通过

---

### Step 3: Schema 迁移 — 新增记忆表

**目的**: 在现有 14 张表基础上，新增统一的 `memories` 表，替代 Markdown 文件记忆。

**参考**: `_legacy/core/models/schema.sql`（14 张表）

**方案**:

3.1 创建 `2workbench/core/models/schema.sql`：

```sql
-- ============================================================
-- Game Master Agent V3 — 数据库 Schema
-- 基于 V2 的 14 张表 + 新增 memories 表（统一记忆系统）
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;

-- ===== 世界 =====
CREATE TABLE IF NOT EXISTS worlds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    setting TEXT DEFAULT 'fantasy',
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- ===== 地点 =====
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    connections TEXT DEFAULT '{}',  -- JSON: {"north": 2, "south": 3}
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

-- ===== 玩家 =====
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    hp INTEGER DEFAULT 100,
    max_hp INTEGER DEFAULT 100,
    mp INTEGER DEFAULT 50,
    max_mp INTEGER DEFAULT 50,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    gold INTEGER DEFAULT 0,
    location_id INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

-- ===== NPC =====
CREATE TABLE IF NOT EXISTS npcs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    location_id INTEGER DEFAULT 0,
    name TEXT NOT NULL,
    personality TEXT DEFAULT '{}',      -- JSON: Personality
    backstory TEXT DEFAULT '',
    mood TEXT DEFAULT 'neutral',
    goals TEXT DEFAULT '[]',           -- JSON: [string]
    relationships TEXT DEFAULT '{}',   -- JSON: {"player": 0.5}
    speech_style TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

-- ===== 道具模板 =====
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    item_type TEXT DEFAULT 'misc',
    rarity TEXT DEFAULT 'common',
    slot TEXT DEFAULT '',
    stats TEXT DEFAULT '{}',           -- JSON: ItemStats
    description TEXT DEFAULT '',
    level_req INTEGER DEFAULT 1,
    stackable INTEGER DEFAULT 0,
    usable INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ===== 玩家物品栏 =====
CREATE TABLE IF NOT EXISTS player_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    equipped INTEGER DEFAULT 0,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id)
);

-- ===== 任务 =====
CREATE TABLE IF NOT EXISTS quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    player_id INTEGER DEFAULT 0,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    quest_type TEXT DEFAULT 'side',
    status TEXT DEFAULT 'not_started',
    rewards TEXT DEFAULT '{}',         -- JSON
    prerequisites TEXT DEFAULT '{}',   -- JSON
    branches TEXT DEFAULT '{}',        -- JSON
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

-- ===== 任务步骤 =====
CREATE TABLE IF NOT EXISTS quest_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id INTEGER NOT NULL,
    step_order INTEGER DEFAULT 0,
    description TEXT DEFAULT '',
    step_type TEXT DEFAULT '',         -- goto / kill / talk / collect
    target TEXT DEFAULT '',
    required_count INTEGER DEFAULT 1,
    current_count INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE
);

-- ===== 游戏日志 =====
CREATE TABLE IF NOT EXISTS game_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    event_type TEXT DEFAULT 'system',
    content TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

-- ===== 对话消息 =====
CREATE TABLE IF NOT EXISTS game_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    role TEXT DEFAULT 'user',
    name TEXT DEFAULT '',
    content TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

-- ===== Prompt 版本 =====
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_key TEXT NOT NULL,
    content TEXT DEFAULT '',
    version INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

-- ===== LLM 调用记录 =====
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER DEFAULT 0,
    call_type TEXT DEFAULT '',
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    model TEXT DEFAULT '',
    tool_calls_count INTEGER DEFAULT 0,
    tool_names TEXT DEFAULT '[]',      -- JSON
    error TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- 新增: 统一记忆表（替代 Markdown 文件记忆）
-- ============================================================
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    category TEXT DEFAULT 'session',   -- npc / location / player / quest / world / session
    source TEXT DEFAULT '',            -- 来源标识: "npc:张三" / "location:酒馆"
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',           -- Markdown 格式内容
    importance REAL DEFAULT 0.5,       -- 重要性 0.0 - 1.0
    tags TEXT DEFAULT '[]',            -- JSON: ["战斗", "重要"]
    metadata TEXT DEFAULT '{}',        -- JSON: 扩展元数据
    turn_created INTEGER DEFAULT 0,    -- 创建时的回合数
    turn_last_referenced INTEGER DEFAULT 0,
    reference_count INTEGER DEFAULT 0, -- 被引用次数
    compressed INTEGER DEFAULT 0,      -- 是否已压缩
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_locations_world ON locations(world_id);
CREATE INDEX IF NOT EXISTS idx_players_world ON players(world_id);
CREATE INDEX IF NOT EXISTS idx_npcs_world ON npcs(world_id);
CREATE INDEX IF NOT EXISTS idx_npcs_location ON npcs(location_id);
CREATE INDEX IF NOT EXISTS idx_player_items_player ON player_items(player_id);
CREATE INDEX IF NOT EXISTS idx_quests_world ON quests(world_id);
CREATE INDEX IF NOT EXISTS idx_quests_player ON quests(player_id);
CREATE INDEX IF NOT EXISTS idx_quests_status ON quests(status);
CREATE INDEX IF NOT EXISTS idx_quest_steps_quest ON quest_steps(quest_id);
CREATE INDEX IF NOT EXISTS idx_game_logs_world ON game_logs(world_id);
CREATE INDEX IF NOT EXISTS idx_game_logs_timestamp ON game_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_game_messages_world ON game_messages(world_id);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_key ON prompt_versions(prompt_key);
CREATE INDEX IF NOT EXISTS idx_llm_calls_world ON llm_calls(world_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_timestamp ON llm_calls(timestamp);

-- 记忆表索引
CREATE INDEX IF NOT EXISTS idx_memories_world ON memories(world_id);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(world_id, category);
CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(world_id, source);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(world_id, importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_turn ON memories(world_id, turn_created);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(world_id, tags);
```

3.2 更新 `foundation/database.py` 中的 `SCHEMA_VERSION` 和 schema 路径：

在 `foundation/database.py` 中修改：

```python
# 将 SCHEMA_VERSION 从 1 改为 2
SCHEMA_VERSION = 2

# 修改 init_db 中的默认 schema 路径
def init_db(schema_path=None, db_path=None):
    if schema_path is None:
        # 指向新的 schema.sql
        schema_path = Path(__file__).parent.parent / "core" / "models" / "schema.sql"
    ...
```

3.3 测试 Schema 初始化：

```bash
cd 2workbench ; python -c "
from foundation.database import init_db, get_db, execute_query
import tempfile, os

with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp_db = f.name

try:
    success = init_db(db_path=tmp_db)
    assert success, 'init_db 失败'

    # 验证所有表都创建了
    with get_db(tmp_db) as db:
        tables = db.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()
        table_names = [t['name'] for t in tables]
        print(f'创建的表: {table_names}')
        assert 'memories' in table_names, 'memories 表未创建'
        assert 'worlds' in table_names
        assert 'players' in table_names
        assert 'npcs' in table_names
        assert len(table_names) == 15, f'期望 15 张表，实际 {len(table_names)}'

    print('✅ Schema 迁移测试通过')
finally:
    os.unlink(tmp_db)
"
```

**验收**:
- [ ] `core/models/schema.sql` 创建完成（15 张表）
- [ ] `memories` 表包含所有设计字段
- [ ] 索引创建正确（6 个记忆表索引）
- [ ] `init_db()` 成功初始化所有表
- [ ] 测试通过

---

### Step 4: Repository 重构 — 类式 + 事务

**目的**: 将现有 10 个函数式 Repo 重构为类式 Repository，增加事务支持和 Pydantic 模型转换。

**参考**: `_legacy/core/models/*.py`

**方案**:

4.1 创建 `2workbench/core/models/repository.py` — 基类 + 所有 Repository：

```python
# 2workbench/core/models/repository.py
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

    def create(self, name: str, setting: str = "fantasy", description: str = "", db_path: str | None = None) -> World:
        with get_db(db_path) as db:
            cursor = db.execute(
                "INSERT INTO worlds (name, setting, description) VALUES (?, ?, ?)",
                (name, setting, description),
            )
            row = db.execute("SELECT * FROM worlds WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return World(**self._row_to_dict(row))

    def get_by_id(self, world_id: int, db_path: str | None = None) -> World | None:
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
            return World(**self._row_to_dict(row)) if row else None

    def list_all(self, db_path: str | None = None) -> list[World]:
        with get_db(db_path) as db:
            rows = db.execute("SELECT * FROM worlds ORDER BY created_at DESC").fetchall()
            return [World(**self._row_to_dict(r)) for r in rows]

    def update(self, world_id: int, **kwargs, db_path: str | None = None) -> World | None:
        if not kwargs:
            return self.get_by_id(world_id, db_path)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [world_id]
        with get_db(db_path) as db:
            db.execute(f"UPDATE worlds SET {sets}, updated_at = datetime('now') WHERE id = ?", values)
            return self.get_by_id(world_id, db_path)

    def delete(self, world_id: int, db_path: str | None = None) -> bool:
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
            return Location(**self._row_to_dict(row))

    def get_by_id(self, location_id: int, db_path: str | None = None) -> Location | None:
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
            return Location(**self._row_to_dict(row)) if row else None

    def get_by_world(self, world_id: int, db_path: str | None = None) -> list[Location]:
        with get_db(db_path) as db:
            rows = db.execute("SELECT * FROM locations WHERE world_id = ?", (world_id,)).fetchall()
            return [Location(**self._row_to_dict(r)) for r in rows]

    def update(self, location_id: int, **kwargs, db_path: str | None = None) -> Location | None:
        if "connections" in kwargs and isinstance(kwargs["connections"], dict):
            kwargs["connections"] = self._json_dumps(kwargs["connections"])
        if not kwargs:
            return self.get_by_id(location_id, db_path)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [location_id]
        with get_db(db_path) as db:
            db.execute(f"UPDATE locations SET {sets}, updated_at = datetime('now') WHERE id = ?", values)
            return self.get_by_id(location_id, db_path)


# ========== PlayerRepo ==========

class PlayerRepo(BaseRepository):
    """玩家仓库"""

    def create(self, world_id: int, name: str, **kwargs, db_path: str | None = None) -> Player:
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
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
            return Player(**self._row_to_dict(row)) if row else None

    def get_by_world(self, world_id: int, db_path: str | None = None) -> Player | None:
        with get_db(db_path) as db:
            row = db.execute("SELECT * FROM players WHERE world_id = ? LIMIT 1", (world_id,)).fetchone()
            return Player(**self._row_to_dict(row)) if row else None

    def update(self, player_id: int, **kwargs, db_path: str | None = None) -> Player | None:
        if not kwargs:
            return self.get_by_id(player_id, db_path)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [player_id]
        with get_db(db_path) as db:
            db.execute(f"UPDATE players SET {sets}, updated_at = datetime('now') WHERE id = ?", values)
            return self.get_by_id(player_id, db_path)

    def get_inventory(self, player_id: int, db_path: str | None = None) -> list[PlayerItem]:
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

    def create(self, world_id: int, name: str, location_id: int = 0, **kwargs, db_path: str | None = None) -> NPC:
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

    def update(self, npc_id: int, **kwargs, db_path: str | None = None) -> NPC | None:
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

    def create(self, name: str, item_type: str = "misc", **kwargs, db_path: str | None = None) -> Item:
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

    def _row_to_item(self, row) -> Item:
        if row is None:
            return None
        d = self._row_to_dict(row)
        d["stats"] = ItemStats(**self._json_loads(d.get("stats"), {}))
        return Item(**d)


# ========== QuestRepo ==========

class QuestRepo(BaseRepository):
    """任务仓库"""

    def create(self, world_id: int, title: str, **kwargs, db_path: str | None = None) -> Quest:
        defaults = {"player_id": 0, "description": "", "quest_type": "side", "status": "not_started", "rewards": {}, "prerequisites": {}, "branches": {}}
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

    def update_status(self, quest_id: int, status: str, db_path: str | None = None) -> bool:
        if status not in ("active", "completed", "failed", "not_started"):
            return False
        with get_db(db_path) as db:
            db.execute("UPDATE quests SET status = ?, updated_at = datetime('now') WHERE id = ?", (status, quest_id))
            return True

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
```

4.2 更新 `core/models/__init__.py`：

```python
# 2workbench/core/models/__init__.py
"""数据模型包"""
from core.models.entities import (
    WorldType, ItemType, ItemRarity, QuestStatus, QuestType,
    EventType, MemoryCategory, PersonalityTrait,
    World, Location, Player, NPC, Personality,
    Item, ItemStats, PlayerItem,
    Quest, QuestStep,
    Memory, GameLog, GameMessage,
    PromptVersion, LLMCallRecord,
)
from core.models.repository import (
    BaseRepository,
    WorldRepo, LocationRepo, PlayerRepo, NPCRepo, ItemRepo,
    QuestRepo, MemoryRepo, LogRepo, PromptRepo, MetricsRepo,
)

__all__ = [
    # 实体
    "World", "Location", "Player", "NPC", "Personality",
    "Item", "ItemStats", "PlayerItem",
    "Quest", "QuestStep",
    "Memory", "GameLog", "GameMessage",
    "PromptVersion", "LLMCallRecord",
    # 枚举
    "WorldType", "ItemType", "ItemRarity", "QuestStatus", "QuestType",
    "EventType", "MemoryCategory", "PersonalityTrait",
    # Repository
    "BaseRepository",
    "WorldRepo", "LocationRepo", "PlayerRepo", "NPCRepo", "ItemRepo",
    "QuestRepo", "MemoryRepo", "LogRepo", "PromptRepo", "MetricsRepo",
]
```

4.3 测试：

```bash
cd 2workbench ; python -c "
from foundation.database import init_db
from core.models import WorldRepo, PlayerRepo, NPCRepo, MemoryRepo, ItemRepo
from core.models import World, Player, NPC, Memory, Personality
import tempfile, os

with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp_db = f.name

try:
    init_db(db_path=tmp_db)

    # 测试 WorldRepo
    world_repo = WorldRepo()
    world = world_repo.create(name='测试世界', setting='fantasy', db_path=tmp_db)
    assert world.id > 0
    assert world.name == '测试世界'
    worlds = world_repo.list_all(db_path=tmp_db)
    assert len(worlds) == 1

    # 测试 PlayerRepo
    player_repo = PlayerRepo()
    player = player_repo.create(world_id=world.id, name='冒险者', hp=100, db_path=tmp_db)
    assert player.name == '冒险者'

    # 测试 NPCRepo
    npc_repo = NPCRepo()
    npc = npc_repo.create(world_id=world.id, name='老村长', personality={'openness': 0.8}, db_path=tmp_db)
    assert npc.personality.openness == 0.8
    assert isinstance(npc.personality, Personality)

    # 测试 MemoryRepo
    mem_repo = MemoryRepo()
    mem = mem_repo.store(world_id=world.id, category='npc', source='npc:老村长',
                         content='村长讲述了古老的传说', importance=0.8, turn=1, db_path=tmp_db)
    assert mem.id > 0
    memories = mem_repo.recall(world_id=world.id, category='npc', db_path=tmp_db)
    assert len(memories) == 1
    assert memories[0].importance == 0.8

    # 测试记忆压缩
    for i in range(60):
        mem_repo.store(world_id=world.id, category='session', source='system',
                      content=f'日志 {i}', importance=0.1, turn=i, db_path=tmp_db)
    deleted = mem_repo.compress(world_id=world.id, keep_count=50, db_path=tmp_db)
    assert deleted == 11  # 60 + 1 - 50 = 11

    print('✅ Repository 测试通过')
finally:
    os.unlink(tmp_db)
"
```

**验收**:
- [ ] `core/models/repository.py` 创建完成
- [ ] 10 个 Repository 类全部实现
- [ ] 返回 Pydantic 模型而非 SQLite Row
- [ ] JSON 字段自动序列化/反序列化
- [ ] MemoryRepo 支持存储/检索/压缩
- [ ] 测试通过

---

### Step 5: 纯函数计算器

**目的**: 从现有 service 中提取纯函数逻辑到 Core 层。

**参考**: `_legacy/core/services/combat.py`、`_legacy/core/services/ending_system.py`

**方案**:

5.1 创建 `2workbench/core/calculators/combat.py`：

```python
# 2workbench/core/calculators/combat.py
"""战斗计算器 — 纯函数

从 _legacy/core/services/combat.py 提取的纯计算逻辑。
无 IO、无副作用、无 LLM 调用。
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Combatant:
    """战斗者"""
    name: str
    hp: int
    max_hp: int
    attack_bonus: int = 0
    damage_dice: str = "1d6"
    ac: int = 10
    is_player: bool = False


@dataclass
class AttackResult:
    """攻击结果"""
    attacker: str
    defender: str
    hit: bool
    is_crit: bool
    attack_roll: int
    damage: int
    narrative: str


@dataclass
class CombatResult:
    """战斗结果"""
    rounds: list[list[AttackResult]] = field(default_factory=list)
    victory: bool = False
    rewards: dict[str, Any] = field(default_factory=dict)
    survivors: list[str] = field(default_factory=list)


def roll_dice(dice_str: str) -> int:
    """掷骰子 — 支持 XdY 格式

    Args:
        dice_str: 骰子表达式，如 "1d20", "2d6", "1d8+3"

    Returns:
        掷骰结果
    """
    match = re.match(r"(\d+)d(\d+)([+-]\d+)?", dice_str.strip())
    if not match:
        return 0
    count, sides = int(match.group(1)), int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0
    total = sum(random.randint(1, sides) for _ in range(count)) + modifier
    return total


def calculate_attack_bonus(level: int, stat_bonus: int = 0) -> int:
    """计算攻击加值"""
    return stat_bonus + (level // 2)


def calculate_ac(base_ac: int = 10, dex_bonus: int = 0, armor_bonus: int = 0) -> int:
    """计算护甲等级"""
    return base_ac + dex_bonus + armor_bonus


def attack(attacker: Combatant, defender: Combatant) -> AttackResult:
    """执行一次攻击

    Returns:
        AttackResult
    """
    attack_roll = roll_dice("1d20")
    is_crit = attack_roll == 20
    total_attack = attack_roll + attacker.attack_bonus

    hit = is_crit or total_attack >= defender.ac

    if hit:
        damage = roll_dice(attacker.damage_dice)
        if is_crit:
            damage *= 2  # 暴击双倍伤害
        narrative = f"{'暴击！' if is_crit else ''}{attacker.name} 命中了 {defender.name}，造成 {damage} 点伤害"
    else:
        damage = 0
        narrative = f"{attacker.name} 攻击 {defender.name} 未命中（{total_attack} vs AC {defender.ac}）"

    return AttackResult(
        attacker=attacker.name,
        defender=defender.name,
        hit=hit,
        is_crit=is_crit,
        attack_roll=total_attack,
        damage=damage,
        narrative=narrative,
    )


def combat_round(player: Combatant, enemies: list[Combatant]) -> list[AttackResult]:
    """执行一轮战斗

    Args:
        player: 玩家
        enemies: 敌人列表

    Returns:
        本轮所有攻击结果
    """
    results = []

    # 玩家攻击所有存活敌人
    for enemy in enemies:
        if enemy.hp > 0:
            result = attack(player, enemy)
            results.append(result)
            if result.hit:
                enemy.hp = max(0, enemy.hp - result.damage)

    # 存活敌人反击
    for enemy in enemies:
        if enemy.hp > 0:
            result = attack(enemy, player)
            results.append(result)
            if result.hit:
                player.hp = max(0, player.hp - result.damage)

    return results


def is_combat_over(player: Combatant, enemies: list[Combatant]) -> bool:
    """检查战斗是否结束"""
    return player.hp <= 0 or all(e.hp <= 0 for e in enemies)


def calculate_rewards(enemies: list[Combatant]) -> dict[str, Any]:
    """计算战斗奖励"""
    defeated = [e for e in enemies if e.hp <= 0]
    exp = len(defeated) * 25
    gold = random.randint(5, 20) * len(defeated)
    return {"exp": exp, "gold": gold, "defeated_count": len(defeated)}
```

5.2 创建 `2workbench/core/calculators/ending.py`：

```python
# 2workbench/core/calculators/ending.py
"""结局计算器 — 纯函数

从 _legacy/core/services/ending_system.py 提取。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EndingScore:
    """结局评分"""
    hero: float = 0
    villain: float = 0
    neutral: float = 0
    tragic: float = 0
    secret: float = 0


def calculate_ending_score(
    main_quests_completed: int = 0,
    side_quests_completed: int = 0,
    total_main_quests: int = 5,
    player_hp: int = 100,
    max_hp: int = 100,
    npc_relationships: dict[str, float] | None = None,
    choices: list[dict[str, Any]] | None = None,
) -> EndingScore:
    """计算各结局分数

    Args:
        main_quests_completed: 完成的主线任务数
        side_quests_completed: 完成的支线任务数
        total_main_quests: 总主线任务数
        player_hp: 玩家当前 HP
        max_hp: 玩家最大 HP
        npc_relationships: NPC 关系值
        choices: 关键选择记录

    Returns:
        EndingScore
    """
    scores = EndingScore()
    relationships = npc_relationships or {}

    # 英雄路线: 完成主线 + 高关系值
    main_ratio = main_quests_completed / max(total_main_quests, 1)
    scores.hero = main_ratio * 50 + side_quests_completed * 5
    avg_relationship = sum(relationships.values()) / max(len(relationships), 1)
    scores.hero += max(0, avg_relationship * 20)

    # 反派路线: 低关系值 + 特定选择
    scores.villain = max(0, -avg_relationship * 30)
    if choices:
        evil_choices = sum(1 for c in choices if c.get("alignment") == "evil")
        scores.villain += evil_choices * 15

    # 悲剧路线: 低 HP
    hp_ratio = player_hp / max(max_hp, 1)
    scores.tragic = max(0, (1 - hp_ratio) * 40)

    # 中立路线
    scores.neutral = 30 - abs(scores.hero - scores.villain) * 0.3

    # 隐藏路线: 完成所有任务 + 发现秘密
    if main_quests_completed >= total_main_quests and side_quests_completed >= 3:
        scores.secret = 60

    return scores


def determine_ending(scores: EndingScore) -> str:
    """确定最终结局

    Returns:
        结局类型: hero / villain / neutral / tragic / secret
    """
    all_scores = {
        "hero": scores.hero,
        "villain": scores.villain,
        "neutral": scores.neutral,
        "tragic": scores.tragic,
        "secret": scores.secret,
    }
    return max(all_scores, key=all_scores.get)


def format_ending_narrative(ending_type: str, player_name: str = "冒险者") -> str:
    """格式化结局叙事文本"""
    narratives = {
        "hero": f"传奇英雄 — {player_name}拯救了世界，成为传说中的英雄。人民传颂着你的故事。",
        "villain": f"黑暗降临 — {player_name}选择了黑暗的道路，世界陷入了永恒的阴影。",
        "neutral": f"平凡之路 — {player_name}完成了旅程，但世界既没有变得更好，也没有变得更坏。",
        "tragic": f"悲壮牺牲 — {player_name}付出了生命的代价，但世界得以延续。",
        "secret": f"隐藏真相 — {player_name}发现了世界的终极秘密，超越了凡人的命运。",
    }
    return narratives.get(ending_type, f"未知结局 — {player_name}的故事以一种意想不到的方式结束了。")
```

5.3 创建 `2workbench/core/calculators/__init__.py`：

```python
# 2workbench/core/calculators/__init__.py
"""纯函数计算器"""
from core.calculators.combat import (
    Combatant, AttackResult, CombatResult,
    roll_dice, calculate_attack_bonus, calculate_ac,
    attack, combat_round, is_combat_over, calculate_rewards,
)
from core.calculators.ending import (
    EndingScore, calculate_ending_score, determine_ending, format_ending_narrative,
)

__all__ = [
    "Combatant", "AttackResult", "CombatResult",
    "roll_dice", "calculate_attack_bonus", "calculate_ac",
    "attack", "combat_round", "is_combat_over", "calculate_rewards",
    "EndingScore", "calculate_ending_score", "determine_ending", "format_ending_narrative",
]
```

5.4 测试：

```bash
cd 2workbench ; python -c "
import random
random.seed(42)

from core.calculators.combat import (
    roll_dice, Combatant, attack, combat_round, is_combat_over, calculate_rewards
)
from core.calculators.ending import calculate_ending_score, determine_ending, format_ending_narrative

# 战斗计算测试
assert 1 <= roll_dice('1d20') <= 20
assert 2 <= roll_dice('2d6') <= 12

player = Combatant(name='冒险者', hp=100, max_hp=100, attack_bonus=3, damage_dice='1d8', ac=15)
goblin = Combatant(name='哥布林', hp=20, max_hp=20, attack_bonus=1, damage_dice='1d6', ac=12)

result = attack(player, goblin)
assert result.attacker == '冒险者'
assert isinstance(result.damage, int)
print(f'攻击结果: {result.narrative}')

# 结局计算测试
scores = calculate_ending_score(
    main_quests_completed=5, total_main_quests=5,
    side_quests_completed=4, player_hp=80, max_hp=100,
    npc_relationships={'村长': 0.8, '铁匠': 0.6}
)
ending = determine_ending(scores)
narrative = format_ending_narrative(ending, '测试玩家')
print(f'结局: {ending}')
print(f'叙事: {narrative}')

print('✅ 纯函数计算器测试通过')
"
```

**验收**:
- [ ] `core/calculators/combat.py` — 战斗纯函数
- [ ] `core/calculators/ending.py` — 结局纯函数
- [ ] 所有函数无副作用、无 IO
- [ ] 测试通过

---

### Step 6: 常量定义

**目的**: 将散落在各处的常量集中到 Core 层。

**参考**: `_legacy/core/data/npc_templates.py`、`_legacy/core/data/story_templates.py`

**方案**:

6.1 创建 `2workbench/core/constants/npc_templates.py`：

```python
# 2workbench/core/constants/npc_templates.py
"""NPC 性格模板 — 基于 Big Five 人格模型

从 _legacy/core/data/npc_templates.py 提取。
"""
from core.models.entities import Personality

TEMPLATES: dict[str, dict] = {
    "brave_warrior": {
        "name": "勇敢战士",
        "personality": Personality(
            openness=0.4, conscientiousness=0.8,
            extraversion=0.7, agreeableness=0.5, neuroticism=0.3,
        ),
        "speech_style": "直率、豪爽，喜欢用简短的句子",
        "mood": "confident",
        "common_topics": ["战斗", "荣誉", "训练", "冒险"],
        "goals": ["保护弱者", "变强", "击败强敌"],
    },
    "mysterious_mage": {
        "name": "神秘法师",
        "personality": Personality(
            openness=0.9, conscientiousness=0.6,
            extraversion=0.2, agreeableness=0.4, neuroticism=0.5,
        ),
        "speech_style": "深奥、隐晦，喜欢用比喻和典故",
        "mood": "contemplative",
        "common_topics": ["魔法", "知识", "远古秘密", "星辰"],
        "goals": ["追求真理", "掌握禁忌魔法", "解开世界之谜"],
    },
    "friendly_merchant": {
        "name": "友好商人",
        "personality": Personality(
            openness=0.5, conscientiousness=0.6,
            extraversion=0.9, agreeableness=0.8, neuroticism=0.3,
        ),
        "speech_style": "热情、健谈，喜欢讨价还价",
        "mood": "cheerful",
        "common_topics": ["商品", "价格", "旅行见闻", "美食"],
        "goals": ["赚钱", "扩大生意", "结交人脉"],
    },
    "sinister_villain": {
        "name": "阴险反派",
        "personality": Personality(
            openness=0.7, conscientiousness=0.8,
            extraversion=0.4, agreeableness=0.1, neuroticism=0.6,
        ),
        "speech_style": "阴冷、讽刺，喜欢暗示和威胁",
        "mood": "menacing",
        "common_topics": ["权力", "控制", "弱点", "阴谋"],
        "goals": ["统治世界", "复仇", "获取神器"],
    },
    "wise_elder": {
        "name": "智慧长者",
        "personality": Personality(
            openness=0.8, conscientiousness=0.7,
            extraversion=0.4, agreeableness=0.8, neuroticism=0.2,
        ),
        "speech_style": "温和、睿智，喜欢讲寓言和故事",
        "mood": "serene",
        "common_topics": ["历史", "智慧", "传承", "命运"],
        "goals": ["守护知识", "引导后辈", "维护和平"],
    },
    "naive_villager": {
        "name": "天真村民",
        "personality": Personality(
            openness=0.3, conscientiousness=0.4,
            extraversion=0.6, agreeableness=0.9, neuroticism=0.7,
        ),
        "speech_style": "朴实、紧张，经常问问题",
        "mood": "nervous",
        "common_topics": ["村庄", "天气", "庄稼", "传闻"],
        "goals": ["过上安稳生活", "保护家人", "不被卷入冒险"],
    },
}


def get_template(template_name: str) -> dict | None:
    """获取 NPC 模板"""
    return TEMPLATES.get(template_name)


def list_templates() -> list[str]:
    """列出所有可用模板"""
    return list(TEMPLATES.keys())


def apply_template(template_name: str, overrides: dict | None = None) -> dict:
    """应用模板，返回 NPC 属性字典"""
    template = TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"未知 NPC 模板: {template_name}，可用: {list_templates()}")
    result = dict(template)
    if overrides:
        result.update(overrides)
    return result
```

6.2 创建 `2workbench/core/constants/story_templates.py`：

```python
# 2workbench/core/constants/story_templates.py
"""剧情模板

从 _legacy/core/data/story_templates.py 提取。
"""
from __future__ import annotations

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "rescue": {
        "name": "救援",
        "description_template": "{target} 被 {enemy} 抓走了，需要前往 {location} 救出 {target}。",
        "steps": [
            {"type": "goto", "description": "前往 {location}"},
            {"type": "kill", "description": "击败 {enemy}"},
            {"type": "talk", "description": "与 {target} 对话"},
        ],
        "rewards": {"exp": 100, "gold": 50},
        "branches": {
            "stealth": {"description": "潜入 {location}，不惊动守卫", "modifier": 1.5},
            "direct": {"description": "正面突破", "modifier": 1.0},
        },
        "variables": ["target", "enemy", "location"],
    },
    "escort": {
        "name": "护送",
        "description_template": "护送 {npc} 安全到达 {destination}。",
        "steps": [
            {"type": "goto", "description": "与 {npc} 会合"},
            {"type": "goto", "description": "前往 {destination}"},
            {"type": "talk", "description": "与 {npc} 告别"},
        ],
        "rewards": {"exp": 80, "gold": 30},
        "branches": {
            "safe_route": {"description": "走安全路线（更远但更安全）", "modifier": 0.8},
            "dangerous_route": {"description": "走危险捷径", "modifier": 1.5},
        },
        "variables": ["npc", "destination"],
    },
    "collect": {
        "name": "收集",
        "description_template": "收集 {count} 个 {item}，交给 {npc}。",
        "steps": [
            {"type": "talk", "description": "与 {npc} 接受任务"},
            {"type": "collect", "description": "收集 {count} 个 {item}"},
            {"type": "talk", "description": "将物品交给 {npc}"},
        ],
        "rewards": {"exp": 60, "gold": 40},
        "variables": ["npc", "item", "count"],
    },
    "investigate": {
        "name": "调查",
        "description_template": "调查 {location} 发生的 {event}。",
        "steps": [
            {"type": "goto", "description": "前往 {location}"},
            {"type": "talk", "description": "询问目击者"},
            {"type": "goto", "description": "追踪线索到 {clue_location}"},
        ],
        "rewards": {"exp": 120, "gold": 60},
        "variables": ["location", "event", "clue_location"],
    },
    "exterminate": {
        "name": "消灭",
        "description_template": "消灭 {location} 的 {enemy}，威胁等级: {threat_level}。",
        "steps": [
            {"type": "goto", "description": "前往 {location}"},
            {"type": "kill", "description": "消灭 {enemy}（{count} 只）"},
            {"type": "talk", "description": "向 {npc} 报告"},
        ],
        "rewards": {"exp": 150, "gold": 80},
        "variables": ["location", "enemy", "count", "threat_level", "npc"],
    },
}


def generate_quest_from_template(template_name: str, **variables) -> dict[str, Any]:
    """从模板生成任务数据"""
    template = TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"未知剧情模板: {template_name}")

    # 填充变量
    description = template["description_template"]
    for key, value in variables.items():
        description = description.replace(f"{{{key}}}", str(value))

    # 填充步骤
    steps = []
    for step in template["steps"]:
        step_desc = step["description"]
        for key, value in variables.items():
            step_desc = step_desc.replace(f"{{{key}}}", str(value))
        steps.append({
            "description": step_desc,
            "type": step["type"],
            "completed": False,
        })

    return {
        "title": description[:30] + ("..." if len(description) > 30 else ""),
        "description": description,
        "steps": steps,
        "rewards": template["rewards"],
        "branches": template.get("branches", {}),
        "template_name": template_name,
    }
```

6.3 创建 `2workbench/core/constants/__init__.py`：

```python
# 2workbench/core/constants/__init__.py
"""常量定义"""
from core.constants.npc_templates import TEMPLATES as NPC_TEMPLATES, get_template, list_templates, apply_template
from core.constants.story_templates import TEMPLATES as STORY_TEMPLATES, generate_quest_from_template

__all__ = [
    "NPC_TEMPLATES", "get_template", "list_templates", "apply_template",
    "STORY_TEMPLATES", "generate_quest_from_template",
]
```

6.4 测试：

```bash
cd 2workbench ; python -c "
from core.constants.npc_templates import list_templates, get_template, apply_template
from core.constants.story_templates import generate_quest_from_template

# NPC 模板
templates = list_templates()
assert len(templates) == 6
assert 'brave_warrior' in templates

warrior = apply_template('brave_warrior')
assert warrior['name'] == '勇敢战士'
assert warrior['personality'].extraversion == 0.7

# 剧情模板
quest = generate_quest_from_template('rescue', target='公主', enemy='恶龙', location='龙巢')
assert '公主' in quest['description']
assert '恶龙' in quest['description']
assert len(quest['steps']) == 3

print('✅ 常量定义测试通过')
"
```

**验收**:
- [ ] `core/constants/npc_templates.py` — 6 种 NPC 模板
- [ ] `core/constants/story_templates.py` — 5 种剧情模板
- [ ] 模板变量填充正确
- [ ] 测试通过

---

### Step 7: Core 层集成测试

**目的**: 验证 Core 层所有模块协同工作。

**方案**:

7.1 创建 `2workbench/tests/test_core_integration.py`：

```python
# 2workbench/tests/test_core_integration.py
"""Core 层集成测试"""
import sys, os, tempfile, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

random.seed(42)


def test_full_game_state_flow():
    """测试完整的游戏状态流程"""
    from foundation.database import init_db
    from core.models import (
        WorldRepo, PlayerRepo, NPCRepo, LocationRepo, ItemRepo,
        MemoryRepo, QuestRepo, LogRepo,
    )
    from core.state import create_initial_state

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        tmp_db = f.name

    try:
        init_db(db_path=tmp_db)

        # 创建世界
        world_repo = WorldRepo()
        world = world_repo.create(name='测试世界', setting='fantasy', db_path=tmp_db)

        # 创建地点
        loc_repo = LocationRepo()
        village = loc_repo.create(world_id=world.id, name='宁静村', connections={'north': 0}, db_path=tmp_db)
        forest = loc_repo.create(world_id=world.id, name='幽暗森林', connections={'south': village.id}, db_path=tmp_db)

        # 创建玩家
        player_repo = PlayerRepo()
        player = player_repo.create(world_id=world.id, name='冒险者', location_id=village.id, db_path=tmp_db)

        # 创建 NPC
        npc_repo = NPCRepo()
        elder = npc_repo.create(world_id=world.id, name='老村长', location_id=village.id, db_path=tmp_db)

        # 创建道具
        item_repo = ItemRepo()
        sword = item_repo.create(name='木剑', item_type='weapon', stats={'attack': 5}, db_path=tmp_db)
        potion = item_repo.create(name='治疗药水', item_type='consumable', usable=True, stackable=True, db_path=tmp_db)

        # 给玩家添加物品
        player_repo.add_item(player.id, sword.id, db_path=tmp_db)
        player_repo.add_item(player.id, potion.id, quantity=3, db_path=tmp_db)
        inventory = player_repo.get_inventory(player.id, db_path=tmp_db)
        assert len(inventory) == 2

        # 创建任务
        quest_repo = QuestRepo()
        quest = quest_repo.create(world_id=world.id, title='消灭哥布林', quest_type='main', db_path=tmp_db)
        quest_repo.update_status(quest.id, 'active', db_path=tmp_db)

        # 存储记忆
        mem_repo = MemoryRepo()
        mem_repo.store(world_id=world.id, category='session', source='system',
                      content='冒险者来到了宁静村', importance=0.9, turn=0, db_path=tmp_db)
        mem_repo.store(world_id=world.id, category='npc', source='npc:老村长',
                      content='老村长请求冒险者消灭哥布林', importance=0.8, turn=1, db_path=tmp_db)

        # 记录日志
        log_repo = LogRepo()
        log_repo.log(world.id, 'quest', '任务开始: 消灭哥布林', db_path=tmp_db)

        # 创建 Agent State
        state = create_initial_state(world_id=str(world.id), player_name=player.name)
        state['player']['id'] = player.id
        state['current_location'] = {'id': village.id, 'name': village.name}
        state['active_npcs'] = [{'id': elder.id, 'name': elder.name}]
        state['turn_count'] = 1

        # 检索记忆
        memories = mem_repo.recall(world_id=world.id, limit=10, db_path=tmp_db)
        assert len(memories) == 2

        # 验证 State
        assert state['world_id'] == str(world.id)
        assert state['turn_count'] == 1
        assert len(state['active_npcs']) == 1

        print('✅ test_full_game_state_flow')

    finally:
        os.unlink(tmp_db)


def test_calculators_with_state():
    """测试计算器与 State 的配合"""
    from core.calculators.combat import Combatant, combat_round, is_combat_over, calculate_rewards
    from core.calculators.ending import calculate_ending_score, determine_ending

    player = Combatant(name='冒险者', hp=100, max_hp=100, attack_bonus=3, damage_dice='1d8', ac=15)
    enemies = [
        Combatant(name='哥布林A', hp=15, max_hp=15, attack_bonus=1, damage_dice='1d4', ac=10),
        Combatant(name='哥布林B', hp=15, max_hp=15, attack_bonus=1, damage_dice='1d4', ac=10),
    ]

    round_num = 0
    while not is_combat_over(player, enemies) and round_num < 20:
        combat_round(player, enemies)
        round_num += 1

    rewards = calculate_rewards(enemies)
    assert rewards['defeated_count'] >= 0

    # 结局计算
    scores = calculate_ending_score(main_quests_completed=3, total_main_quests=5, player_hp=player.hp)
    ending = determine_ending(scores)
    assert ending in ('hero', 'villain', 'neutral', 'tragic', 'secret')

    print(f'✅ test_calculators_with_state (战斗 {round_num} 轮, 结局: {ending})')


def test_templates_with_repo():
    """测试模板与 Repository 的配合"""
    from core.constants.npc_templates import apply_template
    from core.constants.story_templates import generate_quest_from_template

    # NPC 模板
    npc_data = apply_template('wise_elder', overrides={'name': '自定义长者'})
    assert npc_data['name'] == '自定义长者'
    assert npc_data['personality'].openness == 0.8

    # 剧情模板
    quest = generate_quest_from_template('collect', npc='铁匠', item='铁矿石', count=5)
    assert '铁矿石' in quest['description']
    assert len(quest['steps']) == 3

    print('✅ test_templates_with_repo')


if __name__ == "__main__":
    test_full_game_state_flow()
    test_calculators_with_state()
    test_templates_with_repo()
    print("\n🎉 Core 层集成测试全部通过!")
```

7.2 运行测试：

```bash
cd 2workbench ; python tests/test_core_integration.py
```

**验收**:
- [ ] 3 个集成测试全部通过
- [ ] 完整游戏状态流程（创建世界→地点→玩家→NPC→物品→任务→记忆→日志→State）
- [ ] 计算器与 State 配合正常
- [ ] 模板与 Repository 配合正常

---

### Step 8: 更新 Core 层 `__init__.py`

**目的**: 统一 Core 层的导出接口。

**方案**:

8.1 更新 `2workbench/core/__init__.py`：

```python
# 2workbench/core/__init__.py
"""Core 层 — 纯数据 + 纯规则

本层包含:
- 数据模型（Pydantic BaseModel）
- LangGraph State 定义
- Repository（数据访问对象）
- 纯函数计算器
- 常量定义

本层只依赖 Foundation 层，不依赖 Feature/Presentation 层。
"""
# 数据模型
from core.models import (
    World, Location, Player, NPC, Personality,
    Item, ItemStats, PlayerItem,
    Quest, QuestStep,
    Memory, GameLog, GameMessage,
    PromptVersion, LLMCallRecord,
    WorldType, ItemType, ItemRarity, QuestStatus, QuestType,
    EventType, MemoryCategory, PersonalityTrait,
    WorldRepo, LocationRepo, PlayerRepo, NPCRepo, ItemRepo,
    QuestRepo, MemoryRepo, LogRepo, PromptRepo, MetricsRepo,
)

# LangGraph State
from core.state import AgentState, create_initial_state

# 纯函数计算器
from core.calculators import (
    Combatant, AttackResult, CombatResult,
    roll_dice, attack, combat_round, is_combat_over, calculate_rewards,
    EndingScore, calculate_ending_score, determine_ending, format_ending_narrative,
)

# 常量
from core.constants import (
    NPC_TEMPLATES, get_template, list_templates, apply_template,
    STORY_TEMPLATES, generate_quest_from_template,
)

__all__ = [
    # 实体
    "World", "Location", "Player", "NPC", "Personality",
    "Item", "ItemStats", "PlayerItem",
    "Quest", "QuestStep",
    "Memory", "GameLog", "GameMessage",
    "PromptVersion", "LLMCallRecord",
    # 枚举
    "WorldType", "ItemType", "ItemRarity", "QuestStatus", "QuestType",
    "EventType", "MemoryCategory", "PersonalityTrait",
    # Repository
    "WorldRepo", "LocationRepo", "PlayerRepo", "NPCRepo", "ItemRepo",
    "QuestRepo", "MemoryRepo", "LogRepo", "PromptRepo", "MetricsRepo",
    # State
    "AgentState", "create_initial_state",
    # 计算器
    "Combatant", "AttackResult", "CombatResult",
    "roll_dice", "attack", "combat_round", "is_combat_over", "calculate_rewards",
    "EndingScore", "calculate_ending_score", "determine_ending", "format_ending_narrative",
    # 常量
    "NPC_TEMPLATES", "get_template", "list_templates", "apply_template",
    "STORY_TEMPLATES", "generate_quest_from_template",
]
```

8.2 最终导入测试：

```bash
cd 2workbench ; python -c "
from core import (
    World, Player, NPC, Memory, AgentState, create_initial_state,
    WorldRepo, PlayerRepo, NPCRepo, MemoryRepo,
    Combatant, roll_dice, calculate_ending_score,
    NPC_TEMPLATES, generate_quest_from_template,
)
print('✅ Core 层全部导入测试通过')
"
```

**验收**:
- [ ] `core/__init__.py` 导出完整
- [ ] 所有模块可从 `core` 直接导入
- [ ] 无循环依赖

---

## 注意事项

### 依赖方向检查

Core 层**只允许** import:
- `foundation.*` — Foundation 层
- `typing` / `dataclasses` / `enum` / `json` / `re` / `random` — 标准库
- `pydantic` — 第三方数据验证库
- `langgraph.graph.message` — 仅 `add_messages` reducer

Core 层**禁止** import:
- `feature.*` — Feature 层
- `presentation.*` — Presentation 层
- `openai` / `tenacity` — LLM 相关（属于 Foundation 层）

### Pydantic 与 SQLite Row 的转换

Repository 层负责 Pydantic 模型与 SQLite Row 之间的转换：
- **读取**: `dict(row)` → `Model(**dict)`
- **写入**: `model.model_dump()` → SQL 参数

### 记忆系统统一

原有的 Markdown 文件记忆（`1agent_core/src/memory/`）已废弃。
所有记忆统一存储在 `memories` 表中，通过 `MemoryRepo` 访问。

---

## 完成检查清单

- [ ] Step 1: Pydantic 数据模型（15+ 个实体类 + 8 个枚举）
- [ ] Step 2: LangGraph State 定义
- [ ] Step 3: Schema 迁移（15 张表 + 6 个记忆索引）
- [ ] Step 4: Repository 重构（10 个类式 Repo）
- [ ] Step 5: 纯函数计算器（战斗 + 结局）
- [ ] Step 6: 常量定义（6 NPC 模板 + 5 剧情模板）
- [ ] Step 7: Core 层集成测试全部通过
- [ ] Step 8: Core 层 `__init__.py` 导出完整
