"""探索系统 — 地点发现与移动"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import LocationRepo, NPCRepo, PlayerRepo

logger = get_logger(__name__)


class ExplorationSystem(BaseFeature):
    """探索系统"""

    name = "exploration"

    def on_enable(self) -> None:
        super().on_enable()
        # 订阅 AI 命令事件
        self.subscribe("feature.ai.command.executed", self._on_command_executed)

    def _on_command_executed(self, event) -> None:
        """处理 AI 命令"""
        intent = event.get("intent", "")
        params = event.get("params", {})

        if intent == "move_to_location":
            player_id = params.get("player_id", 1)
            location_name = params.get("location_name", "")
            if location_name:
                self.move_to_location(player_id, location_name)
        elif intent == "explore":
            player_id = params.get("player_id", 1)
            location_id = params.get("location_id", 0)
            world_id = params.get("world_id", 1)
            if location_id:
                self.explore_location(location_id, world_id)

    def move_to_location(self, player_id: int, location_name: str, db_path: str | None = None) -> dict:
        """移动玩家到指定地点（通过名称）"""
        db = db_path or self._db_path
        loc_repo = LocationRepo()
        player_repo = PlayerRepo()

        # 查找地点
        locations = loc_repo.search(name=location_name, db_path=db)
        if not locations:
            return {"error": f"地点不存在: {location_name}"}

        location = locations[0]

        # 更新玩家位置
        player_repo.update(player_id, location_id=location.id, db_path=db)

        self.emit("feature.exploration.moved", {
            "player_id": player_id,
            "to": location.name,
        })

        return {"success": True, "location": location.name}

    def explore_location(self, location_id: int, world_id: int, db_path: str | None = None) -> dict:
        """探索地点

        Returns:
            地点信息（描述、NPC、出口）
        """
        db = db_path or self._db_path
        loc_repo = LocationRepo()
        npc_repo = NPCRepo()

        location = loc_repo.get_by_id(location_id, db_path=db)
        if not location:
            return {"error": f"地点不存在: {location_id}"}

        npcs = npc_repo.get_by_location(location_id, db_path=db)
        exits = list(location.connections.keys()) if location.connections else []

        result = {
            "name": location.name,
            "description": location.description,
            "npcs": [{"name": n.name, "mood": n.mood} for n in npcs],
            "exits": exits,
        }

        self.emit("feature.exploration.discovered", {
            "location_id": location_id,
            "location_name": location.name,
            "npcs_found": len(npcs),
        })

        return result

    def move_player(self, player_id: int, direction: str, db_path: str | None = None) -> dict:
        """移动玩家到相邻地点

        Args:
            direction: 方向（north/south/east/west）
        """
        db = db_path or self._db_path
        player_repo = PlayerRepo()
        loc_repo = LocationRepo()

        player = player_repo.get_by_id(player_id, db_path=db)
        if not player:
            return {"error": "玩家不存在"}

        current_loc = loc_repo.get_by_id(player.location_id, db_path=db)
        if not current_loc or direction not in current_loc.connections:
            return {"error": f"无法向 {direction} 移动"}

        new_loc_id = current_loc.connections[direction]
        player_repo.update(player_id, location_id=new_loc_id, db_path=db)

        new_loc = loc_repo.get_by_id(new_loc_id, db_path=db)
        self.emit("feature.exploration.moved", {
            "player_id": player_id,
            "from": current_loc.name,
            "to": new_loc.name if new_loc else "未知",
            "direction": direction,
        })

        return {"success": True, "location": new_loc.name if new_loc else "未知"}
