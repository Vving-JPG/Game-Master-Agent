"""LLM 客户端抽象基类

所有 LLM 供应商必须实现此接口。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator


@dataclass
class LLMMessage:
    """LLM 消息"""
    role: str  # system / user / assistant / tool
    content: str = ""
    name: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str = ""
    reasoning_content: str = ""  # 思考过程（DeepSeek Reasoner）
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    latency_ms: int = 0


@dataclass
class StreamEvent:
    """流式事件"""
    type: str  # reasoning / token / tool_call / complete / error
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error: str = ""


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类

    所有供应商客户端必须实现:
    - chat(): 同步对话
    - chat_async(): 异步对话
    - stream(): 流式对话
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """供应商名称"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """当前模型名称"""
        ...

    @abstractmethod
    async def chat_async(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """异步对话

        Args:
            messages: 消息列表
            temperature: 温度（覆盖默认值）
            max_tokens: 最大 token 数
            tools: 工具定义列表（OpenAI function calling 格式）

        Returns:
            LLMResponse
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """流式对话

        Args:
            messages: 消息列表
            temperature: 温度
            max_tokens: 最大 token 数
            tools: 工具定义列表

        Yields:
            StreamEvent（reasoning/token/tool_call/complete/error）
        """
        ...

    def get_usage_stats(self) -> dict[str, int]:
        """获取 Token 使用统计"""
        return {
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens,
            "total_tokens": self._prompt_tokens + self._completion_tokens,
        }

    def reset_usage_stats(self) -> None:
        """重置 Token 统计"""
        self._prompt_tokens = 0
        self._completion_tokens = 0

    # 子类需要初始化这些
    _prompt_tokens: int = 0
    _completion_tokens: int = 0
