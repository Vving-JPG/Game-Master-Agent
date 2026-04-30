# V2 引擎适配层设计

> **版本**: v2.0-draft
> **日期**: 2026-04-28
> **前置文档**: `architecture_v2.md`, `communication_protocol.md`
> **关联文档**: `memory_system.md`

---

## 1. 设计理念

### 1.1 为什么需要适配层？

V2 的核心目标是**通用游戏驱动 Agent**。Agent 不应该绑定到任何特定的游戏引擎。适配层将 Agent 与引擎解耦：

```
┌──────────┐         ┌──────────────┐         ┌──────────┐
│  MUD     │         │              │         │          │
│  (Text)  │◄───────►│  Engine      │◄───────►│  Agent   │
│          │         │  Adapter     │         │  Service │
├──────────┤         │  (抽象层)    │         │          │
│  Godot   │         │              │         │          │
│  (HTTP)  │◄───────►│              │         │          │
└──────────┘         └──────────────┘         └──────────┘
```

Agent 只与 `EngineAdapter` 接口交互，不关心背后是 MUD、Godot 还是其他引擎。

### 1.2 适配层职责

| 职责 | 说明 |
|------|------|
| **连接管理** | 建立和维持与引擎的连接 |
| **事件接收** | 接收引擎发来的玩家操作、状态变化等事件 |
| **指令发送** | 将 Agent 的 commands 发送给引擎执行 |
| **状态查询** | 查询引擎当前游戏状态 |
| **结果返回** | 返回指令执行结果（成功/拒绝/错误） |
| **格式转换** | 将引擎特有格式转换为标准 JSON 协议 |

---

## 2. EngineAdapter 抽象接口

### 2.1 接口定义

```python
from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Optional
from dataclasses import dataclass, field
from enum import Enum


class ConnectionStatus(str, Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class EngineEvent:
    """标准引擎事件（引擎 → Agent）"""
    event_id: str
    timestamp: str
    type: str  # player_action, combat_start, etc.
    data: dict  # 事件数据
    context_hints: list[str] = field(default_factory=list)
    game_state: dict = field(default_factory=dict)


@dataclass
class CommandResult:
    """单条指令执行结果"""
    intent: str
    status: str  # success, rejected, partial, error
    new_value: Optional[any] = None
    state_changes: Optional[dict] = None
    reason: Optional[str] = None
    suggestion: Optional[str] = None


# 事件回调类型
EventCallback = Callable[[EngineEvent], Awaitable[None]]


class EngineAdapter(ABC):
    """
    引擎适配器抽象基类。

    所有引擎适配器必须实现此接口。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称，如 'text', 'godot'"""
        ...

    @property
    @abstractmethod
    def connection_status(self) -> ConnectionStatus:
        """当前连接状态"""
        ...

    @abstractmethod
    async def connect(self) -> None:
        """
        建立与引擎的连接。

        Raises:
            ConnectionError: 连接失败
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """断开与引擎的连接"""
        ...

    @abstractmethod
    async def send_commands(self, commands: list[dict]) -> list[CommandResult]:
        """
        发送指令到引擎并等待结果。

        :param commands: Agent 生成的指令列表
        :return: 每条指令的执行结果列表
        """
        ...

    @abstractmethod
    async def subscribe_events(
        self,
        event_types: list[str],
        callback: EventCallback
    ) -> None:
        """
        订阅引擎事件。

        :param event_types: 要订阅的事件类型列表，空列表表示订阅所有
        :param callback: 事件到达时的回调函数
        """
        ...

    @abstractmethod
    async def query_state(self, query: dict) -> dict:
        """
        查询引擎当前状态。

        :param query: 查询参数，如 {"type": "player_stats", "player_id": "p1"}
        :return: 查询结果
        """
        ...

    async def health_check(self) -> dict:
        """
        健康检查。

        :return: {"status": "ok", "adapter": self.name, "latency_ms": ...}
        """
        import time
        start = time.time()
        try:
            state = await self.query_state({"type": "ping"})
            latency = int((time.time() - start) * 1000)
            return {"status": "ok", "adapter": self.name, "latency_ms": latency}
        except Exception as e:
            return {"status": "error", "adapter": self.name, "error": str(e)}
```

---

## 3. TextAdapter 实现 (MUD 演示)

### 3.1 设计说明

TextAdapter 是 V2 的首要适配器，用于 MUD 文字游戏演示。

- **连接方式**: 本地进程内调用（不需要网络）
- **事件来源**: 命令行输入（玩家输入文本）
- **指令执行**: 直接调用 V1 的现有 Python 函数
- **状态存储**: 使用 V1 的 SQLite 数据库

### 3.2 完整实现

```python
import asyncio
import uuid
from datetime import datetime
from typing import Callable, Awaitable

from .base import (
    EngineAdapter, EngineEvent, CommandResult,
    ConnectionStatus, EventCallback
)


class TextAdapter(EngineAdapter):
    """
    MUD 文字游戏适配器。

    直接在进程内运行，通过命令行与玩家交互。
    复用 V1 的 SQLite 数据层执行指令。
    """

    def __init__(self, world_service, player_service, npc_service, item_service, quest_service):
        """
        :param world_service: V1 WorldService 实例
        :param player_service: V1 PlayerService 实例
        :param npc_service: V1 NPCService 实例
        :param item_service: V1 ItemService 实例
        :param quest_service: V1 QuestService 实例
        """
        self._world = world_service
        self._player = player_service
        self._npc = npc_service
        self._item = item_service
        self._quest = quest_service

        self._status = ConnectionStatus.DISCONNECTED
        self._event_callback: EventCallback = None
        self._event_types: list[str] = []
        self._player_id: str = None
        self._world_id: str = None

    @property
    def name(self) -> str:
        return "text"

    @property
    def connection_status(self) -> ConnectionStatus:
        return self._status

    async def connect(self, world_id: str = None, player_id: str = None) -> None:
        """连接到 MUD 世界"""
        self._status = ConnectionStatus.CONNECTING

        try:
            # 如果没有指定 world_id，使用默认世界
            if world_id:
                self._world_id = world_id
            else:
                worlds = self._world.list_worlds()
                if worlds:
                    self._world_id = worlds[0]["id"]
                else:
                    raise ConnectionError("没有可用的游戏世界")

            # 如果没有指定 player_id，使用默认玩家
            if player_id:
                self._player_id = player_id
            else:
                players = self._player.list_players(self._world_id)
                if players:
                    self._player_id = players[0]["id"]
                else:
                    raise ConnectionError("没有可用的玩家角色")

            self._status = ConnectionStatus.CONNECTED

        except Exception as e:
            self._status = ConnectionStatus.ERROR
            raise ConnectionError(f"连接失败: {e}")

    async def disconnect(self) -> None:
        """断开连接"""
        self._status = ConnectionStatus.DISCONNECTED
        self._player_id = None
        self._world_id = None

    async def send_commands(self, commands: list[dict]) -> list[CommandResult]:
        """
        执行 Agent 的指令。

        将标准 intent 映射到 V1 的 Service 层调用。
        """
        results = []

        for cmd in commands:
            intent = cmd.get("intent", "no_op")
            params = cmd.get("params", {})

            try:
                result = await self._execute_intent(intent, params)
                results.append(result)
            except Exception as e:
                results.append(CommandResult(
                    intent=intent,
                    status="error",
                    reason=str(e)
                ))

        return results

    async def _execute_intent(self, intent: str, params: dict) -> CommandResult:
        """将 intent 路由到对应的 V1 Service 方法"""

        # ===== NPC 相关 =====
        if intent == "update_npc_relationship":
            npc_id = params["npc_id"]
            change = params.get("change", 0)
            npc = self._npc.get_npc(self._world_id, npc_id)
            if not npc:
                return CommandResult(intent=intent, status="rejected", reason=f"NPC not found: {npc_id}")
            new_rel = max(0, min(100, npc.get("relationship", 0) + change))
            self._npc.update_npc(self._world_id, npc_id, {"relationship": new_rel})
            return CommandResult(
                intent=intent, status="success", new_value=new_rel,
                state_changes={
                    "file": f"npcs/{npc.get('name', npc_id)}.md",
                    "frontmatter": {
                        "relationship_with_player": new_rel,
                        "version": npc.get("version", 0) + 1,
                        "last_modified": datetime.now().isoformat(),
                        "modified_by": "engine"
                    }
                }
            )

        elif intent == "update_npc_state":
            npc_id = params["npc_id"]
            field_name = params["field"]
            value = params["value"]
            npc = self._npc.get_npc(self._world_id, npc_id)
            if not npc:
                return CommandResult(intent=intent, status="rejected", reason=f"NPC not found: {npc_id}")
            self._npc.update_npc(self._world_id, npc_id, {field_name: value})
            return CommandResult(
                intent=intent, status="success", new_value=value,
                state_changes={
                    "file": f"npcs/{npc.get('name', npc_id)}.md",
                    "frontmatter": {
                        field_name: value,
                        "version": npc.get("version", 0) + 1,
                        "last_modified": datetime.now().isoformat(),
                        "modified_by": "engine"
                    }
                }
            )

        # ===== 任务相关 =====
        elif intent == "offer_quest":
            quest_data = {
                "title": params["title"],
                "description": params.get("description", ""),
                "objective": params.get("objective", ""),
                "reward": params.get("reward", ""),
                "status": "active"
            }
            quest_id = self._quest.create_quest(self._world_id, quest_data)
            return CommandResult(
                intent=intent, status="success",
                new_value=quest_id,
                state_changes={
                    "file": f"quests/{params['quest_id']}.md",
                    "frontmatter": {
                        "status": "active",
                        "version": 1,
                        "last_modified": datetime.now().isoformat(),
                        "modified_by": "engine"
                    }
                }
            )

        elif intent == "update_quest":
            quest_id = params["quest_id"]
            self._quest.update_quest(self._world_id, quest_id, {
                "status": params.get("status"),
                "progress": params.get("progress")
            })
            return CommandResult(
                intent=intent, status="success",
                state_changes={
                    "file": f"quests/{quest_id}.md",
                    "frontmatter": {
                        "status": params.get("status"),
                        "version": 0,  # 由 MemoryManager 递增
                        "last_modified": datetime.now().isoformat(),
                        "modified_by": "engine"
                    }
                }
            )

        # ===== 物品相关 =====
        elif intent == "give_item":
            item_data = {
                "name": params.get("name", params["item_id"]),
                "type": params.get("type", "misc"),
                "player_id": self._player_id
            }
            self._item.create_item(self._world_id, item_data)
            return CommandResult(intent=intent, status="success")

        elif intent == "remove_item":
            self._item.delete_item(self._world_id, params["item_id"])
            return CommandResult(intent=intent, status="success")

        # ===== 玩家相关 =====
        elif intent == "modify_stat":
            player = self._player.get_player(self._world_id, self._player_id)
            stat = params["stat"]
            change = params.get("change", 0)
            new_value = player.get(stat, 0) + change
            self._player.update_player(self._world_id, self._player_id, {stat: new_value})
            return CommandResult(
                intent=intent, status="success", new_value=new_value,
                state_changes={
                    "file": "player/profile.md",
                    "frontmatter": {
                        stat: new_value,
                        "version": player.get("version", 0) + 1,
                        "last_modified": datetime.now().isoformat(),
                        "modified_by": "engine"
                    }
                }
            )

        # ===== 地点相关 =====
        elif intent == "update_location":
            # V1 没有独立的 location service，记录到日志
            return CommandResult(intent=intent, status="success", new_value=params.get("value"))

        elif intent == "teleport_player":
            self._player.update_player(self._world_id, self._player_id, {
                "location": params["location_id"]
            })
            return CommandResult(intent=intent, status="success")

        # ===== 通知类 =====
        elif intent == "show_notification":
            # MUD 模式下直接打印到控制台
            print(f"[通知] {params.get('message', '')}")
            return CommandResult(intent=intent, status="success")

        elif intent == "play_sound":
            # MUD 模式下无音效，忽略
            return CommandResult(intent=intent, status="success")

        elif intent == "no_op":
            return CommandResult(intent=intent, status="success")

        else:
            return CommandResult(
                intent=intent, status="rejected",
                reason=f"Unknown intent: {intent}",
                suggestion="Check available intents in Skill files"
            )

    async def subscribe_events(
        self,
        event_types: list[str],
        callback: EventCallback
    ) -> None:
        """TextAdapter 不需要订阅，事件由命令行输入触发"""
        self._event_callback = callback
        self._event_types = event_types

    async def query_state(self, query: dict) -> dict:
        """查询当前游戏状态"""
        query_type = query.get("type", "ping")

        if query_type == "ping":
            return {"pong": True}

        elif query_type == "player_stats":
            player = self._player.get_player(self._world_id, self._player_id)
            return player or {}

        elif query_type == "world_info":
            world = self._world.get_world(self._world_id)
            return world or {}

        elif query_type == "npc_list":
            npcs = self._npc.list_npcs(self._world_id)
            return {"npcs": npcs}

        elif query_type == "quest_list":
            quests = self._quest.list_quests(self._world_id)
            return {"quests": quests}

        else:
            return {"error": f"Unknown query type: {query_type}"}

    async def handle_player_input(self, raw_text: str) -> EngineEvent:
        """
        处理玩家命令行输入，转换为标准 EngineEvent。

        这是 TextAdapter 特有的方法，由命令行循环调用。
        """
        # 简单的关键词检测来确定事件类型
        event_type = "player_action"

        # 检测移动意图
        move_keywords = ["去", "走", "前往", "移动", "进入", "离开"]
        if any(kw in raw_text for kw in move_keywords):
            event_type = "player_move"

        # 检测战斗意图
        combat_keywords = ["攻击", "战斗", "打", "杀", "使用技能"]
        if any(kw in raw_text for kw in combat_keywords):
            event_type = "combat_start"

        # 生成 context_hints（简单关键词匹配）
        context_hints = []
        player = self._player.get_player(self._world_id, self._player_id)
        if player:
            current_location = player.get("location", "")
            if current_location:
                context_hints.append(f"locations/{current_location}")

        # 检查是否提到了 NPC
        npcs = self._npc.list_npcs(self._world_id)
        for npc in npcs:
            if npc.get("name", "") in raw_text:
                context_hints.append(f"npcs/{npc['name']}")

        # 获取 game_state 快照
        game_state = {}
        if player:
            game_state = {
                "location": player.get("location", "unknown"),
                "player_hp": player.get("hp", 100),
                "player_level": player.get("level", 1)
            }

        event = EngineEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(),
            type=event_type,
            data={"raw_text": raw_text, "player_id": self._player_id},
            context_hints=context_hints,
            game_state=game_state
        )

        # 触发回调
        if self._event_callback:
            await self._event_callback(event)

        return event
```

### 3.3 TextAdapter 命令行循环

```python
import asyncio


async def run_text_mode(adapter: TextAdapter, event_handler):
    """
    MUD 文字模式主循环。

    1. 连接到游戏世界
    2. 等待玩家输入
    3. 将输入转换为 EngineEvent
    4. 交给 EventHandler 处理
    5. 输出 Agent 的 narrative
    """
    await adapter.connect()

    print("=" * 50)
    print("  通用游戏驱动 Agent - MUD 演示模式")
    print("  输入 'quit' 退出")
    print("=" * 50)
    print()

    while True:
        try:
            raw_text = input("\n> ").strip()

            if not raw_text:
                continue

            if raw_text.lower() in ("quit", "exit", "q"):
                print("再见！")
                break

            # 将玩家输入转换为事件
            event = await adapter.handle_player_input(raw_text)

            # 交给 EventHandler 处理（异步，不阻塞输入）
            # EventHandler 会调用 Agent，Agent 返回 narrative
            response = await event_handler(event)

            # 输出 narrative
            if response and response.get("narrative"):
                print(f"\n{response['narrative']}")

        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n[错误] {e}")

    await adapter.disconnect()
```

---

## 4. GodotAdapter 设计 (V3)

### 4.1 架构概览

GodotAdapter 通过 HTTP API 与 Godot 游戏引擎通信：

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│              │  HTTP   │              │  JSON   │              │
│   Godot      │◄───────►│  Godot       │◄───────►│  Agent       │
│   Game       │  REST   │  Adapter     │  协议   │  Service     │
│              │         │              │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
     │                         │
     │                         │
  Godot 端插件            FastAPI 端
  (GDScript)             (Python)
```

### 4.2 Godot 端接口设计

Godot 游戏端需要实现以下 HTTP 端点（由 GDScript 插件提供）：

```
# Godot 端提供的 API（Agent 调用 Godot）

POST /godot/commands
# 接收 Agent 的指令列表，执行后返回结果
# Body: {"commands": [{intent, params}, ...]}
# Response: {"results": [{intent, status, new_value, state_changes}, ...]}

GET /godot/state?query=player_stats
# 查询游戏状态
# Response: {"hp": 85, "level": 3, ...}

POST /godot/events
# Agent 主动触发游戏事件（如生成 NPC、播放音效）
# Body: {"event_type": "spawn_npc", "params": {...}}
```

### 4.3 GodotAdapter 实现框架

```python
import aiohttp
from .base import (
    EngineAdapter, EngineEvent, CommandResult,
    ConnectionStatus, EventCallback
)


class GodotAdapter(EngineAdapter):
    """
    Godot 游戏引擎适配器 (V3)。

    通过 HTTP API 与 Godot 游戏通信。
    """

    def __init__(self, godot_base_url: str = "http://localhost:8080"):
        self._base_url = godot_base_url.rstrip("/")
        self._status = ConnectionStatus.DISCONNECTED
        self._session: aiohttp.ClientSession = None

    @property
    def name(self) -> str:
        return "godot"

    @property
    def connection_status(self) -> ConnectionStatus:
        return self._status

    async def connect(self) -> None:
        """通过健康检查确认 Godot 端可用"""
        self._status = ConnectionStatus.CONNECTING
        self._session = aiohttp.ClientSession()

        try:
            async with self._session.get(
                f"{self._base_url}/godot/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    self._status = ConnectionStatus.CONNECTED
                else:
                    raise ConnectionError(f"Godot returned status {resp.status}")
        except Exception as e:
            self._status = ConnectionStatus.ERROR
            self._session = None
            raise ConnectionError(f"无法连接到 Godot: {e}")

    async def disconnect(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        self._status = ConnectionStatus.DISCONNECTED

    async def send_commands(self, commands: list[dict]) -> list[CommandResult]:
        """通过 HTTP 发送指令到 Godot"""
        if not self._session:
            raise ConnectionError("未连接到 Godot")

        async with self._session.post(
            f"{self._base_url}/godot/commands",
            json={"commands": commands},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            data = await resp.json()

        results = []
        for r in data.get("results", []):
            results.append(CommandResult(
                intent=r.get("intent", ""),
                status=r.get("status", "error"),
                new_value=r.get("new_value"),
                state_changes=r.get("state_changes"),
                reason=r.get("reason"),
                suggestion=r.get("suggestion")
            ))

        return results

    async def subscribe_events(
        self,
        event_types: list[str],
        callback: EventCallback
    ) -> None:
        """
        订阅 Godot 事件。

        Godot 通过 POST /api/agent/event 将事件推送到 Agent。
        此方法注册回调，由 FastAPI 路由调用。
        """
        # GodotAdapter 的事件订阅通过 Agent 的 HTTP API 实现
        # Godot 端调用 POST /api/agent/event 发送事件
        # FastAPI 路由将事件转发到此处注册的 callback
        self._event_callback = callback
        self._event_types = event_types

    async def query_state(self, query: dict) -> dict:
        """查询 Godot 游戏状态"""
        if not self._session:
            raise ConnectionError("未连接到 Godot")

        async with self._session.get(
            f"{self._base_url}/godot/state",
            params=query,
            timeout=aiohttp.ClientTimeout(total=5)
        ) as resp:
            return await resp.json()
```

### 4.4 Godot 端 GDScript 插件 (参考设计)

```gdscript
# Godot 端 Agent 插件 (GDScript)
# 文件: addons/agent_plugin/agent_connection.gd

extends Node

var http_request: HTTPRequest
var agent_url: String = "http://localhost:8000"

func _ready():
    http_request = HTTPRequest.new()
    add_child(http_request)
    http_request.request_completed.connect(_on_request_completed)

# 将玩家操作发送给 Agent
func send_player_action(action_text: String, context_hints: Array = []):
    var event = {
        "event_id": "evt_" + str(Time.get_ticks_msec()),
        "timestamp": Time.get_datetime_string_from_system(),
        "type": "player_action",
        "data": {
            "raw_text": action_text,
            "player_id": Game.player_id
        },
        "context_hints": context_hints,
        "game_state": _get_game_state_snapshot()
    }
    _post_to_agent("/api/agent/event", event)

# 接收 Agent 的指令
func _receive_commands(commands: Array):
    var results = []
    for cmd in commands:
        var result = _execute_command(cmd)
        results.append(result)

    # 将结果返回给 Agent
    _post_to_agent("/api/agent/command_results", {
        "results": results
    })

# 执行单条指令
func _execute_command(cmd: Dictionary) -> Dictionary:
    var intent = cmd.get("intent", "no_op")
    var params = cmd.get("params", {})

    match intent:
        "modify_stat":
            var stat = params.get("stat", "")
            var change = params.get("change", 0)
            Game.player.set(stat, Game.player.get(stat, 0) + change)
            return {"intent": intent, "status": "success", "new_value": Game.player.get(stat)}

        "show_notification":
            UI.show_notification(params.get("message", ""), params.get("type", "info"))
            return {"intent": intent, "status": "success"}

        "play_sound":
            Audio.play(params.get("sound_id", ""))
            return {"intent": intent, "status": "success"}

        "update_npc_state":
            var npc_id = params.get("npc_id", "")
            var npc = Game.get_npc(npc_id)
            if npc:
                npc.set(params.get("field", ""), params.get("value"))
                return {"intent": intent, "status": "success"}
            return {"intent": intent, "status": "rejected", "reason": "NPC not found"}

        _:
            return {"intent": intent, "status": "rejected", "reason": "Unsupported intent"}
```

---

## 5. 适配器注册与管理

### 5.1 AdapterRegistry

```python
from typing import Optional


class AdapterRegistry:
    """适配器注册表，管理所有可用的引擎适配器"""

    def __init__(self):
        self._adapters: dict[str, EngineAdapter] = {}

    def register(self, adapter: EngineAdapter) -> None:
        """注册适配器"""
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> Optional[EngineAdapter]:
        """获取适配器"""
        return self._adapters.get(name)

    def list_adapters(self) -> list[dict]:
        """列出所有适配器及其状态"""
        return [
            {
                "name": adapter.name,
                "status": adapter.connection_status.value
            }
            for adapter in self._adapters.values()
        ]

    async def connect(self, name: str, **kwargs) -> EngineAdapter:
        """连接到指定适配器"""
        adapter = self.get(name)
        if not adapter:
            raise ValueError(f"Unknown adapter: {name}")
        await adapter.connect(**kwargs)
        return adapter

    async def disconnect_all(self) -> None:
        """断开所有适配器"""
        for adapter in self._adapters.values():
            if adapter.connection_status != ConnectionStatus.DISCONNECTED:
                await adapter.disconnect()
```

### 5.2 使用示例

```python
# 初始化
registry = AdapterRegistry()

# 注册适配器
text_adapter = TextAdapter(
    world_service=world_svc,
    player_service=player_svc,
    npc_service=npc_svc,
    item_service=item_svc,
    quest_service=quest_svc
)
registry.register(text_adapter)

# V3 时注册 Godot 适配器
# godot_adapter = GodotAdapter("http://localhost:8080")
# registry.register(godot_adapter)

# 连接
await registry.connect("text", world_id="world_001")

# 使用
adapter = registry.get("text")
results = await adapter.send_commands([
    {"intent": "modify_stat", "params": {"stat": "hp", "change": -10}}
])
```

---

## 6. 测试要点

```python
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestEngineAdapter:
    """引擎适配层测试"""

    def test_text_adapter_name(self):
        """TextAdapter 应返回正确名称"""
        adapter = TextAdapter(
            world_service=MagicMock(),
            player_service=MagicMock(),
            npc_service=MagicMock(),
            item_service=MagicMock(),
            quest_service=MagicMock()
        )
        assert adapter.name == "text"

    @pytest.mark.asyncio
    async def test_text_adapter_connect_success(self):
        """TextAdapter 连接成功应设置状态为 CONNECTED"""
        adapter = TextAdapter(
            world_service=MagicMock(),
            player_service=MagicMock(),
            npc_service=MagicMock(),
            item_service=MagicMock(),
            quest_service=MagicMock()
        )
        # Mock 返回数据
        adapter._world.list_worlds.return_value = [{"id": "w1"}]
        adapter._player.list_players.return_value = [{"id": "p1"}]

        await adapter.connect()
        assert adapter.connection_status == ConnectionStatus.CONNECTED
        assert adapter._world_id == "w1"
        assert adapter._player_id == "p1"

    @pytest.mark.asyncio
    async def test_text_adapter_connect_no_world(self):
        """没有可用世界时应抛出 ConnectionError"""
        adapter = TextAdapter(
            world_service=MagicMock(),
            player_service=MagicMock(),
            npc_service=MagicMock(),
            item_service=MagicMock(),
            quest_service=MagicMock()
        )
        adapter._world.list_worlds.return_value = []

        with pytest.raises(ConnectionError, match="没有可用的游戏世界"):
            await adapter.connect()

    @pytest.mark.asyncio
    async def test_send_commands_no_op(self):
        """no_op 指令应返回 success"""
        adapter = TextAdapter(
            world_service=MagicMock(),
            player_service=MagicMock(),
            npc_service=MagicMock(),
            item_service=MagicMock(),
            quest_service=MagicMock()
        )
        results = await adapter.send_commands([{"intent": "no_op", "params": {}}])
        assert len(results) == 1
        assert results[0].status == "success"

    @pytest.mark.asyncio
    async def test_send_commands_unknown_intent(self):
        """未知 intent 应返回 rejected"""
        adapter = TextAdapter(
            world_service=MagicMock(),
            player_service=MagicMock(),
            npc_service=MagicMock(),
            item_service=MagicMock(),
            quest_service=MagicMock()
        )
        results = await adapter.send_commands([
            {"intent": "fly_to_moon", "params": {}}
        ])
        assert results[0].status == "rejected"
        assert "Unknown intent" in results[0].reason

    @pytest.mark.asyncio
    async def test_update_npc_relationship(self):
        """更新 NPC 好感度应返回正确结果"""
        adapter = TextAdapter(
            world_service=MagicMock(),
            player_service=MagicMock(),
            npc_service=MagicMock(),
            item_service=MagicMock(),
            quest_service=MagicMock()
        )
        adapter._npc.get_npc.return_value = {
            "id": "npc_1", "name": "铁匠", "relationship": 30, "version": 3
        }

        results = await adapter.send_commands([
            {"intent": "update_npc_relationship", "params": {"npc_id": "npc_1", "change": 5}}
        ])
        assert results[0].status == "success"
        assert results[0].new_value == 35
        assert results[0].state_changes is not None

    def test_registry_register_and_get(self):
        """注册表应正确注册和获取适配器"""
        registry = AdapterRegistry()
        mock_adapter = MagicMock(spec=EngineAdapter)
        mock_adapter.name = "test"
        registry.register(mock_adapter)
        assert registry.get("test") is mock_adapter
        assert registry.get("nonexistent") is None
```
