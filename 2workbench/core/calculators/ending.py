"""结局计算器 — 纯函数

从 _legacy/core/services/ending_system.py 提取。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EndingScore:
    """结局评分"""
    hero: float = 0
    villain: float = 0
    neutral: float = 0
    tragic: float = 0
    secret: float = 0


def calculate_ending_score(
    main_quests_completed: int = 0,
    side_quests_completed: int = 0,
    total_main_quests: int = 5,
    player_hp: int = 100,
    max_hp: int = 100,
    npc_relationships: dict[str, float] | None = None,
    choices: list[dict[str, Any]] | None = None,
) -> EndingScore:
    """计算各结局分数

    Args:
        main_quests_completed: 完成的主线任务数
        side_quests_completed: 完成的支线任务数
        total_main_quests: 总主线任务数
        player_hp: 玩家当前 HP
        max_hp: 玩家最大 HP
        npc_relationships: NPC 关系值
        choices: 关键选择记录

    Returns:
        EndingScore
    """
    scores = EndingScore()
    relationships = npc_relationships or {}

    # 英雄路线: 完成主线 + 高关系值
    main_ratio = main_quests_completed / max(total_main_quests, 1)
    scores.hero = main_ratio * 50 + side_quests_completed * 5
    avg_relationship = sum(relationships.values()) / max(len(relationships), 1)
    scores.hero += max(0, avg_relationship * 20)

    # 反派路线: 低关系值 + 特定选择
    scores.villain = max(0, -avg_relationship * 30)
    if choices:
        evil_choices = sum(1 for c in choices if c.get("alignment") == "evil")
        scores.villain += evil_choices * 15

    # 悲剧路线: 低 HP
    hp_ratio = player_hp / max(max_hp, 1)
    scores.tragic = max(0, (1 - hp_ratio) * 40)

    # 中立路线
    scores.neutral = 30 - abs(scores.hero - scores.villain) * 0.3

    # 隐藏路线: 完成所有任务 + 发现秘密
    if main_quests_completed >= total_main_quests and side_quests_completed >= 3:
        scores.secret = 60

    return scores


def determine_ending(scores: EndingScore) -> str:
    """确定最终结局

    Returns:
        结局类型: hero / villain / neutral / tragic / secret
    """
    all_scores = {
        "hero": scores.hero,
        "villain": scores.villain,
        "neutral": scores.neutral,
        "tragic": scores.tragic,
        "secret": scores.secret,
    }
    return max(all_scores, key=all_scores.get)


def format_ending_narrative(ending_type: str, player_name: str = "冒险者") -> str:
    """格式化结局叙事文本"""
    narratives = {
        "hero": f"传奇英雄 — {player_name}拯救了世界，成为传说中的英雄。人民传颂着你的故事。",
        "villain": f"黑暗降临 — {player_name}选择了黑暗的道路，世界陷入了永恒的阴影。",
        "neutral": f"平凡之路 — {player_name}完成了旅程，但世界既没有变得更好，也没有变得更坏。",
        "tragic": f"悲壮牺牲 — {player_name}付出了生命的代价，但世界得以延续。",
        "secret": f"隐藏真相 — {player_name}发现了世界的终极秘密，超越了凡人的命运。",
    }
    return narratives.get(ending_type, f"未知结局 — {player_name}的故事以一种意想不到的方式结束了。")