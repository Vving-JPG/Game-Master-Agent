"""缓存系统测试"""
from src.services.cache import LRUCache


def test_basic_cache():
    """基本缓存读写"""
    cache = LRUCache(max_size=10)
    cache.set("hello", "world")
    assert cache.get("hello") == "world"
    assert cache.get("nonexistent") is None


def test_lru_eviction():
    """LRU 淘汰"""
    cache = LRUCache(max_size=3)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.set("c", "3")
    cache.set("d", "4")  # 应该淘汰 "a"
    assert cache.get("a") is None
    assert cache.get("d") == "4"


def test_ttl():
    """TTL 过期"""
    cache = LRUCache(max_size=10, ttl_seconds=0)
    cache.set("x", "y")
    import time
    time.sleep(0.1)
    assert cache.get("x") is None


def test_invalidate():
    """清除缓存"""
    cache = LRUCache()
    cache.set("a", "1")
    cache.set("b", "2")
    cache.invalidate()
    assert cache.size == 0


def test_kwargs_key():
    """不同参数不同缓存"""
    cache = LRUCache()
    cache.set("prompt", "result1", model="gpt-3")
    cache.set("prompt", "result2", model="gpt-4")
    assert cache.get("prompt", model="gpt-3") == "result1"
    assert cache.get("prompt", model="gpt-4") == "result2"
