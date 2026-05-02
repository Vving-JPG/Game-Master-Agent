# P0: Foundation 层 — 四层架构基础设施

> 创建时间: 2026-05-01
> 对应代码: `d:\Game-Master-Agent\2workbench\foundation\`

---

## 1. 概述

### 1.1 架构定位

Foundation 层是四层架构的最底层：

```
Presentation → Feature → Core → Foundation
```

**设计原则**:
- 上层可以依赖下层，下层绝对不能引用上层
- 同层模块间通过 EventBus 通信，禁止直接依赖
- 无循环依赖、无跨层直调、无硬编码引用

### 1.2 模块清单

| 模块 | 文件 | 职责 | 全局单例 |
|------|------|------|----------|
| EventBus | `event_bus.py` | 同层/跨层事件通信 | `event_bus` |
| Config | `config.py` | 多模型配置管理 | `settings` |
| Logger | `logger.py` | 结构化日志+彩色输出 | - |
| Database | `database.py` | SQLite + WAL + 迁移 | - |
| LLM Client | `llm/base.py`, `openai_client.py` | 多模型抽象 | - |
| ModelRouter | `llm/model_router.py` | 智能模型路由 | `model_router` |
| SaveManager | `save_manager.py` | 版本化存档 | - |
| Cache | `cache.py` | LRU + TTL 缓存 | `llm_cache` |
| ResourceManager | `resource_manager.py` | 安全文件操作 | - |
| Base | `base/singleton.py`, `interfaces.py` | 单例基类+接口 | - |

---

## 2. 核心设计

### 2.1 EventBus 事件总线

**事件命名规范**: `layer.module.action`

```python
# Foundation 层事件
foundation.config.changed      # 配置变更
foundation.db.initialized      # 数据库初始化完成
foundation.llm.response        # LLM 响应完成
foundation.llm.error           # LLM 调用失败
foundation.llm.stream_token    # LLM 流式 token
foundation.save.created        # 存档创建
foundation.save.loaded         # 存档加载

# Core 层事件（P1 定义）
core.state.changed             # 游戏状态变更
core.state.snapshot            # 状态快照请求

# Feature 层事件（P3 定义）
feature.battle.started         # 战斗开始
feature.battle.ended           # 战斗结束
feature.quest.updated          # 任务状态更新

# Presentation 层事件（P4/P5 定义）
presentation.ui.refresh        # UI 刷新请求
presentation.ui.notification   # UI 通知
```

**使用示例**:
```python
from foundation.event_bus import event_bus, Event

# 订阅事件
event_bus.subscribe("foundation.llm.response", on_llm_response)

# 装饰器方式订阅
@event_bus.on("core.state.changed")
def handle_state_change(event: Event):
    world_id = event.get("world_id")
    
# 发布事件
event_bus.emit(Event(
    type="foundation.llm.response",
    data={"content": "你好", "tokens": 100},
    source="feature.dialogue"
))
```

**特性**:
- 支持 sync/async 两种事件处理
- 支持优先级（HIGHEST/HIGH/NORMAL/LOW/LOWEST）
- 支持过滤器 `filter_fn`
- 支持一次性订阅 `once=True`
- 支持通配符 `*` 订阅所有事件

### 2.2 Config 配置管理

**多模型配置**:
```python
from foundation.config import settings

# 获取默认供应商配置
config = settings.get_provider_config()  # 默认 deepseek

# 获取指定供应商配置
openai_config = settings.get_provider_config("openai")

# 获取已配置的供应商列表
available = settings.get_available_providers()  # ["deepseek", "openai"]
```

**环境变量映射**:
```env
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

DEFAULT_PROVIDER=deepseek
```

### 2.3 Logger 日志系统

**特性**:
- 控制台彩色输出
- 文件结构化日志 + 轮转
- 支持 `extra` 字段传递上下文

```python
from foundation.logger import get_logger, setup_logging

setup_logging("DEBUG")
logger = get_logger(__name__)

logger.info("Agent 启动", extra={"world_id": "1", "turn": 5})
logger.error("LLM 调用失败", exc_info=True)
```

### 2.4 Database 数据库连接

**特性**:
- SQLite WAL 模式提升并发
- Row 工厂支持字典式访问
- 线程安全（每个线程独立连接）
- 版本号管理支持迁移

```python
from foundation.database import get_db, get_connection, init_db

# 上下文管理器（自动 commit/rollback）
with get_db() as db:
    db.execute("INSERT INTO ...")
    # 自动 commit

# 获取线程本地连接
conn = get_thread_db()

# 初始化数据库（执行 schema.sql）
init_db()
```

### 2.5 LLM Client 多模型抽象

**数据类**:
```python
from foundation.llm import LLMMessage, LLMResponse, StreamEvent

msg = LLMMessage(role="user", content="你好")
```

**OpenAI 兼容客户端**:
```python
from foundation.llm import OpenAICompatibleClient

client = OpenAICompatibleClient(
    provider_name="deepseek",
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
    model="deepseek-chat",
)

# 异步对话
response = await client.chat_async(messages)

# 流式对话
async for event in client.stream(messages):
    if event.type == "token":
        print(event.content)
```

### 2.6 ModelRouter 模型路由

**路由策略**:
1. 显式指定 → 跳过路由
2. 规则匹配 → 关键词+事件类型+对话长度评分
3. 默认回退 → `settings.default_provider`

```python
from foundation.llm import model_router

# 自动路由
client, config = model_router.route(content="战斗开始！")

# 显式指定
client, config = model_router.route(provider="openai", model="gpt-4o")
```

**默认规则**:
| 规则名 | 触发条件 | 目标模型 |
|--------|----------|----------|
| critical_narrative | 关键词: 战斗/boss/决战/死亡/结局... | deepseek-reasoner |
| npc_deep_dialogue | 关键词: 关系/信任/背叛/秘密... | deepseek-reasoner |
| standard_narrative | 默认 | deepseek-chat |

### 2.7 SaveManager 存档管理

```python
from foundation.save_manager import SaveManager

sm = SaveManager()

# 创建存档
save_info = sm.save_game(
    world_id=1,
    slot_name="auto",
    description="自动存档"
)

# 加载存档
sm.load_game(world_id=1, slot_name="auto")

# 列出存档
saves = sm.list_saves(world_id=1)
```

### 2.8 Cache LRU 缓存

```python
from foundation.cache import LRUCache

cache = LRUCache(max_size=200, ttl_seconds=600)

# 设置/获取
cache.set("key", "value")
value = cache.get("key")

# 按前缀失效
cache.invalidate_prefix("pregen:")

# 统计
stats = cache.get_stats()
```

### 2.9 ResourceManager 资源管理

```python
from foundation.resource_manager import ResourceManager

rm = ResourceManager(base_path="./workspace")

# 扫描目录
tree = rm.scan_directory()

# 读写文件
rm.write_file("npcs/张三.md", "# 张三")
content = rm.read_file("npcs/张三.md")
```

### 2.10 Base 基类与接口

**单例基类**:
```python
from foundation.base import Singleton

class MyService(Singleton):
    pass

s1 = MyService()
s2 = MyService()
assert s1 is s2  # True
```

**核心接口**:
```python
from foundation.base import (
    ILLMClient,           # LLM 客户端接口
    IGameStateProvider,   # 游戏状态提供者
    IMemoryStore,         # 记忆存储
    IToolExecutor,        # 工具执行器
    INotificationSink,    # 通知接收器
)
```

---

## 3. 依赖方向检查

Foundation 层**绝对不能** import:
- `core.*` — Core 层
- `feature.*` — Feature 层
- `presentation.*` — Presentation 层
- `bridge.*` — 桥接层
- `widgets.*` — UI 组件

**唯一例外**: `foundation.database.init_db()` 读取 `core/models/schema.sql` 文件路径，这是**文件路径引用**而非代码 import。

---

## 4. 测试

### 4.1 单元测试

```bash
cd 2workbench
python tests/test_event_bus.py
```

### 4.2 集成测试

```bash
python tests/test_foundation_integration.py
```

### 4.3 导入测试

```python
from foundation import (
    EventBus, event_bus,
    Settings, settings,
    get_logger, setup_logging,
    get_db_path, get_db, init_db,
    SaveManager, LRUCache, ResourceManager
)

from foundation.llm import (
    BaseLLMClient, LLMMessage, LLMResponse, StreamEvent,
    OpenAICompatibleClient, ModelRouter, model_router
)

from foundation.base import (
    Singleton, ILLMClient, IGameStateProvider,
    IMemoryStore, IToolExecutor, INotificationSink
)
```

---

## 5. 关键设计决策

### 5.1 为什么使用 EventBus 而不是直接调用？

**问题**: 同层模块间如何通信？

**方案对比**:
| 方案 | 优点 | 缺点 |
|------|------|------|
| 直接 import | 简单直观 | 强耦合，难以测试 |
| 依赖注入 | 解耦 | 需要传递大量依赖 |
| **EventBus** | 完全解耦，支持异步，可过滤 | 需要约定事件格式 |

**结论**: 使用 EventBus，事件格式按 `layer.module.action` 约定。

### 5.2 为什么 LLM Client 要抽象基类？

**问题**: 如何支持多供应商（DeepSeek/OpenAI/Anthropic）？

**方案**:
- 所有供应商使用 OpenAI 兼容 API 格式
- 通过 `base_url` 和 `api_key` 区分
- 统一接口 `chat_async()` 和 `stream()`
- 支持 `reasoning_content`（DeepSeek Reasoner 特有）

### 5.3 为什么 ModelRouter 使用规则评分？

**问题**: 如何选择合适的模型？

**方案**:
- 关键词匹配 + 基础分
- 支持显式指定（跳过路由）
- 支持动态添加规则
- 默认回退保证可用性

---

## 6. 下一步

P0 Foundation 层完成后，继续：

- **P1**: Core 层 — 纯数据 + 纯规则
  - `core/state.py` — LangGraph State 定义
  - `core/models/` — Pydantic 数据类
  - `core/constants/` — 常量定义
  - `core/calculators/` — 纯函数计算器

- **P2**: Feature 层 — 业务功能
  - `feature/battle/` — 战斗系统
  - `feature/dialogue/` — 对话系统
  - `feature/quest/` — 任务系统
  - ...

- **P3**: AI 层 — LangGraph 编排
  - `feature/ai/` — AI 编排

- **P4/P5**: Presentation 层 — UI 系统
  - `presentation/` — PyQt6 UI

---

*最后更新: 2026-05-01*
