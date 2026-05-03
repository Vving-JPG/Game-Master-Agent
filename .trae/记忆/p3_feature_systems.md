# P3-02: Feature Systems 各子系统

> 模块: `feature.battle`, `feature.dialogue`, `feature.quest`, `feature.item`, `feature.exploration`, `feature.narration`
> 文件: `2workbench/feature/*/system.py`

---

## 战斗系统 (battle)

```python
from feature.battle.system import BattleSystem

battle = BattleSystem()
battle.start_combat(player, enemies)
battle.execute_turn(player_action)
battle.end_combat()
```

**功能**:
- 回合制战斗管理
- 伤害计算
- 技能释放
- 战斗日志

---

## 对话系统 (dialogue)

```python
from feature.dialogue.system import DialogueSystem

dialogue = DialogueSystem()
dialogue.start_dialogue(npc_id)
dialogue.player_say("你好")
response = dialogue.get_npc_response()
```

**功能**:
- NPC 对话管理
- 好感度系统
- 对话历史
- 上下文记忆

---

## 任务系统 (quest)

```python
from feature.quest.system import QuestSystem

quest = QuestSystem()
quest.accept_quest(quest_id)
quest.update_objective(objective_id, progress)
quest.complete_quest(quest_id)
```

**功能**:
- 任务接受/完成
- 目标追踪
- 奖励发放
- 任务链

---

## 物品系统 (item)

```python
from feature.item.system import ItemSystem

item_sys = ItemSystem()
item_sys.add_item(player_id, item_id, quantity)
item_sys.use_item(player_id, item_id)
item_sys.equip_item(player_id, item_id)
```

**功能**:
- 物品增删
- 使用/装备
- 物品效果
- 库存管理

---

## 探索系统 (exploration)

```python
from feature.exploration.system import ExplorationSystem

explore = ExplorationSystem()
explore.move_to(location_id)
explore.search()
explore.interact(object_id)
```

**功能**:
- 地点移动
- 搜索发现
- 环境交互
- 随机事件

---

## 叙事系统 (narration)

```python
from feature.narration.system import NarrationSystem

narration = NarrationSystem()
narration.generate_scene_description()
narration.generate_combat_narrative(action)
narration.generate_dialogue_narrative(npc_id, content)
```

**功能**:
- 场景描述生成
- 战斗叙事
- 对话叙事
- 氛围渲染
