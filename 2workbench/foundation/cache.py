"""通用 LRU 缓存 — 泛化版本

改进点（相比现有版本）:
1. 泛化为通用缓存（不限于 LLM）
2. 支持按前缀批量失效
3. 支持缓存统计
4. 线程安全（使用 threading.Lock）
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable

from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: float = 0  # 0 = 永不过期


class LRUCache:
    """LRU 缓存（线程安全）

    用法:
        cache = LRUCache(max_size=200, ttl_seconds=600)

        # 设置
        cache.set("key", "value")
        cache.set_with_ttl("temp_key", "temp_value", ttl_seconds=60)

        # 获取
        value = cache.get("key", default=None)

        # 按前缀失效
        cache.invalidate_prefix("pregen:")

        # 统计
        stats = cache.get_stats()
    """

    def __init__(self, max_size: int = 200, ttl_seconds: int = 600):
        self._max_size = max_size
        self._default_ttl = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

    def _make_key(self, key: str, **kwargs) -> str:
        """生成缓存键（支持附加参数）"""
        if not kwargs:
            return key
        raw = json.dumps(kwargs, sort_keys=True, default=str)
        hash_part = hashlib.md5(raw.encode()).hexdigest()[:8]
        return f"{key}:{hash_part}"

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return default

            # 检查 TTL
            if entry.ttl > 0 and (time.time() - entry.created_at) > entry.ttl:
                del self._cache[key]
                self._misses += 1
                return default

            # LRU: 移到末尾
            self._cache.move_to_end(key)
            entry.accessed_at = time.time()
            entry.access_count += 1
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """设置缓存值"""
        with self._lock:
            now = time.time()

            # 如果已存在，先删除（更新 TTL 和位置）
            if key in self._cache:
                del self._cache[key]

            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                accessed_at=now,
                ttl=ttl if ttl is not None else self._default_ttl,
            )

            # 淘汰最旧条目
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """按前缀批量失效

        Args:
            prefix: 键前缀

        Returns:
            失效的条目数
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
            if keys_to_delete:
                logger.debug(f"缓存失效: prefix={prefix}, count={len(keys_to_delete)}")
            return len(keys_to_delete)

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
        logger.debug("缓存已清空")

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{(self._hits / total * 100):.1f}%" if total > 0 else "N/A",
            }


# 全局实例
llm_cache = LRUCache(max_size=200, ttl_seconds=600)
