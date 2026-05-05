"""Memory Store 配置 — 长期记忆存储

使用 langgraph.store 实现跨会话持久化存储。
支持语义检索和命名空间隔离。
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from foundation.logger import get_logger

if TYPE_CHECKING:
    from langgraph.store.base import BaseStore

logger = get_logger(__name__)

# 缓存 store 实例（每个项目一个）
_store_cache: dict[str, "BaseStore"] = {}

# 默认命名空间配置
DEFAULT_NAMESPACES = [
    "player_preferences",  # 玩家偏好
    "world_state",         # 世界状态
    "story_events",        # 故事事件
    "npc_relationships",   # NPC 关系
    "quest_history",       # 任务历史
]


def get_memory_store(
    project_path: str | Path,
    use_sqlite: bool = True,
) -> "BaseStore":
    """获取长期记忆存储

    Args:
        project_path: 项目根目录路径
        use_sqlite: 是否使用 SQLite 持久化（生产环境推荐 True）

    Returns:
        BaseStore 实例
    """
    project_path = Path(project_path)
    cache_key = str(project_path.resolve())

    # 检查缓存
    if cache_key in _store_cache:
        return _store_cache[cache_key]

    # 创建数据库目录
    db_path = project_path / "data" / "memory.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if use_sqlite:
        # 使用 SQLite 持久化存储
        try:
            from langgraph.store.sqlite import SqliteStore

            logger.info(f"创建 SQLite Memory Store: {db_path}")
            store = SqliteStore.from_conn_string(str(db_path))
        except ImportError:
            logger.warning("SqliteStore 不可用，回退到 InMemoryStore")
            from langgraph.store.memory import InMemoryStore

            store = InMemoryStore()
    else:
        # 使用内存存储（开发/测试环境）
        from langgraph.store.memory import InMemoryStore

        logger.info("创建 InMemory Memory Store")
        store = InMemoryStore()

    # 缓存实例
    _store_cache[cache_key] = store

    return store


def clear_store_cache(project_path: str | Path | None = None) -> None:
    """清除 store 缓存

    Args:
        project_path: 指定项目路径则清除该项目，None 则清除所有
    """
    global _store_cache

    if project_path is None:
        _store_cache.clear()
        logger.info("已清除所有 Memory Store 缓存")
    else:
        cache_key = str(Path(project_path).resolve())
        if cache_key in _store_cache:
            del _store_cache[cache_key]
            logger.info(f"已清除项目 Memory Store 缓存: {cache_key}")


class MemoryStoreWrapper:
    """Memory Store 包装器 — 提供更友好的 API

    封装 BaseStore 的底层操作，提供游戏相关的记忆管理方法。
    """

    def __init__(self, store: "BaseStore", world_id: str = "1"):
        self._store = store
        self._world_id = world_id

    def _make_namespace(self, category: str) -> tuple[str, ...]:
        """构建命名空间"""
        return (self._world_id, category)

    def save(
        self,
        category: str,
        content: str,
        key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """保存记忆

        Args:
            category: 记忆类别（如 player_preferences, world_state）
            content: 记忆内容
            key: 记忆键（可选，自动生成）
            metadata: 元数据（如 importance, tags, turn）
        """
        namespace = self._make_namespace(category)

        # 自动生成 key
        if key is None:
            import uuid

            key = str(uuid.uuid4())

        # 构建 value
        value = {
            "content": content,
            "metadata": metadata or {},
            "timestamp": metadata.get("timestamp") if metadata else None,
        }

        self._store.put(namespace, key, value)
        logger.debug(f"记忆已保存: {category}/{key}")

    def search(
        self,
        category: str,
        query: str = "",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """搜索记忆

        Args:
            category: 记忆类别
            query: 搜索查询（语义检索）
            limit: 返回数量限制

        Returns:
            记忆列表
        """
        namespace = self._make_namespace(category)

        try:
            # 尝试语义搜索
            results = self._store.search(
                namespace,
                query=query,
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"语义搜索失败，回退到列表: {e}")
            # 回退到简单列表
            results = self._store.list(namespace, limit=limit)

        return [
            {
                "key": r.key,
                "content": r.value.get("content", ""),
                "metadata": r.value.get("metadata", {}),
                "score": getattr(r, "score", 1.0),
            }
            for r in results
        ]

    def get(self, category: str, key: str) -> dict[str, Any] | None:
        """获取特定记忆

        Args:
            category: 记忆类别
            key: 记忆键

        Returns:
            记忆内容或 None
        """
        namespace = self._make_namespace(category)
        result = self._store.get(namespace, key)

        if result is None:
            return None

        return {
            "key": result.key,
            "content": result.value.get("content", ""),
            "metadata": result.value.get("metadata", {}),
        }

    def delete(self, category: str, key: str) -> bool:
        """删除记忆

        Args:
            category: 记忆类别
            key: 记忆键

        Returns:
            是否成功删除
        """
        namespace = self._make_namespace(category)

        try:
            self._store.delete(namespace, key)
            logger.debug(f"记忆已删除: {category}/{key}")
            return True
        except Exception as e:
            logger.warning(f"删除记忆失败: {e}")
            return False

    def list_categories(self) -> list[str]:
        """列出所有记忆类别"""
        # 获取所有命名空间
        all_namespaces = self._store.list_namespaces()

        # 提取当前世界的类别
        categories = set()
        for ns in all_namespaces:
            if len(ns) >= 2 and ns[0] == self._world_id:
                categories.add(ns[1])

        return sorted(list(categories))


def get_memory_store_wrapper(
    project_path: str | Path,
    world_id: str = "1",
    use_sqlite: bool = True,
) -> MemoryStoreWrapper:
    """获取 MemoryStoreWrapper 实例

    Args:
        project_path: 项目根目录路径
        world_id: 世界 ID
        use_sqlite: 是否使用 SQLite 持久化

    Returns:
        MemoryStoreWrapper 实例
    """
    store = get_memory_store(project_path, use_sqlite)
    return MemoryStoreWrapper(store, world_id)
