"""单例基类"""
from __future__ import annotations

import threading
from typing import TypeVar

T = TypeVar("T")


class Singleton:
    """线程安全的单例基类

    用法:
        class MyService(Singleton):
            def __init__(self):
                self.data = {}

        instance = MyService()
    """
    _instances: dict[type, object] = {}
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                # 双重检查
                if cls not in cls._instances:
                    instance = super().__new__(cls)
                    cls._instances[cls] = instance
        return cls._instances[cls]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 子类需要自己的实例
        if cls not in Singleton._instances:
            pass  # 延迟到 __new__ 中创建
