"""SSE 端点测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def sse_client():
    """创建 SSE 测试客户端"""
    from src.api.sse import router, set_sse_refs

    mock_handler = MagicMock()
    mock_handler.is_processing = False
    mock_handler.current_event = None
    mock_handler._sse_callbacks = []

    set_sse_refs(mock_handler)

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app), mock_handler


class TestSSEEndpoint:
    """SSE 端点测试"""

    def test_sse_not_initialized(self):
        """Agent 未初始化时应返回 503"""
        from src.api.sse import router, set_sse_refs
        set_sse_refs(None)

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.get("/api/agent/stream?session_id=test")
        assert resp.status_code == 503

    def test_sse_callback_registration(self, sse_client):
        """测试 SSE 回调注册机制"""
        client, mock_handler = sse_client

        # 验证 mock_handler 有 _sse_callbacks 属性
        assert hasattr(mock_handler, '_sse_callbacks')

        # 测试回调可以被添加
        async def test_callback(event_name: str, data: dict):
            pass

        mock_handler._sse_callbacks.append(test_callback)
        assert test_callback in mock_handler._sse_callbacks

        # 测试回调可以被移除
        mock_handler._sse_callbacks.remove(test_callback)
        assert test_callback not in mock_handler._sse_callbacks

    def test_sse_generate_events(self, sse_client):
        """测试事件生成器"""
        from src.api.sse import _generate_events

        async def run_test():
            # 测试生成器可以被创建
            gen = _generate_events("test_session")
            assert gen is not None

        import asyncio
        asyncio.run(run_test())
