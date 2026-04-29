"""天气系统插件 - 影响场景描述"""
import random
from src.plugins import GamePlugin


class WeatherPlugin(GamePlugin):
    name = "weather_system"
    description = "天气系统，影响场景描述"

    def __init__(self):
        self.current_weather = random.choice(["晴朗", "多云", "小雨", "大雾", "暴风雨"])
        self.weather_effects = {
            "晴朗": "阳光透过树叶洒下斑驳的光影",
            "多云": "厚重的云层遮蔽了天空，空气沉闷",
            "小雨": "细雨绵绵，雨滴打在盔甲上发出清脆的声响",
            "大雾": "浓雾弥漫，能见度不足十步",
            "暴风雨": "狂风暴雨肆虐，闪电撕裂天空",
        }

    def on_game_start(self, world_id, **kwargs):
        self.current_weather = random.choice(list(self.weather_effects.keys()))

    def on_location_change(self, world_id, old_location, new_location, **kwargs):
        # 30% 概率天气变化
        if random.random() < 0.3:
            self.current_weather = random.choice(list(self.weather_effects.keys()))

    def get_narrative_modifier(self) -> str:
        effect = self.weather_effects.get(self.current_weather, "")
        return f"[天气: {self.current_weather}] {effect}"
