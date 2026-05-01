"""adapters/base.py 单元测试"""
import pytest
from src.adapters.base import EngineAdapter, EngineEvent, CommandResult, ConnectionStatus


class TestEngineEvent:
    def test_create(self):
        event = EngineEvent(event_id="evt_001", timestamp="t", type="player_action",
            data={"raw_text": "hello"}, context_hints=["npcs/铁匠"], game_state={"location": "town"})
        assert event.event_id == "evt_001"
        assert len(event.context_hints) == 1

    def test_defaults(self):
        event = EngineEvent(event_id="e1", timestamp="t", type="test")
        assert event.data == {}
        assert event.context_hints == []


class TestCommandResult:
    def test_success(self):
        r = CommandResult(intent="no_op", status="success")
        assert r.new_value is None

    def test_rejected(self):
        r = CommandResult(intent="fly", status="rejected", reason="Unknown", suggestion="Check skills")
        assert "Unknown" in r.reason


class TestEngineAdapter:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            EngineAdapter()

    def test_concrete(self):
        class MockAdapter(EngineAdapter):
            @property
            def name(self): return "mock"
            @property
            def connection_status(self): return ConnectionStatus.DISCONNECTED
            async def connect(self, **kw): pass
            async def disconnect(self): pass
            async def send_commands(self, cmds): return []
            async def subscribe_events(self, types, cb): pass
            async def query_state(self, q): return {}
        assert MockAdapter().name == "mock"
