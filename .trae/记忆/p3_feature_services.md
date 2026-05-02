# P3: Feature 层 — 业务功能系统

> 本文件记录 P3 Phase 的实现细节和架构决策。
> **状态**: ✅ 已完成
> **完成日期**: 2026-05-02

---

## 1. 概述

Feature 层是四层架构的第三层，负责封装具体的业务功能系统。所有 Feature 模块继承自 `BaseFeature`，通过 EventBus 与其他模块通信，禁止直接依赖。

### 1.1 架构位置

```
Presentation (表现层) → Feature (功能层) → Core (核心层) → Foundation (基础层)
```

### 1.2 设计原则

- ✅ Feature 层**只依赖** Core 和 Foundation 层
- ❌ Feature 层**绝对不能** import Presentation 层
- ✅ **同层模块间仅通过 EventBus 通信**，禁止直接 import 其他 Feature 模块
- ❌ 无循环依赖、无跨模块直调

---

## 2. Feature 基类

### 2.1 文件位置

`2workbench/feature/base.py`

### 2.2 核心设计

```python
class BaseFeature(ABC):
    name: str = ""  # 子类必须设置
    
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path
        self._enabled = False
        self._subscriptions: list[tuple[str, Any]] = []
        
    def on_enable(self) -> None: ...      # 启用时调用
    def on_disable(self) -> None: ...     # 禁用时调用（自动清理订阅）
    def subscribe(self, event_type, handler) -> None: ...  # 订阅事件
    def emit(self, event_type, data) -> list: ...          # 发送事件
```

### 2.3 生命周期

1. `__init__` — 初始化（保存 db_path）
2. `on_enable()` — 启用（注册 EventBus 订阅）
3. `on_disable()` — 禁用（自动取消所有订阅）

### 2.4 EventBus 封装

- `subscribe()` — 记录订阅以便清理
- `emit()` / `emit_async()` — 发送事件，自动设置 source 为 `feature.{name}`

---

## 3. 各 Feature 系统

### 3.1 BattleSystem — 战斗系统

**文件**: `feature/battle/system.py`

**职责**:
- 管理战斗生命周期（开始→轮次→结束）
- 调用 Core 层纯函数进行战斗计算
- 调用 LLM 生成战斗叙事（带降级）

**关键类**:
```python
@dataclass
class BattleState:
    active: bool = False
    player: Combatant | None = None
    enemies: list[Combatant] = field(default_factory=list)
    round_num: int = 0
    results: list[list[AttackResult]] = field(default_factory=list)
    victory: bool = False
```

**EventBus 事件**:
- `feature.battle.started` — 战斗开始
- `feature.battle.round_completed` — 回合完成
- `feature.battle.ended` — 战斗结束

**使用示例**:
```python
battle = BattleSystem(db_path=tmp_db)
battle.on_enable()

state = battle.start_combat({
    'player': {'name': '冒险者', 'hp': 100, 'attack_bonus': 5, ...},
    'enemies': [{'name': '哥布林', 'hp': 15, ...}],
})

while state.active:
    results = battle.execute_round()
```

---

### 3.2 DialogueSystem — NPC 对话系统

**文件**: `feature/dialogue/system.py`

**职责**:
- 根据 NPC 性格和关系值生成对话
- 管理对话历史（最近 10 轮）
- 通过 LLM 生成角色扮演式回复

**关键方法**:
```python
def build_npc_context(self, npc: NPC, player_relationship: float = 0.0) -> str:
    """构建 NPC 上下文（性格 + 关系 + 目标）"""
    
async def generate_dialogue(
    self, npc: NPC, player_input: str, 
    player_name: str = "冒险者", dialogue_history: list[dict] | None = None
) -> str:
    """生成 NPC 对话"""
```

**关系值映射**:
```python
RELATIONSHIP_MAP = {
    (0.7, 1.0): "非常友好，充满信任",
    (0.3, 0.7): "友善但保持一定距离",
    (0.0, 0.3): "冷淡疏远",
    (-1.0, 0.0): "充满敌意",
}
```

---

### 3.3 QuestSystem — 任务系统

**文件**: `feature/quest/system.py`

**职责**:
- 从模板创建任务
- 前置条件检查（等级/NPC关系/前置任务）
- 任务激活/完成

**关键方法**:
```python
def create_from_template(
    self, template_name: str, world_id: int, **variables
) -> Quest | None:
    """从模板创建任务（rescue/escort/collect/investigate/exterminate）"""

def check_prerequisites(
    self, quest: Quest, player_level: int = 1,
    npc_relationships: dict[str, float] | None = None,
    completed_quests: list[str] | None = None,
) -> tuple[bool, str]:
    """检查任务前置条件"""

def activate_quest(self, quest_id: int) -> bool:
    """激活任务（自动检查前置条件）"""

def complete_quest(self, quest_id: int) -> bool:
    """完成任务"""
```

**EventBus 事件**:
- `feature.quest.created` — 任务创建
- `feature.quest.activated` — 任务激活
- `feature.quest.activation_failed` — 激活失败
- `feature.quest.completed` — 任务完成

---

### 3.4 ItemSystem — 物品管理系统

**文件**: `feature/item/system.py`

**职责**:
- 给予/移除玩家物品
- 查询玩家物品栏

**关键方法**:
```python
def give_item(self, player_id: int, item_name: str, quantity: int = 1) -> dict:
def remove_item(self, player_id: int, item_name: str, quantity: int = 1) -> dict:
def get_inventory(self, player_id: int) -> list[dict]:
```

**EventBus 事件**:
- `feature.item.given` — 物品给予
- `feature.item.removed` — 物品移除

---

### 3.5 ExplorationSystem — 探索系统

**文件**: `feature/exploration/system.py`

**职责**:
- 地点探索（获取描述、NPC、出口）
- 玩家移动（方向导航）

**关键方法**:
```python
def explore_location(self, location_id: int, world_id: int) -> dict:
    """探索地点，返回 {name, description, npcs, exits}"""

def move_player(self, player_id: int, direction: str) -> dict:
    """移动玩家到相邻地点（north/south/east/west）"""
```

**EventBus 事件**:
- `feature.exploration.discovered` — 地点发现
- `feature.exploration.moved` — 玩家移动

---

### 3.6 NarrationSystem — 叙事增强系统

**文件**: `feature/narration/system.py`

**职责**:
- 从叙事中提取关键信息并存储为记忆
- 获取上下文记忆（用于注入 Prompt）

**关键方法**:
```python
def extract_and_store(
    self, narrative: str, world_id: int, turn: int
) -> int:
    """从叙事中提取信息并存储为 session 记忆"""

def get_context_memories(
    self, world_id: int, limit: int = 10, min_importance: float = 0.3
) -> str:
    """获取格式化的记忆上下文（用于 Prompt）"""
```

**EventBus 事件**:
- `feature.narration.stored` — 记忆存储

---

## 4. Feature 注册表

### 4.1 文件位置

`2workbench/feature/registry.py`

### 4.2 设计

全局单例模式，统一管理所有 Feature 模块：

```python
from feature.registry import feature_registry

# 注册
feature_registry.register(BattleSystem())
feature_registry.register(DialogueSystem())

# 启用全部
feature_registry.enable_all()

# 获取系统
battle = feature_registry.get("battle")

# 获取所有状态
states = feature_registry.get_all_states()
```

### 4.3 API

```python
class FeatureRegistry:
    def register(self, feature: BaseFeature) -> None: ...
    def unregister(self, name: str) -> None: ...
    def get(self, name: str) -> BaseFeature | None: ...
    def enable(self, name: str) -> bool: ...
    def disable(self, name: str) -> bool: ...
    def enable_all(self) -> None: ...
    def disable_all(self) -> None: ...
    def get_all_states(self) -> dict[str, dict]: ...
    def list_features(self) -> list[str]: ...
```

---

## 5. EventBus 事件命名规范

所有 Feature 事件遵循 `feature.{system}.{action}` 格式：

```
# Battle
feature.battle.started
feature.battle.round_completed
feature.battle.ended

# Dialogue
feature.dialogue.started

# Quest
feature.quest.created
feature.quest.activated
feature.quest.activation_failed
feature.quest.completed

# Item
feature.item.given
feature.item.removed

# Exploration
feature.exploration.discovered
feature.exploration.moved

# Narration
feature.narration.stored
```

---

## 6. 使用示例

### 6.1 完整集成示例

```python
from feature import feature_registry
from feature.battle import BattleSystem
from feature.dialogue import DialogueSystem
from feature.quest import QuestSystem

# 注册所有 Feature
feature_registry.register(BattleSystem(db_path=db_path))
feature_registry.register(DialogueSystem(db_path=db_path))
feature_registry.register(QuestSystem(db_path=db_path))

# 启用全部
feature_registry.enable_all()

# 使用
battle = feature_registry.get("battle")
state = battle.start_combat({...})

# 获取状态
states = feature_registry.get_all_states()

# 禁用全部
feature_registry.disable_all()
```

### 6.2 单独使用某个 Feature

```python
from feature.battle import BattleSystem

battle = BattleSystem(db_path=db_path)
battle.on_enable()

# 使用...

battle.on_disable()  # 自动清理 EventBus 订阅
```

---

## 7. 测试

### 7.1 各系统独立测试

每个 Feature 系统都可以独立测试，通过传入 `db_path` 参数使用临时数据库：

```python
import tempfile
from feature.battle import BattleSystem

with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp_db = f.name

battle = BattleSystem(db_path=tmp_db)
battle.on_enable()
# ... 测试 ...
battle.on_disable()
```

### 7.2 集成测试

所有 Feature 系统可以一起注册到 `feature_registry` 进行集成测试。

---

## 8. 注意事项

### 8.1 同层隔离

❌ **错误**（在 dialogue 中直接 import battle）:
```python
from feature.battle import BattleSystem  # 禁止！
```

✅ **正确**（通过 EventBus 通信）:
```python
self.emit("feature.battle.request", {...})
```

### 8.2 数据库路径

所有 Feature 系统通过构造函数接收 `db_path` 参数，不直接读取 `settings.database_path`。这样便于测试和灵活配置。

### 8.3 生命周期管理

- 必须在 `on_enable()` 中注册 EventBus 订阅
- `on_disable()` 会自动清理所有订阅，无需手动处理

---

## 9. 文件清单

```
2workbench/feature/
├── __init__.py              # 统一导出
├── base.py                  # Feature 基类
├── registry.py              # Feature 注册表
├── battle/
│   ├── __init__.py
│   └── system.py            # 战斗系统
├── dialogue/
│   ├── __init__.py
│   └── system.py            # NPC 对话系统
├── quest/
│   ├── __init__.py
│   └── system.py            # 任务系统
├── item/
│   ├── __init__.py
│   └── system.py            # 物品系统
├── exploration/
│   ├── __init__.py
│   └── system.py            # 探索系统
├── narration/
│   ├── __init__.py
│   └── system.py            # 叙事系统
└── skill/
    └── __init__.py          # 玩家技能系统（占位）
```

---

## 10. 依赖关系

```
feature.base
    ↓ 依赖
    foundation.event_bus
    foundation.logger

feature.battle
    ↓ 依赖
    feature.base
    core.calculators
    foundation.llm

feature.dialogue
    ↓ 依赖
    feature.base
    core.models
    foundation.llm

feature.quest
    ↓ 依赖
    feature.base
    core.models
    core.constants

feature.item
    ↓ 依赖
    feature.base
    core.models

feature.exploration
    ↓ 依赖
    feature.base
    core.models

feature.narration
    ↓ 依赖
    feature.base
    core.models
```

---

*文档版本: 1.0*
*最后更新: 2026-05-02*
