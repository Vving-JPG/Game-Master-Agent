"""上下文管理测试"""
from src.services.context_manager import estimate_tokens, compress_history, trim_history


def test_estimate_tokens():
    """Token 估算"""
    t1 = estimate_tokens("你好世界")  # 4个中文字
    assert t1 > 0
    t2 = estimate_tokens("Hello World")  # 11个英文字符
    assert t2 > 0


def test_compress_short_history():
    """短历史不压缩"""
    history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！欢迎来到冒险世界。"},
    ]
    result = compress_history(history)
    assert len(result) == len(history)


def test_compress_long_history():
    """长历史被压缩"""
    history = [{"role": "system", "content": "你是GM"}]
    for i in range(30):
        history.append({"role": "user", "content": f"这是第{i}轮玩家输入，内容比较长，包含很多信息。"})
        history.append({"role": "assistant", "content": f"这是第{i}轮GM回复，描述了丰富的场景和NPC互动。"})

    # 不传 llm，使用截断降级
    result = compress_history(history)
    assert len(result) < len(history)
    # system 消息保留
    assert result[0]["role"] == "system"


def test_trim_history():
    """裁剪历史"""
    history = [{"role": "system", "content": "系统提示"}]
    for i in range(100):
        history.append({"role": "user", "content": "x" * 500})
        history.append({"role": "assistant", "content": "y" * 500})

    result = trim_history(history, max_tokens=1000)
    assert result[0]["role"] == "system"
    assert len(result) < len(history)
