---
name: quest
description: 任务系统管理。当涉及任务发布、进度追踪、任务完成、奖励发放时使用此 Skill。
version: 1.0.0
tags: [quest, mission, reward]
allowed-tools:
  - offer_quest
  - update_quest
  - give_item
  - show_notification
triggers:
  - event_type: quest_update
  - keyword: ["任务", "委托", "目标", "完成", "奖励"]
---

# 任务系统

## 核心规则

### 任务状态
- inactive: 未激活 / active: 进行中 / completed: 已完成 / failed: 已失败

## 可用指令
| intent | params | 说明 |
|--------|--------|------|
| offer_quest | {quest_id, title, description, objective, reward} | 发布任务 |
| update_quest | {quest_id, status, progress} | 更新任务状态 |
| give_item | {item_id, player_id, quantity} | 给予物品 |
