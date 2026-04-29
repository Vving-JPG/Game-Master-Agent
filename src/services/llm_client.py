"""LLM客户端封装 - 统一管理DeepSeek API调用"""
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """DeepSeek API 客户端封装

    功能:
    - 普通对话
    - 带工具调用的对话
    - 流式输出
    - 自动重试（3次，指数退避）
    - Token 用量统计
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self.model = settings.deepseek_model
        # Token 统计
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _call_api(self, messages: list[dict], **kwargs):
        """底层API调用（用于重试包装）"""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )

    def chat(self, messages: list[dict], model: str | None = None) -> str:
        """普通对话

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            model: 可选，指定模型名称

        Returns:
            模型回复文本
        """
        # 保存原始模型
        original_model = self.model
        if model:
            self.model = model

        try:
            logger.info(f"调用LLM，消息数: {len(messages)}")
            response = self._call_api(messages)
            # 累计Token
            usage = response.usage
            self.total_prompt_tokens += usage.prompt_tokens
            self.total_completion_tokens += usage.completion_tokens
            logger.info(
                f"Token使用 - 本次: prompt={usage.prompt_tokens}, "
                f"completion={usage.completion_tokens} | "
                f"累计: prompt={self.total_prompt_tokens}, "
                f"completion={self.total_completion_tokens}"
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"API调用失败，启用降级模式: {e}")
            return self._fallback_response(messages)
        finally:
            # 恢复原始模型
            self.model = original_model

    def _fallback_response(self, messages) -> str:
        """降级回复"""
        import random
        fallback_responses = [
            "（GM正在沉思中……请稍后再试。）",
            "（一阵迷雾笼罩了你的视野，你暂时无法感知周围的环境。）",
            "（时间仿佛静止了，等待命运的齿轮重新转动……）",
        ]
        return random.choice(fallback_responses)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def chat_with_tools(self, messages: list[dict], tools: list[dict]):
        """带工具调用的对话

        Args:
            messages: 消息列表
            tools: 工具定义列表

        Returns:
            完整的API响应对象（包含tool_calls）
        """
        logger.info(f"调用LLM(带工具)，消息数: {len(messages)}, 工具数: {len(tools)}")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
        )
        usage = response.usage
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        return response

    def chat_stream(self, messages: list[dict]):
        """流式对话

        Args:
            messages: 消息列表

        Yields:
            每个文本片段
        """
        logger.info(f"调用LLM(流式)，消息数: {len(messages)}")
        for chunk in self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        ):
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_usage_stats(self) -> dict:
        """获取Token使用统计"""
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
        }
