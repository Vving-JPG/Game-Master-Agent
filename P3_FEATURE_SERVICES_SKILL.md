# P3: Feature 层 — 业务功能系统

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。
> **前置条件**: P0 Foundation + P1 Core + P2 LangGraph Agent 核心已全部完成。

## 项目概述

你正在帮助用户将 **Game Master Agent V2** 的 `2workbench/` 目录重构为**四层架构**。

- **技术**: Python 3.11+ / PyQt6 / SQLite / LangGraph / uv
- **包管理器**: uv
- **开发 IDE**: Trae
- **本 Phase 目标**: 实现 Feature 层各业务系统（Battle/Dialogue/Quest/Item/Exploration/Narration/Skill），从现有 service 中提取业务逻辑，封装为独立 Feature 模块。

### 架构约束

```
入口层 → Presentation (表现层) → Feature (功能层) → Core (核心层) → Foundation (基础层)
```

- ✅ Feature 层**只依赖** Core 和 Foundation 层
- ❌ Feature 层**绝对不能** import Presentation 层
- ✅ **同层模块间仅通过 EventBus 通信**，禁止直接 import 其他 Feature 模块
- ❌ 无循环依赖、无跨模块直调

### 本 Phase (P3) 范围

1. **Feature 基类** — 定义 Feature 模块的通用接口和生命周期
2. **BattleSystem** — 战斗系统（从 `_legacy/core/services/combat.py` + `combat_narrative.py` 提取）
3. **DialogueSystem** — NPC 对话系统（从 `_legacy/core/services/npc_dialog.py` 提取）
4. **QuestSystem** — 任务系统（从 `_legacy/core/services/story_coherence.py` 提取）
5. **ItemSystem** — 物品管理系统
6. **ExplorationSystem** — 探索系统
7. **NarrationSystem** — 叙事增强系统
8. **SkillSystem** — 技能系统（玩家技能，非 Agent Skill）
9. **Feature 注册表** — 统一管理所有 Feature 模块
10. **集成测试**

### 现有代码参考

| 现有文件（`_legacy/`） | 参考内容 | 改进方向 |
|---------|---------|---------|
| `_legacy/core/services/combat.py` | D&D 5e 简化战斗 | 提取为 BattleSystem，纯计算在 Core，LLM 叙事在 Feature |
| `_legacy/core/services/combat_narrative.py` | LLM 战斗叙事 | 集成到 BattleSystem |
| `_legacy/core/services/npc_dialog.py` | NPC 对话生成 | 提取为 DialogueSystem |
| `_legacy/core/services/story_coherence.py` | 剧情连贯性检查 | 提取为 QuestSystem |
| `_legacy/core/services/info_extractor.py` | 关键信息提取 | 提取为 NarrationSystem |
| `_legacy/core/services/pregenerator.py` | 预生成服务 | 集成到各系统 |
| `_legacy/core/services/ending_system.py` | 多结局系统 | 已在 Core calculators 中，Feature 层调用 |

### P0/P1/P2 产出（本 Phase 依赖）

```python
# Foundation
from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger
from foundation.database import get_db
from foundation.llm import LLMMessage, LLMResponse
from foundation.llm.model_router import model_router
from foundation.cache import llm_cache

# Core
from core.models import (
    World, Player, NPC, Item, Quest, Memory, Personality,
    WorldRepo, PlayerRepo, NPCRepo, ItemRepo, QuestRepo, MemoryRepo, LogRepo,
    QuestStatus, MemoryCategory, ItemType,
)
from core.state import AgentState, create_initial_state
from core.calculators import (
    Combatant, AttackResult, CombatResult,
    roll_dice, attack, combat_round, is_combat_over, calculate_rewards,
    EndingScore, calculate_ending_score, determine_ending, format_ending_narrative,
)
from core.constants import NPC_TEMPLATES, apply_template, generate_quest_from_template

# Feature AI
from feature.ai import GMAgent, parse_llm_output, PromptBuilder
from feature.ai.events import (
    TURN_START, TURN_END, AGENT_ERROR,
    LLM_STREAM_TOKEN, COMMAND_PARSED, COMMAND_EXECUTED,
)
```

---

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始"后，主动执行
4. **遇到错误先尝试修复**：3 次失败后再询问
5. **代码规范**：UTF-8，中文注释，PEP 8，类型注解
6. **同层隔离**：Feature 模块间禁止直接 import，必须通过 EventBus
7. **EventBus 命名**：`feature.{system_name}.{action}`，如 `feature.battle.started`

---

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **工作目录**: `2workbench/`
- **Feature 层**: `2workbench/feature/`
- **Legacy 参考**: `2workbench/_legacy/core/services/`

---

## 步骤

### Step 1: Feature 基类

**目的**: 定义所有 Feature 模块的通用接口、生命周期和 EventBus 集成模式。

**方案**:

1.1 创建 `2workbench/feature/base.py`：

```python
# 2workbench/feature/base.py
"""Feature 模块基类 — 定义通用接口和生命周期

所有 Feature 模块（Battle/Dialogue/Quest/...）继承此基类。
通过 EventBus 与其他模块通信，禁止直接依赖。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger


class BaseFeature(ABC):
    """Feature 模块基类

    生命周期:
    1. __init__ — 初始化（注册 EventBus 订阅）
    2. on_enable — 启用（加载资源、初始化状态）
    3. on_disable — 禁用（释放资源）
    4. on_event — 处理 EventBus 事件

    使用方式:
        class BattleSystem(BaseFeature):
            name = "battle"

            def handle_combat_start(self, event: Event):
                ...

            def on_enable(self):
                self.subscribe("feature.battle.start", self.handle_combat_start)
    """

    name: str = ""  # 子类必须设置

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path
        self._enabled = False
        self._subscriptions: list[tuple[str, Any]] = []
        self._logger = get_logger(f"feature.{self.name}")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def on_enable(self) -> None:
        """启用 Feature（子类重写以注册 EventBus 订阅）"""
        self._enabled = True
        self._logger.info(f"[{self.name}] 已启用")

    def on_disable(self) -> None:
        """禁用 Feature（子类重写以清理资源）"""
        self._enabled = False
        # 取消所有订阅
        for event_type, handler in self._subscriptions:
            event_bus.unsubscribe(event_type, handler)
        self._subscriptions.clear()
        self._logger.info(f"[{self.name}] 已禁用")

    def subscribe(self, event_type: str, handler) -> None:
        """订阅 EventBus 事件（记录以便清理）"""
        event_bus.subscribe(event_type, handler)
        self._subscriptions.append((event_type, handler))

    def emit(self, event_type: str, data: dict | None = None) -> list:
        """发出 EventBus 事件"""
        event = Event(
            type=event_type,
            data=data or {},
            source=f"feature.{self.name}",
        )
        return event_bus.emit(event)

    async def emit_async(self, event_type: str, data: dict | None = None) -> list:
        """异步发出 EventBus 事件"""
        event = Event(
            type=event_type,
            data=data or {},
            source=f"feature.{self.name}",
        )
        return await event_bus.emit_async(event)

    def get_state(self) -> dict[str, Any]:
        """获取 Feature 状态（用于 UI 展示）"""
        return {"name": self.name, "enabled": self._enabled}
```

1.2 测试：

```bash
cd 2workbench ; python -c "
from feature.base import BaseFeature

class TestFeature(BaseFeature):
    name = 'test'

    def on_enable(self):
        super().on_enable()
        self.subscribe('test.event', lambda e: None)

feature = TestFeature()
assert not feature.enabled
feature.on_enable()
assert feature.enabled
feature.on_disable()
assert not feature.enabled

state = feature.get_state()
assert state['name'] == 'test'

print('✅ Feature 基类测试通过')
"
```

**验收**:
- [ ] `feature/base.py` 创建完成
- [ ] 生命周期方法（enable/disable）
- [ ] EventBus 订阅/发布封装
- [ ] 测试通过

---

### Step 2: BattleSystem — 战斗系统

**目的**: 封装战斗逻辑，集成 Core 层的纯函数计算器 + LLM 叙事生成。

**参考**: `_legacy/core/services/combat.py` + `_legacy/core/services/combat_narrative.py`

**方案**:

2.1 创建 `2workbench/feature/battle/system.py`：

```python
# 2workbench/feature/battle/system.py
"""战斗系统 — 战斗流程管理 + LLM 叙事生成

职责:
1. 管理战斗生命周期（开始→轮次→结束）
2. 调用 Core 层纯函数进行战斗计算
3. 调用 LLM 生成战斗叙事
4. 通过 EventBus 通知其他模块

从 _legacy/core/services/combat.py + combat_narrative.py 重构。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from foundation.event_bus import event_bus, Event
from foundation.llm import LLMMessage
from foundation.llm.model_router import model_router
from foundation.logger import get_logger
from feature.base import BaseFeature
from core.calculators import (
    Combatant, AttackResult, CombatResult,
    attack, combat_round, is_combat_over, calculate_rewards,
)
from core.models import PlayerRepo, LogRepo

logger = get_logger(__name__)


@dataclass
class BattleState:
    """战斗状态"""
    active: bool = False
    player: Combatant | None = None
    enemies: list[Combatant] = field(default_factory=list)
    round_num: int = 0
    results: list[list[AttackResult]] = field(default_factory=list)
    victory: bool = False


class BattleSystem(BaseFeature):
    """战斗系统"""

    name = "battle"

    def on_enable(self) -> None:
        super().on_enable()
        # 订阅战斗相关事件
        self.subscribe("feature.ai.command.executed", self._on_command_executed)

    def _on_command_executed(self, event: Event) -> None:
        """监听 AI 层的命令执行，处理战斗相关命令"""
        result = event.get("result", {})
        intent = event.get("intent", "")
        if intent == "start_combat":
            self.start_combat(event.get("params", {}))

    def start_combat(self, params: dict[str, Any]) -> BattleState:
        """开始战斗

        Args:
            params: {"enemies": [{"name": "哥布林", "hp": 20, ...}], "player_id": 1}

        Returns:
            BattleState
        """
        self._state = BattleState(active=True)

        # 创建玩家战斗者
        player_data = params.get("player", {})
        self._state.player = Combatant(
            name=player_data.get("name", "冒险者"),
            hp=player_data.get("hp", 100),
            max_hp=player_data.get("max_hp", 100),
            attack_bonus=player_data.get("attack_bonus", 3),
            damage_dice=player_data.get("damage_dice", "1d8"),
            ac=player_data.get("ac", 15),
            is_player=True,
        )

        # 创建敌人
        for enemy_data in params.get("enemies", []):
            self._state.enemies.append(Combatant(
                name=enemy_data.get("name", "敌人"),
                hp=enemy_data.get("hp", 20),
                max_hp=enemy_data.get("max_hp", 20),
                attack_bonus=enemy_data.get("attack_bonus", 1),
                damage_dice=enemy_data.get("damage_dice", "1d6"),
                ac=enemy_data.get("ac", 10),
            ))

        self.emit("feature.battle.started", {
            "enemies": [e.name for e in self._state.enemies],
            "player_hp": self._state.player.hp,
        })

        logger.info(f"战斗开始: {self._state.player.name} vs {[e.name for e in self._state.enemies]}")
        return self._state

    def execute_round(self) -> list[AttackResult]:
        """执行一轮战斗

        Returns:
            本轮攻击结果列表
        """
        if not self._state.active or not self._state.player:
            return []

        self._state.round_num += 1
        results = combat_round(self._state.player, self._state.enemies)
        self._state.results.append(results)

        # 检查战斗是否结束
        if is_combat_over(self._state.player, self._state.enemies):
            self._state.active = False
            self._state.victory = self._state.player.hp > 0
            rewards = calculate_rewards(self._state.enemies)

            self.emit("feature.battle.ended", {
                "victory": self._state.victory,
                "rounds": self._state.round_num,
                "rewards": rewards,
                "player_hp": self._state.player.hp,
            })

            logger.info(
                f"战斗结束: {'胜利' if self._state.victory else '失败'} "
                f"({self._state.round_num} 轮)"
            )
        else:
            self.emit("feature.battle.round_completed", {
                "round": self._state.round_num,
                "player_hp": self._state.player.hp,
                "enemies_alive": sum(1 for e in self._state.enemies if e.hp > 0),
            })

        return results

    async def generate_narrative(self, results: list[AttackResult]) -> str:
        """用 LLM 生成战斗叙事

        Args:
            results: 攻击结果列表

        Returns:
            战斗叙事文本
        """
        # 构建战斗数据描述
        combat_data = []
        for r in results:
            combat_data.append(
                f"- {r.attacker} {'暴击！' if r.is_crit else ''}{'命中' if r.hit else '未命中'} "
                f"{r.defender}，{'造成' if r.hit else ''} {r.damage} 点伤害"
            )

        prompt = (
            "你是一个游戏主持人。请根据以下战斗数据，生成 2-3 句生动的中文战斗叙事：\n\n"
            + "\n".join(combat_data)
            + "\n\n要求: 简洁有力，突出关键动作和结果。"
        )

        try:
            client, config = model_router.route(content="战斗叙事")
            response = await client.chat_async(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=0.8,
            )
            return response.content
        except Exception as e:
            logger.error(f"战斗叙事生成失败: {e}")
            # 降级: 使用纯文本拼接
            return "；".join(r.narrative for r in results)

    def get_state(self) -> dict[str, Any]:
        """获取战斗状态"""
        base = super().get_state()
        if hasattr(self, "_state"):
            base.update({
                "active": self._state.active,
                "round": self._state.round_num,
                "player_hp": self._state.player.hp if self._state.player else 0,
                "enemies": [
                    {"name": e.name, "hp": e.hp, "max_hp": e.max_hp}
                    for e in self._state.enemies
                ],
                "victory": self._state.victory,
            })
        return base
```

2.2 创建 `2workbench/feature/battle/__init__.py`：

```python
# 2workbench/feature/battle/__init__.py
"""战斗系统"""
from feature.battle.system import BattleSystem, BattleState

__all__ = ["BattleSystem", "BattleState"]
```

2.3 测试：

```bash
cd 2workbench ; python -c "
import random
random.seed(42)

from feature.battle import BattleSystem

system = BattleSystem()
system.on_enable()

# 开始战斗
state = system.start_combat({
    'player': {'name': '冒险者', 'hp': 100, 'max_hp': 100, 'attack_bonus': 5, 'damage_dice': '1d10', 'ac': 16},
    'enemies': [
        {'name': '哥布林', 'hp': 15, 'max_hp': 15, 'attack_bonus': 1, 'damage_dice': '1d4', 'ac': 10},
        {'name': '哥布林首领', 'hp': 30, 'max_hp': 30, 'attack_bonus': 3, 'damage_dice': '1d6', 'ac': 12},
    ],
})

assert state.active
assert len(state.enemies) == 2

# 执行战斗直到结束
while state.active:
    results = system.execute_round()
    for r in results:
        print(f'  {r.narrative}')

print(f'战斗结束: 胜利={state.victory}, 轮数={state.round_num}')

# 获取状态
battle_state = system.get_state()
assert 'active' in battle_state
assert 'enemies' in battle_state

system.on_disable()
print('✅ BattleSystem 测试通过')
"
```

**验收**:
- [ ] `feature/battle/system.py` 创建完成
- [ ] 战斗生命周期（开始→轮次→结束）
- [ ] LLM 叙事生成（带降级）
- [ ] EventBus 事件通知
- [ ] 测试通过

---

### Step 3: DialogueSystem — NPC 对话系统

**目的**: 封装 NPC 对话生成逻辑，集成大五人格和关系值。

**参考**: `_legacy/core/services/npc_dialog.py`

**方案**:

3.1 创建 `2workbench/feature/dialogue/system.py`：

```python
# 2workbench/feature/dialogue/system.py
"""NPC 对话系统 — 基于性格的对话生成

职责:
1. 根据 NPC 性格和关系值生成对话
2. 管理对话历史
3. 通过 EventBus 通知对话事件

从 _legacy/core/services/npc_dialog.py 重构。
"""
from __future__ import annotations

from typing import Any

from foundation.event_bus import event_bus, Event
from foundation.llm import LLMMessage
from foundation.llm.model_router import model_router
from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import NPCRepo, LogRepo, MemoryRepo, NPC, Personality

logger = get_logger(__name__)


# 关系值 → 关系描述
RELATIONSHIP_MAP = {
    (0.7, 1.0): "非常友好，充满信任",
    (0.3, 0.7): "友善但保持一定距离",
    (0.0, 0.3): "冷淡疏远",
    (-1.0, 0.0): "充满敌意",
}


class DialogueSystem(BaseFeature):
    """NPC 对话系统"""

    name = "dialogue"

    def on_enable(self) -> None:
        super().on_enable()
        self.subscribe("feature.ai.command.executed", self._on_command_executed)

    def _on_command_executed(self, event: Event) -> None:
        """监听对话命令"""
        intent = event.get("intent", "")
        if intent == "npc_talk":
            self.handle_dialogue(event.get("params", {}))

    def build_npc_context(self, npc: NPC, player_relationship: float = 0.0) -> str:
        """构建 NPC 上下文描述

        Args:
            npc: NPC 数据
            player_relationship: 与玩家的关系值

        Returns:
            NPC 上下文文本
        """
        # 关系描述
        relation_desc = "陌生人"
        for (low, high), desc in RELATIONSHIP_MAP.items():
            if low <= player_relationship < high:
                relation_desc = desc
                break

        # 大五人格描述
        personality = npc.personality
        trait_desc = (
            f"开放性:{personality.openness:.1f} 尽责性:{personality.conscientiousness:.1f} "
            f"外向性:{personality.extraversion:.1f} 宜人性:{personality.agreeableness:.1f} "
            f"神经质:{personality.neuroticism:.1f}"
        )

        return (
            f"## NPC: {npc.name}\n"
            f"- 性格: {trait_desc}\n"
            f"- 心情: {npc.mood}\n"
            f"- 说话风格: {npc.speech_style}\n"
            f"- 背景: {npc.backstory}\n"
            f"- 目标: {', '.join(npc.goals)}\n"
            f"- 对玩家的态度: {relation_desc} (关系值: {player_relationship:.1f})\n"
        )

    async def generate_dialogue(
        self,
        npc: NPC,
        player_input: str,
        player_name: str = "冒险者",
        dialogue_history: list[dict] | None = None,
    ) -> str:
        """生成 NPC 对话

        Args:
            npc: NPC 数据
            player_input: 玩家输入
            player_name: 玩家名称
            dialogue_history: 对话历史

        Returns:
            NPC 回复文本
        """
        context = self.build_npc_context(npc)

        # 构建消息
        messages = [
            LLMMessage(role="system", content=(
                f"你正在扮演 NPC「{npc.name}」。请根据以下角色设定与玩家对话。\n"
                f"保持角色的性格和说话风格，不要出戏。\n\n{context}"
            )),
        ]

        # 添加对话历史
        if dialogue_history:
            for turn in dialogue_history[-10:]:  # 最近 10 轮
                messages.append(LLMMessage(role=turn["role"], content=turn["content"]))

        # 添加当前输入
        messages.append(LLMMessage(role="user", content=f"{player_name}: {player_input}"))

        try:
            client, config = model_router.route(content=player_input)
            response = await client.chat_async(
                messages=messages,
                temperature=0.8,
            )
            return response.content
        except Exception as e:
            logger.error(f"NPC 对话生成失败 ({npc.name}): {e}")
            return f"[{npc.name} 沉默不语...]"

    def handle_dialogue(self, params: dict[str, Any]) -> None:
        """处理对话事件（同步入口，实际生成是异步的）"""
        npc_name = params.get("npc_name", "")
        player_input = params.get("player_input", "")

        self.emit("feature.dialogue.started", {
            "npc_name": npc_name,
            "player_input": player_input,
        })

        logger.info(f"对话开始: 玩家 -> {npc_name}: {player_input[:50]}")

    def get_state(self) -> dict[str, Any]:
        base = super().get_state()
        base["dialogue_count"] = 0  # TODO: 从数据库统计
        return base
```

3.2 创建 `2workbench/feature/dialogue/__init__.py`：

```python
# 2workbench/feature/dialogue/__init__.py
"""NPC 对话系统"""
from feature.dialogue.system import DialogueSystem

__all__ = ["DialogueSystem"]
```

3.3 测试：

```bash
cd 2workbench ; python -c "
from feature.dialogue import DialogueSystem
from core.models import NPC, Personality

system = DialogueSystem()
system.on_enable()

# 测试上下文构建
npc = NPC(
    name='老村长',
    personality=Personality(openness=0.8, extraversion=0.4, agreeableness=0.8),
    mood='serene',
    speech_style='温和、睿智',
    backstory='守护村庄五十年的老人',
    goals=['守护知识', '引导后辈'],
)

context = system.build_npc_context(npc, player_relationship=0.6)
assert '老村长' in context
assert '友善' in context
print(context[:200])

system.on_disable()
print('✅ DialogueSystem 测试通过')
"
```

**验收**:
- [ ] `feature/dialogue/system.py` 创建完成
- [ ] NPC 上下文构建（性格+关系+目标）
- [ ] LLM 对话生成（带降级）
- [ ] 测试通过

---

### Step 4: QuestSystem — 任务系统

**目的**: 封装任务生命周期管理、前置条件检查、分支选择。

**参考**: `_legacy/core/services/story_coherence.py`

**方案**:

4.1 创建 `2workbench/feature/quest/system.py`：

```python
# 2workbench/feature/quest/system.py
"""任务系统 — 任务生命周期管理

职责:
1. 任务创建（从模板或自定义）
2. 前置条件检查
3. 任务进度追踪
4. 分支选择处理
5. 任务完成/失败判定

从 _legacy/core/services/story_coherence.py 重构。
"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import QuestRepo, QuestStep, Quest, QuestStatus
from core.constants import generate_quest_from_template

logger = get_logger(__name__)


class QuestSystem(BaseFeature):
    """任务系统"""

    name = "quest"

    def on_enable(self) -> None:
        super().on_enable()
        self.subscribe("feature.ai.command.executed", self._on_command_executed)

    def _on_command_executed(self, event: Event) -> None:
        intent = event.get("intent", "")
        if intent in ("update_quest_status", "check_quest_prerequisites"):
            self.handle_quest_command(intent, event.get("params", {}))

    def create_from_template(
        self,
        template_name: str,
        world_id: int,
        **variables,
    ) -> Quest | None:
        """从模板创建任务

        Args:
            template_name: 模板名称（rescue/escort/collect/investigate/exterminate）
            world_id: 世界 ID
            **variables: 模板变量

        Returns:
            Quest 对象
        """
        try:
            quest_data = generate_quest_from_template(template_name, **variables)
            repo = QuestRepo()
            quest = repo.create(
                world_id=world_id,
                title=quest_data["title"],
                description=quest_data["description"],
                quest_type="side",
                status="not_started",
                branches=quest_data.get("branches", {}),
            )
            self.emit("feature.quest.created", {
                "quest_id": quest.id,
                "title": quest.title,
                "template": template_name,
            })
            logger.info(f"任务创建: [{quest.title}] (模板: {template_name})")
            return quest
        except Exception as e:
            logger.error(f"任务创建失败: {e}")
            return None

    def check_prerequisites(
        self,
        quest: Quest,
        player_level: int = 1,
        npc_relationships: dict[str, float] | None = None,
        completed_quests: list[str] | None = None,
    ) -> tuple[bool, str]:
        """检查任务前置条件

        Returns:
            (是否满足, 原因描述)
        """
        prereqs = quest.prerequisites if isinstance(quest.prerequisites, dict) else {}

        # 等级检查
        level_req = prereqs.get("level", 0)
        if player_level < level_req:
            return False, f"等级不足: 需要 {level_req} 级，当前 {player_level} 级"

        # NPC 关系检查
        npc_req = prereqs.get("npc_relationship", {})
        if npc_req and npc_relationships:
            for npc_name, min_rel in npc_req.items():
                actual = npc_relationships.get(npc_name, 0)
                if actual < min_rel:
                    return False, f"与 {npc_name} 的关系不足: 需要 {min_rel}，当前 {actual:.1f}"

        # 前置任务检查
        prev_quests = prereqs.get("completed_quests", [])
        if prev_quests and completed_quests:
            for prev in prev_quests:
                if prev not in completed_quests:
                    return False, f"前置任务未完成: {prev}"

        return True, "条件满足"

    def activate_quest(self, quest_id: int) -> bool:
        """激活任务"""
        repo = QuestRepo()
        # 先检查前置条件
        quest = repo.get_by_id(quest_id)
        if not quest:
            return False

        ok, reason = self.check_prerequisites(quest)
        if not ok:
            logger.warning(f"任务激活失败 ({quest.title}): {reason}")
            self.emit("feature.quest.activation_failed", {
                "quest_id": quest_id, "reason": reason,
            })
            return False

        repo.update_status(quest_id, "active")
        self.emit("feature.quest.activated", {"quest_id": quest_id, "title": quest.title})
        logger.info(f"任务激活: [{quest.title}]")
        return True

    def complete_quest(self, quest_id: int) -> bool:
        """完成任务"""
        repo = QuestRepo()
        repo.update_status(quest_id, "completed")
        quest = repo.get_by_id(quest_id)
        if quest:
            self.emit("feature.quest.completed", {
                "quest_id": quest_id,
                "title": quest.title,
                "rewards": quest.rewards,
            })
            logger.info(f"任务完成: [{quest.title}]")
        return True

    def handle_quest_command(self, intent: str, params: dict) -> None:
        """处理任务相关命令"""
        if intent == "update_quest_status":
            quest_id = params.get("quest_id", 0)
            status = params.get("status", "")
            if quest_id and status:
                if status == "completed":
                    self.complete_quest(quest_id)
                else:
                    QuestRepo().update_status(quest_id, status)

    def get_active_quests(self, world_id: int, player_id: int | None = None) -> list[Quest]:
        """获取活跃任务列表"""
        repo = QuestRepo()
        if player_id:
            quests = repo.get_by_player(player_id)
        else:
            quests = []
        return [q for q in quests if q.status == "active"]

    def get_state(self) -> dict[str, Any]:
        base = super().get_state()
        return base
```

4.2 创建 `2workbench/feature/quest/__init__.py`：

```python
# 2workbench/feature/quest/__init__.py
"""任务系统"""
from feature.quest.system import QuestSystem

__all__ = ["QuestSystem"]
```

4.3 测试：

```bash
cd 2workbench ; python -c "
from feature.quest import QuestSystem
from core.models import Quest, QuestStatus
import tempfile, os

with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp_db = f.name

try:
    from foundation.database import init_db
    init_db(db_path=tmp_db)

    system = QuestSystem(db_path=tmp_db)
    system.on_enable()

    # 创建任务
    quest = system.create_from_template('rescue', world_id=1, target='公主', enemy='恶龙', location='龙巢')
    assert quest is not None
    assert quest.title != ''

    # 检查前置条件
    ok, reason = system.check_prerequisites(quest, player_level=1)
    assert ok

    # 等级不足
    ok2, reason2 = system.check_prerequisites(quest, player_level=1)
    # 默认模板无等级要求，所以应该通过

    system.on_disable()
    print('✅ QuestSystem 测试通过')
finally:
    os.unlink(tmp_db)
"
```

**验收**:
- [ ] `feature/quest/system.py` 创建完成
- [ ] 从模板创建任务
- [ ] 前置条件检查（等级/关系/前置任务）
- [ ] 任务激活/完成
- [ ] 测试通过

---

### Step 5: ItemSystem + ExplorationSystem + NarrationSystem

**目的**: 实现剩余的 Feature 模块。

**方案**:

5.1 创建 `2workbench/feature/item/system.py`：

```python
# 2workbench/feature/item/system.py
"""物品管理系统"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import ItemRepo, PlayerRepo, Item, ItemType, ItemRarity

logger = get_logger(__name__)


class ItemSystem(BaseFeature):
    """物品管理系统"""

    name = "item"

    def give_item(self, player_id: int, item_name: str, quantity: int = 1, db_path: str | None = None) -> dict:
        """给予玩家物品"""
        repo = ItemRepo()
        db = db_path or self._db_path

        # 查找或创建物品
        items = repo.search(item_name, db_path=db)
        if items:
            item = items[0]
        else:
            item = repo.create(name=item_name, item_type="misc", db_path=db)

        # 添加到玩家物品栏
        player_repo = PlayerRepo()
        player_repo.add_item(player_id, item.id, quantity, db_path=db)

        self.emit("feature.item.given", {
            "player_id": player_id,
            "item_name": item_name,
            "quantity": quantity,
        })
        return {"success": True, "item": item_name, "quantity": quantity}

    def remove_item(self, player_id: int, item_name: str, quantity: int = 1, db_path: str | None = None) -> dict:
        """移除玩家物品"""
        repo = ItemRepo()
        db = db_path or self._db_path
        items = repo.search(item_name, db_path=db)

        if not items:
            return {"success": False, "error": f"物品不存在: {item_name}"}

        player_repo = PlayerRepo()
        player_repo.remove_item(player_id, items[0].id, quantity, db_path=db)

        self.emit("feature.item.removed", {
            "player_id": player_id,
            "item_name": item_name,
            "quantity": quantity,
        })
        return {"success": True, "item": item_name, "quantity": quantity}

    def get_inventory(self, player_id: int, db_path: str | None = None) -> list[dict]:
        """获取玩家物品栏"""
        player_repo = PlayerRepo()
        items = player_repo.get_inventory(player_id, db_path=db_path or self._db_path)
        return [{"name": i.item_name if hasattr(i, 'item_name') else str(i), "quantity": i.quantity} for i in items]
```

5.2 创建 `2workbench/feature/exploration/system.py`：

```python
# 2workbench/feature/exploration/system.py
"""探索系统 — 地点发现与移动"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import LocationRepo, NPCRepo, PlayerRepo

logger = get_logger(__name__)


class ExplorationSystem(BaseFeature):
    """探索系统"""

    name = "exploration"

    def explore_location(self, location_id: int, world_id: int, db_path: str | None = None) -> dict:
        """探索地点

        Returns:
            地点信息（描述、NPC、出口）
        """
        db = db_path or self._db_path
        loc_repo = LocationRepo()
        npc_repo = NPCRepo()

        location = loc_repo.get_by_id(location_id, db_path=db)
        if not location:
            return {"error": f"地点不存在: {location_id}"}

        npcs = npc_repo.get_by_location(location_id, db_path=db)
        exits = list(location.connections.keys()) if location.connections else []

        result = {
            "name": location.name,
            "description": location.description,
            "npcs": [{"name": n.name, "mood": n.mood} for n in npcs],
            "exits": exits,
        }

        self.emit("feature.exploration.discovered", {
            "location_id": location_id,
            "location_name": location.name,
            "npcs_found": len(npcs),
        })

        return result

    def move_player(self, player_id: int, direction: str, db_path: str | None = None) -> dict:
        """移动玩家到相邻地点

        Args:
            direction: 方向（north/south/east/west）
        """
        db = db_path or self._db_path
        player_repo = PlayerRepo()
        loc_repo = LocationRepo()

        player = player_repo.get_by_id(player_id, db_path=db)
        if not player:
            return {"error": "玩家不存在"}

        current_loc = loc_repo.get_by_id(player.location_id, db_path=db)
        if not current_loc or direction not in current_loc.connections:
            return {"error": f"无法向 {direction} 移动"}

        new_loc_id = current_loc.connections[direction]
        player_repo.update(player_id, location_id=new_loc_id, db_path=db)

        new_loc = loc_repo.get_by_id(new_loc_id, db_path=db)
        self.emit("feature.exploration.moved", {
            "player_id": player_id,
            "from": current_loc.name,
            "to": new_loc.name if new_loc else "未知",
            "direction": direction,
        })

        return {"success": True, "location": new_loc.name if new_loc else "未知"}
```

5.3 创建 `2workbench/feature/narration/system.py`：

```python
# 2workbench/feature/narration/system.py
"""叙事增强系统 — 信息提取 + 记忆管理"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import MemoryRepo, MemoryCategory

logger = get_logger(__name__)


class NarrationSystem(BaseFeature):
    """叙事增强系统"""

    name = "narration"

    def extract_and_store(self, narrative: str, world_id: int, turn: int, db_path: str | None = None) -> int:
        """从叙事中提取关键信息并存储为记忆

        简化版: 将整段叙事存储为 session 类别记忆。
        完整版应使用 LLM 提取结构化信息（从 _legacy/core/services/info_extractor.py）。

        Returns:
            存储的记忆数
        """
        db = db_path or self._db_path
        repo = MemoryRepo()

        # 简化: 存储为 session 记忆
        repo.store(
            world_id=world_id,
            category="session",
            source="narration",
            content=narrative,
            importance=0.5,
            turn=turn,
            db_path=db,
        )

        self.emit("feature.narration.stored", {
            "world_id": world_id,
            "turn": turn,
            "length": len(narrative),
        })

        return 1

    def get_context_memories(
        self,
        world_id: int,
        limit: int = 10,
        min_importance: float = 0.3,
        db_path: str | None = None,
    ) -> str:
        """获取上下文记忆（用于注入 Prompt）

        Returns:
            格式化的记忆文本
        """
        db = db_path or self._db_path
        repo = MemoryRepo()
        memories = repo.recall(world_id=world_id, min_importance=min_importance, limit=limit, db_path=db)

        if not memories:
            return ""

        parts = ["## 相关记忆\n"]
        for mem in memories:
            source = mem.source or "未知"
            parts.append(f"- [{source}] {mem.content[:100]}")

        return "\n".join(parts)
```

5.4 创建各模块的 `__init__.py`：

```python
# 2workbench/feature/item/__init__.py
from feature.item.system import ItemSystem
__all__ = ["ItemSystem"]

# 2workbench/feature/exploration/__init__.py
from feature.exploration.system import ExplorationSystem
__all__ = ["ExplorationSystem"]

# 2workbench/feature/narration/__init__.py
from feature.narration.system import NarrationSystem
__all__ = ["NarrationSystem"]
```

5.5 创建 `2workbench/feature/skill/__init__.py`（占位）：

```python
# 2workbench/feature/skill/__init__.py
"""玩家技能系统（占位，后续 Phase 实现）"""
# TODO: P4/P5 阶段实现玩家技能树、技能升级等
```

5.6 测试：

```bash
cd 2workbench ; python -c "
from feature.item import ItemSystem
from feature.exploration import ExplorationSystem
from feature.narration import NarrationSystem
import tempfile, os

with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp_db = f.name

try:
    from foundation.database import init_db
    init_db(db_path=tmp_db)

    # ItemSystem
    item_sys = ItemSystem(db_path=tmp_db)
    item_sys.on_enable()
    print('✅ ItemSystem 初始化成功')

    # ExplorationSystem
    expl_sys = ExplorationSystem(db_path=tmp_db)
    expl_sys.on_enable()
    print('✅ ExplorationSystem 初始化成功')

    # NarrationSystem
    narr_sys = NarrationSystem(db_path=tmp_db)
    narr_sys.on_enable()
    count = narr_sys.extract_and_store('玩家探索了幽暗森林，发现了一个隐藏的洞穴。', world_id=1, turn=5, db_path=tmp_db)
    assert count == 1
    context = narr_sys.get_context_memories(world_id=1, db_path=tmp_db)
    assert '幽暗森林' in context
    print('✅ NarrationSystem 初始化成功')

    # 清理
    item_sys.on_disable()
    expl_sys.on_disable()
    narr_sys.on_disable()

    print('✅ 所有 Feature 系统测试通过')
finally:
    os.unlink(tmp_db)
"
```

**验收**:
- [ ] `feature/item/system.py` — 物品给予/移除/查询
- [ ] `feature/exploration/system.py` — 地点探索/玩家移动
- [ ] `feature/narration/system.py` — 信息提取/记忆管理
- [ ] 所有 `__init__.py` 创建完成
- [ ] 测试通过

---

### Step 6: Feature 注册表

**目的**: 统一管理所有 Feature 模块的启用/禁用和状态查询。

**方案**:

6.1 创建 `2workbench/feature/registry.py`：

```python
# 2workbench/feature/registry.py
"""Feature 注册表 — 统一管理所有 Feature 模块

使用方式:
    from feature.registry import feature_registry

    # 注册
    feature_registry.register(BattleSystem())
    feature_registry.register(DialogueSystem())

    # 启用全部
    feature_registry.enable_all()

    # 获取某个系统
    battle = feature_registry.get("battle")

    # 获取所有状态
    states = feature_registry.get_all_states()
"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from feature.base import BaseFeature

logger = get_logger(__name__)


class FeatureRegistry:
    """Feature 注册表"""

    def __init__(self):
        self._features: dict[str, BaseFeature] = {}

    def register(self, feature: BaseFeature) -> None:
        """注册 Feature 模块"""
        name = feature.name
        if name in self._features:
            logger.warning(f"Feature 已存在，将被覆盖: {name}")
        self._features[name] = feature
        logger.debug(f"Feature 注册: {name}")

    def unregister(self, name: str) -> None:
        """注销 Feature 模块"""
        if name in self._features:
            self._features[name].on_disable()
            del self._features[name]
            logger.debug(f"Feature 注销: {name}")

    def get(self, name: str) -> BaseFeature | None:
        """获取 Feature 模块"""
        return self._features.get(name)

    def enable(self, name: str) -> bool:
        """启用指定 Feature"""
        feature = self._features.get(name)
        if feature:
            feature.on_enable()
            return True
        return False

    def disable(self, name: str) -> bool:
        """禁用指定 Feature"""
        feature = self._features.get(name)
        if feature:
            feature.on_disable()
            return True
        return False

    def enable_all(self) -> None:
        """启用所有 Feature"""
        for name, feature in self._features.items():
            feature.on_enable()
        logger.info(f"已启用 {len(self._features)} 个 Feature")

    def disable_all(self) -> None:
        """禁用所有 Feature"""
        for name, feature in self._features.items():
            feature.on_disable()
        logger.info(f"已禁用 {len(self._features)} 个 Feature")

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """获取所有 Feature 的状态"""
        return {
            name: feature.get_state()
            for name, feature in self._features.items()
        }

    def list_features(self) -> list[str]:
        """列出所有已注册的 Feature"""
        return list(self._features.keys())


# 全局单例
feature_registry = FeatureRegistry()
```

6.2 更新 `2workbench/feature/__init__.py`：

```python
# 2workbench/feature/__init__.py
"""Feature 层 — 业务功能集合"""
from feature.base import BaseFeature
from feature.registry import FeatureRegistry, feature_registry
from feature.battle import BattleSystem
from feature.dialogue import DialogueSystem
from feature.quest import QuestSystem
from feature.item import ItemSystem
from feature.exploration import ExplorationSystem
from feature.narration import NarrationSystem

__all__ = [
    "BaseFeature",
    "FeatureRegistry", "feature_registry",
    "BattleSystem",
    "DialogueSystem",
    "QuestSystem",
    "ItemSystem",
    "ExplorationSystem",
    "NarrationSystem",
]
```

6.3 测试：

```bash
cd 2workbench ; python -c "
from feature import (
    feature_registry, BaseFeature,
    BattleSystem, DialogueSystem, QuestSystem,
    ItemSystem, ExplorationSystem, NarrationSystem,
)

# 注册所有 Feature
feature_registry.register(BattleSystem())
feature_registry.register(DialogueSystem())
feature_registry.register(QuestSystem())
feature_registry.register(ItemSystem())
feature_registry.register(ExplorationSystem())
feature_registry.register(NarrationSystem())

# 列出
names = feature_registry.list_features()
assert len(names) == 6
print(f'已注册 Feature: {names}')

# 启用全部
feature_registry.enable_all()

# 获取状态
states = feature_registry.get_all_states()
for name, state in states.items():
    assert state['enabled']
    print(f'  {name}: enabled={state[\"enabled\"]}')

# 禁用全部
feature_registry.disable_all()

# 获取单个
battle = feature_registry.get('battle')
assert battle is not None
assert not battle.enabled

print('✅ Feature 注册表测试通过')
"
```

**验收**:
- [ ] `feature/registry.py` 创建完成
- [ ] 全局单例 `feature_registry`
- [ ] 注册/启用/禁用/状态查询
- [ ] 测试通过

---

### Step 7: Feature 层集成测试

**目的**: 验证所有 Feature 模块协同工作。

**方案**:

7.1 创建 `2workbench/tests/test_feature_integration.py`：

```bash
cd 2workbench ; python -c "
import tempfile, os, random
random.seed(42)

from foundation.database import init_db
from feature import feature_registry
from feature.battle import BattleSystem
from feature.dialogue import DialogueSystem
from feature.quest import QuestSystem
from feature.item import ItemSystem
from feature.exploration import ExplorationSystem
from feature.narration import NarrationSystem
from core.models import (
    WorldRepo, PlayerRepo, NPCRepo, LocationRepo, ItemRepo,
    MemoryRepo, LogRepo, NPC, Personality,
)

with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp_db = f.name

try:
    init_db(db_path=tmp_db)

    # 创建测试数据
    world_repo = WorldRepo()
    world = world_repo.create(name='测试世界', db_path=tmp_db)

    loc_repo = LocationRepo()
    village = loc_repo.create(world_id=world.id, name='宁静村', connections={'north': 0}, db_path=tmp_db)
    forest = loc_repo.create(world_id=world.id, name='幽暗森林', connections={'south': village.id}, db_path=tmp_db)

    player_repo = PlayerRepo()
    player = player_repo.create(world_id=world.id, name='冒险者', location_id=village.id, db_path=tmp_db)

    npc_repo = NPCRepo()
    elder = npc_repo.create(world_id=world.id, name='老村长', location_id=village.id,
                             personality={'openness': 0.8, 'agreeableness': 0.8}, db_path=tmp_db)

    item_repo = ItemRepo()
    sword = item_repo.create(name='木剑', item_type='weapon', stats={'attack': 5}, db_path=tmp_db)

    # 注册并启用所有 Feature
    feature_registry.register(BattleSystem(db_path=tmp_db))
    feature_registry.register(DialogueSystem(db_path=tmp_db))
    feature_registry.register(QuestSystem(db_path=tmp_db))
    feature_registry.register(ItemSystem(db_path=tmp_db))
    feature_registry.register(ExplorationSystem(db_path=tmp_db))
    feature_registry.register(NarrationSystem(db_path=tmp_db))
    feature_registry.enable_all()

    # 测试战斗系统
    battle = feature_registry.get('battle')
    battle_state = battle.start_combat({
        'player': {'name': '冒险者', 'hp': 100, 'max_hp': 100, 'attack_bonus': 5, 'damage_dice': '1d10', 'ac': 16},
        'enemies': [{'name': '史莱姆', 'hp': 10, 'max_hp': 10, 'attack_bonus': 0, 'damage_dice': '1d4', 'ac': 8}],
    })
    while battle_state.active:
        battle.execute_round()
    print(f'战斗: 胜利={battle_state.victory}, 轮数={battle_state.round_num}')

    # 测试物品系统
    item_sys = feature_registry.get('item')
    item_sys.give_item(player.id, '木剑', db_path=tmp_db)
    inv = item_sys.get_inventory(player.id, db_path=tmp_db)
    assert len(inv) >= 1
    print(f'物品栏: {inv}')

    # 测试探索系统
    expl_sys = feature_registry.get('exploration')
    info = expl_sys.explore_location(village.id, world.id, db_path=tmp_db)
    assert info['name'] == '宁静村'
    print(f'探索: {info[\"name\"]}, NPC: {[n[\"name\"] for n in info[\"npcs\"]]}')

    # 测试叙事系统
    narr_sys = feature_registry.get('narration')
    narr_sys.extract_and_store('冒险者在宁静村遇到了老村长。', world_id=world.id, turn=1, db_path=tmp_db)
    context = narr_sys.get_context_memories(world_id=world.id, db_path=tmp_db)
    assert '宁静村' in context
    print(f'记忆上下文: {context[:100]}')

    # 测试对话系统
    dialog_sys = feature_registry.get('dialogue')
    npc_data = npc_repo.get_by_id(elder.id, db_path=tmp_db)
    ctx = dialog_sys.build_npc_context(npc_data, player_relationship=0.5)
    assert '老村长' in ctx
    print(f'NPC 上下文: {ctx[:100]}')

    # 获取所有状态
    states = feature_registry.get_all_states()
    for name, state in states.items():
        print(f'  {name}: {state.get(\"enabled\", False)}')

    feature_registry.disable_all()
    print('✅ Feature 层集成测试通过')

finally:
    os.unlink(tmp_db)
"
```

**验收**:
- [ ] 6 个 Feature 系统全部注册并启用
- [ ] 战斗系统完整流程（开始→轮次→结束）
- [ ] 物品系统（给予+查询）
- [ ] 探索系统（地点探索）
- [ ] 叙事系统（记忆存储+上下文获取）
- [ ] 对话系统（NPC 上下文构建）
- [ ] Feature 注册表状态查询
- [ ] 测试通过

---

## 注意事项

### 同层隔离

Feature 模块间**禁止直接 import**。例如：
- ❌ `from feature.battle import BattleSystem`（在 dialogue 中）
- ✅ 通过 EventBus 通信：`self.emit("feature.battle.request", {...})`

### EventBus 事件命名

所有 Feature 事件遵循 `feature.{system}.{action}` 格式：
```
feature.battle.started / feature.battle.ended / feature.battle.round_completed
feature.dialogue.started / feature.dialogue.response
feature.quest.created / feature.quest.activated / feature.quest.completed
feature.item.given / feature.item.removed
feature.exploration.discovered / feature.exploration.moved
feature.narration.stored
```

### 数据库路径

所有 Feature 系统通过构造函数接收 `db_path` 参数，不直接读取 `settings.database_path`。这样便于测试和灵活配置。

---

## 完成检查清单

- [ ] Step 1: Feature 基类（生命周期 + EventBus 集成）
- [ ] Step 2: BattleSystem（战斗流程 + LLM 叙事）
- [ ] Step 3: DialogueSystem（NPC 对话 + 性格系统）
- [ ] Step 4: QuestSystem（任务生命周期 + 前置条件）
- [ ] Step 5: ItemSystem + ExplorationSystem + NarrationSystem
- [ ] Step 6: Feature 注册表（统一管理）
- [ ] Step 7: Feature 层集成测试
