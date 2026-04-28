"""LLMClient 测试"""
from src.services.llm_client import LLMClient


def test_llm_client_init():
    """测试LLMClient能正常初始化"""
    client = LLMClient()
    assert client.model == "deepseek-v4-flash"
    assert client.total_prompt_tokens == 0


def test_llm_client_chat():
    """测试基础对话"""
    client = LLMClient()
    response = client.chat([{"role": "user", "content": "说一个字：好"}])
    assert response is not None
    assert len(response) > 0
    assert client.total_prompt_tokens > 0
    print(f"\n回复: {response}")
    print(f"Token统计: {client.get_usage_stats()}")


def test_llm_client_tool_calling():
    """测试工具调用"""
    client = LLMClient()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "roll_dice",
                "description": "掷骰子",
                "parameters": {
                    "type": "object",
                    "properties": {"sides": {"type": "integer"}},
                    "required": ["sides"],
                },
            },
        }
    ]
    response = client.chat_with_tools(
        messages=[{"role": "user", "content": "帮我掷一个20面骰子"}],
        tools=tools,
    )
    assert response.choices[0].message.tool_calls is not None
    print(f"\ntool_calls: {response.choices[0].message.tool_calls}")
