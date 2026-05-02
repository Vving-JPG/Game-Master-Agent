"""NPC 对话系统 — 基于性格的对话生成

职责:
1. 根据 NPC 性格和关系值生成对话
2. 管理对话历史
3. 通过 EventBus 通知对话事件

从 _legacy/core/services/npc_dialog.py 重构。
"""
from __future__ import annotations

from typing import Any

from foundation.event_bus import event_bus, Event
from foundation.llm import LLMMessage
from foundation.llm.model_router import model_router
from foundation.logger import get_logger
from feature.base import BaseFeature
from core.models import NPCRepo, LogRepo, MemoryRepo, NPC, Personality

logger = get_logger(__name__)


# 关系值 → 关系描述
RELATIONSHIP_MAP = {
    (0.7, 1.0): "非常友好，充满信任",
    (0.3, 0.7): "友善但保持一定距离",
    (0.0, 0.3): "冷淡疏远",
    (-1.0, 0.0): "充满敌意",
}


class DialogueSystem(BaseFeature):
    """NPC 对话系统"""

    name = "dialogue"

    def on_enable(self) -> None:
        super().on_enable()
        self.subscribe("feature.ai.command.executed", self._on_command_executed)

    def _on_command_executed(self, event: Event) -> None:
        """监听对话命令"""
        intent = event.get("intent", "")
        if intent == "npc_talk":
            self.handle_dialogue(event.get("params", {}))

    def build_npc_context(self, npc: NPC, player_relationship: float = 0.0) -> str:
        """构建 NPC 上下文描述

        Args:
            npc: NPC 数据
            player_relationship: 与玩家的关系值

        Returns:
            NPC 上下文文本
        """
        # 关系描述
        relation_desc = "陌生人"
        for (low, high), desc in RELATIONSHIP_MAP.items():
            if low <= player_relationship < high:
                relation_desc = desc
                break

        # 大五人格描述
        personality = npc.personality
        trait_desc = (
            f"开放性:{personality.openness:.1f} 尽责性:{personality.conscientiousness:.1f} "
            f"外向性:{personality.extraversion:.1f} 宜人性:{personality.agreeableness:.1f} "
            f"神经质:{personality.neuroticism:.1f}"
        )

        return (
            f"## NPC: {npc.name}\n"
            f"- 性格: {trait_desc}\n"
            f"- 心情: {npc.mood}\n"
            f"- 说话风格: {npc.speech_style}\n"
            f"- 背景: {npc.backstory}\n"
            f"- 目标: {', '.join(npc.goals)}\n"
            f"- 对玩家的态度: {relation_desc} (关系值: {player_relationship:.1f})\n"
        )

    async def generate_dialogue(
        self,
        npc: NPC,
        player_input: str,
        player_name: str = "冒险者",
        dialogue_history: list[dict] | None = None,
    ) -> str:
        """生成 NPC 对话

        Args:
            npc: NPC 数据
            player_input: 玩家输入
            player_name: 玩家名称
            dialogue_history: 对话历史

        Returns:
            NPC 回复文本
        """
        context = self.build_npc_context(npc)

        # 构建消息
        messages = [
            LLMMessage(role="system", content=(
                f"你正在扮演 NPC「{npc.name}」。请根据以下角色设定与玩家对话。\n"
                f"保持角色的性格和说话风格，不要出戏。\n\n{context}"
            )),
        ]

        # 添加对话历史
        if dialogue_history:
            for turn in dialogue_history[-10:]:  # 最近 10 轮
                messages.append(LLMMessage(role=turn["role"], content=turn["content"]))

        # 添加当前输入
        messages.append(LLMMessage(role="user", content=f"{player_name}: {player_input}"))

        try:
            client, config = model_router.route(content=player_input)
            response = await client.chat_async(
                messages=messages,
                temperature=0.8,
            )
            return response.content
        except Exception as e:
            logger.error(f"NPC 对话生成失败 ({npc.name}): {e}")
            return f"[{npc.name} 沉默不语...]"

    def handle_dialogue(self, params: dict[str, Any]) -> None:
        """处理对话事件（同步入口，实际生成是异步的）"""
        npc_name = params.get("npc_name", "")
        player_input = params.get("player_input", "")

        self.emit("feature.dialogue.started", {
            "npc_name": npc_name,
            "player_input": player_input,
        })

        logger.info(f"对话开始: 玩家 -> {npc_name}: {player_input[:50]}")

    def get_state(self) -> dict[str, Any]:
        base = super().get_state()
        base["dialogue_count"] = 0  # TODO: 从数据库统计
        return base
