"""Memory Manager — 智能记忆管理

使用 langmem 实现自动记忆提取、衰减和语义检索。
提供更高级的记忆管理功能。
"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from foundation.config import settings

logger = get_logger(__name__)


class MemoryManager:
    """智能记忆管理器

    负责：
    1. 自动从对话中提取重要信息
    2. 记忆重要性衰减
    3. 语义检索相关记忆
    4. 记忆压缩和总结
    """

    def __init__(
        self,
        model_name: str = "deepseek-chat",
        provider: str = "deepseek",
        namespaces: list[str] | None = None,
    ):
        self._model_name = model_name
        self._provider = provider
        self._namespaces = namespaces or [
            "player_preferences",
            "world_state",
            "story_events",
            "npc_relationships",
        ]
        self._memory_manager = None

    def _get_manager(self):
        """懒加载 langmem memory manager"""
        if self._memory_manager is None:
            try:
                from langmem import create_memory_manager

                self._memory_manager = create_memory_manager(
                    model=self._model_name,
                    namespaces=self._namespaces,
                )
                logger.info(f"Memory Manager 已创建: model={self._model_name}")
            except Exception as e:
                logger.warning(f"创建 langmem Memory Manager 失败: {e}")
                self._memory_manager = None

        return self._memory_manager

    async def extract_memories(
        self,
        conversation: list[dict[str, Any]],
        categories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """从对话中提取记忆

        Args:
            conversation: 对话历史，格式为 [{"role": "user", "content": "..."}, ...]
            categories: 指定提取的记忆类别，None 则自动判断

        Returns:
            提取的记忆列表
        """
        manager = self._get_manager()

        if manager is None:
            # 回退到简单提取
            return self._simple_extract(conversation, categories)

        try:
            # 使用 langmem 提取记忆
            memories = await manager.extract_memories(
                conversation,
                categories=categories or self._namespaces,
            )
            return [
                {
                    "category": m.category,
                    "content": m.content,
                    "importance": m.importance,
                    "metadata": m.metadata,
                }
                for m in memories
            ]
        except Exception as e:
            logger.warning(f"langmem 提取记忆失败，使用简单提取: {e}")
            return self._simple_extract(conversation, categories)

    def _simple_extract(
        self,
        conversation: list[dict[str, Any]],
        categories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """简单记忆提取（回退方案）"""
        memories = []

        # 从最后几条消息中提取
        for msg in conversation[-3:]:
            content = msg.get("content", "")
            role = msg.get("role", "")

            if role == "assistant" and len(content) > 50:
                # 提取关键信息（简化版）
                memories.append({
                    "category": "story_events",
                    "content": content[:200],  # 截取前200字符
                    "importance": 0.5,
                    "metadata": {"source": "conversation", "extracted_by": "simple"},
                })

        return memories

    async def retrieve_relevant(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """检索相关记忆

        Args:
            query: 查询内容
            context: 上下文信息（如当前场景、NPC 等）
            limit: 返回数量限制

        Returns:
            相关记忆列表
        """
        manager = self._get_manager()

        if manager is None:
            return []

        try:
            memories = await manager.retrieve_relevant(
                query=query,
                context=context,
                limit=limit,
            )
            return [
                {
                    "category": m.category,
                    "content": m.content,
                    "relevance": m.relevance,
                    "metadata": m.metadata,
                }
                for m in memories
            ]
        except Exception as e:
            logger.warning(f"langmem 检索记忆失败: {e}")
            return []

    async def compress_memories(
        self,
        memories: list[dict[str, Any]],
        max_tokens: int = 1000,
    ) -> str:
        """压缩记忆为摘要

        Args:
            memories: 记忆列表
            max_tokens: 最大 token 数

        Returns:
            压缩后的摘要
        """
        if not memories:
            return ""

        manager = self._get_manager()

        if manager is None:
            # 简单拼接
            return "\n".join([m.get("content", "") for m in memories[:3]])

        try:
            summary = await manager.compress_memories(
                memories=memories,
                max_tokens=max_tokens,
            )
            return summary
        except Exception as e:
            logger.warning(f"langmem 压缩记忆失败: {e}")
            return "\n".join([m.get("content", "") for m in memories[:3]])

    def calculate_decay(self, memory: dict[str, Any], current_turn: int) -> float:
        """计算记忆衰减后的重要性

        Args:
            memory: 记忆数据
            current_turn: 当前回合数

        Returns:
            衰减后的重要性分数 (0-1)
        """
        original_importance = memory.get("importance", 0.5)
        turn_created = memory.get("metadata", {}).get("turn_created", current_turn)

        # 计算回合差
        turn_diff = max(0, current_turn - turn_created)

        # 衰减公式：每10回合衰减10%，最低保留50%
        decay_factor = max(0.5, 1.0 - (turn_diff / 100))

        return original_importance * decay_factor


# 全局 Memory Manager 实例
_memory_manager: MemoryManager | None = None


def get_memory_manager(
    model_name: str | None = None,
    provider: str | None = None,
) -> MemoryManager:
    """获取 Memory Manager 实例

    Args:
        model_name: 模型名称，None 则使用配置
        provider: 提供商，None 则使用配置

    Returns:
        MemoryManager 实例
    """
    global _memory_manager

    if _memory_manager is None:
        model = model_name or settings.default_model
        prov = provider or settings.default_provider
        _memory_manager = MemoryManager(model_name=model, provider=prov)

    return _memory_manager


def reset_memory_manager() -> None:
    """重置 Memory Manager（用于切换项目时）"""
    global _memory_manager
    _memory_manager = None
    logger.info("Memory Manager 已重置")
