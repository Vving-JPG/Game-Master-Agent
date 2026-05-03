# P3-01: BaseFeature Feature 基类

> 模块: `feature.base`
> 文件: `2workbench/feature/base.py`

---

## 核心类

```python
class BaseFeature(ABC):
    """
    Feature 基类
    
    所有 Feature 必须继承此类。
    """
    
    name: str = ""                    # Feature 名称
    description: str = ""             # 描述
    dependencies: list[str] = []      # 依赖的其他 Feature
    
    def __init__(self):
        self._enabled = False
        self._event_handlers: list[str] = []
    
    @abstractmethod
    def on_enable(self) -> None:
        """启用时调用"""
        pass
    
    @abstractmethod
    def on_disable(self) -> None:
        """禁用时调用"""
        pass
    
    def emit(self, event_type: str, data: dict) -> None:
        """发送事件"""
        pass
    
    def subscribe(self, event_type: str, handler: Callable) -> str:
        """订阅事件"""
        pass
```

---

## 使用示例

```python
from feature.base import BaseFeature

class MyFeature(BaseFeature):
    name = "my_feature"
    description = "我的自定义 Feature"
    dependencies = ["dialogue"]  # 依赖对话系统
    
    def on_enable(self):
        # 注册事件监听
        self.subscribe("player.action", self._on_player_action)
        print(f"{self.name} 已启用")
    
    def on_disable(self):
        print(f"{self.name} 已禁用")
    
    def _on_player_action(self, event):
        # 处理事件
        pass
```

---

## 生命周期

```
实例化 -> on_enable() -> [运行中] -> on_disable() -> 销毁
```

---

## 事件订阅

Feature 可以订阅 EventBus 事件：

```python
def on_enable(self):
    # 方式1: 使用基类方法
    self.subscribe("feature.ai.turn_end", self._on_turn_end)
    
    # 方式2: 直接使用 event_bus
    from foundation.event_bus import event_bus
    event_bus.subscribe("feature.ai.turn_end", self._on_turn_end)
```
