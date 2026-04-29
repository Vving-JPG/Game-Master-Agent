"""剧情模板系统 - 预设剧情模板，程序化生成任务"""

STORY_TEMPLATES = {
    "rescue": {
        "name": "救援任务",
        "description_template": "{victim}被{enemy}抓走了！去{location}救出{victim}。",
        "steps": [
            {"description": "前往{location}", "step_type": "goto", "target": "{location}"},
            {"description": "击败{enemy}", "step_type": "kill", "target": "{enemy}", "required_count": 1},
            {"description": "护送{victim}回到安全地点", "step_type": "goto", "target": "安全地点"},
        ],
        "rewards": {"exp": 150, "gold": 80},
        "branches": [
            {"id": "stealth", "text": "潜入营救", "next_step": 2},
            {"id": "force", "text": "正面突袭", "next_step": 2},
        ],
        "variables": ["victim", "enemy", "location"],
    },
    "escort": {
        "name": "护送任务",
        "description_template": "护送{npc_name}从{from_location}安全到达{to_location}。",
        "steps": [
            {"description": "与{npc_name}在{from_location}会合", "step_type": "talk", "target": "{npc_name}"},
            {"description": "护送{npc_name}前往{to_location}", "step_type": "goto", "target": "{to_location}"},
            {"description": "保护{npc_name}免受袭击", "step_type": "kill", "target": "袭击者", "required_count": 3},
        ],
        "rewards": {"exp": 120, "gold": 60},
        "variables": ["npc_name", "from_location", "to_location"],
    },
    "collect": {
        "name": "收集任务",
        "description_template": "收集{count}个{item}交给{giver}。",
        "steps": [
            {"description": "收集{count}个{item}", "step_type": "collect", "target": "{item}", "required_count": "{count}"},
            {"description": "把{item}交给{giver}", "step_type": "talk", "target": "{giver}"},
        ],
        "rewards": {"exp": 80, "gold": 40},
        "variables": ["item", "count", "giver"],
    },
    "investigate": {
        "name": "调查任务",
        "description_template": "调查{location}的神秘{event}。",
        "steps": [
            {"description": "前往{location}", "step_type": "goto", "target": "{location}"},
            {"description": "搜索线索", "step_type": "collect", "target": "线索", "required_count": 3},
            {"description": "向{informant}询问", "step_type": "talk", "target": "{informant}"},
            {"description": "揭开真相", "step_type": "goto", "target": "真相地点"},
        ],
        "rewards": {"exp": 200, "gold": 100},
        "variables": ["location", "event", "informant"],
    },
    "exterminate": {
        "name": "消灭任务",
        "description_template": "消灭{count}个{enemy}，清除{location}的威胁。",
        "steps": [
            {"description": "前往{location}", "step_type": "goto", "target": "{location}"},
            {"description": "消灭{count}个{enemy}", "step_type": "kill", "target": "{enemy}", "required_count": "{count}"},
        ],
        "rewards": {"exp": 100, "gold": 50},
        "variables": ["enemy", "count", "location"],
    },
}


def generate_quest_from_template(template_name: str, variables: dict, quest_type: str = "side") -> dict:
    """从模板生成任务数据

    Args:
        template_name: 模板名 (rescue/escort/collect/investigate/exterminate)
        variables: 模板变量，如 {"victim": "公主", "enemy": "巨龙", "location": "龙穴"}
        quest_type: 任务类型

    Returns:
        dict: {title, description, steps, rewards, branches}
    """
    template = STORY_TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"未知模板: {template_name}，可用: {list(STORY_TEMPLATES.keys())}")

    # 填充变量
    title = template["description_template"].format(**variables)
    description = title

    steps = []
    for i, step in enumerate(template["steps"]):
        s = dict(step)
        s["description"] = s["description"].format(**variables)
        s["target"] = s["target"].format(**variables)
        if isinstance(s.get("required_count"), str):
            s["required_count"] = int(s["required_count"].format(**variables))
        s["step_order"] = i + 1
        steps.append(s)

    rewards = template["rewards"]
    branches = []
    for b in template.get("branches", []):
        branches.append({**b, "text": b["text"].format(**variables)})

    return {
        "title": title,
        "description": description,
        "steps": steps,
        "rewards": rewards,
        "branches": branches,
        "quest_type": quest_type,
    }
