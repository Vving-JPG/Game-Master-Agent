---
name: exploration
description: 探索系统管理。当玩家移动、探索新区域、搜索物品、调查环境时使用此 Skill。
version: 1.0.0
tags: [exploration, movement, discovery]
allowed-tools:
  - update_location
  - teleport_player
  - give_item
  - show_notification
triggers:
  - event_type: player_move
  - keyword: ["探索", "搜索", "调查", "查看", "周围"]
---

# 探索系统

## 核心规则

### 地点发现
- 首次进入新地点时详细描述
- 重复进入时简要描述或提示变化
- 隐藏区域需要特定条件才能发现

## 可用指令
| intent | params | 说明 |
|--------|--------|------|
| update_location | {location_id, field, value} | 修改地点状态 |
| teleport_player | {player_id, location_id} | 传送玩家 |
| give_item | {item_id, player_id} | 给予发现的物品 |
