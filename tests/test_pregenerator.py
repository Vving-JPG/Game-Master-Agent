"""预生成测试"""
import asyncio
from src.services.pregenerator import pregenerate_location_description, pregenerate_npc_greeting


def test_pregenerate_location():
    """预生成地点描述 - 同步测试"""
    result = asyncio.run(pregenerate_location_description("龙穴", "危险地点"))
    assert result is not None
    assert len(result) > 0
    print(f"\n预生成结果: {result[:100]}")


def test_pregenerate_npc():
    """预生成NPC打招呼"""
    result = asyncio.run(pregenerate_npc_greeting("村长", "智慧"))
    assert result is not None
    assert len(result) > 0
    print(f"\nNPC打招呼: {result[:100]}")


def test_cache_hit():
    """第二次调用命中缓存"""
    r1 = asyncio.run(pregenerate_location_description("测试村"))
    r2 = asyncio.run(pregenerate_location_description("测试村"))
    assert r1 == r2
