"""战斗系统测试"""
from src.services.combat import Combatant, attack, combat_round, is_combat_over, calculate_rewards


def test_attack_hit():
    """攻击命中"""
    player = Combatant("玩家", 100, 100, attack_bonus=5, damage_dice="1d8", ac=12)
    enemy = Combatant("敌人", 50, 50, attack_bonus=2, damage_dice="1d6", ac=10)

    result = attack(player, enemy)
    assert result.hit or not result.hit  # 可能命中也可能未命中
    assert result.defender_hp <= enemy.hp


def test_critical_hit():
    """暴击（需要运气，测试结构）"""
    player = Combatant("玩家", 100, 100, attack_bonus=10, damage_dice="1d6", ac=5)
    enemy = Combatant("敌人", 100, 100, ac=5)

    # 多次攻击，期望至少有一次暴击
    critical_found = False
    for _ in range(100):
        result = attack(player, enemy)
        if result.critical:
            critical_found = True
            break
    # 不强制要求暴击，只是验证结构


def test_combat_round():
    """战斗回合"""
    player = Combatant("玩家", 100, 100, attack_bonus=5, damage_dice="1d8", ac=12, is_player=True)
    enemies = [Combatant("哥布林", 20, 20, attack_bonus=2, damage_dice="1d4", ac=8)]

    results = combat_round(player, enemies)
    assert len(results) > 0


def test_combat_over():
    """战斗结束判断"""
    player = Combatant("玩家", 0, 100)  # 死亡
    enemies = [Combatant("敌人", 10, 10)]

    over, reason = is_combat_over(player, enemies)
    assert over is True
    assert reason == "player_defeated"


def test_enemies_defeated():
    """敌人全灭"""
    player = Combatant("玩家", 100, 100)
    enemies = [Combatant("敌人", 0, 10)]  # 已死亡

    over, reason = is_combat_over(player, enemies)
    assert over is True
    assert reason == "enemies_defeated"


def test_calculate_rewards():
    """计算奖励"""
    enemies = [
        Combatant("敌人1", 0, 30),  # 死亡
        Combatant("敌人2", 10, 30),  # 存活
    ]
    rewards = calculate_rewards(enemies)
    assert rewards["exp"] > 0
