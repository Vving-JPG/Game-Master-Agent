"""知识库服务 — Feature 层

负责知识库数据的 CRUD 操作，通过 EventBus 与 Presentation 层通信。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any
from pathlib import Path

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NPCData:
    """NPC 数据类"""
    id: str = ""
    name: str = ""
    location: str = ""
    mood: str = ""
    personality: str = ""
    background: str = ""
    goals: str = ""
    dialogue_style: str = ""


@dataclass
class LocationData:
    """地点数据类"""
    id: str = ""
    name: str = ""
    description: str = ""
    connections: list[str] = field(default_factory=list)
    npcs: list[str] = field(default_factory=list)


@dataclass
class ItemData:
    """物品数据类"""
    id: str = ""
    name: str = ""
    item_type: str = ""  # weapon / armor / consumable / quest / misc
    rarity: str = "common"  # common / uncommon / rare / epic / legendary
    attributes: dict = field(default_factory=dict)
    description: str = ""


@dataclass
class QuestData:
    """任务数据类"""
    id: str = ""
    title: str = ""
    description: str = ""
    prerequisites: list[str] = field(default_factory=list)
    rewards: list[str] = field(default_factory=list)
    status: str = "inactive"  # inactive / active / completed / failed


@dataclass
class WorldSettingData:
    """世界设定数据类"""
    id: str = ""
    name: str = ""
    description: str = ""
    rules: str = ""


class KnowledgeService:
    """知识库服务

    管理 NPC、地点、物品、任务、世界设定等数据的 CRUD 操作。
    """

    def __init__(self):
        self._npcs: list[NPCData] = []
        self._locations: list[LocationData] = []
        self._items: list[ItemData] = []
        self._quests: list[QuestData] = []
        self._world_settings: list[WorldSettingData] = []
        self._setup_listeners()

    def _setup_listeners(self):
        """设置 EventBus 监听器"""
        # NPC 操作
        event_bus.subscribe("ui.knowledge.npc.load_requested", self._on_load_npcs)
        event_bus.subscribe("ui.knowledge.npc.save_requested", self._on_save_npcs)
        event_bus.subscribe("ui.knowledge.npc.add_requested", self._on_add_npc)
        event_bus.subscribe("ui.knowledge.npc.update_requested", self._on_update_npc)
        event_bus.subscribe("ui.knowledge.npc.delete_requested", self._on_delete_npc)

        # 地点操作
        event_bus.subscribe("ui.knowledge.location.load_requested", self._on_load_locations)
        event_bus.subscribe("ui.knowledge.location.save_requested", self._on_save_locations)

        # 物品操作
        event_bus.subscribe("ui.knowledge.item.load_requested", self._on_load_items)
        event_bus.subscribe("ui.knowledge.item.save_requested", self._on_save_items)

        # 任务操作
        event_bus.subscribe("ui.knowledge.quest.load_requested", self._on_load_quests)
        event_bus.subscribe("ui.knowledge.quest.save_requested", self._on_save_quests)

        # 导入/导出
        event_bus.subscribe("ui.knowledge.export_requested", self._on_export_data)
        event_bus.subscribe("ui.knowledge.import_requested", self._on_import_data)

    def _on_load_npcs(self, event: Event):
        """加载 NPC 数据"""
        try:
            event_bus.emit(Event(
                type="feature.knowledge.npc.loaded",
                data={"npcs": [asdict(npc) for npc in self._npcs], "success": True}
            ))
        except Exception as e:
            logger.error(f"加载 NPC 失败: {e}")
            event_bus.emit(Event(
                type="feature.knowledge.npc.load_failed",
                data={"error": str(e)}
            ))

    def _on_save_npcs(self, event: Event):
        """保存 NPC 数据"""
        try:
            npcs_data = event.data.get("npcs", [])
            self._npcs = [NPCData(**npc) for npc in npcs_data]
            event_bus.emit(Event(
                type="feature.knowledge.npc.saved",
                data={"success": True, "count": len(self._npcs)}
            ))
        except Exception as e:
            logger.error(f"保存 NPC 失败: {e}")
            event_bus.emit(Event(
                type="feature.knowledge.npc.save_failed",
                data={"error": str(e)}
            ))

    def _on_add_npc(self, event: Event):
        """添加 NPC"""
        try:
            npc_data = event.data.get("npc", {})
            npc = NPCData(**npc_data)
            self._npcs.append(npc)
            event_bus.emit(Event(
                type="feature.knowledge.npc.added",
                data={"npc": asdict(npc), "success": True}
            ))
        except Exception as e:
            logger.error(f"添加 NPC 失败: {e}")
            event_bus.emit(Event(
                type="feature.knowledge.npc.add_failed",
                data={"error": str(e)}
            ))

    def _on_update_npc(self, event: Event):
        """更新 NPC"""
        try:
            npc_id = event.data.get("id", "")
            npc_data = event.data.get("npc", {})
            for i, npc in enumerate(self._npcs):
                if npc.id == npc_id:
                    self._npcs[i] = NPCData(**npc_data)
                    event_bus.emit(Event(
                        type="feature.knowledge.npc.updated",
                        data={"npc": npc_data, "success": True}
                    ))
                    return
            event_bus.emit(Event(
                type="feature.knowledge.npc.update_failed",
                data={"error": f"NPC {npc_id} 不存在"}
            ))
        except Exception as e:
            logger.error(f"更新 NPC 失败: {e}")
            event_bus.emit(Event(
                type="feature.knowledge.npc.update_failed",
                data={"error": str(e)}
            ))

    def _on_delete_npc(self, event: Event):
        """删除 NPC"""
        try:
            npc_id = event.data.get("id", "")
            self._npcs = [npc for npc in self._npcs if npc.id != npc_id]
            event_bus.emit(Event(
                type="feature.knowledge.npc.deleted",
                data={"id": npc_id, "success": True}
            ))
        except Exception as e:
            logger.error(f"删除 NPC 失败: {e}")
            event_bus.emit(Event(
                type="feature.knowledge.npc.delete_failed",
                data={"error": str(e)}
            ))

    def _on_load_locations(self, event: Event):
        """加载地点数据"""
        event_bus.emit(Event(
            type="feature.knowledge.location.loaded",
            data={"locations": [asdict(loc) for loc in self._locations]}
        ))

    def _on_save_locations(self, event: Event):
        """保存地点数据"""
        try:
            locations_data = event.data.get("locations", [])
            self._locations = [LocationData(**loc) for loc in locations_data]
            event_bus.emit(Event(
                type="feature.knowledge.location.saved",
                data={"success": True, "count": len(self._locations)}
            ))
        except Exception as e:
            event_bus.emit(Event(
                type="feature.knowledge.location.save_failed",
                data={"error": str(e)}
            ))

    def _on_load_items(self, event: Event):
        """加载物品数据"""
        event_bus.emit(Event(
            type="feature.knowledge.item.loaded",
            data={"items": [asdict(item) for item in self._items]}
        ))

    def _on_save_items(self, event: Event):
        """保存物品数据"""
        try:
            items_data = event.data.get("items", [])
            self._items = [ItemData(**item) for item in items_data]
            event_bus.emit(Event(
                type="feature.knowledge.item.saved",
                data={"success": True, "count": len(self._items)}
            ))
        except Exception as e:
            event_bus.emit(Event(
                type="feature.knowledge.item.save_failed",
                data={"error": str(e)}
            ))

    def _on_load_quests(self, event: Event):
        """加载任务数据"""
        event_bus.emit(Event(
            type="feature.knowledge.quest.loaded",
            data={"quests": [asdict(quest) for quest in self._quests]}
        ))

    def _on_save_quests(self, event: Event):
        """保存任务数据"""
        try:
            quests_data = event.data.get("quests", [])
            self._quests = [QuestData(**quest) for quest in quests_data]
            event_bus.emit(Event(
                type="feature.knowledge.quest.saved",
                data={"success": True, "count": len(self._quests)}
            ))
        except Exception as e:
            event_bus.emit(Event(
                type="feature.knowledge.quest.save_failed",
                data={"error": str(e)}
            ))

    def _on_export_data(self, event: Event):
        """导出数据"""
        try:
            file_path = event.data.get("file_path", "")
            data_type = event.data.get("data_type", "all")

            export_data = {
                "npcs": [asdict(npc) for npc in self._npcs],
                "locations": [asdict(loc) for loc in self._locations],
                "items": [asdict(item) for item in self._items],
                "quests": [asdict(quest) for quest in self._quests],
                "world_settings": [asdict(ws) for ws in self._world_settings],
            }

            if data_type != "all":
                export_data = {data_type: export_data.get(data_type, [])}

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            event_bus.emit(Event(
                type="feature.knowledge.export_completed",
                data={"file_path": file_path, "success": True}
            ))
        except Exception as e:
            event_bus.emit(Event(
                type="feature.knowledge.export_failed",
                data={"error": str(e)}
            ))

    def _on_import_data(self, event: Event):
        """导入数据"""
        try:
            file_path = event.data.get("file_path", "")

            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            if "npcs" in import_data:
                self._npcs = [NPCData(**npc) for npc in import_data["npcs"]]
            if "locations" in import_data:
                self._locations = [LocationData(**loc) for loc in import_data["locations"]]
            if "items" in import_data:
                self._items = [ItemData(**item) for item in import_data["items"]]
            if "quests" in import_data:
                self._quests = [QuestData(**quest) for quest in import_data["quests"]]
            if "world_settings" in import_data:
                self._world_settings = [WorldSettingData(**ws) for ws in import_data["world_settings"]]

            event_bus.emit(Event(
                type="feature.knowledge.import_completed",
                data={"file_path": file_path, "success": True}
            ))
        except Exception as e:
            event_bus.emit(Event(
                type="feature.knowledge.import_failed",
                data={"error": str(e)}
            ))


# 全局单例
knowledge_service = KnowledgeService()
