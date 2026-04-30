"""关键信息提取测试（V2: 异步）"""
import pytest
from src.services.info_extractor import extract_key_info, build_world_summary


@pytest.mark.asyncio
async def test_extract_basic():
    """基本提取（不调LLM，测试降级）"""
    history = [
        {"role": "user", "content": "我去了暗影森林"},
        {"role": "assistant", "content": "你进入了暗影森林，树木遮天蔽日。"},
    ]
    result = await extract_key_info(history)
    # 降级返回空结构
    assert "new_locations" in result
    assert "new_npcs" in result


@pytest.mark.asyncio
async def test_build_summary_empty():
    """空历史不崩溃"""
    summary = await build_world_summary(1, [])
    assert isinstance(summary, str)


@pytest.mark.asyncio
async def test_build_summary_with_history():
    """有历史时构建摘要"""
    history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "欢迎来到新手村。"},
    ]
    summary = await build_world_summary(1, history)
    assert isinstance(summary, str)
