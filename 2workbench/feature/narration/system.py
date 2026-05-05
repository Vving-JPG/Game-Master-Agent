"""叙事增强系统 — 信息提取 + 记忆管理"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import MemoryRepo

logger = get_logger(__name__)


class NarrationSystem(BaseFeature):
    """叙事增强系统"""

    name = "narration"

    def extract_and_store(self, narrative: str, world_id: int, turn: int, db_path: str | None = None) -> int:
        """从叙事中提取关键信息并存储为记忆

        简化版: 将整段叙事存储为 session 类别记忆。
        完整版应使用 LLM 提取结构化信息（从 _legacy/core/services/info_extractor.py）。

        Returns:
            存储的记忆数
        """
        db = db_path or self._db_path
        repo = MemoryRepo()

        # 简化: 存储为 session 记忆
        repo.store(
            world_id=world_id,
            category="session",
            source="narration",
            content=narrative,
            importance=0.5,
            turn=turn,
            db_path=db,
        )

        self.emit("feature.narration.stored", {
            "world_id": world_id,
            "turn": turn,
            "length": len(narrative),
        })

        return 1

    def get_context_memories(
        self,
        world_id: int,
        limit: int = 10,
        min_importance: float = 0.3,
        db_path: str | None = None,
    ) -> str:
        """获取上下文记忆（用于注入 Prompt）

        Returns:
            格式化的记忆文本
        """
        db = db_path or self._db_path
        repo = MemoryRepo()
        memories = repo.recall(world_id=world_id, min_importance=min_importance, limit=limit, db_path=db)

        if not memories:
            return ""

        parts = ["## 相关记忆\n"]
        for mem in memories:
            source = mem.source or "未知"
            parts.append(f"- [{source}] {mem.content[:100]}")

        return "\n".join(parts)
