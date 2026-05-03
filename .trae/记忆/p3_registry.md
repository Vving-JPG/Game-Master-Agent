# P3-03: FeatureRegistry 注册表

> 模块: `feature.registry`
> 文件: `2workbench/feature/registry.py`
> 全局单例: `feature_registry`

---

## 核心类

```python
class FeatureRegistry:
    """
    Feature 注册表
    
    管理所有 Feature 的注册、启用、禁用。
    """
    
    def register(self, feature_class: type[BaseFeature]) -> None
    def enable(self, feature_name: str) -> bool
    def disable(self, feature_name: str) -> bool
    def get(self, feature_name: str) -> BaseFeature | None
    def list_features(self) -> list[str]
    def list_enabled(self) -> list[str]
    def check_dependencies(self, feature_name: str) -> tuple[bool, list[str]]
```

---

## 使用示例

```python
from feature.registry import feature_registry
from feature.battle.system import BattleSystem
from feature.dialogue.system import DialogueSystem

# 注册 Feature
feature_registry.register(BattleSystem)
feature_registry.register(DialogueSystem)

# 启用 Feature
feature_registry.enable("battle")
feature_registry.enable("dialogue")

# 获取 Feature 实例
battle = feature_registry.get("battle")

# 列出所有 Feature
all_features = feature_registry.list_features()
# ['battle', 'dialogue', 'quest', 'item', ...]

# 列出已启用的 Feature
enabled = feature_registry.list_enabled()
# ['battle', 'dialogue']
```

---

## 依赖检查

```python
# 检查依赖是否满足
ok, missing = feature_registry.check_dependencies("quest")
if not ok:
    print(f"缺少依赖: {missing}")
    # 需要先启用依赖
    for dep in missing:
        feature_registry.enable(dep)
```

---

## 事件命名规范

Feature 事件命名: `feature.{feature_name}.{action}`

```python
# 战斗系统事件
feature.battle.started
feature.battle.ended
feature.battle.turn_start
feature.battle.damage_dealt

# 对话系统事件
feature.dialogue.started
feature.dialogue.ended
feature.dialogue.favor_changed

# 任务系统事件
feature.quest.accepted
feature.quest.updated
feature.quest.completed
```
