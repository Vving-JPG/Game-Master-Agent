# Game Master Agent API

## Base URL
`http://localhost:8000`

## 认证
所有请求需要 `X-API-Key` Header（步骤 4.8 实现）

## REST 端点

### 世界管理
| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | /api/worlds | 列出所有世界 | - | [{id, name, setting, created_at}] |
| POST | /api/worlds | 创建新世界 | {name, setting} | {id, name, setting} |
| GET | /api/worlds/{id} | 世界详情 | - | {id, name, setting, locations, npcs} |
| DELETE | /api/worlds/{id} | 删除世界 | - | {message} |

### 玩家
| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | /api/worlds/{id}/player | 玩家信息 | - | {name, hp, max_hp, mp, max_mp, level, exp, gold, location_id} |
| PATCH | /api/worlds/{id}/player | 更新玩家 | {hp?, mp?, gold?, ...} | {message} |
| GET | /api/worlds/{id}/inventory | 背包 | - | [{id, name, quantity, rarity}] |
| POST | /api/worlds/{id}/player/equip | 装备物品 | {item_id, slot} | {message} |

### NPC
| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | /api/worlds/{id}/npcs | NPC列表 | - | [{id, name, mood, location_id}] |
| GET | /api/worlds/{id}/npcs/{npc_id} | NPC详情 | - | {id, name, mood, personality, backstory, ...} |
| POST | /api/worlds/{id}/npcs | 创建NPC | {name, location_id, personality_type?} | {id, name} |

### 任务
| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | /api/worlds/{id}/quests | 任务列表 | - | [{id, title, status, description}] |
| GET | /api/worlds/{id}/quests/{qid} | 任务详情 | - | {id, title, steps, progress} |

### 游戏行动（核心）
| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | /api/worlds/{id}/action | 玩家行动 | {content: "玩家输入", stream?: false} | {reply: "GM回复"} |

### 存档
| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | /api/worlds/{id}/saves | 存档列表 | - | [{slot, saved_at}] |
| POST | /api/worlds/{id}/save | 保存 | {slot: "auto"} | {path} |
| POST | /api/worlds/{id}/load | 读档 | {slot: "auto"} | {message} |

## WebSocket
- 端点: `ws://localhost:8000/ws/worlds/{world_id}`
- 客户端→服务端: `{"type": "action", "content": "玩家输入"}`
- 服务端→客户端: `{"type": "narrative", "content": "文本片段"}`
- 服务端→客户端: `{"type": "system", "content": "系统消息"}`
- 服务端→客户端: `{"type": "combat", "data": {...}}`
- 服务端→客户端: `{"type": "choice", "choices": [...]}`

## 使用示例

### cURL
```bash
# 列出世界
curl http://localhost:8000/api/worlds

# 玩家行动
curl -X POST http://localhost:8000/api/worlds/1/action \
  -H "Content-Type: application/json" \
  -d '{"content": "环顾四周"}'
```

### Python
```python
import httpx
resp = httpx.post("http://localhost:8000/api/worlds/1/action",
                     json={"content": "你好"})
print(resp.json()["reply"])
```

### JavaScript
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/worlds/1");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.send(JSON.stringify({type: "action", content: "你好"}));
```
