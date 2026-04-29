"""多结局系统 - 根据玩家选择生成不同结局"""
from src.models import quest_repo, player_repo
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 结局类型定义
ENDING_TYPES = {
    "hero": {
        "name": "英雄结局",
        "description": "你成为了拯救世界的英雄，被世人传颂。",
        "conditions": ["completed_main_quests", "high_reputation"],
    },
    "villain": {
        "name": "反派结局",
        "description": "你选择了黑暗的道路，成为了新的威胁。",
        "conditions": ["betrayed_allies", "low_morality"],
    },
    "neutral": {
        "name": "中立结局",
        "description": "你保持了中立，世界继续运转，但你留下了自己的传说。",
        "conditions": ["balanced_choices"],
    },
    "tragic": {
        "name": "悲剧结局",
        "description": "你的冒险以悲剧收场，但你的牺牲不会被遗忘。",
        "conditions": ["sacrificed_self"],
    },
    "secret": {
        "name": "隐藏结局",
        "description": "你发现了世界的真相，一切都变得不同了...",
        "conditions": ["found_all_secrets"],
    },
}


def calculate_ending_score(world_id: int, player_id: int, db_path: str | None = None) -> dict:
    """计算结局分数

    Returns:
        {ending_type: score, ...}
    """
    scores = {k: 0 for k in ENDING_TYPES.keys()}

    # 获取玩家任务完成情况
    quests = quest_repo.get_quests_by_player(player_id, db_path)
    completed_main = sum(1 for q in quests if q.get("status") == "completed" and q.get("quest_type") == "main")
    completed_side = sum(1 for q in quests if q.get("status") == "completed" and q.get("quest_type") == "side")

    # 英雄结局分数
    scores["hero"] += completed_main * 10 + completed_side * 5

    # 反派结局分数（简化：假设有背叛行为会记录）
    # scores["villain"] += betrayal_count * 15

    # 中立结局分数
    if completed_main > 0 and completed_side > completed_main:
        scores["neutral"] += 20

    # 悲剧结局（玩家死亡或重大牺牲）
    player = player_repo.get_player(player_id, db_path)
    if player and player.get("hp", 100) <= 0:
        scores["tragic"] += 50

    return scores


def determine_ending(world_id: int, player_id: int, db_path: str | None = None) -> dict:
    """确定最终结局"""
    scores = calculate_ending_score(world_id, player_id, db_path)
    best_ending = max(scores, key=scores.get)

    ending_info = ENDING_TYPES[best_ending].copy()
    ending_info["score"] = scores[best_ending]
    ending_info["all_scores"] = scores

    logger.info(f"玩家{player_id}的结局: {ending_info['name']} (分数: {ending_info['score']})")
    return ending_info


def format_ending_narrative(ending: dict) -> str:
    """格式化结局叙事"""
    lines = [
        "=" * 40,
        "🏆 结局达成",
        "=" * 40,
        f"【{ending['name']}】",
        "",
        ending['description'],
        "",
        f"结局分数: {ending['score']}",
        "=" * 40,
    ]
    return "\n".join(lines)
