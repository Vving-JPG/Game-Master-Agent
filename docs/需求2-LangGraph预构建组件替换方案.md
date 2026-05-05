# 需求2：LangGraph 预构建组件替换方案

> 目标：用 LangGraph 官方生态组件替换自研模块，减少维护量，提升稳定性
> 前置条件：需求1（全面审查修复）执行完成后再执行本方案

---

## 一、替换总览

| 优先级 | 自研模块 | 替换为 | 收益 |
|--------|----------|--------|------|
| 🔴 1 | `MemoryRepo`（简单截断） | `langgraph-checkpoint` + `langmem` | 自动持久化、中断恢复、时间衰减记忆 |
| 🔴 2 | `graph_editor.py`（只读查看器） | LangGraph Studio | 官方可视化 IDE，实时调试 |
| 🟡 3 | `nodes.py` 手写 Agent 循环 | `create_react_agent`（可选） | 代码量从 ~480 行降到 ~100 行 |
| 🟡 4 | `tools/registry.py` | `langchain-mcp-adapters` | 标准化工具接口 |
| 🔵 5 | `multi_agent_service.py`（空壳） | `langgraph-supervisor` | 开箱即用的多 Agent 编排 |

---

## 二、替换 1：记忆系统（收益最大）

### 2.1 安装依赖

```bash
pip install langgraph-checkpoint langgraph-checkpoint-sqlite langmem
```

### 2.2 当前实现分析

你的记忆系统分散在多处：

| 文件 | 当前实现 | 问题 |
|------|----------|------|
| `core/models/repository.py` → `MemoryRepo` | SQLite CRUD，`compress()` 简单截断旧记忆 | 无语义理解，截断丢失信息 |
| `feature/ai/nodes.py` → `node_build_prompt` | 手动从 MemoryRepo 读取记忆拼接到 prompt | 无衰减、无优先级 |
| `core/state.py` → `AgentState` | `messages: list` 仅当前会话 | 无跨会话持久化 |
| `feature/ai/gm_agent.py` → `GMAgent` | 每次运行创建新的 state | 无状态恢复 |

### 2.3 替换方案

#### 短期记忆：Checkpointer

```python
# 新建 feature/ai/checkpoint_config.py
from langgraph.checkpoint.sqlite import SqliteSaver

def get_checkpointer(project_path: str):
    """为每个项目创建独立的 checkpointer"""
    db_path = project_path / "data" / "checkpoint.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(db_path))
```

#### 长期记忆：BaseStore

```python
# 新建 feature/ai/memory_store.py
from langgraph.store.memory import InMemoryStore
# 或持久化版本：
# from langgraph.store.sqlite import SqliteStore

def get_memory_store(project_path: str):
    """长期记忆存储 — 跨会话持久化"""
    return InMemoryStore()
    # 生产环境用：
    # return SqliteStore.from_conn_string(str(project_path / "data" / "memory.db"))
```

#### 智能记忆管理：langmem

```python
# 新建 feature/ai/memory_manager.py
from langmem import create_memory_manager

def get_memory_manager(model_name: str = "deepseek-chat"):
    """创建智能记忆管理器 — 自动提取、衰减、语义检索"""
    return create_memory_manager(
        model=model_name,
        namespaces=["player_preferences", "world_state", "story_events"],
    )
```

#### 修改 GMAgent 集成

```python
# feature/ai/gm_agent.py 修改
from feature.ai.checkpoint_config import get_checkpointer
from feature.ai.memory_store import get_memory_store

class GMAgent:
    def __init__(self, project_path: str):
        self._checkpointer = get_checkpointer(project_path)
        self._store = get_memory_store(project_path)
        self._thread_id = "main_session"

    def compile_graph(self, graph_builder):
        """编译图时注入 checkpointer 和 store"""
        self._graph = graph_builder.compile(
            checkpointer=self._checkpointer,
            store=self._store,
        )
        return self._graph

    async def run(self, user_input: str):
        """运行 Agent — 自动从 checkpoint 恢复状态"""
        config = {"configurable": {"thread_id": self._thread_id}}

        # 短期记忆：checkpoint 自动恢复 messages
        # 长期记忆：通过 store 获取跨会话信息
        result = await self._graph.ainvoke(
            {"current_event": user_input},
            config=config,
        )
        return result

    async def run_stream(self, user_input: str):
        """流式运行 — 支持中断"""
        config = {"configurable": {"thread_id": self._thread_id}}
        async for event in self._graph.astream_events(
            {"current_event": user_input},
            config=config,
            version="v2",
        ):
            yield event

    def get_state(self):
        """获取当前状态 — 用于调试面板"""
        config = {"configurable": {"thread_id": self._thread_id}}
        return self._graph.get_state(config)

    def resume(self):
        """从断点恢复 — TRPG 长剧情非常有用"""
        config = {"configurable": {"thread_id": self._thread_id}}
        return self._graph.ainvoke(None, config)
```

#### 修改 nodes.py 使用 Store

```python
# feature/ai/nodes.py 修改
from langgraph.config import get_store

async def node_build_prompt(state: AgentState, config: dict):
    """构建提示词 — 使用 Store 获取长期记忆"""
    store = get_store(config)

    # 获取玩家偏好（跨会话）
    player_prefs = store.search(("player_preferences",))
    # 获取世界状态
    world_state = store.search(("world_state",))
    # 获取相关故事事件（语义检索）
    story_events = store.search(("story_events",), query=state.get("current_event", ""))

    # 构建系统提示词
    system_prompt = _build_system_prompt(player_prefs, world_state, story_events)
    # ... 后续逻辑不变
```

### 2.4 删除的代码

替换完成后可删除：
- `core/models/repository.py` 中的 `MemoryRepo` 类
- `feature/ai/nodes.py` 中手动调用 `MemoryRepo` 的代码
- `feature/ai/prompt_builder.py` 中 `_format_game_state` 的手动记忆拼接

### 2.5 保留的代码

- `core/state.py` → `AgentState`：保留，LangGraph 需要 TypedDict 定义
- `feature/ai/nodes.py` 中的节点函数：保留，只是记忆获取方式改变

---

## 三、替换 2：图可视化（LangGraph Studio）

### 3.1 安装

```bash
pip install langgraph-cli
```

### 3.2 配置

在项目根目录创建 `langgraph.json`：

```json
{
  "graphs": {
    "gm_agent": "./2workbench/feature/ai/graph.py:gm_graph"
  },
  "dependencies": ["./2workbench"]
}
```

### 3.3 启动

```bash
cd /path/to/Game-Master-Agent
langgraph dev
```

浏览器打开 `http://localhost:8123` 即可看到可视化图。

### 3.4 删除的代码

- `presentation/editor/graph_editor.py` — 整个文件删除
- `main_window.py` 中所有 `_graph_viewer` / `_graph_editor` 相关代码

### 3.5 注意事项

- LangGraph Studio 需要图能独立导入和编译
- 如果图的编译依赖 `project_manager` 等运行时状态，需要提供 mock 或默认值
- Studio 是开发时工具，最终用户不需要安装

---

## 四、替换 3：Agent 循环简化（可选）

### 4.1 评估

你当前的 `nodes.py` 有 ~480 行，手写了完整的 Agent 循环。`create_react_agent` 可以简化但有限制：

| 维度 | 手写（当前） | create_react_agent |
|------|-------------|-------------------|
| 灵活性 | 完全自定义 | 受限于预定义模式 |
| 游戏逻辑 | 可嵌入战斗/对话/任务等 | 需要通过工具间接实现 |
| 代码量 | ~480 行 | ~100 行 |
| 调试 | 完全可控 | 黑盒程度较高 |

### 4.2 建议

**暂不替换**。原因：
1. 你的 Agent 不是标准 ReAct 模式（有游戏状态机、条件分支、多节点协作）
2. TRPG 的游戏逻辑需要精细控制每个节点的行为
3. 手写节点更符合四层架构（Core 定义状态，Feature 定义节点）

**但可以借鉴**：`create_react_agent` 的工具调用循环和错误处理模式，优化你现有代码。

---

## 五、替换 4：工具注册标准化（可选）

### 5.1 安装

```bash
pip install langchain-mcp-adapters
```

### 5.2 当前问题

你的 `tools/registry.py` 自定义了一套工具注册机制，与社区标准不兼容。

### 5.3 替换方案

```python
# feature/ai/tools/mcp_adapter.py
from langchain_mcp_adapters import create_mcp_tools

async def register_tools_from_mcp(server_config: dict):
    """通过 MCP 协议注册工具"""
    tools = await create_mcp_tools(server_config)
    return tools
```

### 5.4 建议

**阶段 4 解耦完成后再考虑**。当前工具系统与游戏逻辑深度耦合，直接替换风险较高。

---

## 六、替换 5：多 Agent 编排（远期）

### 6.1 安装

```bash
pip install langgraph-supervisor
```

### 6.2 当前状态

你的 `multi_agent_service.py` 是空壳实现（只有数据管理，没有执行引擎）。

### 6.3 建议

**远期考虑**。当前项目是单 Agent + 多游戏系统，暂不需要多 Agent 协作。如果未来需要（比如多个 NPC 各自有独立 AI），再引入 `langgraph-supervisor`。

---

## 七、执行顺序

```
步骤 1：pip install langgraph-checkpoint langgraph-checkpoint-sqlite langmem
步骤 2：创建 checkpoint_config.py + memory_store.py + memory_manager.py
步骤 3：修改 GMAgent 集成 checkpointer + store
步骤 4：修改 nodes.py 使用 Store 获取记忆
步骤 5：测试 — 运行 Agent，确认状态自动保存和恢复
步骤 6：pip install langgraph-cli
步骤 7：创建 langgraph.json，启动 Studio 验证
步骤 8：删除 graph_editor.py 及相关代码
步骤 9：清理 MemoryRepo 等被替代的代码
```
