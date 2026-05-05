"""战斗系统 — 战斗流程管理 + LLM 叙事生成

职责:
1. 管理战斗生命周期（开始→轮次→结束）
2. 调用 Core 层纯函数进行战斗计算
3. 调用 LLM 生成战斗叙事
4. 通过 EventBus 通知其他模块

从 _legacy/core/services/combat.py + combat_narrative.py 重构。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from foundation.event_bus import event_bus, Event
from foundation.llm import LLMMessage
from foundation.llm.model_router import model_router
from foundation.logger import get_logger
from feature.base import BaseFeature
from core.calculators import (
    Combatant, AttackResult, CombatResult,
    attack, combat_round, is_combat_over, calculate_rewards,
)
from core.models import PlayerRepo

logger = get_logger(__name__)


@dataclass
class BattleState:
    """战斗状态"""
    active: bool = False
    player: Combatant | None = None
    enemies: list[Combatant] = field(default_factory=list)
    round_num: int = 0
    results: list[list[AttackResult]] = field(default_factory=list)
    victory: bool = False


class BattleSystem(BaseFeature):
    """战斗系统"""

    name = "battle"

    def on_enable(self) -> None:
        super().on_enable()
        # 订阅战斗相关事件
        self.subscribe("feature.ai.command.executed", self._on_command_executed)

    def _on_command_executed(self, event: Event) -> None:
        """监听 AI 层的命令执行，处理战斗相关命令"""
        result = event.data.get("result", {})
        intent = event.data.get("intent", "")
        if intent == "start_combat":
            self.start_combat(event.data.get("params", {}))

    def start_combat(self, params: dict[str, Any]) -> BattleState:
        """开始战斗

        Args:
            params: {"enemies": [{"name": "哥布林", "hp": 20, ...}], "player_id": 1}

        Returns:
            BattleState
        """
        self._state = BattleState(active=True)

        # 创建玩家战斗者
        player_data = params.get("player", {})
        self._state.player = Combatant(
            name=player_data.get("name", "冒险者"),
            hp=player_data.get("hp", 100),
            max_hp=player_data.get("max_hp", 100),
            attack_bonus=player_data.get("attack_bonus", 3),
            damage_dice=player_data.get("damage_dice", "1d8"),
            ac=player_data.get("ac", 15),
            is_player=True,
        )

        # 创建敌人
        for enemy_data in params.get("enemies", []):
            self._state.enemies.append(Combatant(
                name=enemy_data.get("name", "敌人"),
                hp=enemy_data.get("hp", 20),
                max_hp=enemy_data.get("max_hp", 20),
                attack_bonus=enemy_data.get("attack_bonus", 1),
                damage_dice=enemy_data.get("damage_dice", "1d6"),
                ac=enemy_data.get("ac", 10),
            ))

        self.emit("feature.battle.started", {
            "enemies": [e.name for e in self._state.enemies],
            "player_hp": self._state.player.hp,
        })

        logger.info(f"战斗开始: {self._state.player.name} vs {[e.name for e in self._state.enemies]}")
        return self._state

    def execute_round(self) -> list[AttackResult]:
        """执行一轮战斗

        Returns:
            本轮攻击结果列表
        """
        if not self._state.active or not self._state.player:
            return []

        self._state.round_num += 1
        results = combat_round(self._state.player, self._state.enemies)
        self._state.results.append(results)

        # 检查战斗是否结束
        if is_combat_over(self._state.player, self._state.enemies):
            self._state.active = False
            self._state.victory = self._state.player.hp > 0
            rewards = calculate_rewards(self._state.enemies)

            self.emit("feature.battle.ended", {
                "victory": self._state.victory,
                "rounds": self._state.round_num,
                "rewards": rewards,
                "player_hp": self._state.player.hp,
            })

            logger.info(
                f"战斗结束: {'胜利' if self._state.victory else '失败'} "
                f"({self._state.round_num} 轮)"
            )
        else:
            self.emit("feature.battle.round_completed", {
                "round": self._state.round_num,
                "player_hp": self._state.player.hp,
                "enemies_alive": sum(1 for e in self._state.enemies if e.hp > 0),
            })

        return results

    async def generate_narrative(self, results: list[AttackResult]) -> str:
        """用 LLM 生成战斗叙事

        Args:
            results: 攻击结果列表

        Returns:
            战斗叙事文本
        """
        # 构建战斗数据描述
        combat_data = []
        for r in results:
            combat_data.append(
                f"- {r.attacker} {'暴击！' if r.is_crit else ''}{'命中' if r.hit else '未命中'} "
                f"{r.defender}，{'造成' if r.hit else ''} {r.damage} 点伤害"
            )

        prompt = (
            "你是一个游戏主持人。请根据以下战斗数据，生成 2-3 句生动的中文战斗叙事：\n\n"
            + "\n".join(combat_data)
            + "\n\n要求: 简洁有力，突出关键动作和结果。"
        )

        try:
            client, config = model_router.route(content="战斗叙事")
            response = await client.chat_async(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=0.8,
            )
            return response.content
        except Exception as e:
            logger.error(f"战斗叙事生成失败: {e}")
            # 降级: 使用纯文本拼接
            return "；".join(r.narrative for r in results)

    def get_state(self) -> dict[str, Any]:
        """获取战斗状态"""
        base = super().get_state()
        if hasattr(self, "_state"):
            base.update({
                "active": self._state.active,
                "round": self._state.round_num,
                "player_hp": self._state.player.hp if self._state.player else 0,
                "enemies": [
                    {"name": e.name, "hp": e.hp, "max_hp": e.max_hp}
                    for e in self._state.enemies
                ],
                "victory": self._state.victory,
            })
        return base
