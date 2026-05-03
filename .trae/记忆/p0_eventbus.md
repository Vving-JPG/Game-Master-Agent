# P0-01: EventBus 事件总线

> 模块: `foundation.event_bus`
> 文件: `2workbench/foundation/event_bus.py`
> 全局单例: `event_bus`

---

## 核心类

### Event 数据类

```python
@dataclass
class Event:
    type: str                    # 事件类型
    data: dict[str, Any]        # 事件数据
    source: str = ""            # 事件来源
    timestamp: float = 0.0      # 时间戳
    priority: int = 0           # 优先级

    def get(self, key: str, default=None):
        """安全获取 data 字段"""
```

### EventBus 类

```python
class EventBus:
    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        priority: Priority = Priority.NORMAL,
        filter_fn: Callable | None = None,
        once: bool = False
    ) -> str:  # 返回订阅ID

    def unsubscribe(self, subscription_id: str) -> bool
    def emit(self, event: Event | str, data: dict | None = None)
    def emit_async(self, event: Event) -> asyncio.Task
    def on(self, event_type: str, **kwargs):  # 装饰器
```

---

## 事件命名规范

格式: `layer.module.action`

```
# Foundation 层
foundation.config.changed
foundation.db.initialized
foundation.llm.response
foundation.llm.error
foundation.llm.stream_token
foundation.save.created
foundation.save.loaded

# Core 层
core.state.changed
core.state.snapshot

# Feature 层
feature.battle.started
feature.battle.ended
feature.quest.updated

# Presentation 层
presentation.ui.refresh
presentation.ui.notification
```

---

## 使用示例

```python
from foundation.event_bus import event_bus, Event

# 订阅事件
event_bus.subscribe("foundation.llm.response", on_llm_response)

# 装饰器方式
@event_bus.on("core.state.changed")
def handle_state_change(event: Event):
    world_id = event.get("world_id")

# 发布事件
event_bus.emit(Event(
    type="foundation.llm.response",
    data={"content": "你好", "tokens": 100},
    source="feature.dialogue"
))

# 简化发布
event_bus.emit("foundation.llm.response", {"content": "你好"})
```

---

## 优先级

```python
class Priority(IntEnum):
    HIGHEST = 100   # 最先执行
    HIGH = 75
    NORMAL = 50     # 默认
    LOW = 25
    LOWEST = 0      # 最后执行
```

---

## 特性

- ✅ 支持 sync/async 两种事件处理
- ✅ 支持优先级控制
- ✅ 支持过滤器 `filter_fn`
- ✅ 支持一次性订阅 `once=True`
- ✅ 支持通配符 `*` 订阅所有事件
