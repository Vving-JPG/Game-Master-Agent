"""事件总线 — 同层/跨层通信的核心机制

设计原则:
1. 同层模块间禁止直接 import，必须通过 EventBus 通信
2. 跨层通信优先使用 EventBus，而非直接调用
3. 事件类型使用字符串标识，按 "layer.module.action" 命名
4. 支持同步和异步两种事件处理
5. 支持事件过滤和优先级

事件命名规范:
    foundation.config.changed      — 配置变更
    foundation.db.initialized      — 数据库初始化完成
    foundation.llm.response        — LLM 响应完成
    foundation.llm.error           — LLM 调用失败
    foundation.llm.stream_token    — LLM 流式 token
    core.state.changed             — 游戏状态变更
    core.state.snapshot            — 状态快照请求
    feature.battle.started         — 战斗开始
    feature.battle.ended           — 战斗结束
    feature.quest.updated          — 任务状态更新
    presentation.ui.refresh        — UI 刷新请求
    presentation.ui.notification   — UI 通知
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    """事件处理优先级（数值越小优先级越高）"""
    HIGHEST = 0
    HIGH = 1
    NORMAL = 5
    LOW = 10
    LOWEST = 20


@dataclass
class Event:
    """事件对象"""
    type: str                          # 事件类型，如 "foundation.llm.response"
    data: dict[str, Any] = field(default_factory=dict)  # 事件数据
    source: str = ""                   # 事件来源模块
    target: str = ""                   # 目标模块（空=广播）
    timestamp: float = 0.0             # 时间戳

    def __post_init__(self):
        if self.timestamp == 0.0:
            import time
            self.timestamp = time.time()

    def get(self, key: str, default: Any = None) -> Any:
        """获取事件数据中的字段"""
        return self.data.get(key, default)


# 事件处理器类型
SyncHandler = Callable[[Event], None]
AsyncHandler = Callable[[Event], Coroutine[Any, Any, None]]
Handler = SyncHandler | AsyncHandler


@dataclass
class _Subscription:
    """订阅信息"""
    handler: Handler
    priority: Priority
    filter_fn: Callable[[Event], bool] | None = None
    once: bool = False  # 是否只触发一次


class EventBus:
    """事件总线

    使用方式:
        # 订阅事件
        event_bus.subscribe("foundation.llm.response", on_llm_response)

        # 订阅带过滤
        event_bus.subscribe("core.state.changed", on_state_change,
                          filter_fn=lambda e: e.get("world_id") == "1")

        # 发布事件
        event_bus.emit(Event(type="foundation.llm.response",
                            data={"content": "你好", "tokens": 100},
                            source="feature.dialogue"))

        # 异步发布
        await event_bus.emit_async(Event(...))

        # 取消订阅
        event_bus.unsubscribe("foundation.llm.response", on_llm_response)
    """

    def __init__(self):
        self._subscriptions: dict[str, list[_Subscription]] = defaultdict(list)
        self._lock = threading.Lock()
        self._async_handlers: list[tuple[str, AsyncHandler]] = []

    def subscribe(
        self,
        event_type: str,
        handler: Handler,
        priority: Priority = Priority.NORMAL,
        filter_fn: Callable[[Event], bool] | None = None,
        once: bool = False,
    ) -> None:
        """订阅事件

        Args:
            event_type: 事件类型（支持通配符 "*" 订阅所有事件）
            handler: 事件处理函数（同步或异步）
            priority: 优先级
            filter_fn: 过滤函数，返回 True 才处理
            once: 是否只触发一次
        """
        sub = _Subscription(
            handler=handler,
            priority=priority,
            filter_fn=filter_fn,
            once=once,
        )
        with self._lock:
            self._subscriptions[event_type].append(sub)
            # 按优先级排序
            self._subscriptions[event_type].sort(key=lambda s: s.priority)

        if asyncio.iscoroutinefunction(handler):
            self._async_handlers.append((event_type, handler))

        logger.debug(f"事件订阅: {event_type} -> {handler.__qualname__} "
                     f"(priority={priority.name}, once={once})")

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        """取消订阅"""
        with self._lock:
            subs = self._subscriptions.get(event_type, [])
            self._subscriptions[event_type] = [
                s for s in subs if s.handler is not handler
            ]
            self._async_handlers = [
                (et, h) for et, h in self._async_handlers
                if not (et == event_type and h is handler)
            ]
        logger.debug(f"取消订阅: {event_type} -> {handler.__qualname__}")

    def emit(self, event: Event | str, data: dict[str, Any] | None = None, **kwargs) -> list[Any]:
        """同步发布事件，返回所有处理器的返回值列表

        Args:
            event: Event 对象或事件类型字符串
            data: 事件数据（当 event 为字符串时使用）
            **kwargs: 额外的事件属性（source, target 等）

        用法:
            # 方式1: 传入 Event 对象
            event_bus.emit(Event(type="test", data={"key": "value"}))

            # 方式2: 传入事件类型和数据（便捷方式）
            event_bus.emit("test", {"key": "value"}, source="module")
        """
        # 便捷方式：将字符串转换为 Event 对象
        if isinstance(event, str):
            event = Event(
                type=event,
                data=data or {},
                **{k: v for k, v in kwargs.items() if k in ("source", "target")}
            )

        results = []
        handlers_to_remove = []

        # 收集匹配的订阅
        with self._lock:
            # 精确匹配
            matched = list(self._subscriptions.get(event.type, []))
            # 通配符匹配
            if event.type != "*":
                matched.extend(self._subscriptions.get("*", []))

        for sub in matched:
            # 过滤检查
            if sub.filter_fn and not sub.filter_fn(event):
                continue

            # 目标过滤：当事件有 target 时，只处理 target 匹配的订阅者
            if event.target and sub.handler.__qualname__ != event.target:
                continue

            try:
                if asyncio.iscoroutinefunction(sub.handler):
                    # 异步处理器在同步 emit 中只记录，不执行
                    logger.warning(
                        f"异步处理器 {sub.handler.__qualname__} 在同步 emit 中被跳过，"
                        f"请使用 emit_async()"
                    )
                    continue

                result = sub.handler(event)
                results.append(result)

                if sub.once:
                    handlers_to_remove.append((event.type, sub))

            except Exception as e:
                logger.error(f"事件处理器异常: {event.type} -> {sub.handler.__qualname__}: {e}")

        # 清理 once 订阅
        for et, sub in handlers_to_remove:
            with self._lock:
                subs = self._subscriptions.get(et, [])
                if sub in subs:
                    subs.remove(sub)

        return results

    async def emit_async(self, event: Event) -> list[Any]:
        """异步发布事件，支持异步处理器"""
        results = []
        handlers_to_remove = []

        with self._lock:
            matched = list(self._subscriptions.get(event.type, []))
            if event.type != "*":
                matched.extend(self._subscriptions.get("*", []))

        for sub in matched:
            if sub.filter_fn and not sub.filter_fn(event):
                continue
            # 目标过滤：当事件有 target 时，只处理 target 匹配的订阅者
            if event.target and sub.handler.__qualname__ != event.target:
                continue

            try:
                if asyncio.iscoroutinefunction(sub.handler):
                    result = await sub.handler(event)
                else:
                    result = sub.handler(event)
                results.append(result)

                if sub.once:
                    handlers_to_remove.append((event.type, sub))

            except Exception as e:
                logger.error(f"异步事件处理器异常: {event.type} -> {sub.handler.__qualname__}: {e}")

        for et, sub in handlers_to_remove:
            with self._lock:
                subs = self._subscriptions.get(et, [])
                if sub in subs:
                    subs.remove(sub)

        return results

    def on(self, event_type: str, **kwargs):
        """装饰器方式订阅事件

        用法:
            @event_bus.on("foundation.llm.response")
            def handle_response(event: Event):
                print(event.get("content"))
        """
        def decorator(func: Handler):
            self.subscribe(event_type, func, **kwargs)
            return func
        return decorator

    def once(self, event_type: str, **kwargs):
        """装饰器方式订阅一次性事件"""
        def decorator(func: Handler):
            self.subscribe(event_type, func, once=True, **kwargs)
            return func
        return decorator

    def clear(self) -> None:
        """清除所有订阅"""
        with self._lock:
            self._subscriptions.clear()
            self._async_handlers.clear()
        logger.info("事件总线已清除所有订阅")

    def get_subscriptions(self) -> dict[str, int]:
        """获取当前订阅统计（用于调试）"""
        with self._lock:
            return {
                event_type: len(subs)
                for event_type, subs in self._subscriptions.items()
                if subs
            }


# 全局单例
event_bus = EventBus()
