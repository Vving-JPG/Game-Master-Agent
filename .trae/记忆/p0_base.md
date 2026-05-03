# P0-09: Base 基类与接口

> 模块: `foundation.base`
> 文件: `2workbench/foundation/base/singleton.py`, `interfaces.py`

---

## 单例基类

```python
from foundation.base import Singleton

class MyService(Singleton):
    def __init__(self):
        # 只执行一次
        self.initialized = True

s1 = MyService()
s2 = MyService()
assert s1 is s2  # True
```

---

## 核心接口

### ILLMClient

```python
class ILLMClient(ABC):
    @abstractmethod
    async def chat_async(self, messages: list[LLMMessage]) -> LLMResponse
    
    @abstractmethod
    async def stream(self, messages: list[LLMMessage]) -> AsyncGenerator[StreamEvent, None]
```

### IGameStateProvider

```python
class IGameStateProvider(ABC):
    @abstractmethod
    def get_state(self, world_id: str) -> dict
    
    @abstractmethod
    def update_state(self, world_id: str, changes: dict)
```

### IMemoryStore

```python
class IMemoryStore(ABC):
    @abstractmethod
    def store(self, world_id: str, category: str, content: str, **kwargs)
    
    @abstractmethod
    def recall(self, world_id: str, query: str, limit: int = 10) -> list
```

### IToolExecutor

```python
class IToolExecutor(ABC):
    @abstractmethod
    def execute(self, tool_name: str, params: dict) -> dict
    
    @abstractmethod
    def list_tools(self) -> list[dict]
```

### INotificationSink

```python
class INotificationSink(ABC):
    @abstractmethod
    def notify(self, level: str, message: str, **kwargs)
```

---

## 使用场景

| 接口 | 用途 |
|------|------|
| ILLMClient | 实现自定义 LLM 客户端 |
| IGameStateProvider | 接入外部状态系统 |
| IMemoryStore | 接入向量数据库 |
| IToolExecutor | 扩展工具集 |
| INotificationSink | 自定义通知方式 |
