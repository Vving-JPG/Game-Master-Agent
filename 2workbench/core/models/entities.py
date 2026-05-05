"""游戏实体数据模型 — Pydantic BaseModel

所有游戏实体的数据结构定义。
这些模型用于:
1. Repository 层的返回值类型
2. LangGraph State 中的字段类型
3. API 层的请求/响应模型

注意: 这些是纯数据类，不包含任何业务逻辑。
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ========== 枚举 ==========

class WorldType(StrEnum):
    """世界类型"""
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    MODERN = "modern"
    HISTORICAL = "historical"
    CUSTOM = "custom"


class ItemType(StrEnum):
    """道具类型"""
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    QUEST = "quest"
    MISC = "misc"


class ItemRarity(StrEnum):
    """道具稀有度"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class QuestStatus(StrEnum):
    """任务状态"""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_STARTED = "not_started"


class QuestType(StrEnum):
    """任务类型"""
    MAIN = "main"
    SIDE = "side"
    DAILY = "daily"
    HIDDEN = "hidden"


class EventType(StrEnum):
    """游戏事件类型"""
    PLAYER_ACTION = "player_action"
    PLAYER_MOVE = "player_move"
    COMBAT_START = "combat_start"
    COMBAT_ACTION = "combat_action"
    COMBAT_END = "combat_end"
    QUEST_UPDATE = "quest_update"
    ITEM_ACQUIRE = "item_acquire"
    NPC_INTERACT = "npc_interact"
    TIME_PASS = "time_pass"
    SYSTEM_EVENT = "system_event"


class MemoryCategory(StrEnum):
    """记忆类别"""
    NPC = "npc"
    LOCATION = "location"
    PLAYER = "player"
    QUEST = "quest"
    WORLD = "world"
    SESSION = "session"


class PersonalityTrait(StrEnum):
    """大五人格维度"""
    OPENNESS = "openness"          # 开放性
    CONSCIENTIOUSNESS = "conscientiousness"  # 尽责性
    EXTRAVERSION = "extraversion"  # 外向性
    AGREEABLENESS = "agreeableness"  # 宜人性
    NEUROTICISM = "neuroticism"    # 神经质


# ========== 世界 ==========

class World(BaseModel):
    """世界"""
    id: int = 0
    name: str = ""
    setting: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""


# ========== 地点 ==========

class Location(BaseModel):
    """地点"""
    id: int = 0
    world_id: int = 0
    name: str = ""
    description: str = ""
    connections: dict[str, int] = Field(default_factory=dict)  # {"north": 2, "south": 3}
    created_at: str = ""
    updated_at: str = ""


# ========== 玩家 ==========

class Player(BaseModel):
    """玩家"""
    id: int = 0
    world_id: int = 0
    name: str = ""
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    level: int = 1
    exp: int = 0
    gold: int = 0
    location_id: int = 0
    created_at: str = ""
    updated_at: str = ""


# ========== NPC ==========

class Personality(BaseModel):
    """大五人格"""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5


class NPC(BaseModel):
    """NPC"""
    id: int = 0
    world_id: int = 0
    location_id: int = 0
    name: str = ""
    personality: Personality = Field(default_factory=Personality)
    backstory: str = ""
    mood: str = "neutral"
    goals: list[str] = Field(default_factory=list)
    relationships: dict[str, float] = Field(default_factory=dict)  # {"player": 0.5}
    speech_style: str = ""
    created_at: str = ""
    updated_at: str = ""


# ========== 道具 ==========

class ItemStats(BaseModel):
    """道具属性"""
    attack: int = 0
    defense: int = 0
    hp_bonus: int = 0
    mp_bonus: int = 0
    speed: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)


class Item(BaseModel):
    """道具模板"""
    id: int = 0
    name: str = ""
    item_type: ItemType = ItemType.MISC
    rarity: ItemRarity = ItemRarity.COMMON
    slot: str = ""
    stats: ItemStats = Field(default_factory=ItemStats)
    description: str = ""
    level_req: int = 1
    stackable: bool = False
    usable: bool = False
    created_at: str = ""


class PlayerItem(BaseModel):
    """玩家物品栏条目"""
    id: int = 0
    player_id: int = 0
    item_id: int = 0
    quantity: int = 1
    equipped: bool = False
    item: Item | None = None  # 关联查询时填充


# ========== 任务 ==========

class QuestStep(BaseModel):
    """任务步骤"""
    id: int = 0
    quest_id: int = 0
    step_order: int = 0
    description: str = ""
    step_type: str = ""  # goto / kill / talk / collect
    target: str = ""
    required_count: int = 1
    current_count: int = 0
    completed: bool = False


class Quest(BaseModel):
    """任务"""
    id: int = 0
    world_id: int = 0
    player_id: int | None = 0
    title: str = ""
    description: str = ""
    quest_type: QuestType = QuestType.SIDE
    status: QuestStatus = QuestStatus.NOT_STARTED
    rewards: dict[str, Any] = Field(default_factory=dict)
    prerequisites: dict[str, Any] = Field(default_factory=dict)
    branches: dict[str, Any] = Field(default_factory=dict)
    steps: list[QuestStep] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


# ========== 记忆（统一 SQLite） ==========

class Memory(BaseModel):
    """记忆条目 — 统一存储在 SQLite 中

    替代原有的 Markdown 文件记忆系统。
    支持按类别、世界、重要性检索。
    """
    id: int = 0
    world_id: int = 0
    category: MemoryCategory = MemoryCategory.SESSION
    source: str = ""           # 来源标识（如 "npc:张三" 或 "location:酒馆"）
    title: str = ""            # 记忆标题
    content: str = ""          # 记忆内容（Markdown 格式）
    importance: float = 0.5    # 重要性 0-1
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)  # 扩展元数据
    turn_created: int = 0      # 创建时的回合数
    turn_last_referenced: int = 0  # 最后被引用的回合数
    created_at: str = ""
    updated_at: str = ""


# ========== 游戏日志 ==========

class GameLog(BaseModel):
    """游戏日志"""
    id: int = 0
    world_id: int = 0
    event_type: str = ""
    content: str = ""
    timestamp: str = ""


# ========== 对话消息 ==========

class GameMessage(BaseModel):
    """对话消息"""
    id: int = 0
    world_id: int = 0
    role: str = ""             # system / user / assistant / npc / narrator
    name: str = ""             # 说话者名称
    content: str = ""
    timestamp: str = ""


# ========== Prompt 版本 ==========

class PromptVersion(BaseModel):
    """Prompt 版本"""
    id: int = 0
    prompt_key: str = ""
    content: str = ""
    version: int = 1
    is_active: bool = True
    description: str = ""
    created_at: str = ""


# ========== LLM 调用记录 ==========

class LLMCallRecord(BaseModel):
    """LLM 调用记录"""
    id: int = 0
    world_id: int = 0
    call_type: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    model: str = ""
    tool_calls_count: int = 0
    tool_names: list[str] = Field(default_factory=list)
    error: str = ""
    timestamp: str = ""
