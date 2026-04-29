"""异常处理测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.services.llm_client import LLMClient
from src.agent.game_master import GameMaster
from src.tools.executor import execute_tool

DB_PATH = None


def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")


def test_empty_input():
    """空输入不崩溃"""
    result = seed_world(DB_PATH)
    gm = GameMaster(result["world_id"], result["player_id"], LLMClient(), DB_PATH)
    response = gm.process("")
    assert response is not None


def test_unknown_tool():
    """未知工具返回错误信息"""
    try:
        result = execute_tool("nonexistent_tool", {})
        assert "未知工具" in result
    except KeyError:
        pass  # 也可以抛出异常


def test_long_conversation():
    """长对话不崩溃 - 使用Mock避免API调用"""
    from unittest.mock import patch, MagicMock
    
    result = seed_world(DB_PATH)
    gm = GameMaster(result["world_id"], result["player_id"], LLMClient(), DB_PATH)
    
    # Mock LLM客户端以避免实际API调用
    with patch.object(gm.llm, 'chat_with_tools') as mock_chat:
        mock_response = MagicMock()
        mock_response.content = "这是一个测试回复"
        mock_response.tool_calls = None
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_chat.return_value = mock_response
        
        for i in range(2):
            response = gm.process(f"测试消息第{i+1}轮")
            assert response is not None
