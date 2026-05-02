"""纯函数计算器"""
from core.calculators.combat import (
    Combatant, AttackResult, CombatResult,
    roll_dice, calculate_attack_bonus, calculate_ac,
    attack, combat_round, is_combat_over, calculate_rewards,
)
from core.calculators.ending import (
    EndingScore, calculate_ending_score, determine_ending, format_ending_narrative,
)

__all__ = [
    "Combatant", "AttackResult", "CombatResult",
    "roll_dice", "calculate_attack_bonus", "calculate_ac",
    "attack", "combat_round", "is_combat_over", "calculate_rewards",
    "EndingScore", "calculate_ending_score", "determine_ending", "format_ending_narrative",
]