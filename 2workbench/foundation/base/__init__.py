"""基类与接口"""
from foundation.base.singleton import Singleton
from foundation.base.interfaces import (
    ILLMClient,
    IGameStateProvider,
    IMemoryStore,
    IToolExecutor,
    INotificationSink,
)

__all__ = [
    "Singleton",
    "ILLMClient",
    "IGameStateProvider",
    "IMemoryStore",
    "IToolExecutor",
    "INotificationSink",
]
