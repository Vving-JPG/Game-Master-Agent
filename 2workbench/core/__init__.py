"""Core 层 — 纯数据 + 纯规则

本层包含:
- 数据模型（Pydantic BaseModel）
- LangGraph State 定义
- Repository（数据访问对象）
- 纯函数计算器
- 常量定义

本层只依赖 Foundation 层，不依赖 Feature/Presentation 层。
"""
# 数据模型
from core.models import (
    World, Location, Player, NPC, Personality,
    Item, ItemStats, PlayerItem,
    Quest, QuestStep,
    Memory, GameLog, GameMessage,
    PromptVersion, LLMCallRecord,
    WorldType, ItemType, ItemRarity, QuestStatus, QuestType,
    EventType, MemoryCategory, PersonalityTrait,
    WorldRepo, LocationRepo, PlayerRepo, NPCRepo, ItemRepo,
    QuestRepo, MemoryRepo, LogRepo, PromptRepo, MetricsRepo,
)

# LangGraph State
from core.state import AgentState, create_initial_state

# 纯函数计算器
from core.calculators import (
    Combatant, AttackResult, CombatResult,
    roll_dice, attack, combat_round, is_combat_over, calculate_rewards,
    EndingScore, calculate_ending_score, determine_ending, format_ending_narrative,
)

# 常量
from core.constants import (
    NPC_TEMPLATES, get_template, list_templates, apply_template,
    STORY_TEMPLATES, generate_quest_from_template,
)

__all__ = [
    # 实体
    "World", "Location", "Player", "NPC", "Personality",
    "Item", "ItemStats", "PlayerItem",
    "Quest", "QuestStep",
    "Memory", "GameLog", "GameMessage",
    "PromptVersion", "LLMCallRecord",
    # 枚举
    "WorldType", "ItemType", "ItemRarity", "QuestStatus", "QuestType",
    "EventType", "MemoryCategory", "PersonalityTrait",
    # Repository
    "WorldRepo", "LocationRepo", "PlayerRepo", "NPCRepo", "ItemRepo",
    "QuestRepo", "MemoryRepo", "LogRepo", "PromptRepo", "MetricsRepo",
    # State
    "AgentState", "create_initial_state",
    # 计算器
    "Combatant", "AttackResult", "CombatResult",
    "roll_dice", "attack", "combat_round", "is_combat_over", "calculate_rewards",
    "EndingScore", "calculate_ending_score", "determine_ending", "format_ending_narrative",
    # 常量
    "NPC_TEMPLATES", "get_template", "list_templates", "apply_template",
    "STORY_TEMPLATES", "generate_quest_from_template",
]