"""插件系统测试"""
from src.plugins import GamePlugin, load_plugin, get_all_modifiers, trigger_event, _loaded_plugins


def test_plugin_base():
    """插件基类"""
    plugin = GamePlugin()
    assert plugin.on_game_start(1) is None
    assert plugin.get_narrative_modifier() == ""


def test_load_weather_plugin():
    """加载天气插件"""
    _loaded_plugins.clear()
    plugin = load_plugin("src/plugins/weather_system.py")
    assert plugin.name == "weather_system"
    modifier = plugin.get_narrative_modifier()
    assert "天气" in modifier


def test_get_all_modifiers():
    """获取所有修饰"""
    _loaded_plugins.clear()
    load_plugin("src/plugins/weather_system.py")
    modifiers = get_all_modifiers()
    assert len(modifiers) > 0


def test_trigger_event():
    """触发事件"""
    _loaded_plugins.clear()
    load_plugin("src/plugins/weather_system.py")
    # 不应该抛异常
    trigger_event("on_game_start", world_id=1)
    trigger_event("on_location_change", world_id=1, old_location=1, new_location=2)
