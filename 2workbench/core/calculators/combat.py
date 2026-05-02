"""战斗计算器 — 纯函数

从 _legacy/core/services/combat.py 提取的纯计算逻辑。
无 IO、无副作用、无 LLM 调用。
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Combatant:
    """战斗者"""
    name: str
    hp: int
    max_hp: int
    attack_bonus: int = 0
    damage_dice: str = "1d6"
    ac: int = 10
    is_player: bool = False


@dataclass
class AttackResult:
    """攻击结果"""
    attacker: str
    defender: str
    hit: bool
    is_crit: bool
    attack_roll: int
    damage: int
    narrative: str


@dataclass
class CombatResult:
    """战斗结果"""
    rounds: list[list[AttackResult]] = field(default_factory=list)
    victory: bool = False
    rewards: dict[str, Any] = field(default_factory=dict)
    survivors: list[str] = field(default_factory=list)


def roll_dice(dice_str: str) -> int:
    """掷骰子 — 支持 XdY 格式

    Args:
        dice_str: 骰子表达式，如 "1d20", "2d6", "1d8+3"

    Returns:
        掷骰结果
    """
    match = re.match(r"(\d+)d(\d+)([+-]\d+)?", dice_str.strip())
    if not match:
        return 0
    count, sides = int(match.group(1)), int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0
    total = sum(random.randint(1, sides) for _ in range(count)) + modifier
    return total


def calculate_attack_bonus(level: int, stat_bonus: int = 0) -> int:
    """计算攻击加值"""
    return stat_bonus + (level // 2)


def calculate_ac(base_ac: int = 10, dex_bonus: int = 0, armor_bonus: int = 0) -> int:
    """计算护甲等级"""
    return base_ac + dex_bonus + armor_bonus


def attack(attacker: Combatant, defender: Combatant) -> AttackResult:
    """执行一次攻击

    Returns:
        AttackResult
    """
    attack_roll = roll_dice("1d20")
    is_crit = attack_roll == 20
    total_attack = attack_roll + attacker.attack_bonus

    hit = is_crit or total_attack >= defender.ac

    if hit:
        damage = roll_dice(attacker.damage_dice)
        if is_crit:
            damage *= 2  # 暴击双倍伤害
        narrative = f"{'暴击！' if is_crit else ''}{attacker.name} 命中了 {defender.name}，造成 {damage} 点伤害"
    else:
        damage = 0
        narrative = f"{attacker.name} 攻击 {defender.name} 未命中（{total_attack} vs AC {defender.ac}）"

    return AttackResult(
        attacker=attacker.name,
        defender=defender.name,
        hit=hit,
        is_crit=is_crit,
        attack_roll=total_attack,
        damage=damage,
        narrative=narrative,
    )


def combat_round(player: Combatant, enemies: list[Combatant]) -> list[AttackResult]:
    """执行一轮战斗

    Args:
        player: 玩家
        enemies: 敌人列表

    Returns:
        本轮所有攻击结果
    """
    results = []

    # 玩家攻击所有存活敌人
    for enemy in enemies:
        if enemy.hp > 0:
            result = attack(player, enemy)
            results.append(result)
            if result.hit:
                enemy.hp = max(0, enemy.hp - result.damage)

    # 存活敌人反击
    for enemy in enemies:
        if enemy.hp > 0:
            result = attack(enemy, player)
            results.append(result)
            if result.hit:
                player.hp = max(0, player.hp - result.damage)

    return results


def is_combat_over(player: Combatant, enemies: list[Combatant]) -> bool:
    """检查战斗是否结束"""
    return player.hp <= 0 or all(e.hp <= 0 for e in enemies)


def calculate_rewards(enemies: list[Combatant]) -> dict[str, Any]:
    """计算战斗奖励"""
    defeated = [e for e in enemies if e.hp <= 0]
    exp = len(defeated) * 25
    gold = random.randint(5, 20) * len(defeated)
    return {"exp": exp, "gold": gold, "defeated_count": len(defeated)}