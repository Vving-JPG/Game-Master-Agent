"""连接管理器测试"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.api.connection_manager import ConnectionManager


def test_connect_and_disconnect():
    """连接和断开"""
    mgr = ConnectionManager()
    ws = MagicMock()
    mgr.active_connections[1] = set()
    mgr.active_connections[1].add(ws)
    assert mgr.get_connection_count(1) == 1
    mgr.disconnect(1, ws)
    assert mgr.get_connection_count(1) == 0


def test_empty_world():
    """空世界连接数"""
    mgr = ConnectionManager()
    assert mgr.get_connection_count(999) == 0


@pytest.mark.asyncio
async def test_broadcast():
    """广播消息"""
    mgr = ConnectionManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    mgr.active_connections[1] = {ws1, ws2}
    await mgr.broadcast(1, {"type": "test", "content": "hello"})
    assert ws1.send_json.call_count == 1
    assert ws2.send_json.call_count == 1
