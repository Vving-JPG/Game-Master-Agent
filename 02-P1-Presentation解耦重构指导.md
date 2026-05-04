# P1 Presentation 解耦重构指导

> 优先级：🟡 高 | 预计工作量：4-6小时
> 前置条件：P0 修复完成
> 目标：Presentation 层仅负责 UI 渲染，所有业务逻辑通过 EventBus 或 Feature 层接口执行

---

## 核心原则

```
重构前：Presentation → 直接调用 feature.* / project_manager
重构后：Presentation → EventBus.emit(事件) → Feature 层监听并执行
```

### 事件命名规范

```
ui.{模块}.{动作}          # UI 发出的事件（请求）
feature.{模块}.{动作}      # Feature 发出的事件（通知）
```

示例：
- `ui.agent.run_requested` — UI 请求运行 Agent
- `feature.agent.turn_completed` — Feature 通知回合完成
- `ui.project.save_requested` — UI 请求保存项目
- `feature.project.saved` — Feature 通知保存完成

---

## 重构 1：MainWindow 解耦

**文件**：`presentation/main_window.py`

### 1.1 Agent 运行逻辑提取

**当前问题**：`_on_run_agent` 直接创建 `GMAgent` 实例并运行。

**步骤**：

**Step 1**：在 Feature 层定义 Agent 运行服务

```python
# 新建 feature/ai/agent_runner.py
from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger

logger = get_logger(__name__)

class AgentRunner:
    """Agent 运行管理器，监听 UI 请求并执行"""

    def __init__(self):
        self._current_agent = None
        self._setup_listeners()

    def _setup_listeners(self):
        event_bus.subscribe("ui.agent.run_requested", self._on_run)
        event_bus.subscribe("ui.agent.stop_requested", self._on_stop)

    def _on_run(self, event: Event):
        world_id = event.data.get("world_id")
        user_input = event.data.get("user_input")
        # 创建并运行 agent（纯异步）
        # 完成后发出 feature.agent.turn_completed 事件
```

**Step 2**：MainWindow 改为发送事件

```python
# presentation/main_window.py
def _on_run_agent(self):
    event_bus.emit(Event(
        type="ui.agent.run_requested",
        data={"world_id": self._world_id, "user_input": self._get_input()}
    ))
```

**Step 3**：MainWindow 监听结果事件更新 UI

```python
# presentation/main_window.py
self.subscribe("feature.agent.turn_completed", self._on_agent_result)
self.subscribe("feature.agent.stream_chunk", self._on_stream_chunk)
```

### 1.2 AgentThread 提取

**当前问题**：`AgentThread`（QThread 子类）内嵌在 main_window.py 中。

**步骤**：将 `AgentThread` 移至 `presentation/` 下独立文件

```python
# 新建 presentation/agent_thread.py
from PyQt6.QtCore import QThread, pyqtSignal
import asyncio

class AgentThread(QThread):
    """Presentation 层的异步任务线程 — 仅管理事件循环，不包含业务逻辑"""
    result_ready = pyqtSignal(dict)
    stream_chunk = pyqtSignal(str)

    def __init__(self, coro):
        super().__init__()
        self._coro = coro

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self._coro)
            self.result_ready.emit(result)
        finally:
            loop.close()
```

### 1.3 保存逻辑提取

**当前问题**：`_on_save` 直接调用 `project_manager.save_graph()` 等。

**步骤**：

```python
# presentation/main_window.py
def _on_save(self):
    event_bus.emit(Event(
        type="ui.project.save_requested",
        data={"project_path": self._current_project_path}
    ))
```

---

## 重构 2：GraphEditor 解耦

**文件**：`presentation/editor/graph_editor.py`

### 2.1 移除直接编译调用

**当前问题**：第669行直接调用 `graph_compiler.compile(graph_data)`。

**步骤**：

```python
# 修改前
from feature.ai.graph_compiler import graph_compiler
def _save_graph(self):
    graph_data = self._serialize_graph()
    project_manager.save_graph(graph_data)
    compiled = graph_compiler.compile(graph_data)  # ❌ 直接调用

# 修改后
def _save_graph(self):
    graph_data = self._serialize_graph()
    event_bus.emit(Event(
        type="ui.graph.save_requested",
        data={"graph_data": graph_data}
    ))
```

### 2.2 Feature 层监听保存事件

```python
# feature/ai/graph_compiler.py 中增加
event_bus.subscribe("ui.graph.save_requested", _on_save_requested)

def _on_save_requested(event: Event):
    graph_data = event.data["graph_data"]
    # 保存 + 编译
    compiled = graph_compiler.compile(graph_data)
    event_bus.emit(Event(type="feature.graph.compiled", data={"compiled": compiled}))
```

---

## 重构 3：ToolManager 解耦

**文件**：`presentation/editor/tool_manager.py`

### 3.1 移除直接工具注册

**当前问题**：第402行直接调用 `feature.ai.tools.register_tool()`。

**步骤**：

**Step 1**：将 `ToolDefinition` 和 `BUILTIN_TOOLS` 移至 Feature 层

```python
# 新建 feature/ai/tool_registry.py
from dataclasses import dataclass

@dataclass
class ToolDefinition:
    name: str
    description: str
    handler: callable
    category: str = "custom"

BUILTIN_TOOLS = [
    # ... 从 tool_manager.py 移入
]
```

**Step 2**：ToolManager 改为通过 EventBus 请求

```python
# presentation/editor/tool_manager.py
def _register_tool(self, tool_def: dict):
    event_bus.emit(Event(
        type="ui.tool.register_requested",
        data=tool_def
    ))
```

### 3.2 移除直接工具测试

```python
# 修改前
from feature.ai.tools import get_all_tools, set_tool_context, ToolContext

# 修改后 — 通过 EventBus 请求测试
def _test_tool(self, tool_name: str, test_input: str):
    event_bus.emit(Event(
        type="ui.tool.test_requested",
        data={"tool_name": tool_name, "input": test_input}
    ))
self.subscribe("feature.tool.test_result", self._on_test_result)
```

---

## 重构 4：ProjectSelector 解耦

**文件**：`presentation/dialogs/project_selector.py`

### 4.1 提取项目文件操作到 ProjectManager

**当前问题**：`_scan_projects`、`_on_rename_project`、`_on_duplicate_project`、`_on_delete_project` 全部在 UI 中完成。

**步骤**：在 `feature/project/manager.py`（P0已移动）中增加方法

```python
# feature/project/manager.py
class ProjectManager:
    def scan_projects(self, workspace: str) -> list[dict]:
        """扫描工作目录下的所有项目"""
        ...

    def rename_project(self, project_path: str, new_name: str) -> str:
        """重命名项目，返回新路径"""
        ...

    def duplicate_project(self, project_path: str, new_name: str) -> str:
        """复制项目，返回新路径"""
        ...

    def delete_project(self, project_path: str) -> None:
        """删除项目"""
        ...
```

**UI 层改为**：

```python
# presentation/dialogs/project_selector.py
def _scan_projects(self):
    projects = project_manager.scan_projects(self._workspace)
    self._update_project_list(projects)

def _on_rename_project(self):
    new_path = project_manager.rename_project(self._selected_path, new_name)
    self._refresh()
```

---

## 重构 5：DeployManager 解耦

**文件**：`presentation/ops/deploy/deploy_manager.py`

### 5.1 提取打包逻辑

```python
# 新建 feature/services/packager.py
class ProjectPackager:
    def package(self, project_path: str, output_path: str, options: dict) -> str:
        """打包项目为 ZIP，返回输出文件路径"""
        ...
```

### 5.2 提取服务启动逻辑

```python
# 新建 feature/services/server_launcher.py
class ServerLauncher:
    def start(self, host: str, port: int, project_path: str):
        """启动 HTTP 服务"""
        ...
```

---

## 重构 6：知识编辑器数据分离

**文件**：`presentation/ops/knowledge/knowledge_editor.py`

### 6.1 提取数据管理到 Feature 层

```python
# 新建 feature/knowledge/service.py
class KnowledgeService(BaseFeature):
    """知识库管理服务"""

    def get_npcs(self) -> list[dict]: ...
    def save_npc(self, npc_data: dict) -> None: ...
    def delete_npc(self, npc_id: str) -> None: ...
    # ... 同理 Location/Item/Quest
```

### 6.2 UI 仅负责展示和编辑

```python
# presentation/ops/knowledge/knowledge_editor.py
class NPCEditor(BaseWidget):
    def __init__(self):
        super().__init__()
        self.subscribe("feature.knowledge.npcs_updated", self._refresh_list)

    def _refresh_list(self, event: Event):
        self._npcs = event.data["npcs"]
        self._update_table()
```

---

## 重构 7：多Agent编排器数据分离

**文件**：`presentation/ops/multi_agent/orchestrator.py`

### 7.1 提取数据类和验证逻辑

```python
# 新建 feature/multi_agent/models.py
from pydantic import BaseModel

class AgentInstance(BaseModel):
    id: str
    name: str
    model: str = "deepseek-chat"

class ChainStep(BaseModel):
    agent_id: str
    next_agent_id: str | None = None

class ChainConfig(BaseModel):
    name: str
    steps: list[ChainStep]

    def validate_no_cycles(self) -> list[str]:
        """DFS 环检测算法"""
        ...
```

---

## 重构 8：安全面板逻辑分离

**文件**：`presentation/ops/safety/safety_panel.py`

### 8.1 提取过滤逻辑

```python
# 新建 feature/safety/content_filter.py
class ContentFilter(BaseFeature):
    def filter_text(self, text: str) -> str:
        """应用所有过滤规则"""
        ...

    def should_enable_rule(self, rule: dict) -> bool:
        """判断规则是否应启用"""
        ...
```

---

## 重构 9：EventBus Monkey-Patching 移除

**文件**：`presentation/ops/debugger/event_monitor.py`

### 9.1 使用订阅替代 monkey-patch

**当前问题**：第74行 `event_bus.emit = self._hooked_emit` 直接替换全局方法。

**步骤**：

**Step 1**：在 Foundation 层增加通配符订阅支持

```python
# foundation/event_bus.py — EventBus 类增加方法
def subscribe_all(self, handler: Callable) -> str:
    """订阅所有事件（用于调试/监控）"""
    return self.subscribe("*", handler)
```

**Step 2**：EventMonitor 改用订阅

```python
# presentation/ops/debugger/event_monitor.py
class EventMonitor(BaseWidget):
    def __init__(self):
        super().__init__()
        self._sub_id = event_bus.subscribe_all(self._on_any_event)

    def _on_any_event(self, event: Event):
        # 记录事件，更新 UI
        ...
```

---

## 验证清单

重构完成后，逐项验证：

- [ ] `grep -rn "from feature\." 2workbench/presentation/ | grep -v "__pycache__"` 仅包含 EventBus 订阅相关
- [ ] `grep -rn "project_manager\." 2workbench/presentation/ | grep -v "__pycache__"` 无直接业务调用
- [ ] `grep -rn "graph_compiler\." 2workbench/presentation/` 无结果
- [ ] `grep -rn "register_tool\|get_all_tools" 2workbench/presentation/` 无结果
- [ ] 所有 UI 操作通过 `event_bus.emit(Event(type="ui.*", ...))` 发起
- [ ] 所有业务结果通过 `self.subscribe("feature.*", handler)` 接收
- [ ] 应用正常启动，所有功能可用
