"""插件系统 - 方便扩展新功能"""
import importlib.util
import json
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 已加载的插件
_loaded_plugins: dict[str, dict] = {}


class GamePlugin:
    """插件基类"""

    name: str = "unnamed_plugin"
    description: str = ""

    def on_game_start(self, world_id: int, db_path: str | None = None):
        """游戏开始时触发"""
        pass

    def on_player_action(self, world_id: int, player_input: str, db_path: str | None = None):
        """玩家行动时触发"""
        pass

    def on_combat_end(self, world_id: int, victory: bool, rewards: dict, db_path: str | None = None):
        """战斗结束时触发"""
        pass

    def on_quest_complete(self, world_id: int, quest_id: int, db_path: str | None = None):
        """任务完成时触发"""
        pass

    def on_location_change(self, world_id: int, old_location: int, new_location: int, db_path: str | None = None):
        """玩家移动到新地点时触发"""
        pass

    def get_narrative_modifier(self) -> str:
        """返回要注入到叙事中的额外描述"""
        return ""


def load_plugin(plugin_path: str) -> GamePlugin:
    """从 Python 文件加载插件"""
    spec = importlib.util.spec_from_file_location("plugin", plugin_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # 查找 GamePlugin 子类
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, GamePlugin) and attr != GamePlugin:
            plugin = attr()
            _loaded_plugins[plugin.name] = plugin
            logger.info(f"加载插件: {plugin.name} - {plugin.description}")
            return plugin

    raise ValueError(f"在 {plugin_path} 中未找到 GamePlugin 子类")


def load_all_plugins(plugin_dir: str = "src/plugins"):
    """加载目录中所有插件"""
    pdir = Path(plugin_dir)
    if not pdir.exists():
        logger.info(f"插件目录不存在: {plugin_dir}")
        return

    for py_file in pdir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        try:
            load_plugin(str(py_file))
        except Exception as e:
            logger.error(f"加载插件失败 {py_file}: {e}")


def get_plugin(name: str) -> GamePlugin | None:
    return _loaded_plugins.get(name)


def get_all_modifiers() -> str:
    """获取所有插件的叙事修饰"""
    modifiers = []
    for plugin in _loaded_plugins.values():
        mod = plugin.get_narrative_modifier()
        if mod:
            modifiers.append(mod)
    return "\n".join(modifiers)


def trigger_event(event_name: str, **kwargs):
    """触发插件事件"""
    for plugin in _loaded_plugins.values():
        handler = getattr(plugin, event_name, None)
        if handler:
            try:
                handler(**kwargs)
            except Exception as e:
                logger.error(f"插件 {plugin.name} 事件 {event_name} 失败: {e}")
