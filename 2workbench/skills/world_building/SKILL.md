---
name: world_building
description: 世界构建技能 - 指导 AI 动态创建和管理游戏世界元素
version: 1.0.0
tags: [world-building, npc, location, item, quest]
allowed-tools: [create_npc, search_npcs, create_location, create_item, create_quest, get_world_state, update_npc_state]
triggers:
  - event_type: player_action
keywords: [创建, 新的, 出现, 发现, 遇到, 前往, 探索]
---

# 世界构建规则

## 何时创建新元素

1. **创建 NPC**：当玩家进入新区域、故事需要新角色、或玩家与未记录的 NPC 交互时
2. **创建地点**：当玩家探索到新区域、或故事推进需要新场景时
3. **创建物品**：当玩家获得新道具、发现宝箱、或 NPC 给予物品时
4. **创建任务**：当故事发展出新的目标、NPC 发布委托、或玩家触发事件时

## 创建原则

### NPC 创建
- 每个 NPC 必须有独特的名字（不能重名）
- 必须指定所在地点
- 性格和说话风格要鲜明
- 背景故事应与世界观一致
- 心情应反映当前情境

### 地点创建
- 描述要包含视觉、听觉、嗅觉等多感官细节
- 必须定义与其他地点的连接关系
- 氛围要符合区域主题（如森林阴暗、城镇热闹）

### 物品创建
- 类型要准确（weapon/armor/consumable/quest 等）
- 描述要包含外观和使用方式
- 稀有度要合理（普通物品不要设为 legendary）

### 任务创建
- 标题要简洁明确
- 描述要说明目标和奖励
- 类型要准确（main=主线, side=支线）

## 注意事项
- 创建前先用 search_npcs 或 get_world_state 检查是否已存在
- 不要过度创建，保持世界元素的精简和有意义
- 创建后通过叙事自然地介绍给玩家，不要生硬地列出
