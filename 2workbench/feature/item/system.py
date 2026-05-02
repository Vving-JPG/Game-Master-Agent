"""物品管理系统"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import ItemRepo, PlayerRepo, Item, ItemType, ItemRarity

logger = get_logger(__name__)


class ItemSystem(BaseFeature):
    """物品管理系统"""

    name = "item"

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
