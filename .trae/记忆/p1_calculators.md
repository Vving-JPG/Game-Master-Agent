# P1-04: Calculators 纯函数计算器

> 模块: `core.calculators`
> 文件: `2workbench/core/calculators/combat.py`, `ending.py`

---

## 战斗计算器 (combat.py)

### 伤害计算

```python
def calculate_damage(
    attacker: dict,
    defender: dict,
    skill_multiplier: float = 1.0,
    is_critical: bool = False
) -> DamageResult:
    """
    计算战斗伤害
    
    公式: 基础攻击 * 技能倍率 * (1 + 暴击加成) - 防御
    """
```

### 战斗结果

```python
def simulate_combat_round(
    player: dict,
    enemies: list[dict],
    player_action: dict
) -> CombatResult:
    """
    模拟一轮战斗
    
    返回: {
        "player_damage_dealt": list,
        "player_damage_taken": int,
        "enemies_defeated": list,
        "player_hp_after": int,
        "log": list[str],
    }
    """
```

### 使用示例

```python
from core.calculators import calculate_damage, simulate_combat_round

# 计算伤害
result = calculate_damage(
    attacker={"stats": {"attack": 50}},
    defender={"stats": {"defense": 20}},
    skill_multiplier=1.5,
    is_critical=True
)
print(f"造成 {result.damage} 点伤害")

# 模拟战斗回合
combat_result = simulate_combat_round(
    player={"hp": 100, "stats": {"attack": 50}},
    enemies=[{"hp": 30, "stats": {"defense": 10}}],
    player_action={"type": "attack", "target": 0}
)
```

---

## 结局计算器 (ending.py)

### 结局评分

```python
def calculate_ending_score(
    player: dict,
    quests_completed: list[dict],
    choices_made: list[dict],
    play_time_hours: float
) -> EndingScore:
    """
    计算结局评分
    
    维度:
    - 主线完成度 (40%)
    - 支线完成度 (20%)
    - 道德选择 (20%)
    - 探索度 (10%)
    - 生存时间 (10%)
    """
```

### 结局类型判定

```python
def determine_ending_type(score: EndingScore) -> str:
    """
    根据评分判定结局类型
    
    返回: "perfect" | "good" | "normal" | "bad" | "tragic"
    """
```

### 使用示例

```python
from core.calculators import calculate_ending_score, determine_ending_type

score = calculate_ending_score(
    player={"level": 50, "hp": 100},
    quests_completed=[...],
    choices_made=[...],
    play_time_hours=20.5
)
ending_type = determine_ending_type(score)
print(f"结局类型: {ending_type}, 总分: {score.total}")
```

---

## 纯函数特性

- ✅ 无副作用（不修改输入参数）
- ✅ 确定性（相同输入总是产生相同输出）
- ✅ 可测试性（易于单元测试）
- ✅ 可缓存（结果可安全缓存）
