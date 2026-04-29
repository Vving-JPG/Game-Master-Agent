"""战斗叙事生成 - 用LLM生成生动的战斗描述"""
from src.services.llm_client import LLMClient
from src.services.combat import CombatResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

COMBAT_NARRATIVE_PROMPT = """你是一个RPG游戏叙事生成器。请将以下战斗数据转换为生动的中文战斗描述。

## 战斗数据
{combat_data}

## 要求
1. 使用中文，描述要生动形象
2. 包含动作、声音、效果描写
3. 每轮战斗控制在2-3句话
4. 体现战斗的紧张感和刺激感
5. 不要使用游戏术语（如"HP"、"AC"等）

## 输出格式
直接输出叙事文本，不要解释。"""


def generate_combat_narrative(results: list[CombatResult], llm: LLMClient | None = None) -> str:
    """生成战斗叙事

    Args:
        results: 战斗结果列表
        llm: LLM客户端

    Returns:
        生成的叙事文本
    """
    # 格式化战斗数据
    combat_lines = []
    for r in results:
        if r.critical:
            line = f"{r.attacker}对{r.defender}发动暴击，造成{r.damage}点伤害"
        elif r.hit:
            line = f"{r.attacker}击中{r.defender}，造成{r.damage}点伤害"
        else:
            line = f"{r.attacker}攻击{r.defender}但未命中"
        combat_lines.append(line)

    combat_data = "\n".join(combat_lines)

    # 调用LLM生成叙事
    llm = llm or LLMClient()
    prompt = COMBAT_NARRATIVE_PROMPT.format(combat_data=combat_data)

    narrative = llm.chat([
        {"role": "system", "content": "你是一个专业的RPG战斗叙事生成器。"},
        {"role": "user", "content": prompt},
    ])

    return narrative.strip()


def generate_battle_start_narrative(enemy_names: list[str], location: str = "") -> str:
    """生成战斗开始叙事"""
    enemy_str = "、".join(enemy_names)
    location_str = f"在{location}" if location else ""
    return f"战斗开始！你{location_str}遭遇了{enemy_str}！"


def generate_battle_end_narrative(victory: bool, rewards: dict | None = None) -> str:
    """生成战斗结束叙事"""
    if victory:
        lines = ["🎉 战斗胜利！你击败了所有敌人！"]
        if rewards:
            lines.append(f"获得 {rewards.get('exp', 0)} 经验值，{rewards.get('gold', 0)} 金币")
        return "\n".join(lines)
    else:
        return "💀 你倒下了...战斗失败。"
