"""DeepSeek API 基础调用测试"""
from src.config import settings
from openai import OpenAI


def test_basic_chat():
    """测试基础对话功能"""
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
    response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[{"role": "user", "content": "你好，用一句话介绍你自己"}],
    )
    content = response.choices[0].message.content
    print(f"\nDeepSeek回复: {content}")
    assert content is not None
    assert len(content) > 0


def test_tool_calling():
    """测试工具调用(function calling)功能"""
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取指定城市的天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称"},
                    },
                    "required": ["city"],
                },
            },
        }
    ]

    response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[{"role": "user", "content": "北京天气怎么样？"}],
        tools=tools,
    )

    message = response.choices[0].message
    print(f"\ntool_calls: {message.tool_calls}")

    assert message.tool_calls is not None, "应该返回tool_calls"
    assert message.tool_calls[0].function.name == "get_weather"
    assert "北京" in message.tool_calls[0].function.arguments


def test_streaming():
    """测试流式输出功能"""
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    print("\n--- 流式输出开始 ---")
    collected = []
    for chunk in client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[{"role": "user", "content": "讲一个30字的短故事"}],
        stream=True,
    ):
        if chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            print(text, end="", flush=True)
            collected.append(text)
    print("\n--- 流式输出结束 ---")

    full_text = "".join(collected)
    assert len(full_text) > 0, "应该有输出内容"
