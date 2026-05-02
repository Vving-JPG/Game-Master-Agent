"""常量定义"""
from core.constants.npc_templates import TEMPLATES as NPC_TEMPLATES, get_template, list_templates, apply_template
from core.constants.story_templates import TEMPLATES as STORY_TEMPLATES, generate_quest_from_template

__all__ = [
    "NPC_TEMPLATES", "get_template", "list_templates", "apply_template",
    "STORY_TEMPLATES", "generate_quest_from_template",
]