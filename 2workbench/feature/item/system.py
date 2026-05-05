"""物品管理系统"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import ItemRepo, PlayerRepo, Item

logger = get_logger(__name__)


class ItemSystem(BaseFeature):
    """物品管理系统"""

    name = "item"

    def on_enable(self) -> None:
        super().on_enable()
        # 订阅 AI 命令事件
        self.subscribe("feature.ai.command.executed", self._on_command_executed)

    def _on_command_executed(self, event) -> None:
        """处理 AI 命令"""
        intent = event.data.get("intent", "")
        params = event.data.get("params", {})

        if intent == "give_item":
            player_id = params.get("player_id", 1)
            item_name = params.get("item_name", "")
            quantity = params.get("quantity", 1)
            if item_name:
                self.give_item(player_id, item_name, quantity)
        elif intent == "remove_item":
            player_id = params.get("player_id", 1)
            item_name = params.get("item_name", "")
            quantity = params.get("quantity", 1)
            if item_name:
                self.remove_item(player_id, item_name, quantity)
        elif intent == "use_item":
            player_id = params.get("player_id", 1)
            item_name = params.get("item_name", "")
            if item_name:
                self.use_item(player_id, item_name)

    def use_item(self, player_id: int, item_name: str, db_path: str | None = None) -> dict:
        """使用物品"""
        # 简化实现：移除物品并发出事件
        result = self.remove_item(player_id, item_name, 1, db_path)
        if result["success"]:
            self.emit("feature.item.used", {
                "player_id": player_id,
                "item_name": item_name,
            })
        return result

    def give_item(self, player_id: int, item_name: str, quantity: int = 1, db_path: str | None = None) -> dict:
        """给予玩家物品"""
        repo = ItemRepo()
        db = db_path or self._db_path

        # 查找或创建物品
        items = repo.search(item_name, db_path=db)
        if items:
            item = items[0]
        else:
            item = repo.create(name=item_name, item_type="misc", db_path=db)

        # 添加到玩家物品栏
        player_repo = PlayerRepo()
        player_repo.add_item(player_id, item.id, quantity, db_path=db)

        self.emit("feature.item.given", {
            "player_id": player_id,
            "item_name": item_name,
            "quantity": quantity,
        })
        return {"success": True, "item": item_name, "quantity": quantity}

    def remove_item(self, player_id: int, item_name: str, quantity: int = 1, db_path: str | None = None) -> dict:
        """移除玩家物品"""
        repo = ItemRepo()
        db = db_path or self._db_path
        items = repo.search(item_name, db_path=db)

        if not items:
            return {"success": False, "error": f"物品不存在: {item_name}"}

        player_repo = PlayerRepo()
        player_repo.remove_item(player_id, items[0].id, quantity, db_path=db)

        self.emit("feature.item.removed", {
            "player_id": player_id,
            "item_name": item_name,
            "quantity": quantity,
        })
        return {"success": True, "item": item_name, "quantity": quantity}

    def get_inventory(self, player_id: int, db_path: str | None = None) -> list[dict]:
        """获取玩家物品栏"""
        player_repo = PlayerRepo()
        items = player_repo.get_inventory(player_id, db_path=db_path or self._db_path)
        return [{"name": i.item_name if hasattr(i, 'item_name') else str(i), "quantity": i.quantity} for i in items]
