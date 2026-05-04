"""Foundation 层集成测试"""
import asyncio
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_event_bus_cross_module():
    """测试 EventBus 跨模块通信"""
    from foundation.event_bus import event_bus, Event

    results = []

    # Config 模块发出配置变更事件
    event_bus.subscribe("foundation.config.changed", lambda e: results.append(("config", e.get("key"))))

    # Database 模块发出初始化完成事件
    event_bus.subscribe("foundation.db.initialized", lambda e: results.append(("db", e.get("version"))))

    event_bus.emit(Event(type="foundation.config.changed", data={"key": "log_level", "value": "DEBUG"}))
    event_bus.emit(Event(type="foundation.db.initialized", data={"version": 1}))

    assert len(results) == 2
    assert results[0] == ("config", "log_level")
    assert results[1] == ("db", 1)
    event_bus.clear()
    print("✅ test_event_bus_cross_module")


def test_config_and_logger():
    """测试 Config 和 Logger 集成"""
    from foundation.config import Settings
    from foundation.logger import get_logger, setup_logging

    setup_logging("DEBUG")
    logger = get_logger("test.integration")
    logger.info("Config + Logger 集成测试", extra={"test": True})
    print("✅ test_config_and_logger")


def test_database_and_save_manager():
    """测试 Database 和 SaveManager 集成"""
    from foundation.database import get_connection, get_db
    from foundation.save_manager import SaveManager

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试数据库
        db_path = os.path.join(tmpdir, "test.db")
        conn = get_connection(db_path)
        conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO test_data (value) VALUES ('hello')")
        conn.commit()
        conn.close()

        # 创建存档
        save_dir = os.path.join(tmpdir, "saves")
        sm = SaveManager(save_dir=save_dir)
        save_info = sm.save_game(world_id=1, slot_name="test", description="测试存档", db_path=db_path)

        assert save_info.world_id == 1
        assert save_info.slot_name == "test"

        # 列出存档
        saves = sm.list_saves(world_id=1)
        assert len(saves) == 1

        # 删除存档
        sm.delete_save(save_info.save_id)
        saves = sm.list_saves(world_id=1)
        assert len(saves) == 0

    print("✅ test_database_and_save_manager")


def test_cache_with_resource_manager():
    """测试 Cache 和 ResourceManager 集成"""
    from foundation.cache import LRUCache
    from foundation.resource_manager import ResourceManager

    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ResourceManager(tmpdir)
        cache = LRUCache(max_size=10, ttl_seconds=60)

        # 写入文件并缓存
        rm.write_file("test.txt", "cached content")
        content = rm.read_file("test.txt")
        cache.set("file:test.txt", content)

        # 从缓存读取
        cached = cache.get("file:test.txt")
        assert cached == "cached content"

        # 按前缀失效
        cache.invalidate_prefix("file:")
        assert cache.get("file:test.txt") is None

    print("✅ test_cache_with_resource_manager")


def test_llm_client_creation():
    """测试 LLM 客户端创建（不实际调用 API）"""
    from foundation.llm.base import LLMMessage
    from foundation.llm.openai_client import OpenAICompatibleClient
    from foundation.llm.model_router import ModelRouter

    # 创建客户端
    client = OpenAICompatibleClient(
        provider_name="test",
        api_key="test-key",
        base_url="https://api.test.com/v1",
        model="test-model",
    )
    assert client.provider_name == "test"

    # 创建路由器
    router = ModelRouter()
    rule = router._match_rules("战斗开始", event_type="combat_start", turn_length=5)
    assert rule is not None

    print("✅ test_llm_client_creation")


def test_interface_contracts():
    """测试接口定义"""
    from foundation.base.interfaces import (
        IGameStateProvider, IMemoryStore, IToolExecutor, INotificationSink
    )

    # 验证接口可以被继承（ILLMClient 已删除，使用 INotificationSink 测试）
    class MockNotificationSink(INotificationSink):
        def __init__(self):
            self.notifications = []

        def notify(self, event_type: str, data: dict) -> None:
            self.notifications.append((event_type, data))

    mock = MockNotificationSink()
    mock.notify("test", {"message": "hello"})
    assert len(mock.notifications) == 1
    assert isinstance(mock, INotificationSink)

    print("✅ test_interface_contracts")


if __name__ == "__main__":
    test_event_bus_cross_module()
    test_config_and_logger()
    test_database_and_save_manager()
    test_cache_with_resource_manager()
    test_llm_client_creation()
    test_interface_contracts()
    print("\n🎉 Foundation 层集成测试全部通过!")
