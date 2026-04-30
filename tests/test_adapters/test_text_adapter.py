"""adapters/text_adapter.py 单元测试"""
import pytest
from unittest.mock import MagicMock
from src.adapters.text_adapter import TextAdapter
from src.adapters.base import ConnectionStatus


@pytest.fixture
def mock_services():
    s = {k: MagicMock() for k in ("world", "player", "npc", "item", "quest")}
    s["world"].list_worlds.return_value = [{"id": "w1"}]
    s["player"].list_players.return_value = [{"id": "p1"}]
    s["player"].get_player.return_value = {"id": "p1", "hp": 100, "level": 1, "location": "town", "version": 1}
    s["npc"].get_npc.return_value = {"id": "npc_1", "name": "铁匠", "relationship": 30, "version": 3}
    s["npc"].list_npcs.return_value = [{"id": "npc_1", "name": "铁匠"}, {"id": "npc_2", "name": "药剂师"}]
    return s


@pytest.fixture
def adapter(mock_services):
    return TextAdapter(mock_services["world"], mock_services["player"],
        mock_services["npc"], mock_services["item"], mock_services["quest"])


class TestTextAdapter:
    def test_name(self, adapter):
        assert adapter.name == "text"

    @pytest.mark.asyncio
    async def test_connect(self, adapter):
        await adapter.connect()
        assert adapter.connection_status == ConnectionStatus.CONNECTED
        assert adapter._world_id == "w1"

    @pytest.mark.asyncio
    async def test_connect_no_world(self, mock_services):
        mock_services["world"].list_worlds.return_value = []
        a = TextAdapter(mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"])
        with pytest.raises(ConnectionError, match="没有可用的游戏世界"):
            await a.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        await adapter.connect()
        await adapter.disconnect()
        assert adapter.connection_status == ConnectionStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_no_op(self, adapter):
        await adapter.connect()
        results = await adapter.send_commands([{"intent": "no_op", "params": {}}])
        assert results[0].status == "success"

    @pytest.mark.asyncio
    async def test_unknown_intent(self, adapter):
        await adapter.connect()
        results = await adapter.send_commands([{"intent": "fly", "params": {}}])
        assert results[0].status == "rejected"

    @pytest.mark.asyncio
    async def test_update_relationship(self, adapter):
        await adapter.connect()
        results = await adapter.send_commands([
            {"intent": "update_npc_relationship", "params": {"npc_id": "npc_1", "change": 5}}])
        assert results[0].status == "success"
        assert results[0].new_value == 35
        assert results[0].state_changes is not None

    @pytest.mark.asyncio
    async def test_npc_not_found(self, adapter):
        await adapter.connect()
        adapter._npc.get_npc.return_value = None
        results = await adapter.send_commands([
            {"intent": "update_npc_relationship", "params": {"npc_id": "missing", "change": 5}}])
        assert results[0].status == "rejected"

    @pytest.mark.asyncio
    async def test_query_ping(self, adapter):
        assert (await adapter.query_state({"type": "ping"}))["pong"] is True

    @pytest.mark.asyncio
    async def test_query_player(self, adapter):
        await adapter.connect()
        assert (await adapter.query_state({"type": "player_stats"}))["hp"] == 100

    @pytest.mark.asyncio
    async def test_handle_input(self, adapter):
        await adapter.connect()
        event = await adapter.handle_player_input("和铁匠聊聊")
        assert event.type == "player_action"
        assert "npcs/铁匠" in event.context_hints

    @pytest.mark.asyncio
    async def test_handle_input_combat(self, adapter):
        await adapter.connect()
        event = await adapter.handle_player_input("攻击哥布林")
        assert event.type == "combat_start"
