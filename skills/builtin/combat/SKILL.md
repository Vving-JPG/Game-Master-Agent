---
name: combat
description: 战斗系统管理。当涉及战斗、伤害计算、技能使用、战斗结果判定时使用此 Skill。
version: 1.0.0
tags: [combat, battle, damage, skill]
allowed-tools:
  - modify_stat
  - update_npc_state
  - show_notification
  - play_sound
triggers:
  - event_type: combat_start
  - event_type: combat_action
  - event_type: combat_end
  - keyword: ["战斗", "攻击", "防御", "技能", "伤害", "打", "杀"]
---

# 战斗系统

## 核心规则

### 伤害公式
- 基础伤害 = 攻击力 * (1 + 技能加成) - 防御力 * 0.5
- 暴击伤害 = 基础伤害 * 1.5 (暴击率 = 敏捷 / 100)
- 最终伤害 = max(基础伤害, 1)

### 战斗流程
1. 确定先手 (敏捷高者先行动)
2. 攻击方选择技能或普通攻击
3. 计算伤害并应用
4. 检查目标是否倒下
5. 交换攻守，重复 2-4
6. 一方 HP 归零时战斗结束

## 可用指令
| intent | params | 说明 |
|--------|--------|------|
| modify_stat | {player_id, stat: "hp", change: -15} | 修改玩家属性 |
| update_npc_state | {npc_id, field: "hp", value: 0} | 修改 NPC 状态 |
| show_notification | {message: "...", type: "damage"} | 显示通知 |

## 叙事要求
- 动作描写 (挥剑、闪避、格挡)
- 伤害反馈 (数字、效果描述)
- 氛围渲染 (紧张感、危机感)
- 战斗中不要突然切换到非战斗话题
