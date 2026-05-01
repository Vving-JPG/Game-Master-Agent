"""
引擎适配器抽象接口。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable, Optional
import time


class ConnectionStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class EngineEvent:
    """标准引擎事件（引擎 → Agent）"""
    event_id: str
    timestamp: str
    type: str
    data: dict = field(default_factory=dict)
    context_hints: list[str] = field(default_factory=list)
    game_state: dict = field(default_factory=dict)


@dataclass
class CommandResult:
    """单条指令执行结果"""
    intent: str
    status: str  # success, rejected, partial, error
    new_value: Optional[any] = None
    state_changes: Optional[dict] = None
    reason: Optional[str] = None
    suggestion: Optional[str] = None


EventCallback = Callable[["EngineEvent"], Awaitable[None]]


class EngineAdapter(ABC):
    """引擎适配器抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def connection_status(self) -> ConnectionStatus: ...

    @abstractmethod
    async def connect(self, **kwargs) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def send_commands(self, commands: list[dict]) -> list[CommandResult]: ...

    @abstractmethod
    async def subscribe_events(self, event_types: list[str], callback: EventCallback) -> None: ...

    @abstractmethod
    async def query_state(self, query: dict) -> dict: ...

    async def health_check(self) -> dict:
        start = time.time()
        try:
            await self.query_state({"type": "ping"})
            latency = int((time.time() - start) * 1000)
            return {"status": "ok", "adapter": self.name, "latency_ms": latency}
        except Exception as e:
            return {"status": "error", "adapter": self.name, "error": str(e)}
