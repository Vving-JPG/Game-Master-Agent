"""优雅降级测试"""
from unittest.mock import patch, MagicMock
from src.services.llm_client import LLMClient


def test_api_failure_fallback():
    """API 失败时降级回复"""
    client = LLMClient()
    with patch.object(client, '_call_api', side_effect=Exception("API不可用")):
        result = client.chat([{"role": "user", "content": "测试"}])
        assert result is not None
        assert len(result) > 0
        # 检查是否是降级回复之一
        assert "GM" in result or "迷雾" in result or "时间" in result
        print(f"\n降级回复: {result}")


def test_tool_failure_message():
    """工具失败返回友好消息"""
    from src.tools.executor import execute_tool, TOOL_REGISTRY
    # 注册一个会失败的工具
    def failing_tool():
        raise RuntimeError("故意失败")
    TOOL_REGISTRY["_test_fail"] = {"func": failing_tool, "schema": {}}
    result = execute_tool("_test_fail", {})
    assert "失败" in result
    assert "GM将用文字描述代替" in result
    # 清理
    TOOL_REGISTRY.pop("_test_fail", None)
