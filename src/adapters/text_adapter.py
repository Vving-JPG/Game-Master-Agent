"""
MUD 文字游戏适配器。复用 V1 的 SQLite 数据层。
"""
import uuid
from datetime import datetime

from src.adapters.base import (
    EngineAdapter, EngineEvent, CommandResult,
    ConnectionStatus, EventCallback
)


class TextAdapter(EngineAdapter):
    """MUD 文字游戏适配器"""

    def __init__(self, world_service, player_service, npc_service,
                 item_service, quest_service):
        self._world = world_service
        self._player = player_service
        self._npc = npc_service
        self._item = item_service
        self._quest = quest_service
        self._status = ConnectionStatus.DISCONNECTED
        self._event_callback: EventCallback = None
        self._player_id: str = None
        self._world_id: str = None

    @property
    def name(self) -> str:
        return "text"

    @property
    def connection_status(self) -> ConnectionStatus:
        return self._status

    async def connect(self, world_id: str = None, player_id: str = None) -> None:
        self._status = ConnectionStatus.CONNECTING
        try:
            if world_id:
                self._world_id = world_id
            else:
                worlds = self._world.list_worlds()
                if worlds:
                    self._world_id = worlds[0]["id"]
                else:
                    raise ConnectionError("没有可用的游戏世界")
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
        self._status = ConnectionStatus.DISCONNECTED
        self._player_id = None
        self._world_id = None

    async def send_commands(self, commands: list[dict]) -> list[CommandResult]:
        results = []
        for cmd in commands:
            intent = cmd.get("intent", "no_op")
            params = cmd.get("params", {})
            try:
                result = await self._execute_intent(intent, params)
                results.append(result)
            except Exception as e:
                results.append(CommandResult(intent=intent, status="error", reason=str(e)))
        return results

    async def _execute_intent(self, intent: str, params: dict) -> CommandResult:
        now = datetime.now().isoformat()

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
                state_changes={"file": f"npcs/{npc.get('name', npc_id)}.md",
                    "frontmatter": {"relationship_with_player": new_rel,
                        "version": npc.get("version", 0) + 1,
                        "last_modified": now, "modified_by": "engine"}})

        elif intent == "update_npc_state":
            npc_id = params["npc_id"]
            npc = self._npc.get_npc(self._world_id, npc_id)
            if not npc:
                return CommandResult(intent=intent, status="rejected", reason=f"NPC not found: {npc_id}")
            self._npc.update_npc(self._world_id, npc_id, {params["field"]: params["value"]})
            return CommandResult(
                intent=intent, status="success", new_value=params["value"],
                state_changes={"file": f"npcs/{npc.get('name', npc_id)}.md",
                    "frontmatter": {params["field"]: params["value"],
                        "version": npc.get("version", 0) + 1,
                        "last_modified": now, "modified_by": "engine"}})

        elif intent == "offer_quest":
            quest_id = self._quest.create_quest(self._world_id, {
                "title": params["title"], "description": params.get("description", ""),
                "objective": params.get("objective", ""), "reward": params.get("reward", ""),
                "status": "active"})
            return CommandResult(intent=intent, status="success", new_value=quest_id,
                state_changes={"file": f"quests/{params.get('quest_id', quest_id)}.md",
                    "frontmatter": {"status": "active", "version": 1,
                        "last_modified": now, "modified_by": "engine"}})

        elif intent == "update_quest":
            self._quest.update_quest(self._world_id, params["quest_id"],
                {"status": params.get("status"), "progress": params.get("progress")})
            return CommandResult(intent=intent, status="success",
                state_changes={"file": f"quests/{params['quest_id']}.md",
                    "frontmatter": {"status": params.get("status"), "version": 0,
                        "last_modified": now, "modified_by": "engine"}})

        elif intent == "give_item":
            self._item.create_item(self._world_id, {
                "name": params.get("name", params.get("item_id", "")),
                "type": params.get("type", "misc"), "player_id": self._player_id})
            return CommandResult(intent=intent, status="success")

        elif intent == "remove_item":
            self._item.delete_item(self._world_id, params["item_id"])
            return CommandResult(intent=intent, status="success")

        elif intent == "modify_stat":
            player = self._player.get_player(self._world_id, self._player_id)
            stat = params["stat"]
            new_val = player.get(stat, 0) + params.get("change", 0)
            self._player.update_player(self._world_id, self._player_id, {stat: new_val})
            return CommandResult(intent=intent, status="success", new_value=new_val,
                state_changes={"file": "player/profile.md",
                    "frontmatter": {stat: new_val,
                        "version": player.get("version", 0) + 1,
                        "last_modified": now, "modified_by": "engine"}})

        elif intent == "teleport_player":
            self._player.update_player(self._world_id, self._player_id,
                {"location": params["location_id"]})
            return CommandResult(intent=intent, status="success")

        elif intent == "show_notification":
            print(f"[通知] {params.get('message', '')}")
            return CommandResult(intent=intent, status="success")

        elif intent in ("play_sound", "no_op"):
            return CommandResult(intent=intent, status="success")

        else:
            return CommandResult(intent=intent, status="rejected",
                reason=f"Unknown intent: {intent}")

    async def subscribe_events(self, event_types: list[str], callback: EventCallback) -> None:
        self._event_callback = callback

    async def query_state(self, query: dict) -> dict:
        qt = query.get("type", "ping")
        if qt == "ping":
            return {"pong": True}
        elif qt == "player_stats":
            return self._player.get_player(self._world_id, self._player_id) or {}
        elif qt == "world_info":
            return self._world.get_world(self._world_id) or {}
        elif qt == "npc_list":
            return {"npcs": self._npc.list_npcs(self._world_id)}
        elif qt == "quest_list":
            return {"quests": self._quest.list_quests(self._world_id)}
        return {"error": f"Unknown query type: {qt}"}

    async def handle_player_input(self, raw_text: str) -> EngineEvent:
        """将玩家命令行输入转换为标准 EngineEvent"""
        event_type = "player_action"
        if any(kw in raw_text for kw in ["去", "走", "前往", "移动", "进入", "离开"]):
            event_type = "player_move"
        if any(kw in raw_text for kw in ["攻击", "战斗", "打", "杀", "使用技能"]):
            event_type = "combat_start"

        context_hints = []
        player = self._player.get_player(self._world_id, self._player_id)
        if player and player.get("location"):
            context_hints.append(f"locations/{player['location']}")
        for npc in self._npc.list_npcs(self._world_id):
            if npc.get("name", "") in raw_text:
                context_hints.append(f"npcs/{npc['name']}")

        game_state = {}
        if player:
            game_state = {"location": player.get("location", "unknown"),
                "player_hp": player.get("hp", 100), "player_level": player.get("level", 1)}

        event = EngineEvent(event_id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(), type=event_type,
            data={"raw_text": raw_text, "player_id": self._player_id},
            context_hints=context_hints, game_state=game_state)
        if self._event_callback:
            await self._event_callback(event)
        return event
