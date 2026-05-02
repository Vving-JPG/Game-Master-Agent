"""剧情模板

从 _legacy/core/data/story_templates.py 提取。
"""
from __future__ import annotations

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "rescue": {
        "name": "救援",
        "description_template": "{target} 被 {enemy} 抓走了，需要前往 {location} 救出 {target}。",
        "steps": [
            {"type": "goto", "description": "前往 {location}"},
            {"type": "kill", "description": "击败 {enemy}"},
            {"type": "talk", "description": "与 {target} 对话"},
        ],
        "rewards": {"exp": 100, "gold": 50},
        "branches": {
            "stealth": {"description": "潜入 {location}，不惊动守卫", "modifier": 1.5},
            "direct": {"description": "正面突破", "modifier": 1.0},
        },
        "variables": ["target", "enemy", "location"],
    },
    "escort": {
        "name": "护送",
        "description_template": "护送 {npc} 安全到达 {destination}。",
        "steps": [
            {"type": "goto", "description": "与 {npc} 会合"},
            {"type": "goto", "description": "前往 {destination}"},
            {"type": "talk", "description": "与 {npc} 告别"},
        ],
        "rewards": {"exp": 80, "gold": 30},
        "branches": {
            "safe_route": {"description": "走安全路线（更远但更安全）", "modifier": 0.8},
            "dangerous_route": {"description": "走危险捷径", "modifier": 1.5},
        },
        "variables": ["npc", "destination"],
    },
    "collect": {
        "name": "收集",
        "description_template": "收集 {count} 个 {item}，交给 {npc}。",
        "steps": [
            {"type": "talk", "description": "与 {npc} 接受任务"},
            {"type": "collect", "description": "收集 {count} 个 {item}"},
            {"type": "talk", "description": "将物品交给 {npc}"},
        ],
        "rewards": {"exp": 60, "gold": 40},
        "variables": ["npc", "item", "count"],
    },
    "investigate": {
        "name": "调查",
        "description_template": "调查 {location} 发生的 {event}。",
        "steps": [
            {"type": "goto", "description": "前往 {location}"},
            {"type": "talk", "description": "询问目击者"},
            {"type": "goto", "description": "追踪线索到 {clue_location}"},
        ],
        "rewards": {"exp": 120, "gold": 60},
        "variables": ["location", "event", "clue_location"],
    },
    "exterminate": {
        "name": "消灭",
        "description_template": "消灭 {location} 的 {enemy}，威胁等级: {threat_level}。",
        "steps": [
            {"type": "goto", "description": "前往 {location}"},
            {"type": "kill", "description": "消灭 {enemy}（{count} 只）"},
            {"type": "talk", "description": "向 {npc} 报告"},
        ],
        "rewards": {"exp": 150, "gold": 80},
        "variables": ["location", "enemy", "count", "threat_level", "npc"],
    },
}


def generate_quest_from_template(template_name: str, **variables) -> dict[str, Any]:
    """从模板生成任务数据"""
    template = TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"未知剧情模板: {template_name}")

    # 填充变量
    description = template["description_template"]
    for key, value in variables.items():
        description = description.replace(f"{{{key}}}", str(value))

    # 填充步骤
    steps = []
    for step in template["steps"]:
        step_desc = step["description"]
        for key, value in variables.items():
            step_desc = step_desc.replace(f"{{{key}}}", str(value))
        steps.append({
            "description": step_desc,
            "type": step["type"],
            "completed": False,
        })

    return {
        "title": description[:30] + ("..." if len(description) > 30 else ""),
        "description": description,
        "steps": steps,
        "rewards": template["rewards"],
        "branches": template.get("branches", {}),
        "template_name": template_name,
    }