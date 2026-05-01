"""EventBus 测试"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundation.event_bus import EventBus, Event, Priority


def test_basic_subscribe_and_emit():
    """基本订阅和发布"""
    bus = EventBus()
    results = []

    def handler(event: Event):
        results.append(event.get("value"))

    bus.subscribe("test.event", handler)
    bus.emit(Event(type="test.event", data={"value": 42}))

    assert len(results) == 1
    assert results[0] == 42
    print("✅ test_basic_subscribe_and_emit")


def test_priority_order():
    """优先级排序"""
    bus = EventBus()
    order = []

    bus.subscribe("test.priority", lambda e: order.append("low"), priority=Priority.LOW)
    bus.subscribe("test.priority", lambda e: order.append("high"), priority=Priority.HIGH)
    bus.subscribe("test.priority", lambda e: order.append("normal"), priority=Priority.NORMAL)

    bus.emit(Event(type="test.priority"))

    assert order == ["high", "normal", "low"]
    print("✅ test_priority_order")


def test_filter():
    """过滤器"""
    bus = EventBus()
    results = []

    bus.subscribe(
        "test.filter",
        lambda e: results.append(e.get("value")),
        filter_fn=lambda e: e.get("value") > 10,
    )

    bus.emit(Event(type="test.filter", data={"value": 5}))
    bus.emit(Event(type="test.filter", data={"value": 15}))

    assert len(results) == 1
    assert results[0] == 15
    print("✅ test_filter")


def test_once():
    """一次性订阅"""
    bus = EventBus()
    count = [0]

    bus.subscribe("test.once", lambda e: count.__setitem__(0, count[0] + 1), once=True)

    bus.emit(Event(type="test.once"))
    bus.emit(Event(type="test.once"))
    bus.emit(Event(type="test.once"))

    assert count[0] == 1
    print("✅ test_once")


def test_wildcard():
    """通配符订阅"""
    bus = EventBus()
    results = []

    bus.subscribe("*", lambda e: results.append(e.type))

    bus.emit(Event(type="test.a"))
    bus.emit(Event(type="test.b"))

    assert results == ["test.a", "test.b"]
    print("✅ test_wildcard")


def test_decorator():
    """装饰器订阅"""
    bus = EventBus()
    results = []

    @bus.on("test.decorator")
    def handler(event: Event):
        results.append(event.get("msg"))

    bus.emit(Event(type="test.decorator", data={"msg": "hello"}))

    assert results == ["hello"]
    print("✅ test_decorator")


def test_unsubscribe():
    """取消订阅"""
    bus = EventBus()
    results = []

    def handler(event: Event):
        results.append(1)

    bus.subscribe("test.unsub", handler)
    bus.emit(Event(type="test.unsub"))
    bus.unsubscribe("test.unsub", handler)
    bus.emit(Event(type="test.unsub"))

    assert len(results) == 1
    print("✅ test_unsubscribe")


async def test_async_emit():
    """异步发布"""
    bus = EventBus()
    results = []

    async def async_handler(event: Event):
        await asyncio.sleep(0.01)
        results.append(event.get("value"))

    bus.subscribe("test.async", async_handler)
    await bus.emit_async(Event(type="test.async", data={"value": 99}))

    assert len(results) == 1
    assert results[0] == 99
    print("✅ test_async_emit")


if __name__ == "__main__":
    test_basic_subscribe_and_emit()
    test_priority_order()
    test_filter()
    test_once()
    test_wildcard()
    test_decorator()
    test_unsubscribe()
    asyncio.run(test_async_emit())
    print("\n🎉 EventBus 全部测试通过!")
