"""
测试工具 — 测试提示词效果
"""
from foundation.logger import get_logger
from .base import AITool, ToolParameter, ToolResult

logger = get_logger(__name__)


class TestPromptTool(AITool):
    """测试提示词效果"""

    @property
    def name(self) -> str:
        return "test_prompt"

    @property
    def description(self) -> str:
        return "测试指定提示词的 LLM 生成效果。使用当前配置的模型发送测试消息，返回 LLM 的响应。用于验证提示词质量。"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter("prompt_name", "string", "要测试的提示词名称"),
            ToolParameter("test_message", "string", "测试消息（模拟用户输入）"),
            ToolParameter("max_tokens", "integer", "最大生成 token 数", required=False, default=256),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        from feature.project import project_manager
        from foundation.llm.model_router import model_router
        from foundation.llm.base import LLMMessage

        prompt_name = kwargs["prompt_name"]
        test_message = kwargs["test_message"]
        max_tokens = kwargs.get("max_tokens", 256)

        if not project_manager.is_open:
            return ToolResult(success=False, message="没有打开的项目")

        prompt_content = project_manager.load_prompt(prompt_name)
        if not prompt_content:
            return ToolResult(success=False, message=f"提示词 '{prompt_name}' 不存在或为空")

        try:
            client, config = model_router.route(content=test_message)
            messages = [
                LLMMessage(role="system", content=prompt_content),
                LLMMessage(role="user", content=test_message),
            ]

            response = await client.chat_async(
                messages=messages,
                temperature=config.get("temperature", 0.7),
                max_tokens=max_tokens,
            )

            if hasattr(response, "content"):
                result_text = response.content
            elif isinstance(response, dict):
                result_text = response.get("content", str(response))
            else:
                result_text = str(response)

            return ToolResult(
                success=True,
                message=f"提示词 '{prompt_name}' 测试完成",
                data={
                    "response": result_text,
                    "model": config.get("model", "unknown"),
                    "tokens_used": max_tokens,
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"测试失败: {e}",
            )
