"""NPC 性格模板 — 基于 Big Five 人格模型

从 _legacy/core/data/npc_templates.py 提取。
"""
from core.models.entities import Personality

TEMPLATES: dict[str, dict] = {
    "brave_warrior": {
        "name": "勇敢战士",
        "personality": Personality(
            openness=0.4, conscientiousness=0.8,
            extraversion=0.7, agreeableness=0.5, neuroticism=0.3,
        ),
        "speech_style": "直率、豪爽，喜欢用简短的句子",
        "mood": "confident",
        "common_topics": ["战斗", "荣誉", "训练", "冒险"],
        "goals": ["保护弱者", "变强", "击败强敌"],
    },
    "mysterious_mage": {
        "name": "神秘法师",
        "personality": Personality(
            openness=0.9, conscientiousness=0.6,
            extraversion=0.2, agreeableness=0.4, neuroticism=0.5,
        ),
        "speech_style": "深奥、隐晦，喜欢用比喻和典故",
        "mood": "contemplative",
        "common_topics": ["魔法", "知识", "远古秘密", "星辰"],
        "goals": ["追求真理", "掌握禁忌魔法", "解开世界之谜"],
    },
    "friendly_merchant": {
        "name": "友好商人",
        "personality": Personality(
            openness=0.5, conscientiousness=0.6,
            extraversion=0.9, agreeableness=0.8, neuroticism=0.3,
        ),
        "speech_style": "热情、健谈，喜欢讨价还价",
        "mood": "cheerful",
        "common_topics": ["商品", "价格", "旅行见闻", "美食"],
        "goals": ["赚钱", "扩大生意", "结交人脉"],
    },
    "sinister_villain": {
        "name": "阴险反派",
        "personality": Personality(
            openness=0.7, conscientiousness=0.8,
            extraversion=0.4, agreeableness=0.1, neuroticism=0.6,
        ),
        "speech_style": "阴冷、讽刺，喜欢暗示和威胁",
        "mood": "menacing",
        "common_topics": ["权力", "控制", "弱点", "阴谋"],
        "goals": ["统治世界", "复仇", "获取神器"],
    },
    "wise_elder": {
        "name": "智慧长者",
        "personality": Personality(
            openness=0.8, conscientiousness=0.7,
            extraversion=0.4, agreeableness=0.8, neuroticism=0.2,
        ),
        "speech_style": "温和、睿智，喜欢讲寓言和故事",
        "mood": "serene",
        "common_topics": ["历史", "智慧", "传承", "命运"],
        "goals": ["守护知识", "引导后辈", "维护和平"],
    },
    "naive_villager": {
        "name": "天真村民",
        "personality": Personality(
            openness=0.3, conscientiousness=0.4,
            extraversion=0.6, agreeableness=0.9, neuroticism=0.7,
        ),
        "speech_style": "朴实、紧张，经常问问题",
        "mood": "nervous",
        "common_topics": ["村庄", "天气", "庄稼", "传闻"],
        "goals": ["过上安稳生活", "保护家人", "不被卷入冒险"],
    },
}


def get_template(template_name: str) -> dict | None:
    """获取 NPC 模板"""
    return TEMPLATES.get(template_name)


def list_templates() -> list[str]:
    """列出所有可用模板"""
    return list(TEMPLATES.keys())


def apply_template(template_name: str, overrides: dict | None = None) -> dict:
    """应用模板，返回 NPC 属性字典"""
    template = TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"未知 NPC 模板: {template_name}，可用: {list_templates()}")
    result = dict(template)
    if overrides:
        result.update(overrides)
    return result