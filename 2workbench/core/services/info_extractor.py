"""关键信息提取 - 自动从对话中提取重要信息"""
from .core.services.llm_client import LLMClient
from .core.models import world_repo
from .core.utils.logger import get_logger

logger = get_logger(__name__)

EXTRACTION_PROMPT = """从以下游戏对话中提取关键信息，以JSON格式返回。

提取规则:
- new_locations: 新发现的地点
- new_npcs: 新遇到的NPC
- items_obtained: 获得的物品
- key_choices: 玩家做出的重要选择
- current_objective: 当前目标

如果某项没有新信息，返回空列表。

对话:
{conversation}

只返回JSON，不要其他内容。格式:
{{"new_locations":[],"new_npcs":[],"items_obtained":[],"key_choices":[],"current_objective":""}}"""


async def extract_key_info(history: list[dict], llm: LLMClient | None = None) -> dict:
    """从最近对话中提取关键信息

    Args:
        history: 对话历史
        llm: LLM 客户端

    Returns:
        dict: {"new_locations": [...], "new_npcs": [...], ...}
    """
    import json

    # 只取最近 10 轮
    recent = history[-20:] if len(history) > 20 else history
    conversation = "\n".join(
        f"[{m.get('role', '?')}]: {m.get('content', '')}"
        for m in recent
    )

    try:
        llm = llm or LLMClient()
        response = await llm.chat([
            {"role": "system", "content": "你是一个信息提取器。只输出JSON。"},
            {"role": "user", "content": EXTRACTION_PROMPT.format(conversation=conversation)},
        ])

        # 尝试解析 JSON
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(response)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"信息提取失败: {e}")
        return {"new_locations": [], "new_npcs": [], "items_obtained": [], "key_choices": [], "current_objective": ""}


async def build_world_summary(world_id: int, history: list[dict], db_path: str | None = None) -> str:
    """构建世界状态摘要（注入上下文用）"""
    info = await extract_key_info(history)
    parts = []

    if info.get("new_locations"):
        parts.append(f"已探索地点: {', '.join(info['new_locations'])}")
    if info.get("new_npcs"):
        parts.append(f"已遇到NPC: {', '.join(info['new_npcs'])}")
    if info.get("items_obtained"):
        parts.append(f"已获得物品: {', '.join(info['items_obtained'])}")
    if info.get("current_objective"):
        parts.append(f"当前目标: {info['current_objective']}")

    return "\n".join(parts) if parts else ""
