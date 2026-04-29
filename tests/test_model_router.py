"""多模型路由测试"""
from src.services.model_router import route_model, get_model_config


def test_default_route():
    """默认路由到快速模型"""
    model = route_model("你好")
    assert model == "deepseek-chat"


def test_combat_route():
    """战斗路由到推理模型"""
    model = route_model("我挥剑攻击Boss")
    assert model == "deepseek-reasoner"


def test_plot_route():
    """关键剧情路由到推理模型"""
    model = route_model("我要揭开真相")
    assert model == "deepseek-reasoner"


def test_long_conversation():
    """长对话路由到推理模型"""
    history = []
    for i in range(25):
        history.append({"role": "user", "content": f"第{i}轮"})
        history.append({"role": "assistant", "content": f"回复{i}"})
    model = route_model("继续", history)
    assert model == "deepseek-reasoner"


def test_get_config():
    """获取模型配置"""
    config = get_model_config("deepseek-chat")
    assert config["name"] == "deepseek-chat"
