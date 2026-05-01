# P0: Foundation 层 — 四层骨架 + 基础设施

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。
> 这是整个重构的**第一步**，后续所有 Phase 都依赖本 Phase 的产出。

## 项目概述

你正在帮助用户将 **Game Master Agent V2** 的 `2workbench/` 目录全面重构为**四层架构**。

- **技术**: Python 3.11+ / PyQt6 / SQLite / LangGraph / uv
- **包管理器**: uv
- **开发 IDE**: Trae
- **本 Phase 目标**: 搭建四层目录骨架，实现 Foundation 层全部基础设施

### 架构总览：四层依赖方向

```
入口层 → Presentation (表现层) → Feature (功能层) → Core (核心层) → Foundation (基础层)
```

- ✅ 上层可以依赖下层
- ❌ 下层绝对不能引用/调用/依赖上层
- ✅ 同层模块间仅通过 EventBus 通信，禁止直接依赖
- ❌ 无循环依赖、无跨层直调、无硬编码引用

### 四层职责

| 层 | 定位 | 允许的内容 | 禁止的内容 |
|---|---|---|---|
| **Foundation** | 最底层，全项目依赖 | 工具类、全局单例（EventBus/ResourceManager/SaveManager）、基础接口、基类 | 业务逻辑、UI、状态 |
| **Core** | 纯数据 + 纯规则 | 数据类（Pydantic）、纯函数计算器、状态机、常量、LangGraph State 定义 | 节点、动画、UI、输入 |
| **Feature** | 业务功能集合 | 各系统（Battle/Item/Skill/Dialogue/Quest/AI/Dungeon） | UI、动画、直接引用其他功能模块 |
| **Presentation** | 门面展示 | UI 系统（PyQt6）、特效系统、音效系统 | 计算逻辑、修改核心数据 |

### 本 Phase (P0) 范围

**只做 Foundation 层**，包括：
1. 四层目录结构创建
2. EventBus（事件总线）
3. Config（配置管理）
4. Logger（日志系统）
5. Database（数据库连接管理）
6. LLMClient（多模型 LLM 客户端）
7. ModelRouter（多模型路由器）
8. SaveManager（存档管理器）
9. Cache（LRU 缓存）
10. 基类与接口定义

### 前置条件

- 项目根目录已有 `2workbench/` 目录（现有代码将在后续 Phase 逐步迁移）
- Python 3.11+ 已安装
- uv 已安装

### 现有代码参考

本 Phase 需要参考并**改进**以下现有文件（不要直接复制，要按四层架构规范重构）：

| 现有文件 | 参考内容 | 改进方向 |
|---------|---------|---------|
| `2workbench/core/config.py` | pydantic-settings 配置加载 | 扩展为多模型配置 |
| `2workbench/core/utils/logger.py` | 日志工具 | 增加结构化日志支持 |
| `2workbench/core/services/database.py` | SQLite 连接管理 | 增加连接池、迁移支持 |
| `2workbench/core/services/llm_client.py` | AsyncOpenAI 封装 | 改为多模型抽象 |
| `2workbench/core/services/model_router.py` | 关键词路由 | 改为配置驱动 |
| `2workbench/core/services/save_manager.py` | 数据库文件复制存档 | 增加版本管理 |
| `2workbench/core/services/cache.py` | LRU 缓存 | 泛化为通用缓存 |

---

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始"后，主动执行
4. **遇到错误先尝试修复**：3 次失败后再询问
5. **代码规范**：UTF-8，中文注释，PEP 8，类型注解
6. **依赖方向**：Foundation 层的代码**绝对不能** import 任何上层模块
7. **测试**：每个模块都要有对应的测试文件

---

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **新架构根目录**: `2workbench/`（在现有目录下创建新的子目录结构）
- **Foundation 层**: `2workbench/foundation/`
- **包管理**: `pyproject.toml`（项目根目录）

---

## 步骤

### Step 1: 创建四层目录结构

**目的**: 建立四层架构的目录骨架，每个层级有明确的 `__init__.py` 导出。

**方案**:

1.1 在 `2workbench/` 下创建新的四层目录结构（**不删除现有代码**，新结构并行存在）：

```
2workbench/
├── foundation/                    ← Foundation 层（本 Phase 重点）
│   ├── __init__.py
│   ├── event_bus.py              ← 事件总线
│   ├── config.py                 ← 配置管理
│   ├── logger.py                 ← 日志系统
│   ├── database.py               ← 数据库连接管理
│   ├── llm/                      ← LLM 客户端子包
│   │   ├── __init__.py
│   │   ├── base.py               ← LLM 抽象基类
│   │   ├── openai_client.py      ← OpenAI 兼容客户端
│   │   └── model_router.py       ← 多模型路由器
│   ├── save_manager.py           ← 存档管理
│   ├── cache.py                  ← 通用缓存
│   ├── resource_manager.py       ← 资源管理
│   └── base/                     ← 基类与接口
│       ├── __init__.py
│       ├── singleton.py          ← 单例基类
│       └── interfaces.py         ← 核心接口定义
│
├── core/                         ← Core 层（P1 实现）
│   ├── __init__.py
│   ├── state.py                  ← LangGraph State 定义
│   ├── models/                   ← 数据类
│   │   └── __init__.py
│   ├── constants/                ← 常量
│   │   └── __init__.py
│   └── calculators/              ← 纯函数计算器
│       └── __init__.py
│
├── feature/                      ← Feature 层（P3 实现）
│   ├── __init__.py
│   ├── battle/                   ← 战斗系统
│   │   └── __init__.py
│   ├── dialogue/                 ← 对话系统
│   │   └── __init__.py
│   ├── quest/                    ← 任务系统
│   │   └── __init__.py
│   ├── item/                     ← 物品系统
│   │   └── __init__.py
│   ├── exploration/              ← 探索系统
│   │   └── __init__.py
│   ├── narration/                ← 叙事系统
│   │   └── __init__.py
│   ├── skill/                    ← 技能系统
│   │   └── __init__.py
│   └── ai/                       ← AI 编排（LangGraph）
│       └── __init__.py
│
├── presentation/                 ← Presentation 层（P4/P5 实现）
│   ├── __init__.py
│   ├── main_window.py            ← 主窗口
│   ├── widgets/                  ← UI 组件
│   │   └── __init__.py
│   ├── editors/                  ← 编辑器
│   │   └── __init__.py
│   ├── panels/                   ← 面板
│   │   └── __init__.py
│   ├── dialogs/                  ← 对话框
│   │   └── __init__.py
│   └── styles/                   ← 样式
│       └── __init__.py
│
├── app.py                        ← 应用入口（保留）
├── __main__.py                   ← 模块入口（保留）
└── ...                           ← 现有代码暂不删除
```

1.2 创建各层级的 `__init__.py`，使用 `__all__` 明确导出：

```python
# 2workbench/foundation/__init__.py
"""Foundation 层 — 最底层基础设施

本层包含全项目依赖的工具类、全局单例、基础接口和基类。
上层（Core/Feature/Presentation）可以依赖本层，但本层绝对不能引用上层。

模块:
    event_bus: 事件总线（同层/跨层通信）
    config: 配置管理（pydantic-settings）
    logger: 日志系统（结构化日志）
    database: 数据库连接管理（SQLite + WAL）
    llm: LLM 客户端（多模型抽象 + 路由）
    save_manager: 存档管理（版本化存档）
    cache: 通用缓存（LRU + TTL）
    resource_manager: 资源管理（文件系统操作）
    base: 基类与接口（单例、核心接口）
"""
from foundation.event_bus import EventBus, event_bus
from foundation.config import Settings, settings
from foundation.logger import get_logger, setup_logging
from foundation.database import get_db_path, get_db, init_db
from foundation.save_manager import SaveManager
from foundation.cache import LRUCache
from foundation.resource_manager import ResourceManager

__all__ = [
    "EventBus", "event_bus",
    "Settings", "settings",
    "get_logger", "setup_logging",
    "get_db_path", "get_db", "init_db",
    "SaveManager",
    "LRUCache",
    "ResourceManager",
]
```

```python
# 2workbench/core/__init__.py
"""Core 层 — 纯数据 + 纯规则

本层包含数据类（Pydantic）、纯函数计算器、状态机、常量、LangGraph State 定义。
本层只依赖 Foundation 层，不依赖 Feature/Presentation 层。
"""
# P1 阶段填充
```

```python
# 2workbench/feature/__init__.py
"""Feature 层 — 业务功能集合

本层包含各业务系统（Battle/Item/Skill/Dialogue/Quest/AI 等）。
本层只依赖 Core 和 Foundation 层，不依赖 Presentation 层。
同层模块间仅通过 EventBus 通信，禁止直接依赖。
"""
# P3 阶段填充
```

```python
# 2workbench/presentation/__init__.py
"""Presentation 层 — 门面展示

本层包含 UI 系统（PyQt6）、特效系统、音效系统。
本层可以依赖所有下层，但不包含计算逻辑。
"""
# P4/P5 阶段填充
```

1.3 验证目录结构：

```bash
# 验证所有目录和 __init__.py 存在
find 2workbench/foundation 2workbench/core 2workbench/feature 2workbench/presentation -name "*.py" | sort
```

**验收**:
- [ ] `2workbench/foundation/` 目录存在，包含所有规划的子目录和文件
- [ ] `2workbench/core/` 目录存在，包含子目录占位
- [ ] `2workbench/feature/` 目录存在，包含子目录占位
- [ ] `2workbench/presentation/` 目录存在，包含子目录占位
- [ ] 每个 `__init__.py` 都有正确的 docstring 和 `__all__`
- [ ] `python -c "from foundation import EventBus, Settings, get_logger"` 可以正常导入（在 2workbench/ 目录下执行）

---

### Step 2: EventBus — 事件总线

**目的**: 实现同层模块间和跨层通信的事件总线，替代直接依赖。

**参考**: 现有代码中 `AgentBridge` 使用 PyQt6 Signal 进行 GUI↔后端通信，但 Service 层之间没有通信机制。

**方案**:

2.1 创建 `2workbench/foundation/event_bus.py`：

```python
# 2workbench/foundation/event_bus.py
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

    def emit(self, event: Event) -> list[Any]:
        """同步发布事件，返回所有处理器的返回值列表"""
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

            # 来源过滤（不处理自己发出的事件）
            if event.source and event.target and event.source != event.target:
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
            if event.source and event.target and event.source != event.target:
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
```

2.2 创建测试文件 `2workbench/tests/test_event_bus.py`：

```python
# 2workbench/tests/test_event_bus.py
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
```

2.3 运行测试：

```bash
cd 2workbench && python tests/test_event_bus.py
```

**验收**:
- [ ] `foundation/event_bus.py` 创建完成
- [ ] 支持 sync/async 两种事件处理
- [ ] 支持优先级、过滤、一次性订阅、通配符、装饰器
- [ ] 全局单例 `event_bus` 可导入
- [ ] 全部 8 个测试通过

---

### Step 3: Config — 配置管理

**目的**: 扩展现有 `config.py`，支持多模型配置、数据库配置、UI 配置等。

**参考**: 现有 `2workbench/core/config.py` 使用 `pydantic-settings`，只支持 DeepSeek 单模型。

**方案**:

3.1 创建 `2workbench/foundation/config.py`：

```python
# 2workbench/foundation/config.py
"""配置管理 — 多模型 + 全局配置

从 .env 文件和环境变量加载配置，支持多 LLM 供应商配置。
配置变更时通过 EventBus 通知。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderConfig(BaseSettings):
    """单个 LLM 供应商配置"""
    model_config = SettingsConfigDict(env_prefix="")

    api_key: str = ""
    base_url: str = ""
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    max_retries: int = 3


class Settings(BaseSettings):
    """全局配置

    环境变量映射:
        DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
        OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
        ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL

    .env 文件格式:
        DEEPSEEK_API_KEY=sk-xxx
        DEEPSEEK_BASE_URL=https://api.deepseek.com
        DEEPSEEK_MODEL=deepseek-chat
        OPENAI_API_KEY=sk-xxx
        OPENAI_MODEL=gpt-4o
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 应用 ----
    app_name: str = "Game Master Agent"
    app_version: str = "3.0"
    debug: bool = False

    # ---- 数据库 ----
    database_path: str = "./data/game.db"
    database_wal_mode: bool = True

    # ---- 日志 ----
    log_level: str = "INFO"
    log_file: str = "./data/logs/app.log"
    log_max_size_mb: int = 10
    log_backup_count: int = 5

    # ---- LLM 供应商 ----
    # DeepSeek（默认）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_max_tokens: int = 4096
    deepseek_temperature: float = 0.7

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.7

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096
    anthropic_temperature: float = 0.7

    # ---- 默认模型 ----
    default_provider: Literal["deepseek", "openai", "anthropic"] = "deepseek"

    # ---- 缓存 ----
    cache_max_size: int = 200
    cache_ttl_seconds: int = 600

    # ---- 存档 ----
    save_directory: str = "./saves"
    max_save_slots: int = 10

    # ---- HTTP 服务 ----
    http_host: str = "127.0.0.1"
    http_port: int = 18080

    # ---- UI ----
    ui_theme: str = "dark"
    ui_font_size: int = 13
    ui_language: str = "zh-CN"

    def get_provider_config(self, provider: str | None = None) -> LLMProviderConfig:
        """获取指定供应商的配置

        Args:
            provider: 供应商名称（deepseek/openai/anthropic），默认使用 default_provider

        Returns:
            LLMProviderConfig 实例
        """
        provider = provider or self.default_provider
        configs = {
            "deepseek": LLMProviderConfig(
                api_key=self.deepseek_api_key,
                base_url=self.deepseek_base_url,
                model=self.deepseek_model,
                max_tokens=self.deepseek_max_tokens,
                temperature=self.deepseek_temperature,
            ),
            "openai": LLMProviderConfig(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url,
                model=self.openai_model,
                max_tokens=self.openai_max_tokens,
                temperature=self.openai_temperature,
            ),
            "anthropic": LLMProviderConfig(
                api_key=self.anthropic_api_key,
                base_url=self.anthropic_base_url,
                model=self.anthropic_model,
                max_tokens=self.anthropic_max_tokens,
                temperature=self.anthropic_temperature,
            ),
        }
        if provider not in configs:
            raise ValueError(f"未知 LLM 供应商: {provider}，可用: {list(configs.keys())}")
        return configs[provider]

    def get_available_providers(self) -> list[str]:
        """获取已配置 API Key 的可用供应商列表"""
        providers = []
        if self.deepseek_api_key:
            providers.append("deepseek")
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic")
        return providers or [self.default_provider]


# 全局单例
settings = Settings()
```

3.2 创建 `.env.template`（如果不存在则更新）：

```env
# Game Master Agent V3 配置模板
# 复制为 .env 并填入实际值

# ---- DeepSeek（默认）----
DEEPSEEK_API_KEY=sk-your-deepseek-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_TEMPERATURE=0.7

# ---- OpenAI ----
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# ---- Anthropic ----
ANTHROPIC_API_KEY=
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# ---- 默认模型 ----
DEFAULT_PROVIDER=deepseek

# ---- 数据库 ----
DATABASE_PATH=./data/game.db

# ---- 日志 ----
LOG_LEVEL=INFO
LOG_FILE=./data/logs/app.log

# ---- 调试 ----
DEBUG=false
```

3.3 测试：

```bash
cd 2workbench && python -c "
from foundation.config import Settings, settings
print(f'app_name: {settings.app_name}')
print(f'default_provider: {settings.default_provider}')
config = settings.get_provider_config('deepseek')
print(f'deepseek model: {config.model}')
print(f'available: {settings.get_available_providers()}')
print('✅ Config 测试通过')
"
```

**验收**:
- [ ] `foundation/config.py` 创建完成
- [ ] 支持 DeepSeek/OpenAI/Anthropic 三个供应商
- [ ] `get_provider_config()` 返回正确的配置
- [ ] `get_available_providers()` 只返回已配置 Key 的供应商
- [ ] `.env.template` 更新完成

---

### Step 4: Logger — 日志系统

**目的**: 改进现有日志工具，增加结构化日志、文件轮转、控制台彩色输出。

**参考**: 现有 `2workbench/core/utils/logger.py` 是简单的 `logging.getLogger` 封装。

**方案**:

4.1 创建 `2workbench/foundation/logger.py`：

```python
# 2workbench/foundation/logger.py
"""日志系统 — 结构化日志 + 文件轮转 + 彩色控制台

使用方式:
    from foundation.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Agent 启动", extra={"world_id": "1", "turn": 5})
    logger.error("LLM 调用失败", exc_info=True)
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class ColoredFormatter(logging.Formatter):
    """彩色控制台日志格式器"""

    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """结构化日志格式器（用于文件输出）"""

    def format(self, record: logging.LogRecord) -> str:
        # 添加结构化字段
        record.struct = {
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # 附加 extra 字段
        for key in ("world_id", "turn", "player_id", "npc_id",
                     "model", "tokens", "latency_ms", "event_type"):
            if hasattr(record, key):
                record.struct[key] = getattr(record, key)
        return super().format(record)


_initialized = False


def setup_logging(level: str | None = None, log_file: str | None = None) -> None:
    """初始化日志系统

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR），默认从 settings 读取
        log_file: 日志文件路径，默认从 settings 读取
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    # 延迟导入避免循环依赖
    try:
        from foundation.config import settings
        _level = level or settings.log_level
        _log_file = log_file or settings.log_file
        _max_bytes = settings.log_max_size_mb * 1024 * 1024
        _backup_count = settings.log_backup_count
    except Exception:
        _level = level or "INFO"
        _log_file = log_file or "./data/logs/app.log"
        _max_bytes = 10 * 1024 * 1024
        _backup_count = 5

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, _level.upper(), logging.INFO))

    # 控制台处理器（彩色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_fmt = ColoredFormatter(
        fmt="%(asctime)s │ %(levelname)s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # 文件处理器（结构化 + 轮转）
    if _log_file:
        log_path = Path(_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            _log_file,
            maxBytes=_max_bytes,
            backupCount=_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = StructuredFormatter(
            fmt="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        root_logger.addHandler(file_handler)

    # 降低第三方库日志级别
    for lib in ("httpx", "httpcore", "openai", "anthropic", "urllib3"):
        logging.getLogger(lib).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取 logger 实例

    Args:
        name: 通常传入 __name__

    Returns:
        配置好的 Logger 实例
    """
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)
```

4.2 测试：

```bash
cd 2workbench && python -c "
from foundation.logger import get_logger, setup_logging
setup_logging('DEBUG')
logger = get_logger('test')
logger.debug('调试信息')
logger.info('普通信息')
logger.warning('警告信息')
logger.error('错误信息', extra={'world_id': '1'})
print('✅ Logger 测试通过')
"
```

**验收**:
- [ ] `foundation/logger.py` 创建完成
- [ ] 控制台输出带颜色
- [ ] 文件日志带时间戳和轮转
- [ ] `get_logger(__name__)` 正常工作
- [ ] `extra` 字段（world_id, turn 等）可传入

---

### Step 5: Database — 数据库连接管理

**目的**: 改进现有 `database.py`，增加连接池、迁移支持、EventBus 集成。

**参考**: 现有 `2workbench/core/services/database.py` 使用 `sqlite3.connect` + 上下文管理器。

**方案**:

5.1 创建 `2workbench/foundation/database.py`：

```python
# 2workbench/foundation/database.py
"""数据库连接管理 — SQLite + WAL + 迁移支持

设计原则:
1. 使用 SQLite WAL 模式提升并发性能
2. 使用 Row 工厂支持字典式访问
3. 支持数据库迁移（版本号管理）
4. 初始化完成后通过 EventBus 通知
5. 线程安全（每个线程独立连接）
"""
from __future__ import annotations

import contextlib
import sqlite3
import threading
from pathlib import Path
from typing import Any, Generator

from foundation.logger import get_logger

logger = get_logger(__name__)

# 线程本地存储（每个线程独立连接）
_thread_local = threading.local()

# 当前数据库 schema 版本
SCHEMA_VERSION = 1


def get_db_path() -> Path:
    """获取数据库文件路径"""
    try:
        from foundation.config import settings
        return Path(settings.database_path)
    except Exception:
        return Path("./data/game.db")


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """创建新的数据库连接

    Args:
        db_path: 数据库文件路径，默认从 settings 读取

    Returns:
        配置好的 SQLite 连接
    """
    if db_path is None:
        db_path = get_db_path()
    else:
        db_path = Path(db_path)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    return conn


def get_db(db_path: str | Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """获取数据库连接的上下文管理器（自动 commit/rollback/close）

    用法:
        with get_db() as db:
            db.execute("INSERT INTO ...")
            # 自动 commit
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_thread_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """获取当前线程的持久连接（线程安全）

    每个线程复用同一个连接，避免频繁创建/关闭。
    注意: 调用方需要自行管理事务。

    Args:
        db_path: 数据库文件路径

    Returns:
        当前线程的 SQLite 连接
    """
    if not hasattr(_thread_local, "db_connection") or _thread_local.db_connection is None:
        _thread_local.db_connection = get_connection(db_path)
        logger.debug(f"新线程数据库连接: {threading.current_thread().name}")
    return _thread_local.db_connection


def close_thread_db() -> None:
    """关闭当前线程的数据库连接"""
    if hasattr(_thread_local, "db_connection") and _thread_local.db_connection is not None:
        try:
            _thread_local.db_connection.close()
        except Exception:
            pass
        _thread_local.db_connection = None


def init_db(
    schema_path: str | Path | None = None,
    db_path: str | Path | None = None,
) -> bool:
    """初始化数据库（执行 schema.sql）

    Args:
        schema_path: SQL schema 文件路径
        db_path: 数据库文件路径

    Returns:
        是否成功初始化
    """
    if schema_path is None:
        # 默认 schema 路径
        schema_path = Path(__file__).parent.parent / "core" / "models" / "schema.sql"
    else:
        schema_path = Path(schema_path)

    try:
        with get_db(db_path) as db:
            # 检查当前版本
            row = db.execute("PRAGMA user_version").fetchone()
            current_version = row[0] if row else 0

            if current_version >= SCHEMA_VERSION:
                logger.info(f"数据库已是最新版本 (v{current_version})")
                return True

            # 执行 schema
            if schema_path.exists():
                sql = schema_path.read_text(encoding="utf-8")
                db.executescript(sql)
                logger.info(f"数据库 schema 已执行: {schema_path}")
            else:
                logger.warning(f"Schema 文件不存在: {schema_path}，跳过初始化")

            # 更新版本号
            db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

        logger.info(f"数据库初始化完成: {db_path or get_db_path()} (v{SCHEMA_VERSION})")

        # 通知其他模块
        try:
            from foundation.event_bus import event_bus, Event
            event_bus.emit(Event(
                type="foundation.db.initialized",
                data={"db_path": str(db_path or get_db_path()), "version": SCHEMA_VERSION},
                source="foundation.database",
            ))
        except Exception:
            pass

        return True

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False


def execute_query(
    sql: str,
    params: tuple | dict = (),
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    """执行查询并返回结果列表

    Args:
        sql: SQL 语句
        params: 参数
        db_path: 数据库路径

    Returns:
        查询结果列表（sqlite3.Row 对象，支持字典式访问）
    """
    with get_db(db_path) as db:
        cursor = db.execute(sql, params)
        return cursor.fetchall()


def execute_script(
    sql: str,
    db_path: str | Path | None = None,
) -> None:
    """执行多条 SQL 语句

    Args:
        sql: 多条 SQL 语句（分号分隔）
        db_path: 数据库路径
    """
    with get_db(db_path) as db:
        db.executescript(sql)
```

5.2 测试：

```bash
cd 2workbench && python -c "
from foundation.database import get_db, init_db, execute_query
import tempfile, os

# 使用临时数据库测试
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp_db = f.name

try:
    # 初始化（不执行 schema，因为没有 schema.sql）
    from foundation.database import get_connection
    conn = get_connection(tmp_db)
    conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
    conn.commit()
    conn.close()

    # 测试 get_db 上下文管理器
    with get_db(tmp_db) as db:
        db.execute('INSERT INTO test (name) VALUES (?)', ('hello',))

    # 测试查询
    rows = execute_query('SELECT * FROM test', db_path=tmp_db)
    assert len(rows) == 1
    assert rows[0]['name'] == 'hello'
    print('✅ Database 测试通过')
finally:
    os.unlink(tmp_db)
"
```

**验收**:
- [ ] `foundation/database.py` 创建完成
- [ ] WAL 模式、外键约束、busy_timeout 已配置
- [ ] `get_db()` 上下文管理器正常工作（自动 commit/rollback）
- [ ] `get_thread_db()` 线程安全
- [ ] `init_db()` 执行 schema.sql 并设置版本号
- [ ] 初始化完成后发出 EventBus 事件

---

### Step 6: LLM Client — 多模型抽象

**目的**: 将现有 `llm_client.py` 重构为多模型抽象架构，支持 DeepSeek/OpenAI/Anthropic。

**参考**: 现有 `2workbench/core/services/llm_client.py` 基于 `openai.AsyncOpenAI`，支持 chat/chat_with_tools/chat_stream/stream 四种调用方式，使用 tenacity 重试。

**方案**:

6.1 创建 `2workbench/foundation/llm/base.py`：

```python
# 2workbench/foundation/llm/base.py
"""LLM 客户端抽象基类

所有 LLM 供应商必须实现此接口。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator


@dataclass
class LLMMessage:
    """LLM 消息"""
    role: str  # system / user / assistant / tool
    content: str = ""
    name: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str = ""
    reasoning_content: str = ""  # 思考过程（DeepSeek Reasoner）
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    latency_ms: int = 0


@dataclass
class StreamEvent:
    """流式事件"""
    type: str  # reasoning / token / tool_call / complete / error
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error: str = ""


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类

    所有供应商客户端必须实现:
    - chat(): 同步对话
    - chat_async(): 异步对话
    - stream(): 流式对话
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """供应商名称"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """当前模型名称"""
        ...

    @abstractmethod
    async def chat_async(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """异步对话

        Args:
            messages: 消息列表
            temperature: 温度（覆盖默认值）
            max_tokens: 最大 token 数
            tools: 工具定义列表（OpenAI function calling 格式）

        Returns:
            LLMResponse
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """流式对话

        Args:
            messages: 消息列表
            temperature: 温度
            max_tokens: 最大 token 数
            tools: 工具定义列表

        Yields:
            StreamEvent（reasoning/token/tool_call/complete/error）
        """
        ...

    def get_usage_stats(self) -> dict[str, int]:
        """获取 Token 使用统计"""
        return {
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens,
            "total_tokens": self._prompt_tokens + self._completion_tokens,
        }

    def reset_usage_stats(self) -> None:
        """重置 Token 统计"""
        self._prompt_tokens = 0
        self._completion_tokens = 0

    # 子类需要初始化这些
    _prompt_tokens: int = 0
    _completion_tokens: int = 0
```

6.2 创建 `2workbench/foundation/llm/openai_client.py`：

```python
# 2workbench/foundation/llm/openai_client.py
"""OpenAI 兼容客户端 — 支持 DeepSeek / OpenAI / 其他兼容 API

所有使用 OpenAI API 格式的供应商（DeepSeek、OpenAI、各种国产模型）
都可以通过本客户端接入，只需配置不同的 base_url 和 api_key。
"""
from __future__ import annotations

import time
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from foundation.llm.base import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    StreamEvent,
)
from foundation.logger import get_logger

logger = get_logger(__name__)


class OpenAICompatibleClient(BaseLLMClient):
    """OpenAI 兼容客户端

    支持 DeepSeek、OpenAI、以及所有兼容 OpenAI API 的供应商。

    用法:
        client = OpenAICompatibleClient(
            provider_name="deepseek",
            api_key="sk-xxx",
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
        )
        response = await client.chat_async(messages)
    """

    def __init__(
        self,
        provider_name: str,
        api_key: str,
        base_url: str,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self._provider_name = provider_name
        self._model = model
        self._default_max_tokens = max_tokens
        self._default_temperature = temperature

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

        self._retry_decorator = retry(
            retry=retry_if_exception_type(Exception),
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            before_sleep=lambda retry_state: logger.warning(
                f"LLM 重试 ({retry_state.attempt_number}/{max_retries}): "
                f"{retry_state.outcome.exception()}"
            ),
        )

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model

    def _to_openai_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """转换为 OpenAI 格式"""
        result = []
        for msg in messages:
            m: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                m["name"] = msg.name
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            result.append(m)
        return result

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def chat_async(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """异步对话"""
        start_time = time.time()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._to_openai_messages(messages),
            "temperature": temperature or self._default_temperature,
            "max_tokens": max_tokens or self._default_max_tokens,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = await self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            # Token 统计
            if response.usage:
                self._prompt_tokens += response.usage.prompt_tokens
                self._completion_tokens += response.usage.completion_tokens

            latency_ms = int((time.time() - start_time) * 1000)

            # 提取 reasoning_content（DeepSeek Reasoner 特有）
            reasoning = ""
            if hasattr(message, "reasoning_content") and message.reasoning_content:
                reasoning = message.reasoning_content

            # 提取 tool_calls
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })

            return LLMResponse(
                content=message.content or "",
                reasoning_content=reasoning,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason or "",
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                model=response.model,
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"LLM 调用失败 ({self._provider_name}/{self._model}): {e}")
            raise

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """流式对话"""
        start_time = time.time()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._to_openai_messages(messages),
            "temperature": temperature or self._default_temperature,
            "max_tokens": max_tokens or self._default_max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = tools

        try:
            stream = await self._client.chat.completions.create(**kwargs)

            async for chunk in stream:
                if not chunk.choices:
                    # usage 信息
                    if chunk.usage:
                        self._prompt_tokens += chunk.usage.prompt_tokens
                        self._completion_tokens += chunk.usage.completion_tokens
                        yield StreamEvent(
                            type="complete",
                            prompt_tokens=chunk.usage.prompt_tokens,
                            completion_tokens=chunk.usage.completion_tokens,
                            total_tokens=chunk.usage.total_tokens,
                            latency_ms=int((time.time() - start_time) * 1000),
                        )
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # reasoning_content（DeepSeek Reasoner）
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    yield StreamEvent(type="reasoning", content=delta.reasoning_content)

                # 正式内容
                if delta.content:
                    yield StreamEvent(type="token", content=delta.content)

                # tool_calls 增量
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        yield StreamEvent(
                            type="tool_call",
                            tool_calls=[{
                                "index": tc.index,
                                "id": tc.id or "",
                                "type": "function",
                                "function": {
                                    "name": tc.function.name if tc.function else "",
                                    "arguments": tc.function.arguments if tc.function else "",
                                },
                            }],
                        )

        except Exception as e:
            yield StreamEvent(
                type="error",
                error=str(e),
                latency_ms=int((time.time() - start_time) * 1000),
            )
```

6.3 创建 `2workbench/foundation/llm/__init__.py`：

```python
# 2workbench/foundation/llm/__init__.py
"""LLM 客户端子包

提供多模型 LLM 客户端抽象和具体实现。
"""
from foundation.llm.base import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    StreamEvent,
)
from foundation.llm.openai_client import OpenAICompatibleClient
from foundation.llm.model_router import ModelRouter, model_router

__all__ = [
    "BaseLLMClient",
    "LLMMessage",
    "LLMResponse",
    "StreamEvent",
    "OpenAICompatibleClient",
    "ModelRouter",
    "model_router",
]
```

6.4 测试：

```bash
cd 2workbench && python -c "
from foundation.llm.base import LLMMessage, LLMResponse, StreamEvent
from foundation.llm.openai_client import OpenAICompatibleClient

# 测试消息转换
client = OpenAICompatibleClient(
    provider_name='test',
    api_key='test-key',
    base_url='https://api.test.com',
    model='test-model',
)
assert client.provider_name == 'test'
assert client.model_name == 'test-model'

# 测试消息格式转换
msgs = [
    LLMMessage(role='system', content='你是GM'),
    LLMMessage(role='user', content='你好'),
]
result = client._to_openai_messages(msgs)
assert len(result) == 2
assert result[0]['role'] == 'system'
print('✅ LLM Client 测试通过')
"
```

**验收**:
- [ ] `foundation/llm/base.py` 创建完成（抽象基类 + 数据类）
- [ ] `foundation/llm/openai_client.py` 创建完成（OpenAI 兼容客户端）
- [ ] 支持 chat_async 和 stream 两种调用方式
- [ ] 支持 reasoning_content（DeepSeek Reasoner）
- [ ] 支持 tool_calls（OpenAI function calling）
- [ ] 使用 tenacity 自动重试
- [ ] Token 统计正确累计

---

### Step 7: ModelRouter — 多模型路由器

**目的**: 改进现有 `model_router.py`，从硬编码关键词匹配改为配置驱动 + 评分机制。

**参考**: 现有 `2workbench/core/services/model_router.py` 根据关键词（战斗/boss/决战等）路由到 deepseek-reasoner。

**方案**:

7.1 创建 `2workbench/foundation/llm/model_router.py`：

```python
# 2workbench/foundation/llm/model_router.py
"""多模型路由器 — 配置驱动的智能模型选择

路由策略:
1. 显式指定 — 调用方直接指定 provider + model
2. 规则匹配 — 根据内容特征（关键词、长度、事件类型）评分选择
3. 默认回退 — 使用 settings.default_provider

规则配置示例:
    routing_rules:
      - name: critical_narrative
        provider: deepseek
        model: deepseek-reasoner
        conditions:
          keywords: [战斗, boss, 决战, 死亡, 结局, 命运, 秘密, 真相]
          min_turn_length: 20
        score: 10

      - name: creative_writing
        provider: openai
        model: gpt-4o
        conditions:
          keywords: [描写, 描述, 氛围, 场景, 情感]
        score: 5
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from foundation.config import Settings, settings
from foundation.event_bus import event_bus, Event
from foundation.llm.base import BaseLLMClient, LLMMessage
from foundation.llm.openai_client import OpenAICompatibleClient
from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RoutingRule:
    """路由规则"""
    name: str
    provider: str
    model: str
    keywords: list[str] = field(default_factory=list)
    event_types: list[str] = field(default_factory=list)
    min_turn_length: int = 0
    score: int = 0
    temperature: float | None = None
    max_tokens: int | None = None


# 默认路由规则
DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "name": "critical_narrative",
        "provider": "deepseek",
        "model": "deepseek-reasoner",
        "keywords": ["战斗", "boss", "决战", "死亡", "结局", "选择", "命运",
                      "重要", "秘密", "真相", "最终", "关键", "转折", "危机"],
        "min_turn_length": 20,
        "score": 10,
    },
    {
        "name": "npc_deep_dialogue",
        "provider": "deepseek",
        "model": "deepseek-reasoner",
        "keywords": ["关系", "信任", "背叛", "过去", "回忆", "秘密", "身世"],
        "score": 8,
    },
    {
        "name": "standard_narrative",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "score": 0,  # 默认规则
    },
]


class ModelRouter:
    """多模型路由器

    用法:
        router = ModelRouter(settings)

        # 自动路由
        client, config = router.route(content="战斗开始！")

        # 显式指定
        client, config = router.route(provider="openai", model="gpt-4o")
    """

    def __init__(self, settings_obj: Settings | None = None):
        self._settings = settings_obj or settings
        self._clients: dict[str, BaseLLMClient] = {}
        self._rules: list[RoutingRule] = []
        self._load_rules(DEFAULT_RULES)
        self._init_clients()

    def _load_rules(self, rules: list[dict[str, Any]]) -> None:
        """加载路由规则"""
        self._rules = [RoutingRule(**rule) for rule in rules]
        logger.info(f"已加载 {len(self._rules)} 条路由规则")

    def _init_clients(self) -> None:
        """初始化所有已配置的 LLM 客户端"""
        providers = self._settings.get_available_providers()
        for provider in providers:
            config = self._settings.get_provider_config(provider)
            if config.api_key:
                self._clients[provider] = OpenAICompatibleClient(
                    provider_name=provider,
                    api_key=config.api_key,
                    base_url=config.base_url,
                    model=config.model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                )
                logger.info(f"LLM 客户端已初始化: {provider}/{config.model}")

    def route(
        self,
        content: str = "",
        event_type: str = "",
        turn_length: int = 0,
        provider: str | None = None,
        model: str | None = None,
    ) -> tuple[BaseLLMClient, dict[str, Any]]:
        """路由到合适的 LLM 客户端

        Args:
            content: 输入内容（用于规则匹配）
            event_type: 事件类型
            turn_length: 当前对话轮数
            provider: 显式指定供应商（跳过路由）
            model: 显式指定模型（跳过路由）

        Returns:
            (client, config) 元组
            config 包含: provider, model, temperature, max_tokens
        """
        # 显式指定
        if provider:
            client = self._get_client(provider)
            config = self._settings.get_provider_config(provider)
            return client, {
                "provider": provider,
                "model": model or config.model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            }

        # 规则匹配
        best_rule = self._match_rules(content, event_type, turn_length)

        if best_rule:
            client = self._get_client(best_rule.provider)
            provider_config = self._settings.get_provider_config(best_rule.provider)
            logger.debug(
                f"路由匹配: {best_rule.name} -> "
                f"{best_rule.provider}/{best_rule.model} (score={best_rule.score})"
            )
            return client, {
                "provider": best_rule.provider,
                "model": best_rule.model,
                "temperature": best_rule.temperature or provider_config.temperature,
                "max_tokens": best_rule.max_tokens or provider_config.max_tokens,
            }

        # 默认回退
        default_provider = self._settings.default_provider
        client = self._get_client(default_provider)
        config = self._settings.get_provider_config(default_provider)
        return client, {
            "provider": default_provider,
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

    def _match_rules(
        self,
        content: str,
        event_type: str,
        turn_length: int,
    ) -> RoutingRule | None:
        """匹配最佳路由规则"""
        best: RoutingRule | None = None
        best_score = -1

        content_lower = content.lower()

        for rule in self._rules:
            score = 0

            # 关键词匹配
            for keyword in rule.keywords:
                if keyword.lower() in content_lower:
                    score += 1

            # 事件类型匹配
            if event_type and event_type in rule.event_types:
                score += 5

            # 对话长度匹配
            if rule.min_turn_length and turn_length >= rule.min_turn_length:
                score += 3

            # 加上基础分
            score += rule.score

            if score > best_score:
                best_score = score
                best = rule

        return best

    def _get_client(self, provider: str) -> BaseLLMClient:
        """获取或创建客户端"""
        if provider not in self._clients:
            # 尝试初始化
            try:
                config = self._settings.get_provider_config(provider)
                if config.api_key:
                    self._clients[provider] = OpenAICompatibleClient(
                        provider_name=provider,
                        api_key=config.api_key,
                        base_url=config.base_url,
                        model=config.model,
                        max_tokens=config.max_tokens,
                        temperature=config.temperature,
                    )
            except Exception as e:
                logger.error(f"无法初始化 LLM 客户端 ({provider}): {e}")

        if provider not in self._clients:
            raise ValueError(
                f"LLM 客户端未初始化: {provider}。"
                f"请在 .env 中配置 {provider.upper()}_API_KEY"
            )

        return self._clients[provider]

    def get_all_clients(self) -> dict[str, BaseLLMClient]:
        """获取所有已初始化的客户端"""
        return dict(self._clients)

    def add_rule(self, rule: dict[str, Any]) -> None:
        """动态添加路由规则"""
        self._rules.append(RoutingRule(**rule))
        logger.info(f"新增路由规则: {rule.get('name')}")

    def reload(self) -> None:
        """重新加载配置和客户端"""
        self._clients.clear()
        self._rules.clear()
        self._load_rules(DEFAULT_RULES)
        self._init_clients()
        logger.info("模型路由器已重新加载")


# 全局单例
model_router = ModelRouter()
```

7.2 测试：

```bash
cd 2workbench && python -c "
from foundation.llm.model_router import ModelRouter, RoutingRule

# 测试规则匹配
router = ModelRouter()
rule = router._match_rules('战斗开始了！哥布林冲了过来', '', 5)
assert rule is not None
assert rule.name == 'critical_narrative'
print(f'匹配规则: {rule.name} -> {rule.provider}/{rule.model}')

# 测试默认回退
rule2 = router._match_rules('你好', '', 1)
assert rule2 is not None
print(f'默认规则: {rule2.name} -> {rule2.provider}/{rule2.model}')
print('✅ ModelRouter 测试通过')
"
```

**验收**:
- [ ] `foundation/llm/model_router.py` 创建完成
- [ ] 支持关键词 + 事件类型 + 对话长度三种匹配维度
- [ ] 支持显式指定 provider/model（跳过路由）
- [ ] 支持动态添加规则
- [ ] 支持重新加载配置
- [ ] 全局单例 `model_router` 可导入

---

### Step 8: SaveManager + Cache + ResourceManager + 基类

**目的**: 完成剩余 Foundation 层模块。

**方案**:

8.1 创建 `2workbench/foundation/save_manager.py`（改进现有版本，增加版本管理）：

```python
# 2workbench/foundation/save_manager.py
"""存档管理器 — 版本化存档

改进点（相比现有版本）:
1. 存档元数据存入 SQLite（而非仅靠文件名）
2. 支持存档描述和标签
3. 支持自动存档
4. 通过 EventBus 通知存档事件
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from foundation.config import settings
from foundation.database import get_db
from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SaveInfo:
    """存档信息"""
    save_id: str
    world_id: int
    slot_name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    file_path: str = ""
    file_size: int = 0


class SaveManager:
    """存档管理器

    用法:
        sm = SaveManager()
        save_info = sm.save_game(world_id=1, slot_name="auto", description="自动存档")
        sm.load_game(world_id=1, slot_name="auto")
        saves = sm.list_saves(world_id=1)
    """

    def __init__(self, save_dir: str | None = None):
        self._save_dir = Path(save_dir or settings.save_directory)
        self._save_dir.mkdir(parents=True, exist_ok=True)

    def save_game(
        self,
        world_id: int,
        slot_name: str = "manual",
        description: str = "",
        tags: list[str] | None = None,
        db_path: str | Path | None = None,
    ) -> SaveInfo:
        """创建存档

        Args:
            world_id: 世界 ID
            slot_name: 存档槽名称（auto/manual/slot_1/...）
            description: 存档描述
            tags: 标签列表
            db_path: 数据库路径（默认从 settings）

        Returns:
            SaveInfo
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_id = f"world_{world_id}_{slot_name}_{timestamp}"

        # 复制数据库文件
        if db_path is None:
            db_path = settings.database_path

        src = Path(db_path)
        if not src.exists():
            logger.error(f"数据库文件不存在: {src}")
            raise FileNotFoundError(f"数据库文件不存在: {src}")

        dest = self._save_dir / f"{save_id}.db"
        shutil.copy2(src, dest)

        save_info = SaveInfo(
            save_id=save_id,
            world_id=world_id,
            slot_name=slot_name,
            description=description or f"{slot_name} 存档",
            tags=tags or [],
            created_at=datetime.now().isoformat(),
            file_path=str(dest),
            file_size=dest.stat().st_size,
        )

        logger.info(f"存档创建: {save_id} ({dest.stat().st_size // 1024}KB)")

        # 通知
        try:
            from foundation.event_bus import event_bus, Event
            event_bus.emit(Event(
                type="foundation.save.created",
                data={"save_id": save_id, "world_id": world_id, "slot": slot_name},
                source="foundation.save_manager",
            ))
        except Exception:
            pass

        return save_info

    def load_game(
        self,
        world_id: int,
        slot_name: str = "auto",
        db_path: str | Path | None = None,
    ) -> bool:
        """加载存档

        Args:
            world_id: 世界 ID
            slot_name: 存档槽名称
            db_path: 目标数据库路径

        Returns:
            是否成功加载
        """
        if db_path is None:
            db_path = settings.database_path

        # 查找最新匹配的存档
        saves = self.list_saves(world_id=world_id)
        matching = [s for s in saves if s.slot_name == slot_name]

        if not matching:
            logger.error(f"未找到存档: world_id={world_id}, slot={slot_name}")
            return False

        # 取最新的
        matching.sort(key=lambda s: s.created_at, reverse=True)
        save_info = matching[0]

        src = Path(save_info.file_path)
        dest = Path(db_path)

        if not src.exists():
            logger.error(f"存档文件不存在: {src}")
            return False

        shutil.copy2(src, dest)
        logger.info(f"存档加载: {save_info.save_id} -> {dest}")

        try:
            from foundation.event_bus import event_bus, Event
            event_bus.emit(Event(
                type="foundation.save.loaded",
                data={"save_id": save_info.save_id, "world_id": world_id},
                source="foundation.save_manager",
            ))
        except Exception:
            pass

        return True

    def list_saves(self, world_id: int | None = None) -> list[SaveInfo]:
        """列出存档

        Args:
            world_id: 按世界 ID 过滤

        Returns:
            SaveInfo 列表
        """
        saves = []
        for f in sorted(self._save_dir.glob("world_*.db"), reverse=True):
            # 解析文件名: world_{world_id}_{slot}_{timestamp}.db
            parts = f.stem.split("_")
            if len(parts) >= 4:
                w_id = int(parts[1])
                slot = parts[2]
                if world_id is not None and w_id != world_id:
                    continue
                saves.append(SaveInfo(
                    save_id=f.stem,
                    world_id=w_id,
                    slot_name=slot,
                    created_at=datetime.fromtimestamp(f.stat().st_ctime).isoformat(),
                    file_path=str(f),
                    file_size=f.stat().st_size,
                ))
        return saves

    def delete_save(self, save_id: str) -> bool:
        """删除存档"""
        path = self._save_dir / f"{save_id}.db"
        if path.exists():
            path.unlink()
            logger.info(f"存档删除: {save_id}")
            return True
        return False
```

8.2 创建 `2workbench/foundation/cache.py`（泛化现有版本）：

```python
# 2workbench/foundation/cache.py
"""通用 LRU 缓存 — 泛化版本

改进点（相比现有版本）:
1. 泛化为通用缓存（不限于 LLM）
2. 支持按前缀批量失效
3. 支持缓存统计
"""
from __future__ import annotations

import hashlib
import json
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

    def _make_key(self, key: str, **kwargs) -> str:
        """生成缓存键（支持附加参数）"""
        if not kwargs:
            return key
        raw = json.dumps(kwargs, sort_keys=True, default=str)
        hash_part = hashlib.md5(raw.encode()).hexdigest()[:8]
        return f"{key}:{hash_part}"

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
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
        keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._cache[key]
        if keys_to_delete:
            logger.debug(f"缓存失效: prefix={prefix}, count={len(keys_to_delete)}")
        return len(keys_to_delete)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.debug("缓存已清空")

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
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
```

8.3 创建 `2workbench/foundation/resource_manager.py`：

```python
# 2workbench/foundation/resource_manager.py
"""资源管理器 — 文件系统操作

提供安全的文件读写、目录扫描、资源类型检测等功能。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from foundation.logger import get_logger

logger = get_logger(__name__)


# 文件类型 -> 资源类型映射
FILE_TYPE_MAP = {
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".py": "python",
    ".sql": "sql",
    ".env": "config",
    ".cfg": "config",
    ".ini": "config",
    ".toml": "config",
    ".qss": "stylesheet",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".svg": "image",
}


class ResourceManager:
    """资源管理器

    用法:
        rm = ResourceManager(base_path="./workspace")
        tree = rm.scan_directory()
        content = rm.read_file("npcs/张三.md")
        rm.write_file("npcs/新NPC.md", content)
    """

    def __init__(self, base_path: str | Path):
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    @property
    def base_path(self) -> Path:
        return self._base_path

    def scan_directory(
        self,
        relative_path: str = "",
        ignore_patterns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """扫描目录，返回文件/文件夹列表

        Args:
            relative_path: 相对于 base_path 的子目录
            ignore_patterns: 忽略的文件模式（如 ["__pycache__", "*.pyc"]）

        Returns:
            [{"name": str, "type": "file/dir", "path": str, "resource_type": str}]
        """
        ignore = set(ignore_patterns or ["__pycache__", "*.pyc", ".git"])
        scan_dir = self._base_path / relative_path

        if not scan_dir.exists():
            return []

        items = []
        for item in sorted(scan_dir.iterdir()):
            # 跳过忽略项
            if any(item.match(p) for p in ignore):
                continue
            if item.name.startswith(".") and item.name != ".env":
                continue

            rel_path = str(item.relative_to(self._base_path))
            resource_type = ""

            if item.is_file():
                resource_type = FILE_TYPE_MAP.get(item.suffix.lower(), "unknown")

            items.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "path": rel_path,
                "resource_type": resource_type,
            })

        return items

    def read_file(self, relative_path: str, encoding: str = "utf-8") -> str:
        """读取文件内容"""
        full_path = self._resolve(relative_path)
        return full_path.read_text(encoding=encoding)

    def write_file(
        self,
        relative_path: str,
        content: str,
        encoding: str = "utf-8",
    ) -> str:
        """写入文件（自动创建目录）

        Returns:
            文件的完整路径
        """
        full_path = self._resolve(relative_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding=encoding)
        logger.debug(f"文件写入: {full_path}")
        return str(full_path)

    def delete_file(self, relative_path: str) -> bool:
        """删除文件"""
        full_path = self._resolve(relative_path)
        if full_path.exists():
            full_path.unlink()
            logger.debug(f"文件删除: {full_path}")
            return True
        return False

    def file_exists(self, relative_path: str) -> bool:
        """检查文件是否存在"""
        return self._resolve(relative_path).exists()

    def get_resource_type(self, relative_path: str) -> str:
        """获取资源类型"""
        suffix = Path(relative_path).suffix.lower()
        return FILE_TYPE_MAP.get(suffix, "unknown")

    def _resolve(self, relative_path: str) -> Path:
        """解析路径，防止目录遍历"""
        full = (self._base_path / relative_path).resolve()
        base = self._base_path.resolve()
        if not str(full).startswith(str(base)):
            raise ValueError(f"路径越界: {relative_path}")
        return full
```

8.4 创建 `2workbench/foundation/base/singleton.py` 和 `interfaces.py`：

```python
# 2workbench/foundation/base/singleton.py
"""单例基类"""
from __future__ import annotations

import threading
from typing import TypeVar

T = TypeVar("T")


class Singleton:
    """线程安全的单例基类

    用法:
        class MyService(Singleton):
            def __init__(self):
                self.data = {}

        instance = MyService()
    """
    _instances: dict[type, object] = {}
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                # 双重检查
                if cls not in cls._instances:
                    instance = super().__new__(cls)
                    cls._instances[cls] = instance
        return cls._instances[cls]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 子类需要自己的实例
        if cls not in Singleton._instances:
            pass  # 延迟到 __new__ 中创建
```

```python
# 2workbench/foundation/base/interfaces.py
"""核心接口定义 — 定义层间契约

所有跨层通信的接口都在这里定义，确保依赖方向正确。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ILLMClient(ABC):
    """LLM 客户端接口（Foundation 层提供，Feature 层使用）"""

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> dict[str, Any]:
        """对话"""
        ...

    @abstractmethod
    async def stream(self, messages: list[dict], **kwargs):
        """流式对话"""
        ...


class IGameStateProvider(ABC):
    """游戏状态提供者接口（Core 层定义，Feature 层实现）"""

    @abstractmethod
    def get_state(self, world_id: int) -> dict[str, Any]:
        """获取游戏状态"""
        ...

    @abstractmethod
    def update_state(self, world_id: int, changes: dict[str, Any]) -> bool:
        """更新游戏状态"""
        ...


class IMemoryStore(ABC):
    """记忆存储接口（Core 层定义，Feature 层实现）"""

    @abstractmethod
    def store(self, world_id: int, category: str, key: str, content: str, **meta) -> str:
        """存储记忆，返回记忆 ID"""
        ...

    @abstractmethod
    def recall(self, world_id: int, category: str | None = None, limit: int = 10) -> list[dict]:
        """检索记忆"""
        ...

    @abstractmethod
    def forget(self, memory_id: str) -> bool:
        """删除记忆"""
        ...


class IToolExecutor(ABC):
    """工具执行器接口（Feature 层定义，LangGraph 节点使用）"""

    @abstractmethod
    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """执行工具"""
        ...

    @abstractmethod
    def get_tools_schema(self) -> list[dict]:
        """获取工具 schema（OpenAI function calling 格式）"""
        ...


class INotificationSink(ABC):
    """通知接收器接口（Presentation 层实现，Foundation 层调用）"""

    @abstractmethod
    def notify(self, event_type: str, data: dict[str, Any]) -> None:
        """接收通知"""
        ...
```

8.5 创建 `2workbench/foundation/base/__init__.py`：

```python
# 2workbench/foundation/base/__init__.py
"""基类与接口"""
from foundation.base.singleton import Singleton
from foundation.base.interfaces import (
    ILLMClient,
    IGameStateProvider,
    IMemoryStore,
    IToolExecutor,
    INotificationSink,
)

__all__ = [
    "Singleton",
    "ILLMClient",
    "IGameStateProvider",
    "IMemoryStore",
    "IToolExecutor",
    "INotificationSink",
]
```

8.6 测试全部新模块：

```bash
cd 2workbench && python -c "
# Cache
from foundation.cache import LRUCache
cache = LRUCache(max_size=5, ttl_seconds=60)
cache.set('a', 1)
cache.set('b', 2)
assert cache.get('a') == 1
assert cache.get('missing') is None
cache.invalidate_prefix('a')
assert cache.get('a') is None
stats = cache.get_stats()
print(f'Cache stats: {stats}')

# ResourceManager
from foundation.resource_manager import ResourceManager
import tempfile, os
with tempfile.TemporaryDirectory() as tmpdir:
    rm = ResourceManager(tmpdir)
    rm.write_file('test/hello.md', '# Hello')
    assert rm.file_exists('test/hello.md')
    content = rm.read_file('test/hello.md')
    assert content == '# Hello'
    tree = rm.scan_directory()
    assert len(tree) == 1
    print(f'ResourceManager tree: {tree}')

# Singleton
from foundation.base.singleton import Singleton
class TestSingleton(Singleton):
    pass
s1 = TestSingleton()
s2 = TestSingleton()
assert s1 is s2
print('Singleton: OK')

# Interfaces
from foundation.base.interfaces import ILLMClient, IToolExecutor, IMemoryStore
print('Interfaces imported OK')

print('✅ Foundation 全部模块测试通过!')
"
```

**验收**:
- [ ] `foundation/save_manager.py` — 存档/读档/列出/删除，带 EventBus 通知
- [ ] `foundation/cache.py` — LRU + TTL + 前缀失效 + 统计
- [ ] `foundation/resource_manager.py` — 安全的文件操作 + 目录扫描
- [ ] `foundation/base/singleton.py` — 线程安全单例
- [ ] `foundation/base/interfaces.py` — 5 个核心接口定义
- [ ] 全部测试通过

---

### Step 9: Foundation 层集成测试

**目的**: 验证 Foundation 层所有模块可以正确协同工作。

**方案**:

9.1 创建 `2workbench/tests/test_foundation_integration.py`：

```python
# 2workbench/tests/test_foundation_integration.py
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
        ILLMClient, IGameStateProvider, IMemoryStore, IToolExecutor, INotificationSink
    )

    # 验证接口可以被继承
    class MockLLM(ILLMClient):
        async def chat(self, messages, **kwargs):
            return {"content": "mock"}

        async def stream(self, messages, **kwargs):
            yield {"type": "token", "content": "mock"}

    mock = MockLLM()
    assert isinstance(mock, ILLMClient)

    print("✅ test_interface_contracts")


if __name__ == "__main__":
    test_event_bus_cross_module()
    test_config_and_logger()
    test_database_and_save_manager()
    test_cache_with_resource_manager()
    test_llm_client_creation()
    test_interface_contracts()
    print("\n🎉 Foundation 层集成测试全部通过!")
```

9.2 运行集成测试：

```bash
cd 2workbench && python tests/test_foundation_integration.py
```

**验收**:
- [ ] 6 个集成测试全部通过
- [ ] EventBus 跨模块通信正常
- [ ] Config + Logger 协同工作
- [ ] Database + SaveManager 协同工作
- [ ] Cache + ResourceManager 协同工作
- [ ] LLM Client + ModelRouter 可创建
- [ ] 接口定义可被继承

---

### Step 10: 更新 pyproject.toml 依赖

**目的**: 确保 Foundation 层的所有依赖都在 `pyproject.toml` 中声明。

**方案**:

10.1 检查并更新 `pyproject.toml`，确保包含以下依赖：

```toml
[project]
dependencies = [
    # 现有依赖
    "PyQt6>=6.6",
    "qasync>=0.27",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "python-frontmatter>=1.0",
    "openai>=1.0",
    "tenacity>=8.0",
    "pyyaml>=6.0",
    # Foundation 层新增（确认是否已有）
    # uv sync 会自动安装
]
```

10.2 安装依赖：

```bash
uv sync
```

**验收**:
- [ ] `uv sync` 成功
- [ ] `python -c "from foundation import EventBus, Settings, get_logger, SaveManager, LRUCache, ResourceManager"` 成功
- [ ] `python -c "from foundation.llm import BaseLLMClient, OpenAICompatibleClient, ModelRouter"` 成功
- [ ] `python -c "from foundation.base import Singleton, ILLMClient, IToolExecutor"` 成功

---

## 注意事项

### 依赖方向检查

Foundation 层的代码**绝对不能** import 以下模块：
- `core.*` — Core 层
- `feature.*` — Feature 层
- `presentation.*` — Presentation 层
- `bridge.*` — 桥接层
- `widgets.*` — UI 组件

**唯一例外**: `foundation.database.init_db()` 需要读取 `core/models/schema.sql` 文件路径，这是**文件路径引用**而非代码 import，是允许的。

### 线程安全

- EventBus: 使用 `threading.Lock` 保护订阅列表
- Database: 每个线程独立连接（`get_thread_db()`）
- LLM Client: AsyncOpenAI 本身是线程安全的
- Cache: OrderedDict 不是线程安全的，如果需要跨线程使用需要加锁

### 测试策略

- 每个模块有独立测试
- 集成测试验证模块间协同
- 不 mock 外部依赖（LLM API），只测试客户端创建和消息转换

---

## 完成检查清单

- [ ] Step 1: 四层目录结构创建完成
- [ ] Step 2: EventBus 实现并测试通过
- [ ] Step 3: Config 多模型配置实现
- [ ] Step 4: Logger 结构化日志实现
- [ ] Step 5: Database 连接管理实现
- [ ] Step 6: LLM Client 多模型抽象实现
- [ ] Step 7: ModelRouter 配置驱动路由实现
- [ ] Step 8: SaveManager + Cache + ResourceManager + 基类实现
- [ ] Step 9: Foundation 层集成测试全部通过
- [ ] Step 10: pyproject.toml 依赖更新
