"""NPC对话服务 - 根据性格生成对话"""
import json
from src.services.llm_client import LLMClient
from src.models import npc_repo, log_repo
# V1 tool 系统已删除（V2 改用 Skills）
# from src.tools import world_tool
from src.utils.logger import get_logger

logger = get_logger(__name__)

# V2: 活跃玩家 ID 由调用方设置
_active_player_id: int | None = None


def set_active_player(pid: int):
    """设置当前活跃玩家ID"""
    global _active_player_id
    _active_player_id = pid

# 对话用的System Prompt模板
DIALOG_SYSTEM_PROMPT = """你是一个RPG游戏中的NPC。请根据以下人设信息，用中文回复玩家。

## NPC信息
- 名字: {name}
- 心情: {mood}
- 说话风格: {speech_style}
- 性格: {personality_desc}
- 目标: {goals_desc}
- 背景故事: {backstory}
- 与玩家的关系: {relationship_desc}

## 规则
1. 严格保持角色人设，不要跳出角色
2. 根据心情调整语气（开心时热情，愤怒时暴躁）
3. 回复长度控制在1-3句话
4. 可以在对话中透露任务线索或世界信息
5. 不要用括号标注动作，直接说话
"""


def build_npc_context(npc_id: int, db_path: str | None = None) -> dict:
    """构建NPC上下文信息"""
    npc = npc_repo.get_npc(npc_id, db_path)
    if not npc:
        return None

    personality = npc.get("personality") or {}
    goals = npc.get("goals") or []
    relationships = npc.get("relationships") or {}

    # 性格描述
    trait_names = {
        "openness": "开放性", "conscientiousness": "尽责性",
        "extraversion": "外向性", "agreeableness": "宜人性", "neuroticism": "神经质",
    }
    personality_desc = "，".join(
        f"{trait_names.get(k, k)}{v:.0%}" for k, v in personality.items() if v > 0.6
    ) or "普通"

    goals_desc = "，".join(g["description"] for g in goals) or "无特定目标"

    # 与玩家的关系
    pid = _active_player_id
    rel_value = relationships.get(str(pid), 0)
    if rel_value > 50:
        relationship_desc = f"友好（{rel_value}）"
    elif rel_value > 0:
        relationship_desc = f"中立偏善（{rel_value}）"
    elif rel_value > -50:
        relationship_desc = f"中立偏冷（{rel_value}）"
    else:
        relationship_desc = f"敌对（{rel_value}）"

    return {
        "name": npc["name"],
        "mood": npc.get("mood", "neutral"),
        "speech_style": npc.get("speech_style", ""),
        "personality_desc": personality_desc,
        "goals_desc": goals_desc,
        "backstory": npc.get("backstory", ""),
        "relationship_desc": relationship_desc,
    }


async def generate_npc_dialog(npc_id: int, player_message: str,
                        llm: LLMClient | None = None, db_path: str | None = None) -> str:
    """生成NPC对话回复

    Args:
        npc_id: NPC ID
        player_message: 玩家说的话
        llm: LLM客户端（可选，默认新建）
        db_path: 数据库路径

    Returns:
        NPC的回复文本
    """
    ctx = build_npc_context(npc_id, db_path)
    if not ctx:
        return f"未找到ID为{npc_id}的NPC。"

    system_prompt = DIALOG_SYSTEM_PROMPT.format(**ctx)

    llm = llm or LLMClient()
    reply = await llm.chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": player_message},
    ])

    # 记录对话日志
    wid = world_tool._active_world_id
    log_repo.log_event(wid, "dialog",
                       f"[{ctx['name']}] 玩家: {player_message} → NPC: {reply}",
                       db_path)

    logger.info(f"NPC对话: {ctx['name']} ← {player_message} → {reply[:50]}...")
    return reply
