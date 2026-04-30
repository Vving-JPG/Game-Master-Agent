"""预生成服务 - 提前生成可能需要的内容"""
import asyncio
from src.services.llm_client import LLMClient
from src.services.cache import llm_cache
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 预生成缓存键前缀
PREGEN_PREFIX = "pregen:"


async def pregenerate_location_description(location_name: str, location_type: str = "普通地点") -> str:
    """预生成地点描述"""
    cache_key = f"{PREGEN_PREFIX}location:{location_name}"
    cached = llm_cache.get(cache_key)
    if cached:
        return cached

    prompt = f"为一个奇幻RPG游戏生成'{location_name}'的详细场景描述（{location_type}）。2-3句话，包含视觉、听觉、嗅觉。只输出描述。"
    llm = LLMClient()
    description = await llm.chat([
        {"role": "system", "content": "你是RPG场景描述生成器。"},
        {"role": "user", "content": prompt},
    ])
    llm_cache.set(cache_key, description)
    logger.info(f"预生成地点描述: {location_name}")
    return description


async def pregenerate_npc_greeting(npc_name: str, personality: str = "友好") -> str:
    """预生成 NPC 打招呼"""
    cache_key = f"{PREGEN_PREFIX}npc_greet:{npc_name}"
    cached = llm_cache.get(cache_key)
    if cached:
        return cached

    prompt = f"生成NPC'{npc_name}'（性格：{personality}）的首次见面打招呼语。1-2句话。只输出对话。"
    llm = LLMClient()
    greeting = await llm.chat([
        {"role": "system", "content": "你是RPG NPC 对话生成器。"},
        {"role": "user", "content": prompt},
    ])
    llm_cache.set(cache_key, greeting)
    logger.info(f"预生成NPC打招呼: {npc_name}")
    return greeting


async def pregenerate_for_location(location_name: str, npc_names: list[str] | None = None):
    """为进入新地点预生成所有内容"""
    tasks = [pregenerate_location_description(location_name)]
    if npc_names:
        for name in npc_names:
            tasks.append(pregenerate_npc_greeting(name))
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info(f"预生成完成: {location_name} ({len(tasks)}项)")
