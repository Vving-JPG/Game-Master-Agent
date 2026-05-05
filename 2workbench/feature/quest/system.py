"""任务系统 — 任务生命周期管理

职责:
1. 任务创建（从模板或自定义）
2. 前置条件检查
3. 任务进度追踪
4. 分支选择处理
5. 任务完成/失败判定

从 _legacy/core/services/story_coherence.py 重构。
"""
from __future__ import annotations

from typing import Any

from foundation.event_bus import Event
from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import QuestRepo, QuestStep, Quest, QuestStatus
from core.constants import generate_quest_from_template

logger = get_logger(__name__)


class QuestSystem(BaseFeature):
    """任务系统"""

    name = "quest"

    def on_enable(self) -> None:
        super().on_enable()
        self.subscribe("feature.ai.command.executed", self._on_command_executed)

    def _on_command_executed(self, event: Event) -> None:
        intent = event.data.get("intent", "")
        if intent in ("update_quest_status", "check_quest_prerequisites"):
            self.handle_quest_command(intent, event.data.get("params", {}))

    def create_from_template(
        self,
        template_name: str,
        world_id: int,
        **variables,
    ) -> Quest | None:
        """从模板创建任务

        Args:
            template_name: 模板名称（rescue/escort/collect/investigate/exterminate）
            world_id: 世界 ID
            **variables: 模板变量

        Returns:
            Quest 对象
        """
        try:
            quest_data = generate_quest_from_template(template_name, **variables)
            repo = QuestRepo()
            quest = repo.create(
                world_id=world_id,
                title=quest_data["title"],
                description=quest_data["description"],
                quest_type="side",
                status="not_started",
                branches=quest_data.get("branches", {}),
                db_path=self._db_path,
            )
            self.emit("feature.quest.created", {
                "quest_id": quest.id,
                "title": quest.title,
                "template": template_name,
            })
            logger.info(f"任务创建: [{quest.title}] (模板: {template_name})")
            return quest
        except Exception as e:
            logger.error(f"任务创建失败: {e}")
            return None

    def check_prerequisites(
        self,
        quest: Quest,
        player_level: int = 1,
        npc_relationships: dict[str, float] | None = None,
        completed_quests: list[str] | None = None,
    ) -> tuple[bool, str]:
        """检查任务前置条件

        Returns:
            (是否满足, 原因描述)
        """
        prereqs = quest.prerequisites if isinstance(quest.prerequisites, dict) else {}

        # 等级检查
        level_req = prereqs.get("level", 0)
        if player_level < level_req:
            return False, f"等级不足: 需要 {level_req} 级，当前 {player_level} 级"

        # NPC 关系检查
        npc_req = prereqs.get("npc_relationship", {})
        if npc_req and npc_relationships:
            for npc_name, min_rel in npc_req.items():
                actual = npc_relationships.get(npc_name, 0)
                if actual < min_rel:
                    return False, f"与 {npc_name} 的关系不足: 需要 {min_rel}，当前 {actual:.1f}"

        # 前置任务检查
        prev_quests = prereqs.get("completed_quests", [])
        if prev_quests and completed_quests:
            for prev in prev_quests:
                if prev not in completed_quests:
                    return False, f"前置任务未完成: {prev}"

        return True, "条件满足"

    def activate_quest(self, quest_id: int) -> bool:
        """激活任务"""
        repo = QuestRepo()
        # 先检查前置条件
        quest = repo.get_by_id(quest_id)
        if not quest:
            return False

        ok, reason = self.check_prerequisites(quest)
        if not ok:
            logger.warning(f"任务激活失败 ({quest.title}): {reason}")
            self.emit("feature.quest.activation_failed", {
                "quest_id": quest_id, "reason": reason,
            })
            return False

        repo.update_status(quest_id, "active")
        self.emit("feature.quest.activated", {"quest_id": quest_id, "title": quest.title})
        logger.info(f"任务激活: [{quest.title}]")
        return True

    def complete_quest(self, quest_id: int) -> bool:
        """完成任务"""
        repo = QuestRepo()
        repo.update_status(quest_id, "completed")
        quest = repo.get_by_id(quest_id)
        if quest:
            self.emit("feature.quest.completed", {
                "quest_id": quest_id,
                "title": quest.title,
                "rewards": quest.rewards,
            })
            logger.info(f"任务完成: [{quest.title}]")
        return True

    def handle_quest_command(self, intent: str, params: dict) -> None:
        """处理任务相关命令"""
        if intent == "update_quest_status":
            quest_id = params.get("quest_id", 0)
            status = params.get("status", "")
            if quest_id and status:
                if status == "completed":
                    self.complete_quest(quest_id)
                else:
                    QuestRepo().update_status(quest_id, status)

    def get_active_quests(self, world_id: int, player_id: int | None = None) -> list[Quest]:
        """获取活跃任务列表"""
        repo = QuestRepo()
        if player_id:
            quests = repo.get_by_player(player_id)
        else:
            quests = []
        return [q for q in quests if q.status == "active"]

    def get_state(self) -> dict[str, Any]:
        base = super().get_state()
        return base
