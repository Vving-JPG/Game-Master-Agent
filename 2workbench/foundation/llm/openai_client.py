"""OpenAI 兼容客户端 — 支持 DeepSeek / OpenAI / 其他兼容 API

所有使用 OpenAI API 格式的供应商（DeepSeek、OpenAI、各种国产模型）
都可以通过本客户端接入，只需配置不同的 base_url 和 api_key。
"""
from __future__ import annotations

import time
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from foundation.llm.base import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    StreamEvent,
)
from foundation.logger import get_logger

logger = get_logger(__name__)


class OpenAICompatibleClient(BaseLLMClient):
    """OpenAI 兼容客户端

    支持 DeepSeek、OpenAI、以及所有兼容 OpenAI API 的供应商。

    用法:
        client = OpenAICompatibleClient(
            provider_name="deepseek",
            api_key="sk-xxx",
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
        )
        response = await client.chat_async(messages)
    """

    def __init__(
        self,
        provider_name: str = "",
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        # 如果参数为空，尝试从配置读取
        if not all([provider_name, api_key, base_url, model]):
            try:
                from foundation.config import settings
                provider_name = provider_name or settings.default_provider or "deepseek"
                api_key = api_key or getattr(settings, f"{provider_name}_api_key", "")
                base_url = base_url or getattr(settings, f"{provider_name}_base_url", "")
                model = model or settings.default_model or "deepseek-chat"
            except Exception:
                pass

        self._provider_name = provider_name or "unknown"
        self._model = model or "unknown"
        self._default_max_tokens = max_tokens
        self._default_temperature = temperature

        self._client = AsyncOpenAI(
            api_key=api_key or "dummy-key",
            base_url=base_url or "https://api.openai.com",
            timeout=timeout,
        )

        self._retry_decorator = retry(
            retry=retry_if_exception_type(Exception),
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            before_sleep=lambda retry_state: logger.warning(
                f"LLM 重试 ({retry_state.attempt_number}/{max_retries}): "
                f"{retry_state.outcome.exception()}"
            ),
        )

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model

    def _to_openai_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """转换为 OpenAI 格式"""
        result = []
        for msg in messages:
            m: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                m["name"] = msg.name
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            result.append(m)
        return result

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def chat_async(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """异步对话"""
        start_time = time.time()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._to_openai_messages(messages),
            "temperature": temperature if temperature is not None else self._default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self._default_max_tokens,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = await self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            # Token 统计
            if response.usage:
                self._prompt_tokens += response.usage.prompt_tokens
                self._completion_tokens += response.usage.completion_tokens

            latency_ms = int((time.time() - start_time) * 1000)

            # 提取 reasoning_content（DeepSeek Reasoner 特有）
            reasoning = ""
            if hasattr(message, "reasoning_content") and message.reasoning_content:
                reasoning = message.reasoning_content

            # 提取 tool_calls
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })

            return LLMResponse(
                content=message.content or "",
                reasoning_content=reasoning,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason or "",
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                model=response.model,
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"LLM 调用失败 ({self._provider_name}/{self._model}): {e}")
            raise

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """流式对话"""
        start_time = time.time()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._to_openai_messages(messages),
            "temperature": temperature if temperature is not None else self._default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self._default_max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = tools

        try:
            stream = await self._client.chat.completions.create(**kwargs)

            async for chunk in stream:
                if not chunk.choices:
                    # usage 信息
                    if chunk.usage:
                        self._prompt_tokens += chunk.usage.prompt_tokens
                        self._completion_tokens += chunk.usage.completion_tokens
                        yield StreamEvent(
                            type="complete",
                            prompt_tokens=chunk.usage.prompt_tokens,
                            completion_tokens=chunk.usage.completion_tokens,
                            total_tokens=chunk.usage.total_tokens,
                            latency_ms=int((time.time() - start_time) * 1000),
                        )
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # reasoning_content（DeepSeek Reasoner）
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    yield StreamEvent(type="reasoning", content=delta.reasoning_content)

                # 正式内容
                if delta.content:
                    yield StreamEvent(type="token", content=delta.content)

                # tool_calls 增量
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        yield StreamEvent(
                            type="tool_call",
                            tool_calls=[{
                                "index": tc.index,
                                "id": tc.id or "",
                                "type": "function",
                                "function": {
                                    "name": tc.function.name if tc.function else "",
                                    "arguments": tc.function.arguments if tc.function else "",
                                },
                            }],
                        )

        except Exception as e:
            yield StreamEvent(
                type="error",
                error=str(e),
                latency_ms=int((time.time() - start_time) * 1000),
            )
