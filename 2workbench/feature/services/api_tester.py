"""API 测试服务 — 功能层

负责测试 LLM API 连接，与 UI 解耦。
"""
from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from foundation.llm import OpenAICompatibleClient, LLMMessage
from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TestResult:
    """API 测试结果"""
    success: bool
    message: str
    model_name: str
    response_content: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = ""


class ApiTestWorker(threading.Thread):
    """在后台线程中测试 API 连接，支持安全取消
    
    使用标准库 threading.Thread 而非 QThread，保持 Feature 层与 UI 框架解耦。
    回调函数由 Presentation 层提供，用于将结果传回 UI。
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "",
        on_result: Optional[Callable[[TestResult], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(daemon=True)
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._on_result = on_result
        self._on_error = on_error
        self._stop_event = threading.Event()

    def cancel(self):
        """通知线程停止"""
        self._stop_event.set()

    def run(self):
        try:
            if self._stop_event.is_set():
                result = TestResult(
                    success=False, message="测试已取消", model_name=self.model
                )
                if self._on_result:
                    self._on_result(result)
                return

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            client = OpenAICompatibleClient(
                provider_name="test",
                api_key=self.api_key,
                base_url=self.base_url if self.base_url else None,
                model=self.model,
                max_retries=1,
                timeout=15,
            )

            async def do_test():
                for _ in range(100):  # 最长约20秒
                    if self._stop_event.is_set():
                        return None
                    await asyncio.sleep(0.2)
                response = await client.chat_async(
                    messages=[LLMMessage(role="user", content="Hello, reply with 'OK'")],
                    temperature=0.1,
                    max_tokens=50,
                )
                return response

            response = loop.run_until_complete(do_test())
            loop.close()

            if self._stop_event.is_set():
                result = TestResult(
                    success=False, message="测试已取消", model_name=self.model
                )
                if self._on_result:
                    self._on_result(result)
                return

            if not response:
                result = TestResult(
                    success=False, message="API 无响应", model_name=self.model
                )
                if self._on_result:
                    self._on_result(result)
                return

            if response.completion_tokens > 0 or response.prompt_tokens > 0:
                preview = response.content[:100] if response.content else "(空内容)"
                msg = (f"响应: {preview}\n"
                       f"finish_reason: {response.finish_reason}, "
                       f"tokens: {response.prompt_tokens}/{response.completion_tokens}")
                result = TestResult(
                    success=True,
                    message=msg,
                    model_name=self.model,
                    response_content=response.content,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    finish_reason=response.finish_reason,
                )
                if self._on_result:
                    self._on_result(result)
            else:
                result = TestResult(
                    success=False,
                    message=f"API 异常 (finish_reason: {response.finish_reason})",
                    model_name=self.model,
                )
                if self._on_result:
                    self._on_result(result)

        except Exception as e:
            if self._stop_event.is_set():
                result = TestResult(
                    success=False, message="测试已取消", model_name=self.model
                )
                if self._on_result:
                    self._on_result(result)
            else:
                import traceback
                detail = f"{str(e)[:150]}\n{traceback.format_exc()[-200:]}"
                if self._on_error:
                    self._on_error(detail)
                else:
                    result = TestResult(
                        success=False, message=detail, model_name=self.model
                    )
                    if self._on_result:
                        self._on_result(result)
        finally:
            self._stop_event.clear()


class ApiTester:
    """API 测试服务
    
    提供同步和异步方式的 API 测试功能。
    """

    def __init__(self):
        self._current_worker: Optional[ApiTestWorker] = None

    def test_async(
        self,
        model: str,
        api_key: str,
        base_url: str = "",
        callback: Optional[Callable[[TestResult], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
    ) -> ApiTestWorker:
        """异步测试 API（返回 Worker，可取消）
        
        Args:
            model: 模型名称
            api_key: API 密钥
            base_url: 自定义 API 地址
            callback: 测试完成回调函数
            error_callback: 错误回调函数
            
        Returns:
            ApiTestWorker: 工作线程，可用于取消测试
        """
        # 取消之前的测试
        if self._current_worker and self._current_worker.is_alive():
            self._current_worker.cancel()
            self._current_worker.join(timeout=2)

        self._current_worker = ApiTestWorker(
            model, api_key, base_url,
            on_result=callback,
            on_error=error_callback,
        )
        self._current_worker.start()
        return self._current_worker

    def cancel_current_test(self) -> bool:
        """取消当前测试
        
        Returns:
            bool: 是否成功取消
        """
        if self._current_worker and self._current_worker.is_alive():
            self._current_worker.cancel()
            return True
        return False

    def is_testing(self) -> bool:
        """是否正在测试中"""
        return self._current_worker is not None and self._current_worker.is_alive()
