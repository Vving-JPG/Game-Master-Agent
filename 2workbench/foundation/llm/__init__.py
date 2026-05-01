"""LLM 客户端子包

提供多模型 LLM 客户端抽象和具体实现。
"""
from foundation.llm.base import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    StreamEvent,
)
from foundation.llm.openai_client import OpenAICompatibleClient
from foundation.llm.model_router import ModelRouter, model_router

__all__ = [
    "BaseLLMClient",
    "LLMMessage",
    "LLMResponse",
    "StreamEvent",
    "OpenAICompatibleClient",
    "ModelRouter",
    "model_router",
]
