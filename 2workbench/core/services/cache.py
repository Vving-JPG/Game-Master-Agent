"""响应缓存 - LRU 缓存减少重复 API 调用"""
import hashlib
import json
import time
from collections import OrderedDict
from .core.utils.logger import get_logger

logger = get_logger(__name__)


class LRUCache:
    """线程安全的 LRU 缓存"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple] = OrderedDict()

    def _make_key(self, prompt: str, **kwargs) -> str:
        """生成缓存键"""
        raw = prompt + json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, prompt: str, **kwargs) -> str | None:
        """获取缓存"""
        key = self._make_key(prompt, **kwargs)
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                self._cache.move_to_end(key)
                logger.debug(f"缓存命中: {key[:8]}...")
                return value
            else:
                del self._cache[key]
        return None

    def set(self, prompt: str, response: str, **kwargs):
        """设置缓存"""
        key = self._make_key(prompt, **kwargs)
        self._cache[key] = (response, time.time())
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def invalidate(self, prompt_prefix: str = ""):
        """清除缓存（可选按前缀）"""
        if not prompt_prefix:
            self._cache.clear()
            return
        keys_to_remove = [k for k in self._cache if prompt_prefix in str(self._cache[k])]
        for k in keys_to_remove:
            del self._cache[k]

    @property
    def size(self) -> int:
        return len(self._cache)


# 全局缓存实例
llm_cache = LRUCache(max_size=200, ttl_seconds=600)
