"""NPC性格模板 - 预设性格类型，快速生成有特色的NPC"""

# 大五人格: openness(开放性), conscientiousness(尽责性), extraversion(外向性),
#           agreeableness(宜人性), neuroticism(神经质)
NPC_TEMPLATES = {
    "brave_warrior": {
        "name": "勇敢战士",
        "personality": {
            "openness": 0.3, "conscientiousness": 0.8,
            "extraversion": 0.7, "agreeableness": 0.5, "neuroticism": 0.2,
        },
        "speech_style": "直率豪爽，说话简洁有力，常用感叹号！喜欢谈论战斗和荣誉。",
        "mood": "confident",
        "common_topics": ["战斗", "荣誉", "武器", "训练", "冒险"],
        "goals": [{"description": "变得更强", "priority": 1}],
    },
    "mysterious_mage": {
        "name": "神秘法师",
        "personality": {
            "openness": 0.9, "conscientiousness": 0.6,
            "extraversion": 0.2, "agreeableness": 0.4, "neuroticism": 0.5,
        },
        "speech_style": "说话隐晦深奥，喜欢用比喻和暗示。语速缓慢，经常停顿思考……",
        "mood": "contemplative",
        "common_topics": ["魔法", "知识", "古代秘密", "星辰", "命运"],
        "goals": [{"description": "探索魔法的奥秘", "priority": 1}],
    },
    "friendly_merchant": {
        "name": "友好商人",
        "personality": {
            "openness": 0.5, "conscientiousness": 0.7,
            "extraversion": 0.9, "agreeableness": 0.8, "neuroticism": 0.3,
        },
        "speech_style": "热情洋溢，喜欢用亲切的称呼！经常推荐商品，说话带着商人的精明。",
        "mood": "cheerful",
        "common_topics": ["商品", "价格", "旅行见闻", "美食", "交易"],
        "goals": [{"description": "积累财富", "priority": 1}],
    },
    "sinister_villain": {
        "name": "阴险反派",
        "personality": {
            "openness": 0.6, "conscientiousness": 0.9,
            "extraversion": 0.4, "agreeableness": 0.1, "neuroticism": 0.7,
        },
        "speech_style": "阴阳怪气，喜欢嘲讽和威胁。说话时带着冷笑，经常用反问句。",
        "mood": "cunning",
        "common_topics": ["权力", "阴谋", "弱点", "控制", "复仇"],
        "goals": [{"description": "统治一切", "priority": 1}],
    },
    "wise_elder": {
        "name": "智慧长者",
        "personality": {
            "openness": 0.8, "conscientiousness": 0.9,
            "extraversion": 0.3, "agreeableness": 0.7, "neuroticism": 0.2,
        },
        "speech_style": "说话缓慢庄重，喜欢引用古训和谚语。经常用'孩子'称呼年轻人。",
        "mood": "serene",
        "common_topics": ["历史", "智慧", "传统", "和平", "自然"],
        "goals": [{"description": "守护村庄的和平", "priority": 1}],
    },
    "naive_villager": {
        "name": "天真村民",
        "personality": {
            "openness": 0.4, "conscientiousness": 0.4,
            "extraversion": 0.6, "agreeableness": 0.9, "neuroticism": 0.6,
        },
        "speech_style": "说话朴实无华，容易紧张。经常问问题，对冒险者充满好奇和敬畏。",
        "mood": "curious",
        "common_topics": ["村庄日常", "天气", "庄稼", "传闻", "家人"],
        "goals": [{"description": "过上安稳的日子", "priority": 1}],
    },
}


def get_template(template_name: str) -> dict | None:
    """获取性格模板"""
    return NPC_TEMPLATES.get(template_name)


def list_templates() -> list[str]:
    """列出所有可用模板名"""
    return list(NPC_TEMPLATES.keys())


def apply_template(template_name: str, npc_name: str, custom_overrides: dict | None = None) -> dict:
    """应用模板生成NPC属性

    Args:
        template_name: 模板名
        npc_name: NPC名字
        custom_overrides: 自定义覆盖（如 {"mood": "angry"}）

    Returns:
        dict: 可直接传给 npc_repo.create_npc 的关键字参数
    """
    template = NPC_TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"未知模板: {template_name}，可用: {list_templates()}")

    import json
    attrs = {
        "personality": json.dumps(template["personality"]),
        "mood": template["mood"],
        "goals": json.dumps(template["goals"]),
        "speech_style": template["speech_style"],
    }
    if custom_overrides:
        attrs.update(custom_overrides)
    return attrs
