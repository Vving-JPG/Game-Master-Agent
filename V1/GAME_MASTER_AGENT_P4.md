# Game Master Agent - P4' 通信层与正式前端

> 本文件是 Trae AI 助手执行 P4' 阶段的指引。P0 + P1' + P2' + P3' 必须已全部完成。
> **本阶段实现 FastAPI 后端 API + WebSocket 实时通信 + 前端正式版。**

## 前置条件

执行本阶段前，确认以下成果已就绪：
- [ ] P0-P3' 全部完成（100+个测试通过）
- [ ] `uv run pytest tests/ -v` 全部通过
- [ ] `src/agent/game_master.py` 存在（GameMaster 类可用）
- [ ] `src/tools/executor.py` 存在（18+个工具已注册）
- [ ] `src/services/llm_client.py` 存在（LLMClient 可用）
- [ ] `src/web/` 前端骨架存在（index.html + CSS + JS）

## 行为准则

1. **一步一步执行**：严格按步骤顺序，每步验证通过后再继续
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始P4'"后，主动执行每一步
4. **遇到错误先尝试解决**：3次失败后再询问用户
5. **每步完成后汇报**：简要汇报结果和下一步
6. **代码规范**：UTF-8、中文注释、PEP 8、每个模块必须有 pytest 测试
7. **不要跳步**
8. **PowerShell 注意**：Windows PowerShell 不支持 `&&`，用 `;` 分隔命令
9. **依赖安装**：本阶段需要 `fastapi`、`uvicorn`、`httpx`、`pytest-asyncio`、`websockets`

## P2'/P3' 经验教训（必须遵守）

- **DeepSeek reasoning_content**：涉及 LLM 调用时注意传递
- **tool_call_id**：tool 消息必须包含此字段
- **全局状态隔离**：测试中不要污染 `TOOL_REGISTRY`
- **模块引用**：用 `from module import module; module.variable` 避免值拷贝
- **seed_world 返回值**：`seed_world()` 返回 `{"world_id": ..., "player_id": ...}`

---

## 步骤 4.1 - 设计 REST API 接口文档

**目的**: 定义所有 HTTP 端点

**执行**:
1. 创建 `docs/api_design.md`：
   ```markdown
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
   ```

**验收**: `docs/api_design.md` 文件存在，包含所有端点定义

---

## 步骤 4.2 - 搭建 FastAPI 应用

**目的**: 创建 Web 服务框架

**执行**:
1. 安装依赖：
   ```bash
   uv add fastapi uvicorn[standard] httpx pytest-asyncio
   ```
2. 创建 `src/api/__init__.py`（空文件）
3. 创建 `src/api/app.py`：
   ```python
   """FastAPI 应用入口"""
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware

   app = FastAPI(
       title="Game Master Agent API",
       description="AI驱动的RPG游戏Master API",
       version="0.4.0",
   )

   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )


   @app.get("/")
   def root():
       return {"message": "Game Master Agent API", "version": "0.4.0"}


   @app.get("/health")
   def health():
       return {"status": "ok"}


   def run_server():
       """启动服务器"""
       import uvicorn
       uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)
   ```
4. 验证启动：
   ```bash
   uv run python -c "from src.api.app import app; print(f'FastAPI app loaded: {app.title}')"
   ```
5. 启动服务：
   ```bash
   uv run uvicorn src.api.app:app --reload --port 8000
   ```
6. 访问 http://localhost:8000/docs 看到 Swagger UI

**验收**: Swagger UI 可访问，显示 API 文档

---

## 步骤 4.3 - 实现世界管理路由 + 单测

**目的**: 世界 CRUD 端点

**执行**:
1. 创建 `src/api/routes/__init__.py`（空文件）
2. 创建 `src/api/routes/worlds.py`：
   ```python
   """世界管理路由"""
   from fastapi import APIRouter, HTTPException
   from pydantic import BaseModel
   from src.models import world_repo
   from src.data.seed_data import seed_world

   router = APIRouter(prefix="/api/worlds", tags=["世界管理"])


   class WorldCreate(BaseModel):
       name: str = "新世界"
       setting: str = "奇幻世界"


   @router.get("")
   def list_worlds():
       """列出所有世界"""
       worlds = world_repo.list_worlds()
       return [{"id": w["id"], "name": w["name"], "setting": w["setting"], "created_at": w.get("created_at", "")} for w in worlds]


   @router.post("")
   def create_world(body: WorldCreate):
       """创建新世界"""
       result = seed_world()
       return {"id": result["world_id"], "name": body.name, "setting": body.setting}


   @router.get("/{world_id}")
   def get_world(world_id: int):
       """获取世界详情"""
       world = world_repo.get_world(world_id)
       if not world:
           raise HTTPException(status_code=404, detail=f"世界{world_id}不存在")
       return world


   @router.delete("/{world_id}")
   def delete_world(world_id: int):
       """删除世界"""
       world = world_repo.get_world(world_id)
       if not world:
           raise HTTPException(status_code=404, detail=f"世界{world_id}不存在")
       world_repo.delete_world(world_id)
       return {"message": f"世界{world_id}已删除"}
   ```
3. 在 `src/api/app.py` 中注册路由：
   ```python
   from src.api.routes.worlds import router as worlds_router
   app.include_router(worlds_router)
   ```
4. 创建 `tests/test_api_worlds.py`：
   ```python
   """世界API测试"""
   import pytest
   from fastapi.testclient import TestClient
   from src.api.app import app
   from src.data.seed_data import seed_world

   client = TestClient(app)


   def test_list_worlds():
       """列出世界"""
       resp = client.get("/api/worlds")
       assert resp.status_code == 200
       assert isinstance(resp.json(), list)


   def test_create_world():
       """创建世界"""
       resp = client.post("/api/worlds", json={"name": "测试世界", "setting": "测试"})
       assert resp.status_code == 200
       data = resp.json()
       assert "id" in data


   def test_get_world():
       """获取世界详情"""
       # 先创建
       worlds = world_repo.list_worlds()
       if not worlds:
           seed_world()
           worlds = world_repo.list_worlds()
       wid = worlds[0]["id"]
       resp = client.get(f"/api/worlds/{wid}")
       assert resp.status_code == 200
       assert "name" in resp.json()


   def test_get_world_not_found():
       """不存在的世界"""
       resp = client.get("/api/worlds/99999")
       assert resp.status_code == 404


   def test_delete_world():
       """删除世界"""
       result = seed_world()
       wid = result["world_id"]
       resp = client.delete(f"/api/worlds/{wid}")
       assert resp.status_code == 200
   ```

**验收**: `uv run pytest tests/test_api_worlds.py -v` 全绿

---

## 步骤 4.4 - 实现玩家路由 + 单测

**目的**: 玩家信息端点

**执行**:
1. 创建 `src/api/routes/player.py`：
   ```python
   """玩家路由"""
   from fastapi import APIRouter, HTTPException
   from pydantic import BaseModel
   from src.models import player_repo, world_repo, item_repo

   router = APIRouter(prefix="/api/worlds/{world_id}", tags=["玩家"])


   class PlayerUpdate(BaseModel):
       hp: int | None = None
       mp: int | None = None
       gold: int | None = None
       level: int | None = None


   class EquipRequest(BaseModel):
       item_id: int
       slot: str


   def _get_player_id(world_id: int) -> int:
       """获取世界中第一个玩家的ID"""
       from src.services.database import get_db
       with get_db() as conn:
           row = conn.execute("SELECT id FROM players WHERE world_id = ? LIMIT 1", (world_id,)).fetchone()
       if not row:
           raise HTTPException(status_code=404, detail=f"世界{world_id}中没有玩家")
       return row["id"]


   @router.get("/player")
   def get_player(world_id: int):
       """获取玩家信息"""
       pid = _get_player_id(world_id)
       player = player_repo.get_player(pid)
       if not player:
           raise HTTPException(status_code=404, detail="玩家不存在")
       return player


   @router.patch("/player")
   def update_player(world_id: int, body: PlayerUpdate):
       """更新玩家属性"""
       pid = _get_player_id(world_id)
       updates = body.model_dump(exclude_none=True)
       if not updates:
           raise HTTPException(status_code=400, detail="没有指定要更新的属性")
       player_repo.update_player(pid, **updates)
       return {"message": "玩家属性已更新", "updates": updates}


   @router.get("/inventory")
   def get_inventory(world_id: int):
       """获取背包"""
       pid = _get_player_id(world_id)
       items = player_repo.get_inventory(pid)
       return items


   @router.post("/player/equip")
   def equip_item(world_id: int, body: EquipRequest):
       """装备物品"""
       pid = _get_player_id(world_id)
       from src.models import equipment_repo
       equipment_repo.equip_item(pid, body.item_id, body.slot)
       return {"message": f"已装备到{body.slot}槽位"}
   ```
2. 在 `src/api/app.py` 中注册路由。
3. 创建 `tests/test_api_player.py`：
   ```python
   """玩家API测试"""
   import pytest
   from fastapi.testclient import TestClient
   from src.api.app import app
   from src.data.seed_data import seed_world

   client = TestClient(app)
   WORLD_ID = None

   def setup_module():
       global WORLD_ID
       result = seed_world()
       WORLD_ID = result["world_id"]

   def test_get_player():
       resp = client.get(f"/api/worlds/{WORLD_ID}/player")
       assert resp.status_code == 200
       data = resp.json()
       assert "hp" in data
       assert "level" in data

   def test_update_player():
       resp = client.patch(f"/api/worlds/{WORLD_ID}/player", json={"gold": 999})
       assert resp.status_code == 200

   def test_get_inventory():
       resp = client.get(f"/api/worlds/{WORLD_ID}/inventory")
       assert resp.status_code == 200
       assert isinstance(resp.json(), list)

   def test_player_not_found():
       resp = client.get("/api/worlds/99999/player")
       assert resp.status_code == 404
   ```

**验收**: `uv run pytest tests/test_api_player.py -v` 全绿

---

## 步骤 4.5 - 实现游戏行动路由 + 单测

**目的**: 核心交互端点——玩家行动 → GM 回复

**执行**:
1. 创建 `src/api/routes/action.py`：
   ```python
   """游戏行动路由 - 核心交互"""
   from fastapi import APIRouter, HTTPException
   from pydantic import BaseModel
   from src.agent.game_master import GameMaster
   from src.services.llm_client import LLMClient
   from src.models import world_repo
   from src.utils.logger import get_logger

   logger = get_logger(__name__)
   router = APIRouter(prefix="/api/worlds/{world_id}", tags=["游戏行动"])

   # 缓存 GameMaster 实例
   _gm_cache: dict[int, GameMaster] = {}


   class ActionRequest(BaseModel):
       content: str
       stream: bool = False


   def _get_gm(world_id: int) -> GameMaster:
       """获取或创建 GameMaster 实例"""
       if world_id not in _gm_cache:
           world = world_repo.get_world(world_id)
           if not world:
               raise HTTPException(status_code=404, detail=f"世界{world_id}不存在")
           from src.services.database import get_db
           with get_db() as conn:
               row = conn.execute("SELECT id FROM players WHERE world_id = ? LIMIT 1", (world_id,)).fetchone()
           if not row:
               raise HTTPException(status_code=404, detail="世界中没有玩家")
           _gm_cache[world_id] = GameMaster(world_id, row["id"], LLMClient())
       return _gm_cache[world_id]


   @router.post("/action")
   def game_action(world_id: int, body: ActionRequest):
       """玩家行动 → GM回复"""
       if not body.content.strip():
           raise HTTPException(status_code=400, detail="输入不能为空")

       gm = _get_gm(world_id)
       try:
           reply = gm.process(body.content)
           return {"reply": reply}
       except Exception as e:
           logger.error(f"处理行动失败: {e}")
           raise HTTPException(status_code=500, detail=f"GM处理失败: {e}")
   ```
2. 在 `src/api/app.py` 中注册路由。
3. 创建 `tests/test_api_action.py`：
   ```python
   """游戏行动API测试"""
   import pytest
   from unittest.mock import patch, MagicMock
   from fastapi.testclient import TestClient
   from src.api.app import app
   from src.data.seed_data import seed_world

   client = TestClient(app)
   WORLD_ID = None

   def setup_module():
       global WORLD_ID
       result = seed_world()
       WORLD_ID = result["world_id"]

   def test_action_empty_input():
       """空输入返回400"""
       resp = client.post(f"/api/worlds/{WORLD_ID}/action", json={"content": ""})
       assert resp.status_code == 400

   def test_action_mock_gm():
       """Mock GM返回"""
       with patch("src.api.routes.action._get_gm") as mock_gm:
           mock_instance = MagicMock()
           mock_instance.process.return_value = "你站在宁静的村庄广场上。"
           mock_gm.return_value = mock_instance

           resp = client.post(f"/api/worlds/{WORLD_ID}/action", json={"content": "环顾四周"})
           assert resp.status_code == 200
           assert "宁静" in resp.json()["reply"]

   def test_action_world_not_found():
       """不存在的世界"""
       resp = client.post("/api/worlds/99999/action", json={"content": "测试"})
       assert resp.status_code == 404
   ```

**验收**: `uv run pytest tests/test_api_action.py -v` 全绿

---

## 步骤 4.6 - 实现 WebSocket 端点

**目的**: 实时双向通信

**执行**:
1. 创建 `src/api/routes/ws.py`：
   ```python
   """WebSocket 路由 - 实时双向通信"""
   import json
   from fastapi import APIRouter, WebSocket, WebSocketDisconnect
   from src.agent.game_master import GameMaster
   from src.services.llm_client import LLMClient
   from src.models import world_repo
   from src.utils.logger import get_logger

   logger = get_logger(__name__)
   router = APIRouter()


   @router.websocket("/ws/worlds/{world_id}")
   async def game_websocket(websocket: WebSocket, world_id: int):
       """游戏 WebSocket 连接

       消息格式:
       客户端→服务端: {"type": "action", "content": "玩家输入"}
       服务端→客户端: {"type": "narrative", "content": "文本片段"}
       服务端→客户端: {"type": "system", "content": "系统消息"}
       """
       await websocket.accept()
       logger.info(f"WebSocket 连接: world_id={world_id}")

       # 初始化 GameMaster
       world = world_repo.get_world(world_id)
       if not world:
           await websocket.send_json({"type": "system", "content": f"世界{world_id}不存在"})
           await websocket.close()
           return

       from src.services.database import get_db
       with get_db() as conn:
           row = conn.execute("SELECT id FROM players WHERE world_id = ? LIMIT 1", (world_id,)).fetchone()
       if not row:
           await websocket.send_json({"type": "system", "content": "世界中没有玩家"})
           await websocket.close()
           return

       gm = GameMaster(world_id, row["id"], LLMClient())

       try:
           await websocket.send_json({"type": "system", "content": f"已连接到世界: {world['name']}"})

           while True:
               data = await websocket.receive_text()
               try:
                   msg = json.loads(data)
               except json.JSONDecodeError:
                   await websocket.send_json({"type": "system", "content": "无效的JSON格式"})
                   continue

               msg_type = msg.get("type", "action")
               content = msg.get("content", "")

               if msg_type == "action" and content.strip():
                   try:
                       # 处理并流式发送
                       for chunk in gm.process_stream(content):
                           await websocket.send_json({
                               "type": "narrative",
                               "content": chunk,
                           })
                   except Exception as e:
                       logger.error(f"处理消息失败: {e}")
                       await websocket.send_json({"type": "system", "content": f"处理失败: {e}"})
               else:
                   await websocket.send_json({"type": "system", "content": "未知消息类型"})

       except WebSocketDisconnect:
           logger.info(f"WebSocket 断开: world_id={world_id}")
   ```
2. 在 `src/api/app.py` 中注册 WebSocket 路由：
   ```python
   from src.api.routes.ws import router as ws_router
   app.include_router(ws_router)
   ```
3. 手动测试（启动服务器后）：
   ```bash
   # 安装 wscat（如果没装）
   npm install -g wscat
   # 连接测试
   wscat -c ws://localhost:8000/ws/worlds/1
   # 发送: {"type":"action","content":"你好"}
   # 应收到: {"type":"narrative","content":"你"} ... {"type":"narrative","content":"好"} ...
   ```

**验收**: WebSocket 连接成功，发送消息后收到流式回复

---

## 步骤 4.7 - 实现连接管理

**目的**: 管理多客户端连接

**执行**:
1. 创建 `src/api/connection_manager.py`：
   ```python
   """WebSocket 连接管理器"""
   from fastapi import WebSocket
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   class ConnectionManager:
       """管理 WebSocket 连接"""

       def __init__(self):
           # {world_id: set[WebSocket]}
           self.active_connections: dict[int, set[WebSocket]] = {}

       async def connect(self, world_id: int, websocket: WebSocket):
           await websocket.accept()
           if world_id not in self.active_connections:
               self.active_connections[world_id] = set()
           self.active_connections[world_id].add(websocket)
           logger.info(f"客户端连接到世界{world_id}，当前连接数: {len(self.active_connections[world_id])}")

       def disconnect(self, world_id: int, websocket: WebSocket):
           if world_id in self.active_connections:
               self.active_connections[world_id].discard(websocket)
               if not self.active_connections[world_id]:
                   del self.active_connections[world_id]
           logger.info(f"客户端断开世界{world_id}")

       async def broadcast(self, world_id: int, message: dict):
           """广播消息给世界中的所有客户端"""
       if world_id not in self.active_connections:
           return
       dead = []
       for ws in self.active_connections[world_id]:
           try:
               await ws.send_json(message)
           except Exception:
               dead.append(ws)
       for ws in dead:
           self.disconnect(world_id, ws)

       def get_connection_count(self, world_id: int) -> int:
           return len(self.active_connections.get(world_id, set()))


   # 全局连接管理器
   manager = ConnectionManager()
   ```
2. 在 `src/api/routes/ws.py` 中使用 ConnectionManager：
   ```python
   from src.api.connection_manager import manager

   @router.websocket("/ws/worlds/{world_id}")
   async def game_websocket(websocket: WebSocket, world_id: int):
       await manager.connect(world_id, websocket)
       try:
           # ... 原有逻辑 ...
           # 在需要广播时:
           # await manager.broadcast(world_id, {"type": "system", "content": "系统消息"})
       except WebSocketDisconnect:
           manager.disconnect(world_id, websocket)
   ```
3. 创建 `tests/test_connection_manager.py`：
   ```python
   """连接管理器测试"""
   import asyncio
   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.api.connection_manager import ConnectionManager


   def test_connect_and_disconnect():
       """连接和断开"""
       mgr = ConnectionManager()
       ws = MagicMock()
       mgr.active_connections[1] = set()
       mgr.active_connections[1].add(ws)
       assert mgr.get_connection_count(1) == 1
       mgr.disconnect(1, ws)
       assert mgr.get_connection_count(1) == 0


   def test_empty_world():
       """空世界连接数"""
       mgr = ConnectionManager()
       assert mgr.get_connection_count(999) == 0


   @pytest.mark.asyncio
   async def test_broadcast():
       """广播消息"""
       mgr = ConnectionManager()
       ws1 = AsyncMock()
       ws2 = AsyncMock()
       mgr.active_connections[1] = {ws1, ws2}
       await mgr.broadcast(1, {"type": "test", "content": "hello"})
       assert ws1.send_json.call_count == 1
       assert ws2.send_json.call_count == 1
   ```

**验收**: `uv run pytest tests/test_connection_manager.py -v` 全绿

---

## 步骤 4.8 - 实现认证和错误处理

**目的**: API Key 认证 + 统一错误格式

**执行**:
1. 创建 `src/api/auth.py`：
   ```python
   """API Key 认证"""
   import os
   from fastapi import Security, HTTPException, Depends
   from fastapi.security import APIKeyHeader

   API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

   # 默认 API Key（生产环境应从环境变量读取）
   DEFAULT_API_KEY = os.getenv("API_KEY", "gm-agent-dev-key")


   async def verify_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str:
       """验证 API Key

       开发环境下如果没提供 Key，使用默认 Key。
       生产环境必须提供有效 Key。
       """
       if not api_key:
           # 开发环境允许无 Key
           return DEFAULT_API_KEY
       if api_key != DEFAULT_API_KEY:
           raise HTTPException(status_code=401, detail="无效的 API Key")
       return api_key
   ```
2. 创建 `src/api/exceptions.py`：
   ```python
   """自定义异常和全局错误处理"""
   from fastapi import Request
   from fastapi.responses import JSONResponse


   class GameError(Exception):
       """游戏逻辑错误"""
       def __init__(self, message: str, code: int = 400):
           self.message = message
           self.code = code


   class WorldNotFound(GameError):
       def __init__(self, world_id: int):
           super().__init__(f"世界{world_id}不存在", 404)


   class InvalidAction(GameError):
       def __init__(self, message: str = "无效的行动"):
           super().__init__(message, 400)


   class CombatError(GameError):
       def __init__(self, message: str = "战斗出错"):
           super().__init__(message, 409)


   async def game_error_handler(request: Request, exc: GameError):
       """全局异常处理器"""
       return JSONResponse(
           status_code=exc.code,
           content={"error": exc.message, "code": exc.code},
       )
   ```
3. 在 `src/api/app.py` 中注册异常处理器：
   ```python
   from src.api.exceptions import GameError, game_error_handler
   app.add_exception_handler(GameError, game_error_handler)
   ```
4. 创建 `tests/test_api_auth.py`：
   ```python
   """认证和错误处理测试"""
   import pytest
   from fastapi.testclient import TestClient
   from src.api.app import app

   client = TestClient(app)

   def test_no_auth_required_dev():
       """开发环境不需要认证"""
       resp = client.get("/health")
       assert resp.status_code == 200

   def test_invalid_api_key():
       """无效API Key"""
       resp = client.get("/health", headers={"X-API-Key": "wrong-key"})
       # 开发环境应该放行（无Key时使用默认Key）
       # 如果传了错误Key，应该401
       assert resp.status_code in [200, 401]

   def test_error_format():
       """错误格式统一"""
       from src.api.exceptions import InvalidAction
       # 通过路由触发异常
       resp = client.post("/api/worlds/99999/action", json={"content": ""})
       # 应该返回JSON格式的错误
       assert resp.status_code in [400, 404, 500]
   ```

**验收**: `uv run pytest tests/test_api_auth.py -v` 全绿

---

## 步骤 4.9 - 前端升级：连接真实后端

**目的**: 将 Mock 前端替换为真实 WebSocket 连接

**执行**:
1. 修改 `src/web/js/app.js`，替换 Mock 为真实连接：
   ```javascript
   // ===== 真实 WebSocket 连接 =====
   let ws = null;
   let worldId = 1;

   class RealGameClient {
       constructor(worldId) {
           this.worldId = worldId;
           this.ws = null;
           this.reconnectTimer = null;
       }

       connect() {
           const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
           const url = `${protocol}//${location.host}/ws/worlds/${this.worldId}`;
           this.ws = new WebSocket(url);

           this.ws.onopen = () => {
               addMessage('已连接到游戏服务器', 'system-text');
           };

           this.ws.onmessage = (event) => {
               const data = JSON.parse(event.data);
               if (data.type === 'narrative') {
                   appendToLastGMMessage(data.content);
               } else if (data.type === 'system') {
                   addMessage(data.content, 'system-text');
               } else if (data.type === 'combat') {
                   handleCombatUpdate(data.data);
               } else if (data.type === 'choice') {
                   showChoices(data.choices);
               }
           };

           this.ws.onclose = () => {
               addMessage('连接断开，5秒后重连...', 'system-text');
               this.reconnectTimer = setTimeout(() => this.connect(), 5000);
           };

           this.ws.onerror = () => {
               addMessage('连接错误', 'system-text');
           };
       }

       send(userInput) {
           if (this.ws && this.ws.readyState === WebSocket.OPEN) {
               this.ws.send(JSON.stringify({ type: 'action', content: userInput }));
           } else {
               addMessage('未连接到服务器', 'system-text');
           }
       }

       disconnect() {
           if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
           if (this.ws) this.ws.close();
       }
   }

   // 替换 Mock 客户端
   const client = new RealGameClient(worldId);
   client.connect();

   // 修改 appendToLastGMMessage 函数
   function appendToLastGMMessage(char) {
       let container = document.querySelector('#narrative-content .gm-text:last-child');
       if (!container || !container.dataset.streaming) {
           container = document.createElement('div');
           container.className = 'message gm-text';
           container.dataset.streaming = 'true';
           narrativeContent.appendChild(container);
       }
       container.textContent += char;
       narrativeContent.scrollTop = narrativeContent.scrollHeight;

       // 流结束后标记完成
       clearTimeout(container._endTimer);
       container._endTimer = setTimeout(() => {
           delete container.dataset.streaming;
       }, 2000);
   }

   // 修改 sendMessage 函数
   async function sendMessage() {
       const text = userInput.value.trim();
       if (!text) return;
       addMessage(`你> ${text}`, 'user-text');
       userInput.value = '';
       client.send(text);
   }
   ```
2. 保留 `mock.js` 作为离线备用，在 `index.html` 中根据环境切换：
   ```html
   <!-- 开发时用 mock，生产时用真实连接 -->
   <script>
       // 如果后端可用则用真实连接，否则用 Mock
       const USE_MOCK = false; // 设为 true 使用 Mock
   </script>
   <script src="js/mock.js"></script>
   <script src="js/app.js"></script>
   ```
3. 在 `app.js` 顶部添加 Mock 回退逻辑：
   ```javascript
   // 如果 USE_MOCK 为 true，使用 MockGameClient
   if (typeof USE_MOCK !== 'undefined' && USE_MOCK) {
       var client = new MockGameClient();
   }
   ```

**验收**: 启动后端 + 打开前端，浏览器中能通过 WebSocket 与 GM 对话

---

## 步骤 4.10 - 升级战斗 UI

**目的**: 正式版战斗界面

**执行**:
1. 修改 `src/web/index.html`，替换 Mock 战斗面板为正式版：
   ```html
   <div id="combat-panel" style="display:none;">
       <div id="combat-header">⚔️ 战斗</div>
       <div id="combatants"></div>
       <div id="combat-log"></div>
       <div id="combat-actions">
           <button class="combat-btn" onclick="combatAction('attack')">⚔️ 攻击</button>
           <button class="combat-btn" onclick="combatAction('defend')">🛡️ 防御</button>
           <button class="combat-btn" onclick="combatAction('use_item')">🧪 使用物品</button>
           <button class="combat-btn flee" onclick="combatAction('flee')">🏃 逃跑</button>
       </div>
   </div>
   ```
2. 修改 `src/web/css/style.css`：
   ```css
   #combat-panel {
       padding: 16px;
       background: linear-gradient(135deg, #1a0a0a 0%, #2a1515 100%);
       border: 2px solid #e74c3c;
       border-radius: 8px;
       margin: 12px 0;
       animation: combatPulse 2s infinite;
   }
   @keyframes combatPulse {
       0%, 100% { border-color: #e74c3c; }
       50% { border-color: #c0392b; }
   }
   #combat-header {
       font-size: 16px;
       font-weight: bold;
       color: #e74c3c;
       margin-bottom: 12px;
   }
   .combatant {
       display: flex;
       justify-content: space-between;
       align-items: center;
       padding: 6px 0;
       border-bottom: 1px solid #333;
   }
   .combatant-name { color: #e0e0e0; font-size: 14px; }
   .hp-bar-container {
       width: 120px;
       height: 12px;
       background: #333;
       border-radius: 6px;
       overflow: hidden;
   }
   .hp-bar {
       height: 100%;
       background: #2ecc71;
       border-radius: 6px;
       transition: width 0.5s ease;
   }
   .hp-bar.low { background: #e74c3c; }
   .hp-bar.medium { background: #f39c12; }
   .hp-text { font-size: 12px; color: #aaa; margin-left: 6px; }
   #combat-log {
       max-height: 100px;
       overflow-y: auto;
       margin: 8px 0;
       font-size: 12px;
       color: #e74c3c;
       padding: 8px;
       background: rgba(0,0,0,0.3);
       border-radius: 4px;
   }
   #combat-actions {
       display: flex;
       gap: 8px;
   }
   .combat-btn {
       flex: 1;
       padding: 8px;
       border: 1px solid #555;
       background: #2a1515;
       color: #e0e0e0;
       cursor: pointer;
       border-radius: 4px;
       font-family: inherit;
       font-size: 13px;
   }
   .combat-btn:hover { background: #3a2020; border-color: #e74c3c; }
   .combat-btn.flee { color: #f39c12; }
   ```
3. 修改 `src/web/js/app.js`，添加战斗处理：
   ```javascript
   function handleCombatUpdate(data) {
       const panel = document.getElementById('combat-panel');
       panel.style.display = 'block';

       // 更新战斗参与者
       const combatants = document.getElementById('combatants');
       combatants.innerHTML = data.participants.map(p => {
           const hpPercent = Math.max(0, (p.hp / p.max_hp) * 100);
           const hpClass = hpPercent < 25 ? 'low' : hpPercent < 50 ? 'medium' : '';
           return `<div class="combatant">
               <span class="combatant-name">${p.is_player ? '🧙' : '👹'} ${p.name}</span>
               <div style="display:flex;align-items:center;">
                   <div class="hp-bar-container">
                       <div class="hp-bar ${hpClass}" style="width:${hpPercent}%"></div>
                   </div>
                   <span class="hp-text">${p.hp}/${p.max_hp}</span>
               </div>
           </div>`;
       }).join('');

       // 更新战斗日志
       if (data.log) {
           const logEl = document.getElementById('combat-log');
           logEl.innerHTML += data.log.map(l => `<div>${l}</div>`).join('');
           logEl.scrollTop = logEl.scrollHeight;
       }

       // 战斗结束
       if (data.finished) {
           document.getElementById('combat-actions').style.display = 'none';
           if (data.victory) {
               addMessage(`🎉 胜利！获得 ${data.rewards.exp} 经验和 ${data.rewards.gold} 金币。`, 'system-text');
           } else {
               addMessage('💀 你被击败了...', 'combat-text');
           }
           setTimeout(() => {
               panel.style.display = 'none';
               document.getElementById('combat-actions').style.display = 'flex';
           }, 3000);
       }
   }

   function combatAction(action) {
       client.send(JSON.stringify({ type: 'combat_action', action: action }));
   }
   ```

**验收**: 浏览器中战斗面板显示正确，HP 条动态变化

---

## 步骤 4.11 - 升级分支选择 UI

**目的**: 正式版剧情分支选择

**执行**:
1. 修改 `src/web/index.html`，在叙事区下方添加选择面板：
   ```html
   <div id="choice-panel" style="display:none;">
       <div id="choice-options"></div>
   </div>
   ```
2. 修改 `src/web/css/style.css`：
   ```css
   #choice-panel {
       padding: 12px;
       margin: 8px 0;
       border: 1px solid #f1c40f;
       border-radius: 8px;
       background: rgba(241, 196, 15, 0.05);
   }
   .choice-btn {
       display: block;
       width: 100%;
       padding: 10px 16px;
       margin: 6px 0;
       background: rgba(241, 196, 15, 0.1);
       border: 1px solid #f1c40f;
       color: #f1c40f;
       cursor: pointer;
       border-radius: 4px;
       font-family: inherit;
       font-size: 14px;
       text-align: left;
       transition: all 0.2s;
   }
   .choice-btn:hover {
       background: rgba(241, 196, 15, 0.2);
       transform: translateX(4px);
   }
   ```
3. 修改 `src/web/js/app.js`：
   ```javascript
   function showChoices(choices) {
       const panel = document.getElementById('choice-panel');
       const options = document.getElementById('choice-options');
       panel.style.display = 'block';
       options.innerHTML = choices.map((c, i) =>
           `<button class="choice-btn" onclick="selectChoice('${c.id}')">${c.text}</button>`
       ).join('');
       userInput.disabled = true;
   }

   function selectChoice(choiceId) {
       client.send(JSON.stringify({ type: 'choice', choice_id: choiceId }));
       document.getElementById('choice-panel').style.display = 'none';
       userInput.disabled = false;
       addMessage(`你做出了选择。`, 'system-text');
   }
   ```

**验收**: 分支选择 UI 正常显示和交互

---

## 步骤 4.12 - 配置静态文件服务

**目的**: FastAPI 提供前端页面

**执行**:
1. 修改 `src/api/app.py`，添加静态文件服务：
   ```python
   from fastapi.staticfiles import StaticFiles
   from pathlib import Path

   # 静态文件服务（放在所有路由之后）
   web_dir = Path(__file__).parent.parent / "web"
   if web_dir.exists():
       app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")
   ```
2. 在 `pyproject.toml` 中添加启动脚本：
   ```toml
   [project.scripts]
   game-master = "src.cli:main"
   serve = "src.api.app:run_server"
   ```
3. 验证：
   ```bash
   uv run uvicorn src.api.app:app --port 8000
   # 访问 http://localhost:8000/static/index.html
   ```
4. 创建 `src/web/index_redirect.html`（可选，根路径重定向）：
   在 `app.py` 中添加：
   ```python
   from fastapi.responses import RedirectResponse

   @app.get("/")
   def root():
       return RedirectResponse(url="/static/index.html")
   ```

**验收**: http://localhost:8000/static/index.html 能打开游戏界面

---

## 步骤 4.13 - 生成 API 文档

**目的**: 确保 API 文档完整

**执行**:
1. 检查所有路由的 `description` 和 `response_model`：
   - 每个端点函数的 docstring 会自动成为 Swagger 描述
   - 确保每个 Pydantic model 有 `model_config` 或 `Config` 类
2. 访问以下 URL 确认文档完整：
   - http://localhost:8000/docs （Swagger UI）
   - http://localhost:8000/redoc （ReDoc）
3. 在 `docs/api_design.md` 末尾添加使用示例：
   ```markdown
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
   ```

**验收**: /docs 和 /redoc 页面信息完整

---

## 步骤 4.14 - API 综合测试

**目的**: 所有端点 + WebSocket 完整测试

**执行**:
1. 创建 `tests/test_api_full.py`：
   ```python
   """API 综合测试"""
   import pytest
   from fastapi.testclient import TestClient
   from src.api.app import app
   from src.data.seed_data import seed_world

   client = TestClient(app)
   WORLD_ID = None

   def setup_module():
       global WORLD_ID
       result = seed_world()
       WORLD_ID = result["world_id"]


   class TestRESTAPI:
       """REST API 测试"""

       def test_health(self):
           resp = client.get("/health")
           assert resp.status_code == 200

       def test_list_worlds(self):
           resp = client.get("/api/worlds")
           assert resp.status_code == 200
           assert isinstance(resp.json(), list)

       def test_get_world(self):
           resp = client.get(f"/api/worlds/{WORLD_ID}")
           assert resp.status_code == 200

       def test_get_world_404(self):
           resp = client.get("/api/worlds/99999")
           assert resp.status_code == 404

       def test_get_player(self):
           resp = client.get(f"/api/worlds/{WORLD_ID}/player")
           assert resp.status_code == 200
           data = resp.json()
           assert "hp" in data

       def test_get_inventory(self):
           resp = client.get(f"/api/worlds/{WORLD_ID}/inventory")
           assert resp.status_code == 200

       def test_action_empty(self):
           resp = client.post(f"/api/worlds/{WORLD_ID}/action", json={"content": ""})
           assert resp.status_code == 400

       def test_action_invalid_world(self):
           resp = client.post("/api/worlds/99999/action", json={"content": "测试"})
           assert resp.status_code == 404


   class TestWebSocket:
       """WebSocket 测试"""

       def test_ws_connect(self):
           """WebSocket 连接"""
           from fastapi.testclient import TestClient
           with TestClient(app) as c:
               with c.websocket_connect(f"/ws/worlds/{WORLD_ID}") as ws:
                   ws.send_json({"type": "action", "content": "你好"})
                   # 应该收到 narrative 类型的消息
                   data = ws.receive_json()
                   assert data["type"] in ["narrative", "system"]

       def test_ws_invalid_world(self):
           """无效世界的 WebSocket"""
           from fastapi.testclient import TestClient
           with TestClient(app) as c:
               with pytest.raises(Exception):
                   with c.websocket_connect("/ws/worlds/99999") as ws:
                       pass
   ```
2. 运行完整测试：
   ```bash
   uv run pytest tests/test_api_full.py -v
   ```
3. 运行全部测试：
   ```bash
   uv run pytest tests/ -v
   ```

**验收**: 所有 API 测试通过，全部测试套件通过

---

## 步骤 4.15 - 管理端：Prompt 管理系统

**目的**: 查看/编辑 GM 的 System Prompt，修改后立即生效

**执行**:
1. 在 `src/models/schema.sql` 中添加 Prompt 版本表：
   ```sql
   CREATE TABLE IF NOT EXISTS prompt_versions (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       prompt_key TEXT NOT NULL,
       content TEXT NOT NULL,
       version INTEGER NOT NULL DEFAULT 1,
       is_active INTEGER DEFAULT 0,
       created_at TEXT DEFAULT (datetime('now'))
   );
   ```
2. 创建 `src/models/prompt_repo.py`：
   ```python
   """Prompt 版本管理数据访问"""
   from src.services.database import get_db
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def save_prompt(prompt_key: str, content: str, db_path: str | None = None) -> int:
       """保存新版本 Prompt，自动递增版本号"""
       with get_db(db_path) as conn:
           # 获取当前最大版本号
           row = conn.execute(
               "SELECT MAX(version) as max_ver FROM prompt_versions WHERE prompt_key = ?",
               (prompt_key,),
           ).fetchone()
           next_ver = (row["max_ver"] or 0) + 1

           # 将旧版本设为非活跃
           conn.execute(
               "UPDATE prompt_versions SET is_active = 0 WHERE prompt_key = ?",
               (prompt_key,),
           )

           # 插入新版本
           cursor = conn.execute(
               "INSERT INTO prompt_versions (prompt_key, content, version, is_active) VALUES (?, ?, ?, 1)",
               (prompt_key, content, next_ver),
           )
           logger.info(f"Prompt '{prompt_key}' 更新到版本 {next_ver}")
           return cursor.lastrowid


   def get_active_prompt(prompt_key: str, db_path: str | None = None) -> str | None:
       """获取当前活跃版本的 Prompt"""
       with get_db(db_path) as conn:
           row = conn.execute(
               "SELECT content FROM prompt_versions WHERE prompt_key = ? AND is_active = 1 ORDER BY version DESC LIMIT 1",
               (prompt_key,),
           ).fetchone()
       return row["content"] if row else None


   def get_prompt_history(prompt_key: str, limit: int = 20, db_path: str | None = None) -> list[dict]:
       """获取 Prompt 版本历史"""
       with get_db(db_path) as conn:
           rows = conn.execute(
               "SELECT * FROM prompt_versions WHERE prompt_key = ? ORDER BY version DESC LIMIT ?",
               (prompt_key, limit),
           ).fetchall()
       return [dict(r) for r in rows]


   def rollback_prompt(prompt_key: str, version: int, db_path: str | None = None) -> bool:
       """回滚到指定版本"""
       with get_db(db_path) as conn:
           conn.execute("UPDATE prompt_versions SET is_active = 0 WHERE prompt_key = ?", (prompt_key,))
           conn.execute(
               "UPDATE prompt_versions SET is_active = 1 WHERE prompt_key = ? AND version = ?",
               (prompt_key, version),
           )
       logger.info(f"Prompt '{prompt_key}' 回滚到版本 {version}")
       return True
   ```
3. 在 `src/models/__init__.py` 中添加 `from src.models import prompt_repo`。
4. 修改 `src/prompts/gm_system.py`，添加从 DB 加载的能力：
   ```python
   # 在 get_system_prompt() 函数开头添加:
   from src.models import prompt_repo
   db_prompt = prompt_repo.get_active_prompt("game_master_system")
   if db_prompt:
       return db_prompt
   # 否则使用默认硬编码的 Prompt
   ```
5. 创建 `src/api/routes/admin_prompts.py`：
   ```python
   """管理端 - Prompt 管理路由"""
   from fastapi import APIRouter
   from pydantic import BaseModel
   from src.models import prompt_repo

   router = APIRouter(prefix="/api/admin/prompts", tags=["管理端-Prompt"])


   class PromptUpdate(BaseModel):
       prompt_key: str
       content: str


   class PromptRollback(BaseModel):
       prompt_key: str
       version: int


   @router.get("/{prompt_key}")
   def get_prompt(prompt_key: str):
       """获取当前活跃 Prompt"""
       content = prompt_repo.get_active_prompt(prompt_key)
       if not content:
           return {"prompt_key": prompt_key, "content": "", "version": 0, "message": "无活跃版本，使用默认"}
       return {"prompt_key": prompt_key, "content": content}


   @router.post("")
   def update_prompt(body: PromptUpdate):
       """更新 Prompt（立即生效）"""
       version_id = prompt_repo.save_prompt(body.prompt_key, body.content)
       return {"message": f"Prompt 已更新", "version_id": version_id}


   @router.get("/{prompt_key}/history")
   def get_history(prompt_key: str):
       """获取版本历史"""
       return prompt_repo.get_prompt_history(prompt_key)


   @router.post("/rollback")
   def rollback(body: PromptRollback):
       """回滚到指定版本"""
       prompt_repo.rollback_prompt(body.prompt_key, body.version)
       return {"message": f"已回滚到版本 {body.version}"}
   ```
6. 在 `src/api/app.py` 中注册路由。
7. 创建 `tests/test_prompt_repo.py`：
   ```python
   """Prompt 版本管理测试"""
   import tempfile, os
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.models import prompt_repo

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       seed_world(DB_PATH)

   def test_save_and_get():
       """保存和获取 Prompt"""
       prompt_repo.save_prompt("test_key", "你是一个GM。", DB_PATH)
       result = prompt_repo.get_active_prompt("test_key", DB_PATH)
       assert result == "你是一个GM。"

   def test_version_increment():
       """版本自动递增"""
       prompt_repo.save_prompt("ver_test", "v1", DB_PATH)
       prompt_repo.save_prompt("ver_test", "v2", DB_PATH)
       prompt_repo.save_prompt("ver_test", "v3", DB_PATH)
       history = prompt_repo.get_prompt_history("ver_test", DB_PATH)
       assert len(history) == 3
       assert history[0]["version"] == 3  # 最新的在前

   def test_only_latest_active():
       """只有最新版本是活跃的"""
       prompt_repo.save_prompt("active_test", "old", DB_PATH)
       prompt_repo.save_prompt("active_test", "new", DB_PATH)
       result = prompt_repo.get_active_prompt("active_test", DB_PATH)
       assert result == "new"

   def test_rollback():
       """回滚"""
       prompt_repo.save_prompt("rb_test", "v1", DB_PATH)
       prompt_repo.save_prompt("rb_test", "v2", DB_PATH)
       prompt_repo.rollback_prompt("rb_test", 1, DB_PATH)
       result = prompt_repo.get_active_prompt("rb_test", DB_PATH)
       assert result == "v1"
   ```

**验收**: `uv run pytest tests/test_prompt_repo.py -v` 全绿

---

## 步骤 4.16 - 管理端：AI 行为监控

**目的**: 实时查看每次 LLM 调用的详情

**执行**:
1. 在 `src/models/schema.sql` 中添加 LLM 调用记录表：
   ```sql
   CREATE TABLE IF NOT EXISTS llm_calls (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       world_id INTEGER,
       call_type TEXT DEFAULT 'chat',
       prompt_tokens INTEGER DEFAULT 0,
       completion_tokens INTEGER DEFAULT 0,
       total_tokens INTEGER DEFAULT 0,
       latency_ms INTEGER DEFAULT 0,
       tool_calls_count INTEGER DEFAULT 0,
       tool_names TEXT DEFAULT '[]',
       error TEXT DEFAULT '',
       created_at TEXT DEFAULT (datetime('now'))
   );
   ```
2. 创建 `src/models/metrics_repo.py`：
   ```python
   """AI 行为指标数据访问"""
   import json
   from src.services.database import get_db

   def record_llm_call(world_id: int, call_type: str = "chat",
                        prompt_tokens: int = 0, completion_tokens: int = 0,
                        latency_ms: int = 0, tool_calls_count: int = 0,
                        tool_names: list | None = None, error: str = "",
                        db_path: str | None = None) -> int:
       with get_db(db_path) as conn:
           cursor = conn.execute(
               """INSERT INTO llm_calls
                  (world_id, call_type, prompt_tokens, completion_tokens, total_tokens,
                   latency_ms, tool_calls_count, tool_names, error)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
               (world_id, call_type, prompt_tokens, completion_tokens,
                prompt_tokens + completion_tokens, latency_ms, tool_calls_count,
                json.dumps(tool_names or []), error),
           )
           return cursor.lastrowid

   def get_recent_calls(world_id: int | None = None, limit: int = 50,
                        db_path: str | None = None) -> list[dict]:
       with get_db(db_path) as conn:
           if world_id:
               rows = conn.execute(
                   "SELECT * FROM llm_calls WHERE world_id = ? ORDER BY created_at DESC LIMIT ?",
                   (world_id, limit),
               ).fetchall()
           else:
               rows = conn.execute(
                   "SELECT * FROM llm_calls ORDER BY created_at DESC LIMIT ?",
                   (limit,),
               ).fetchall()
       return [dict(r) for r in rows]

   def get_token_stats(db_path: str | None = None) -> dict:
       with get_db(db_path) as conn:
           row = conn.execute("""
               SELECT
                   COUNT(*) as total_calls,
                   COALESCE(SUM(prompt_tokens), 0) as total_prompt,
                   COALESCE(SUM(completion_tokens), 0) as total_completion,
                   COALESCE(SUM(total_tokens), 0) as total_tokens,
                   COALESCE(AVG(latency_ms), 0) as avg_latency,
                   COALESCE(SUM(CASE WHEN error != '' THEN 1 ELSE 0 END), 0) as error_count
               FROM llm_calls
           """).fetchone()
       return dict(row)
   ```
3. 在 `src/models/__init__.py` 中添加 `from src.models import metrics_repo`。
4. 修改 `src/services/llm_client.py`，在每次 API 调用后自动记录指标：
   ```python
   # 在 chat_with_tools() 和 chat() 方法中，API 调用成功后添加:
   from src.models import metrics_repo
   metrics_repo.record_llm_call(
       world_id=self._current_world_id,  # 需要在调用前设置
       call_type="chat_with_tools" if tools else "chat",
       prompt_tokens=usage.prompt_tokens,
       completion_tokens=usage.completion_tokens,
       latency_ms=elapsed_ms,
       tool_calls_count=len(message.tool_calls) if hasattr(message, 'tool_calls') and message.tool_calls else 0,
       tool_names=[tc.function.name for tc in message.tool_calls] if hasattr(message, 'tool_calls') and message.tool_calls else [],
       db_path=self.db_path,
   )
   ```
5. 创建 `src/api/routes/admin_monitor.py`：
   ```python
   """管理端 - AI 监控路由"""
   from fastapi import APIRouter
   from src.models import metrics_repo

   router = APIRouter(prefix="/api/admin/monitor", tags=["管理端-监控"])


   @router.get("/calls")
   def get_recent_calls(world_id: int | None = None, limit: int = 50):
       """获取最近的 LLM 调用记录"""
       return metrics_repo.get_recent_calls(world_id, limit)


   @router.get("/stats")
   def get_stats():
       """获取 Token 消耗统计"""
       return metrics_repo.get_token_stats()
   ```
6. 在 `src/api/app.py` 中注册路由。
7. 创建 `tests/test_metrics_repo.py`：
   ```python
   """AI 行为指标测试"""
   import tempfile, os
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.models import metrics_repo

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       seed_world(DB_PATH)

   def test_record_and_get():
       metrics_repo.record_llm_call(1, prompt_tokens=100, completion_tokens=50, latency_ms=500, db_path=DB_PATH)
       calls = metrics_repo.get_recent_calls(1, db_path=DB_PATH)
       assert len(calls) == 1
       assert calls[0]["prompt_tokens"] == 100

   def test_token_stats():
       metrics_repo.record_llm_call(1, prompt_tokens=100, completion_tokens=50, db_path=DB_PATH)
       metrics_repo.record_llm_call(1, prompt_tokens=200, completion_tokens=100, db_path=DB_PATH)
       stats = metrics_repo.get_token_stats(DB_PATH)
       assert stats["total_calls"] >= 2
       assert stats["total_tokens"] >= 450
   ```

**验收**: `uv run pytest tests/test_metrics_repo.py -v` 全绿

---

## 步骤 4.17 - 管理端：游戏数据管理 API

**目的**: 通过 API 管理 NPC/任务/道具/世界

**执行**:
1. 创建 `src/api/routes/admin_data.py`：
   ```python
   """管理端 - 游戏数据管理路由"""
   from fastapi import APIRouter, HTTPException
   from pydantic import BaseModel
   from src.models import npc_repo, quest_repo, item_repo, world_repo, player_repo

   router = APIRouter(prefix="/api/admin/data", tags=["管理端-数据"])


   # ===== NPC 管理 =====
   @router.get("/npcs")
   def list_npcs(world_id: int):
       from src.models import location_repo
       npcs = []
       for loc in location_repo.get_locations_by_world(world_id):
           npcs.extend(npc_repo.get_npcs_by_location(loc["id"]))
       return npcs

   @router.delete("/npcs/{npc_id}")
   def delete_npc(npc_id: int):
       npc_repo.delete_npc(npc_id)
       return {"message": f"NPC {npc_id} 已删除"}

   # ===== 任务管理 =====
   @router.get("/quests")
   def list_quests(world_id: int):
       return quest_repo.get_quests_by_world(world_id)

   @router.patch("/quests/{quest_id}")
   def update_quest(quest_id: int, status: str | None = None):
       if status:
           quest_repo.update_quest(quest_id, status=status)
       return {"message": "任务已更新"}

   @router.delete("/quests/{quest_id}")
   def delete_quest(quest_id: int):
       quest_repo.delete_quest(quest_id)
       return {"message": f"任务 {quest_id} 已删除"}

   # ===== 道具管理 =====
   @router.get("/items")
   def list_items(world_id: int):
       return item_repo.get_items_by_world(world_id)

   @router.delete("/items/{item_id}")
   def delete_item(item_id: int):
       item_repo.delete_item(item_id)
       return {"message": f"道具 {item_id} 已删除"}

   # ===== 玩家管理 =====
   @router.get("/players")
   def list_players(world_id: int):
       from src.services.database import get_db
       with get_db() as conn:
           rows = conn.execute("SELECT * FROM players WHERE world_id = ?", (world_id,)).fetchall()
       return [dict(r) for r in rows]

   @router.patch("/players/{player_id}")
   def update_player(player_id: int, hp: int | None = None, gold: int | None = None,
                     level: int | None = None, exp: int | None = None):
       updates = {}
       if hp is not None: updates["hp"] = hp
       if gold is not None: updates["gold"] = gold
       if level is not None: updates["level"] = level
       if exp is not None: updates["exp"] = exp
       if updates:
           player_repo.update_player(player_id, **updates)
       return {"message": "玩家已更新", "updates": updates}
   ```
2. 在 `src/api/app.py` 中注册路由。
3. 创建 `tests/test_admin_data.py`：
   ```python
   """管理端数据管理测试"""
   import tempfile, os
   from fastapi.testclient import TestClient
   from src.api.app import app
   from src.data.seed_data import seed_world
   from src.models import npc_repo

   client = TestClient(app)
   WORLD_ID = None

   def setup_module():
       global WORLD_ID
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       WORLD_ID = result["world_id"]

   def test_list_npcs():
       resp = client.get(f"/api/admin/data/npcs?world_id={WORLD_ID}")
       assert resp.status_code == 200

   def test_list_quests():
       resp = client.get(f"/api/admin/data/quests?world_id={WORLD_ID}")
       assert resp.status_code == 200

   def test_list_players():
       resp = client.get(f"/api/admin/data/players?world_id={WORLD_ID}")
       assert resp.status_code == 200
   ```

**验收**: `uv run pytest tests/test_admin_data.py -v` 全绿

---

## 步骤 4.18 - 管理端：日志和对话记录 API

**目的**: 查看完整对话历史和游戏事件日志

**执行**:
1. 创建 `src/api/routes/admin_logs.py`：
   ```python
   """管理端 - 日志和对话记录路由"""
   from fastapi import APIRouter
   from src.models import log_repo
   from src.services.database import get_db

   router = APIRouter(prefix="/api/admin/logs", tags=["管理端-日志"])


   @router.get("/game-events")
   def get_game_events(world_id: int, limit: int = 100, event_type: str | None = None):
       """获取游戏事件日志"""
       logs = log_repo.get_recent_logs(world_id, limit)
       if event_type:
           logs = [l for l in logs if l["event_type"] == event_type]
       return logs


   @router.get("/conversations")
   def get_conversations(world_id: int, limit: int = 100):
       """获取对话历史"""
       with get_db() as conn:
           rows = conn.execute(
               "SELECT * FROM game_messages WHERE world_id = ? ORDER BY timestamp ASC LIMIT ?",
               (world_id, limit),
           ).fetchall()
       return [dict(r) for r in rows]


   @router.get("/conversations/search")
   def search_conversations(world_id: int, keyword: str):
       """搜索对话内容"""
       with get_db() as conn:
           rows = conn.execute(
               "SELECT * FROM game_messages WHERE world_id = ? AND content LIKE ? ORDER BY timestamp DESC LIMIT 50",
               (world_id, f"%{keyword}%"),
           ).fetchall()
       return [dict(r) for r in rows]
   ```
2. 在 `src/api/app.py` 中注册路由。

**验收**: Swagger UI 中测试日志查询端点

---

## 步骤 4.19 - 管理端：GM 参数控制 API

**目的**: 运行时调整 GM 行为参数

**执行**:
1. 创建 `src/api/routes/admin_control.py`：
   ```python
   """管理端 - GM 参数控制路由"""
   from fastapi import APIRouter
   from pydantic import BaseModel
   from src.utils.logger import get_logger

   logger = get_logger(__name__)
   router = APIRouter(prefix="/api/admin/control", tags=["管理端-控制"])

   # 运行时参数（全局可修改）
   runtime_config = {
       "temperature": 0.7,
       "max_tool_rounds": 10,
       "max_context_messages": 100,
       "paused": False,
   }


   class ConfigUpdate(BaseModel):
       temperature: float | None = None
       max_tool_rounds: int | None = None
       max_context_messages: int | None = None
       paused: bool | None = None


   @router.get("/config")
   def get_config():
       """获取当前运行时配置"""
       return runtime_config


   @router.post("/config")
   def update_config(body: ConfigUpdate):
       """更新运行时配置（立即生效）"""
       updates = body.model_dump(exclude_none=True)
       runtime_config.update(updates)
       logger.info(f"GM 配置已更新: {updates}")
       return {"message": "配置已更新", "config": runtime_config}


   @router.post("/pause")
   def pause_gm():
       """暂停 GM（拒绝新请求）"""
       runtime_config["paused"] = True
       return {"message": "GM 已暂停"}


   @router.post("/resume")
   def resume_gm():
       """恢复 GM"""
       runtime_config["paused"] = False
       return {"message": "GM 已恢复"}
   ```
2. 在 `src/api/app.py` 中注册路由。
3. 修改 `src/agent/game_master.py`，在 `process()` 开头检查暂停状态：
   ```python
   from src.api.routes.admin_control import runtime_config

   def process(self, user_input: str) -> str:
       if runtime_config.get("paused"):
           return "（系统提示：GM 暂时不可用，请稍后再试。）"
       # ... 原有逻辑
   ```
4. 创建 `tests/test_admin_control.py`：
   ```python
   """管理端控制测试"""
   from fastapi.testclient import TestClient
   from src.api.app import app
   from src.api.routes.admin_control import runtime_config

   client = TestClient(app)

   def test_get_config():
       resp = client.get("/api/admin/control/config")
       assert resp.status_code == 200
       assert "temperature" in resp.json()

   def test_update_config():
       resp = client.post("/api/admin/control/config", json={"temperature": 0.9})
       assert resp.status_code == 200
       assert runtime_config["temperature"] == 0.9

   def test_pause_resume():
       client.post("/api/admin/control/pause")
       assert runtime_config["paused"] == True
       client.post("/api/admin/control/resume")
       assert runtime_config["paused"] == False
   ```

**验收**: `uv run pytest tests/test_admin_control.py -v` 全绿

---

## 步骤 4.20 - 管理端：Vue 3 + Naive UI 前端搭建

**目的**: 搭建管理端前端界面

**执行**:
1. 安装 Node.js 依赖（如果没装）：
   ```bash
   # 检查 Node.js 是否已安装
   node --version
   # 如果没装，参考 https://nodejs.org/
   ```
2. 创建 Vue 3 项目：
   ```bash
   cd src
   npm create vite@latest admin -- --template vue
   cd admin
   npm install
   npm install naive-ui @vicons/ionicons5 axios
   ```
3. 创建 `src/admin/src/App.vue`（主布局）：
   ```vue
   <template>
     <n-config-provider :theme="darkTheme">
       <n-layout has-sider style="height: 100vh;">
         <n-layout-sider bordered :width="220">
           <div class="logo">GM Admin</div>
           <n-menu :options="menuOptions" @update:value="handleMenuSelect" />
         </n-layout-sider>
         <n-layout>
           <n-layout-header bordered style="height: 50px; display: flex; align-items: center; padding: 0 20px;">
             <span style="font-weight: bold;">{{ currentPageTitle }}</span>
           </n-layout-header>
           <n-layout-content content-style="padding: 20px;">
             <component :is="currentComponent" />
           </n-layout-content>
         </n-layout>
       </n-layout>
     </n-config-provider>
   </template>

   <script setup>
   import { ref, computed, markRaw } from 'vue'
   import { darkTheme, NConfigProvider, NLayout, NLayoutSider, NLayoutHeader, NLayoutContent, NMenu } from 'naive-ui'
   import PromptPanel from './components/PromptPanel.vue'
   import MonitorPanel from './components/MonitorPanel.vue'
   import DataPanel from './components/DataPanel.vue'
   import LogsPanel from './components/LogsPanel.vue'
   import ControlPanel from './components/ControlPanel.vue'

   const API_BASE = '/api/admin'

   const components = {
     prompt: markRaw(PromptPanel),
     monitor: markRaw(MonitorPanel),
     data: markRaw(DataPanel),
     logs: markRaw(LogsPanel),
     control: markRaw(ControlPanel),
   }

   const currentPage = ref('prompt')
   const currentComponent = computed(() => components[currentPage.value])

   const menuOptions = [
     { label: 'Prompt 管理', key: 'prompt' },
     { label: 'AI 监控', key: 'monitor' },
     { label: '游戏数据', key: 'data' },
     { label: '日志记录', key: 'logs' },
     { label: 'GM 控制', key: 'control' },
   ]

   const currentPageTitle = computed(() => {
     return menuOptions.find(o => o.key === currentPage.value)?.label || ''
   })

   function handleMenuSelect(key) {
     currentPage.value = key
   }
   </script>

   <style>
   .logo { padding: 16px; font-size: 18px; font-weight: bold; color: #63e2b7; text-align: center; }
   </style>
   ```
4. 创建核心组件（每个组件对应一个管理功能）：

   **PromptPanel.vue**（Prompt 管理）：
   ```vue
   <template>
     <n-card title="System Prompt">
       <n-input v-model:value="promptContent" type="textarea" :rows="20" placeholder="输入 GM System Prompt..." />
       <template #action>
         <n-space>
           <n-button type="primary" @click="savePrompt" :loading="saving">应用</n-button>
           <n-button @click="loadHistory">版本历史</n-button>
         </n-space>
       </template>
     </n-card>
     <n-card v-if="showHistory" title="版本历史" style="margin-top: 16px;">
       <n-timeline>
         <n-timeline-item v-for="h in history" :key="h.id"
           :type="h.is_active ? 'success' : 'default'">
           版本 {{ h.version }} - {{ h.created_at }}
           <n-button size="small" @click="rollback(h.version)" :disabled="h.is_active">回滚</n-button>
         </n-timeline-item>
       </n-timeline>
     </n-card>
   </template>

   <script setup>
   import { ref, onMounted } from 'vue'
   import { useMessage } from 'naive-ui'

   const API = '/api/admin/prompts/game_master_system'
   const promptContent = ref('')
   const saving = ref(false)
   const showHistory = ref(false)
   const history = ref([])
   const message = useMessage()

   onMounted(async () => {
     const resp = await fetch(API)
     const data = await resp.json()
     promptContent.value = data.content || ''
   })

   async function savePrompt() {
     saving.value = true
     await fetch('/api/admin/prompts', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ prompt_key: 'game_master_system', content: promptContent.value }),
     })
     saving.value = false
     message.success('Prompt 已更新，立即生效！')
   }

   async function loadHistory() {
     const resp = await fetch(`${API}/history`)
     history.value = await resp.json()
     showHistory.value = true
   }

   async function rollback(version) {
     await fetch('/api/admin/prompts/rollback', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ prompt_key: 'game_master_system', version }),
     })
     message.success(`已回滚到版本 ${version}`)
     loadHistory()
     // 重新加载当前版本
     const resp = await fetch(API)
     const data = await resp.json()
     promptContent.value = data.content || ''
   }
   </script>
   ```

   **MonitorPanel.vue**（AI 监控）：
   ```vue
   <template>
     <n-grid :cols="4" :x-gap="12">
       <n-gi><n-statistic label="总调用次数" :value="stats.total_calls" /></n-gi>
       <n-gi><n-statistic label="总 Token" :value="stats.total_tokens" /></n-gi>
       <n-gi><n-statistic label="平均延迟(ms)" :value="Math.round(stats.avg_latency)" /></n-gi>
       <n-gi><n-statistic label="错误次数" :value="stats.error_count" /></n-gi>
     </n-grid>
     <n-card title="最近调用" style="margin-top: 16px;">
       <n-data-table :columns="columns" :data="calls" :max-height="400" />
     </n-card>
   </template>

   <script setup>
   import { ref, onMounted } from 'vue'

   const stats = ref({})
   const calls = ref([])
   const columns = [
     { title: '时间', key: 'created_at', width: 180 },
     { title: '类型', key: 'call_type', width: 120 },
     { title: 'Prompt Tokens', key: 'prompt_tokens', width: 120 },
     { title: 'Completion Tokens', key: 'completion_tokens', width: 140 },
     { title: '延迟(ms)', key: 'latency_ms', width: 100 },
     { title: '工具调用', key: 'tool_names', width: 200 },
     { title: '错误', key: 'error', width: 200 },
   ]

   onMounted(async () => {
     const [statsResp, callsResp] = await Promise.all([
       fetch('/api/admin/monitor/stats'),
       fetch('/api/admin/monitor/calls?limit=50'),
     ])
     stats.value = await statsResp.json()
     calls.value = await callsResp.json()
   })
   </script>
   ```

   **ControlPanel.vue**（GM 控制）：
   ```vue
   <template>
     <n-card title="GM 运行时参数">
       <n-form>
         <n-form-item label="Temperature">
           <n-slider v-model:value="config.temperature" :min="0" :max="2" :step="0.1" />
         </n-form-item>
         <n-form-item label="最大工具轮次">
           <n-input-number v-model:value="config.max_tool_rounds" :min="1" :max="20" />
         </n-form-item>
         <n-form-item label="最大上下文消息数">
           <n-input-number v-model:value="config.max_context_messages" :min="10" :max="200" />
         </n-form-item>
         <n-space>
           <n-button type="primary" @click="saveConfig">应用配置</n-button>
           <n-button type="warning" @click="pauseGM" v-if="!config.paused">暂停 GM</n-button>
           <n-button type="success" @click="resumeGM" v-else>恢复 GM</n-button>
         </n-space>
       </n-form>
     </n-card>
   </template>

   <script setup>
   import { ref, onMounted } from 'vue'
   import { useMessage } from 'naive-ui'

   const config = ref({})
   const message = useMessage()

   onMounted(async () => {
     const resp = await fetch('/api/admin/control/config')
     config.value = await resp.json()
   })

   async function saveConfig() {
     await fetch('/api/admin/control/config', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify(config.value),
     })
     message.success('配置已更新')
   }

   async function pauseGM() {
     await fetch('/api/admin/control/pause', { method: 'POST' })
     config.value.paused = true
     message.warning('GM 已暂停')
   }

   async function resumeGM() {
     await fetch('/api/admin/control/resume', { method: 'POST' })
     config.value.paused = false
     message.success('GM 已恢复')
   }
   </script>
   ```

5. 创建 DataPanel.vue 和 LogsPanel.vue（类似结构，调用对应 API）。
6. 构建前端：
   ```bash
   cd src/admin
   npm run build
   ```
7. 在 `src/api/app.py` 中挂载管理端静态文件：
   ```python
   from pathlib import Path
   admin_dist = Path(__file__).parent.parent / "admin" / "dist"
   if admin_dist.exists():
       app.mount("/admin", StaticFiles(directory=str(admin_dist), html=True), name="admin")
   ```
8. 访问 http://localhost:8000/admin 查看管理端。

**验收**: http://localhost:8000/admin 显示管理端界面，5 个功能面板可切换

---

## ★ P4' 里程碑验收

运行完整测试套件：

```bash
uv run pytest tests/ -v
```

逐项确认：

**API 层（4.1-4.14）**
- [ ] 4.1 API 设计文档完成
- [ ] 4.2 FastAPI 能启动，Swagger UI 可访问
- [ ] 4.3 世界管理路由通过单测
- [ ] 4.4 玩家路由通过单测
- [ ] 4.5 游戏行动路由通过单测
- [ ] 4.6 WebSocket 双向通信正常
- [ ] 4.7 连接管理正常
- [ ] 4.8 认证和错误处理正常
- [ ] 4.9 前端连接真实后端
- [ ] 4.10 战斗 UI 完整
- [ ] 4.11 分支选择 UI 正常
- [ ] 4.12 静态文件服务正常
- [ ] 4.13 API 文档完整
- [ ] 4.14 API 综合测试通过

**管理端（4.15-4.20）**
- [ ] 4.15 Prompt 管理系统通过单测（版本/回滚/热更新）
- [ ] 4.16 AI 行为监控通过单测（调用记录/Token 统计）
- [ ] 4.17 游戏数据管理 API 通过单测
- [ ] 4.18 日志和对话记录 API 正常
- [ ] 4.19 GM 参数控制通过单测（暂停/恢复/配置）
- [ ] 4.20 管理端 Vue 前端可访问

**全部 ✅ 后，P4' 阶段完成！Game Master Agent 拥有完整的 Web 应用 + 管理后台！** 🎉

---

## P4' 完成后的项目结构

```
game-master-agent/
├── src/
│   ├── api/
│   │   ├── app.py                     # ★ FastAPI 应用入口
│   │   ├── auth.py                    # API Key 认证
│   │   ├── exceptions.py              # 自定义异常
│   │   ├── connection_manager.py      # WebSocket 连接管理
│   │   └── routes/
│   │       ├── worlds.py              # 世界管理路由
│   │       ├── player.py              # 玩家路由
│   │       ├── action.py              # 游戏行动路由
│   │       ├── ws.py                  # WebSocket 路由
│   │       ├── admin_prompts.py       # ★ 管理端-Prompt 管理
│   │       ├── admin_monitor.py       # ★ 管理端-AI 监控
│   │       ├── admin_data.py          # ★ 管理端-游戏数据
│   │       ├── admin_logs.py          # ★ 管理端-日志记录
│   │       └── admin_control.py       # ★ 管理端-GM 控制
│   ├── admin/                         # ★ Vue 3 管理端前端
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   ├── dist/                      # 构建产物
│   │   └── src/
│   │       ├── App.vue
│   │       └── components/
│   │           ├── PromptPanel.vue    # Prompt 编辑器
│   │           ├── MonitorPanel.vue   # AI 监控面板
│   │           ├── DataPanel.vue      # 游戏数据管理
│   │           ├── LogsPanel.vue      # 日志记录
│   │           └── ControlPanel.vue   # GM 参数控制
│   ├── agent/
│   │   └── game_master.py
│   ├── tools/
│   ├── models/
│   │   ├── prompt_repo.py             # ★ Prompt 版本管理
│   │   ├── metrics_repo.py            # ★ AI 行为指标
│   │   └── ...
│   ├── services/
│   ├── data/
│   ├── web/                           # 玩家端 MUD 前端
│   └── cli.py
├── docs/
│   └── api_design.md
└── tests/                             # 140+个测试
```
