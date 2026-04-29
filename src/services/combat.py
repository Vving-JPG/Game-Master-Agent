"""战斗系统 - D&D 5e 简化版"""
import random
from dataclasses import dataclass
from typing import Optional
from src.tools.dice import roll_dice
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Combatant:
    """战斗参与者"""
    name: str
    hp: int
    max_hp: int
    attack_bonus: int = 0
    damage_dice: str = "1d6"
    ac: int = 10  # 护甲等级
    is_player: bool = False


@dataclass
class CombatResult:
    """战斗结果"""
    attacker: str
    defender: str
    hit: bool
    critical: bool
    damage: int
    defender_hp: int
    narrative: str


def calculate_attack_bonus(level: int) -> int:
    """根据等级计算攻击加值"""
    return level // 2 + 2


def calculate_ac(equipped_items: list) -> int:
    """计算护甲等级（简化版）"""
    base_ac = 10
    # 如果有盾牌 +2
    # 如果有护甲 +2~+6 根据类型
    return base_ac + 2  # 简化：默认+2


def attack(attacker: Combatant, defender: Combatant) -> CombatResult:
    """执行攻击

    D&D 5e 简化规则:
    1. 攻击检定: d20 + 攻击加值
    2. 命中条件: 结果 >= 目标AC
    3. 暴击: 掷出20
    4. 伤害: 武器骰 + 加值
    """
    # 攻击检定
    roll_result = roll_dice("1d20")
    attack_roll = roll_result["total"]
    total_attack = attack_roll + attacker.attack_bonus

    # 判断是否命中
    hit = total_attack >= defender.ac
    critical = attack_roll == 20

    damage = 0
    if hit or critical:
        # 伤害骰
        damage_result = roll_dice(attacker.damage_dice)
        damage = damage_result["total"]
        if critical:
            # 暴击：双倍伤害骰
            damage += damage_result["total"]
        # 简化：不加攻击加值到伤害

    # 应用伤害
    new_hp = max(0, defender.hp - damage)

    # 生成叙事
    narrative = _generate_attack_narrative(
        attacker.name, defender.name, hit, critical, damage, attack_roll, total_attack, defender.ac
    )

    return CombatResult(
        attacker=attacker.name,
        defender=defender.name,
        hit=hit,
        critical=critical,
        damage=damage,
        defender_hp=new_hp,
        narrative=narrative,
    )


def _generate_attack_narrative(attacker: str, defender: str, hit: bool,
                               critical: bool, damage: int, roll: int,
                               total: int, ac: int) -> str:
    """生成攻击叙事"""
    if critical:
        return f"💥 {attacker}发动致命一击！造成{damage}点伤害！"
    elif hit:
        return f"⚔️ {attacker}击中{defender}，造成{damage}点伤害。"
    else:
        return f"🛡️ {attacker}的攻击被{defender}闪避（{total} vs AC{ac}）。"


def combat_round(player: Combatant, enemies: list[Combatant]) -> list[CombatResult]:
    """执行一轮战斗"""
    results = []

    # 玩家攻击每个敌人（简化）
    for enemy in enemies:
        if enemy.hp > 0:
            result = attack(player, enemy)
            enemy.hp = result.defender_hp
            results.append(result)

            # 敌人反击
            if enemy.hp > 0:
                counter = attack(enemy, player)
                player.hp = counter.defender_hp
                results.append(counter)

    return results


def is_combat_over(player: Combatant, enemies: list[Combatant]) -> tuple[bool, Optional[str]]:
    """检查战斗是否结束"""
    if player.hp <= 0:
        return True, "player_defeated"

    if all(e.hp <= 0 for e in enemies):
        return True, "enemies_defeated"

    return False, None


def calculate_rewards(enemies: list[Combatant]) -> dict:
    """计算战斗奖励"""
    exp = sum(e.max_hp // 10 for e in enemies if e.hp <= 0)
    gold = sum(random.randint(1, 10) for e in enemies if e.hp <= 0)
    return {"exp": exp, "gold": gold}
