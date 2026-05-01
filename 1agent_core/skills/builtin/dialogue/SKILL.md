---
name: dialogue
description: 对话系统管理。当玩家与NPC交谈、询问信息、建立关系时使用此 Skill。
version: 1.0.0
tags: [dialogue, npc, relationship]
allowed-tools:
  - update_npc_relationship
  - show_notification
triggers:
  - event_type: npc_interact
  - keyword: ["聊天", "对话", "询问", "说话", "谈谈", "聊聊"]
---

# 对话系统

## 核心规则

### 好感度影响
- 0-20: 冷淡，只回答必要问题
- 21-50: 友好，愿意分享一般信息
- 51-80: 信任，愿意分享秘密
- 81-100: 亲密，愿意付出帮助

### 信息透露控制
- 关键剧情信息需要好感度达到阈值
- NPC 不会一次性透露所有信息
- 信息透露应该自然

## 可用指令
| intent | params | 说明 |
|--------|--------|------|
| update_npc_relationship | {npc_id, change: 5} | 修改好感度 |

## 叙事要求
- 保持 NPC 性格一致性
- 对话要有个性
- 描写 NPC 的表情、动作、语气
