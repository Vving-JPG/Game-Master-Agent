# P0-07: Cache LRU 缓存

> 模块: `foundation.cache`
> 文件: `2workbench/foundation/cache.py`
> 全局单例: `llm_cache`

---

## 核心类

```python
class LRUCache:
    def __init__(self, max_size: int = 200, ttl_seconds: int = 600)
    
    def get(self, key: str) -> Any | None
    def set(self, key: str, value: Any)
    def delete(self, key: str) -> bool
    def invalidate_prefix(self, prefix: str) -> int  # 返回失效数量
    def clear(self)
    def get_stats(self) -> dict  # 命中率统计
```

---

## 使用示例

```python
from foundation.cache import LRUCache

cache = LRUCache(max_size=200, ttl_seconds=600)

# 设置缓存
cache.set("pregen:world:1", world_data)

# 获取缓存
value = cache.get("pregen:world:1")
if value is None:
    # 缓存未命中，重新生成
    value = generate_world_data()
    cache.set("pregen:world:1", value)

# 按前缀失效（如世界数据更新时）
cache.invalidate_prefix("pregen:world:1:")

# 统计
stats = cache.get_stats()
print(f"命中率: {stats['hit_rate']:.2%}")
```

---

## 特性

- 🔄 LRU 淘汰策略（最近最少使用）
- ⏰ TTL 过期时间
- 📊 命中率统计
- 🔍 前缀批量失效

---

## 应用场景

| 场景 | 缓存键示例 |
|------|-----------|
| LLM 响应缓存 | `llm:{hash(messages)}` |
| 预生成内容 | `pregen:world:{world_id}` |
| NPC 对话缓存 | `npc:{npc_id}:context` |
