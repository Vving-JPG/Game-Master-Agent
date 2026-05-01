"""核心接口定义 — 定义层间契约

所有跨层通信的接口都在这里定义，确保依赖方向正确。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ILLMClient(ABC):
    """LLM 客户端接口（Foundation 层提供，Feature 层使用）"""

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> dict[str, Any]:
        """对话"""
        ...

    @abstractmethod
    async def stream(self, messages: list[dict], **kwargs):
        """流式对话"""
        ...


class IGameStateProvider(ABC):
    """游戏状态提供者接口（Core 层定义，Feature 层实现）"""

    @abstractmethod
    def get_state(self, world_id: int) -> dict[str, Any]:
        """获取游戏状态"""
        ...

    @abstractmethod
    def update_state(self, world_id: int, changes: dict[str, Any]) -> bool:
        """更新游戏状态"""
        ...


class IMemoryStore(ABC):
    """记忆存储接口（Core 层定义，Feature 层实现）"""

    @abstractmethod
    def store(self, world_id: int, category: str, key: str, content: str, **meta) -> str:
        """存储记忆，返回记忆 ID"""
        ...

    @abstractmethod
    def recall(self, world_id: int, category: str | None = None, limit: int = 10) -> list[dict]:
        """检索记忆"""
        ...

    @abstractmethod
    def forget(self, memory_id: str) -> bool:
        """删除记忆"""
        ...


class IToolExecutor(ABC):
    """工具执行器接口（Feature 层定义，LangGraph 节点使用）"""

    @abstractmethod
    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """执行工具"""
        ...

    @abstractmethod
    def get_tools_schema(self) -> list[dict]:
        """获取工具 schema（OpenAI function calling 格式）"""
        ...


class INotificationSink(ABC):
    """通知接收器接口（Presentation 层实现，Foundation 层调用）"""

    @abstractmethod
    def notify(self, event_type: str, data: dict[str, Any]) -> None:
        """接收通知"""
        ...
