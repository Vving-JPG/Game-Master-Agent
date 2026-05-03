# P7: LangGraph 可视化集成 — GraphCompiler + 运行时高亮 + 图编辑器增强

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。
> **前置条件**: P0-P6 已全部完成。本 Phase 基于现有代码进行增量修改。

## 项目概述

你正在修复 **Game Master Agent IDE** 中 LangGraph 可视化与实际执行之间的**断裂问题**。

### 当前问题

```
graph.json ←→ 图编辑器 ✅ 已连通（可视化编辑）
LangGraph  ←→ GMAgent  ✅ 已连通（Agent 执行）
graph.json ←→ LangGraph ❌ 完全断开
运行时高亮 ←→ EventBus  ❌ 代码写了但没接线
条件边     ←→ graph.json ❌ 不支持 condition 字段
```

具体表现：
1. `graph.py` 中 `build_gm_graph()` 硬编码了 6 个节点，`gm_graph = build_gm_graph()` 在模块加载时就编译好了，**永远不读 graph.json**
2. `gm_agent.py` 直接 `from .graph import gm_graph`，不接收外部图定义
3. 图编辑器保存的 graph.json **没人读**，只是装饰品
4. `set_running_node()` 已实现但**没有代码订阅 EventBus 节点事件来调用它**
5. LangGraph 有 `route_after_llm` 和 `route_after_parse` 两个条件路由，但 graph.json 的 edges 格式**不支持条件分支**

### 修复目标

```
graph.json ←→ GraphCompiler ←→ LangGraph StateGraph ←→ GMAgent
     ↑                                        ↓
  图编辑器                              EventBus 节点事件
     ↓                                        ↓
  保存/加载                           运行时高亮（已接线）
```

### 本 Phase 范围

1. **GraphCompiler** — graph.json → StateGraph 编译器
2. **GMAgent 改造** — 支持从 graph.json 编译的图运行
3. **运行时高亮接线** — EventBus 节点事件 → 图编辑器高亮
4. **条件边可视化** — graph.json 支持 condition 字段，图编辑器支持条件边渲染
5. **graph_editor.py 增强** — 保存时触发编译、条件边绘制、节点选中联动右侧属性面板
6. **TRPG 模板更新** — 添加 condition 字段，与实际 LangGraph 图结构一致
7. **集成测试**

### 现有代码（必须基于这些文件修改）

| 文件 | 当前状态 | 需要修改 |
|------|---------|---------|
| `feature/ai/graph.py` | 硬编码 6 节点 + 2 条件路由 | 保留作为默认回退，新增 `build_graph_from_json()` |
| `feature/ai/gm_agent.py` | `from .graph import gm_graph` | 改为支持动态图，优先使用 graph.json 编译 |
| `feature/ai/nodes.py` | 6 节点函数 + 2 路由函数，已发出 `create_node_event` | 不修改（事件已正确发出） |
| `feature/ai/__init__.py` | 导出 `gm_graph, build_gm_graph` | 新增导出 `graph_compiler` |
| `presentation/editor/graph_editor.py` | `_save_graph` 未完整实现，无运行时高亮接线 | 完善保存、接线高亮、条件边渲染 |
| `presentation/project/manager.py` | `save_graph`/`load_graph` 只操作文件 | 新增 `compile_graph()` 方法 |
| `presentation/main_window.py` | `CenterPanel` 管理图编辑器标签页 | 接线运行时高亮 |
| `core/state.py` | `AgentState` TypedDict | 不修改 |

---

## 行为准则

1. **一步一步执行**：严格按照步骤顺序
2. **增量修改**：不重写文件，只修改必要的部分
3. **先验证再继续**：每个步骤都有验收标准
4. **Windows 兼容**：使用 `New-Item` 创建目录，`;` 连接命令
5. **复杂测试写成独立 .py 文件**，执行后删除

---

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **工作目录**: `2workbench/`

---

## 步骤

### Step 1: 创建 GraphCompiler — graph.json → StateGraph

**目的**: 创建编译器，将 graph.json 的 JSON 定义编译为 LangGraph StateGraph。

**现有代码参考**:
- `feature/ai/graph.py` — 硬编码的图构建逻辑（需要复用其中的节点函数和路由函数）
- `feature/ai/nodes.py` — 6 个节点函数 + 2 个条件路由函数

**方案**:

1.1 创建 `2workbench/feature/ai/graph_compiler.py`：

```python
# 2workbench/feature/ai/graph_compiler.py
"""GraphCompiler — 将 graph.json 编译为 LangGraph StateGraph

graph.json 格式:
{
  "nodes": [
    {"id": "handle_event", "type": "event", "label": "事件处理", "position": {"x": 100, "y": 200}},
    {"id": "llm_reasoning", "type": "llm", "label": "LLM 推理", "position": {"x": 500, "y": 200}},
    ...
  ],
  "edges": [
    {"from": "__start__", "to": "handle_event"},
    {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"},
    {"from": "parse_output", "to": "update_memory"},
    {"from": "update_memory", "to": "__end__"},
    ...
  ]
}

节点类型 → 节点函数映射:
  event    → node_handle_event
  prompt   → node_build_prompt
  llm      → node_llm_reasoning
  parser   → node_parse_output
  executor → node_execute_commands
  memory   → node_update_memory
  input    → node_handle_event      (复用)
  output   → node_update_memory     (复用)
  custom   → 需要用户注册

条件路由映射:
  route_after_llm   → llm_reasoning 后的路由（有 tool_calls → execute_commands, 否则 → parse_output）
  route_after_parse → parse_output 后的路由（有命令 → execute_commands, 否则 → update_memory）
"""
from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import StateGraph, START, END

from core.state import AgentState
from foundation.logger import get_logger

logger = get_logger(__name__)


# 节点类型 → 节点函数映射
NODE_FUNCTIONS: dict[str, Callable] = {}

# 条件路由函数映射
CONDITION_FUNCTIONS: dict[str, Callable] = {}

# 条件路由的分支映射（路由函数返回值 → 目标节点）
CONDITION_BRANCHES: dict[str, dict[str, str]] = {}


def _init_mappings():
    """延迟初始化映射，避免循环导入"""
    global NODE_FUNCTIONS, CONDITION_FUNCTIONS, CONDITION_BRANCHES

    if NODE_FUNCTIONS:
        return  # 已初始化

    from feature.ai.nodes import (
        node_handle_event,
        node_build_prompt,
        node_llm_reasoning,
        node_parse_output,
        node_execute_commands,
        node_update_memory,
        route_after_llm,
        route_after_parse,
    )

    NODE_FUNCTIONS = {
        "event": node_handle_event,
        "prompt": node_build_prompt,
        "llm": node_llm_reasoning,
        "parser": node_parse_output,
        "executor": node_execute_commands,
        "memory": node_update_memory,
        "input": node_handle_event,
        "output": node_update_memory,
    }

    CONDITION_FUNCTIONS = {
        "route_after_llm": route_after_llm,
        "route_after_parse": route_after_parse,
    }

    # 每个条件路由函数的返回值 → 目标节点名的默认映射
    CONDITION_BRANCHES = {
        "route_after_llm": {
            "execute_commands": "execute_commands",
            "parse_output": "parse_output",
        },
        "route_after_parse": {
            "execute_commands": "execute_commands",
            "update_memory": "update_memory",
        },
    }


class GraphCompiler:
    """将 graph.json 编译为 LangGraph StateGraph"""

    def compile(self, graph_data: dict) -> Any:
        """编译图定义为 CompiledStateGraph

        Args:
            graph_data: graph.json 的内容，格式:
                {
                    "nodes": [{"id": str, "type": str, "label": str, "position": dict}, ...],
                    "edges": [{"from": str, "to": str, "condition": str|None}, ...]
                }

        Returns:
            编译好的 CompiledGraph

        Raises:
            ValueError: 图定义无效（缺少必要节点、未知节点类型等）
        """
        _init_mappings()

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            raise ValueError("图定义不能为空：没有节点")

        # 创建 StateGraph
        graph = StateGraph(AgentState)

        # 收集所有节点 ID
        node_ids = set()

        # 添加节点
        for node_data in nodes:
            node_id = node_data["id"]
            node_type = node_data.get("type", "custom")
            node_func = NODE_FUNCTIONS.get(node_type)

            if node_func is None:
                logger.warning(f"未知节点类型 '{node_type}' (节点: {node_id})，跳过")
                continue

            graph.add_node(node_id, node_func)
            node_ids.add(node_id)
            logger.debug(f"编译节点: {node_id} ({node_type} → {node_func.__name__})")

        # 添加边
        for edge_data in edges:
            source = edge_data["from"]
            target = edge_data["to"]
            condition = edge_data.get("condition", "")

            # 处理 START/END 特殊标记
            actual_source = source
            actual_target = target
            if source in ("START", "__start__"):
                actual_source = START
            if target in ("END", "__end__"):
                actual_target = END

            if condition and condition in CONDITION_FUNCTIONS:
                # 条件边
                route_func = CONDITION_FUNCTIONS[condition]
                branches = CONDITION_BRANCHES.get(condition, {})

                # 如果边指定了具体目标，覆盖默认分支
                # 格式: {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"}
                # 含义: 当 route_after_llm 返回 "parse_output" 时，走这条边
                if isinstance(actual_target, str) and actual_target not in (START, END):
                    # 单分支条件边：只有返回值匹配 target 时走这条边
                    # 需要收集同一 source 的所有条件边来构建完整映射
                    pass  # 在下面统一处理

                graph.add_conditional_edges(
                    actual_source,
                    route_func,
                    branches,
                )
                logger.debug(f"编译条件边: {source} --[{condition}]--> {branches}")
            else:
                # 普通边
                graph.add_edge(actual_source, actual_target)
                logger.debug(f"编译边: {source} --> {target}")

        # 编译
        compiled = graph.compile()
        node_count = len(node_ids)
        edge_count = len(edges)
        logger.info(f"图编译完成: {node_count} 节点, {edge_count} 边")
        return compiled


# 全局单例
graph_compiler = GraphCompiler()
```

1.2 测试：

```bash
cd 2workbench ; python -c "
from feature.ai.graph_compiler import graph_compiler

# 测试 TRPG 模板图编译
trpg_graph = {
    'nodes': [
        {'id': 'handle_event', 'type': 'event', 'label': '事件处理', 'position': {'x': 100, 'y': 200}},
        {'id': 'build_prompt', 'type': 'prompt', 'label': 'Prompt 组装', 'position': {'x': 300, 'y': 200}},
        {'id': 'llm_reasoning', 'type': 'llm', 'label': 'LLM 推理', 'position': {'x': 500, 'y': 200}},
        {'id': 'parse_output', 'type': 'parser', 'label': '命令解析', 'position': {'x': 700, 'y': 150}},
        {'id': 'execute_commands', 'type': 'executor', 'label': '命令执行', 'position': {'x': 700, 'y': 250}},
        {'id': 'update_memory', 'type': 'memory', 'label': '记忆更新', 'position': {'x': 900, 'y': 200}},
    ],
    'edges': [
        {'from': '__start__', 'to': 'handle_event'},
        {'from': 'handle_event', 'to': 'build_prompt'},
        {'from': 'build_prompt', 'to': 'llm_reasoning'},
        {'from': 'llm_reasoning', 'to': 'parse_output', 'condition': 'route_after_llm'},
        {'from': 'parse_output', 'to': 'update_memory', 'condition': 'route_after_parse'},
        {'from': 'execute_commands', 'to': 'update_memory'},
        {'from': 'update_memory', 'to': '__end__'},
    ],
}

compiled = graph_compiler.compile(trpg_graph)
assert compiled is not None
print(f'✅ TRPG 图编译成功')

# 测试 blank 模板图编译
blank_graph = {
    'nodes': [
        {'id': 'input', 'type': 'input', 'label': '用户输入', 'position': {'x': 100, 'y': 200}},
        {'id': 'reasoning', 'type': 'llm', 'label': 'LLM 推理', 'position': {'x': 400, 'y': 200}},
        {'id': 'output', 'type': 'output', 'label': '输出', 'position': {'x': 700, 'y': 200}},
    ],
    'edges': [
        {'from': '__start__', 'to': 'input'},
        {'from': 'input', 'to': 'reasoning'},
        {'from': 'reasoning', 'to': 'output'},
        {'from': 'output', 'to': '__end__'},
    ],
}

compiled2 = graph_compiler.compile(blank_graph)
assert compiled2 is not None
print(f'✅ Blank 图编译成功')

# 测试空图报错
try:
    graph_compiler.compile({'nodes': [], 'edges': []})
    assert False, '应该抛出 ValueError'
except ValueError:
    print('✅ 空图正确报错')

print('✅ GraphCompiler 测试通过')
"
```

**验收**:
- [ ] `graph_compiler.py` 创建完成
- [ ] TRPG 模板图（6 节点 + 条件边）编译成功
- [ ] Blank 模板图（3 节点）编译成功
- [ ] 空图抛出 ValueError
- [ ] 测试通过

---

### Step 2: 改造 GMAgent — 支持动态图

**目的**: 让 GMAgent 支持从 graph.json 编译的图运行，同时保留硬编码图作为回退。

**现有代码**: `feature/ai/gm_agent.py`
- 第 37 行: `from .graph import gm_graph`
- 第 96 行: `result = await gm_graph.ainvoke(input_state)`

**方案**:

2.1 修改 `feature/ai/gm_agent.py`：

将 `from .graph import gm_graph` 替换为动态图加载逻辑。

在文件顶部，找到：
```python
from .graph import gm_graph
```

替换为：
```python
# 默认硬编码图（回退用）
from .graph import gm_graph as _default_gm_graph
```

在 `GMAgent.__init__` 方法中，找到现有的 `__init__` 方法，在 `self._last_result: dict[str, Any] = {}` 之后添加：

```python
        # 图实例（优先使用 graph.json 编译的图）
        self._graph = _default_gm_graph
        self._graph_source = "default"  # default / json
```

在 `__init__` 方法末尾（`self._initial_state = self._load_initial_state()` 之后）添加：

```python
    def set_graph(self, compiled_graph: Any, source: str = "json") -> None:
        """设置 Agent 使用的图实例

        Args:
            compiled_graph: 编译好的 StateGraph
            source: 图来源标识（"json" 或 "default"）
        """
        self._graph = compiled_graph
        self._graph_source = source
        logger.info(f"Agent 图已更新: source={source}")
```

在 `run` 方法中，找到：
```python
            result = await gm_graph.ainvoke(input_state)
```

替换为：
```python
            result = await self._graph.ainvoke(input_state)
```

在 `get_state_snapshot` 方法中，在返回字典中添加 `graph_source`：

```python
    def get_state_snapshot(self) -> dict[str, Any]:
        """获取当前状态快照（用于 UI 显示）"""
        return {
            "world_id": self._world_id,
            "turn_count": self._initial_state.get("turn_count", 0),
            "execution_state": self._execution_state,
            "graph_source": self._graph_source,
            "player": self._initial_state.get("player", {}),
            "location": self._initial_state.get("current_location", {}),
            "npcs": self._initial_state.get("active_npcs", []),
        }
```

2.2 更新 `feature/ai/__init__.py`：

在文件中找到：
```python
from feature.ai.graph import gm_graph, build_gm_graph
```

在这行之后添加：
```python
from feature.ai.graph_compiler import graph_compiler
```

在 `__all__` 列表中添加 `"graph_compiler"`：
```python
__all__ = [
    "gm_graph", "build_gm_graph", "graph_compiler", "GMAgent",
    ...
]
```

2.3 测试：

```bash
cd 2workbench ; python -c "
from feature.ai.gm_agent import GMAgent

# 测试默认图
agent = GMAgent(world_id=1)
assert agent._graph is not None
assert agent._graph_source == 'default'
print(f'✅ GMAgent 默认图: source={agent._graph_source}')

# 测试 set_graph
from feature.ai.graph_compiler import graph_compiler
trpg_graph = {
    'nodes': [
        {'id': 'handle_event', 'type': 'event', 'label': '事件处理', 'position': {'x': 100, 'y': 200}},
        {'id': 'build_prompt', 'type': 'prompt', 'label': 'Prompt', 'position': {'x': 300, 'y': 200}},
        {'id': 'llm_reasoning', 'type': 'llm', 'label': 'LLM', 'position': {'x': 500, 'y': 200}},
        {'id': 'parse_output', 'type': 'parser', 'label': '解析', 'position': {'x': 700, 'y': 200}},
        {'id': 'execute_commands', 'type': 'executor', 'label': '执行', 'position': {'x': 700, 'y': 300}},
        {'id': 'update_memory', 'type': 'memory', 'label': '记忆', 'position': {'x': 900, 'y': 200}},
    ],
    'edges': [
        {'from': '__start__', 'to': 'handle_event'},
        {'from': 'handle_event', 'to': 'build_prompt'},
        {'from': 'build_prompt', 'to': 'llm_reasoning'},
        {'from': 'llm_reasoning', 'to': 'parse_output', 'condition': 'route_after_llm'},
        {'from': 'parse_output', 'to': 'update_memory', 'condition': 'route_after_parse'},
        {'from': 'execute_commands', 'to': 'update_memory'},
        {'from': 'update_memory', 'to': '__end__'},
    ],
}
compiled = graph_compiler.compile(trpg_graph)
agent.set_graph(compiled, source='json')
assert agent._graph_source == 'json'
assert agent._graph is compiled
print(f'✅ GMAgent 动态图: source={agent._graph_source}')

# 测试 state_snapshot 包含 graph_source
snapshot = agent.get_state_snapshot()
assert snapshot['graph_source'] == 'json'
print(f'✅ state_snapshot: {snapshot[\"graph_source\"]}')

# 测试导入
from feature.ai import graph_compiler
assert graph_compiler is not None
print('✅ graph_compiler 导出成功')

print('✅ GMAgent 改造测试通过')
"
```

**验收**:
- [ ] GMAgent 默认使用硬编码图（`_graph_source == "default"`）
- [ ] `set_graph()` 可切换到 graph.json 编译的图
- [ ] `run()` 方法使用 `self._graph` 而非全局 `gm_graph`
- [ ] `get_state_snapshot()` 包含 `graph_source`
- [ ] `graph_compiler` 可从 `feature.ai` 导入
- [ ] 测试通过

---

### Step 3: 运行时高亮接线

**目的**: 将 EventBus 的节点执行事件连接到图编辑器的 `set_running_node()`。

**现有代码**:
- `feature/ai/nodes.py` — 每个节点函数已调用 `create_node_event(node_id, "started"/"completed")`
- `presentation/editor/graph_editor.py` — `GraphScene.set_running_node(node_id)` 已实现
- `presentation/main_window.py` — `CenterPanel` 管理图编辑器，但未订阅节点事件

**方案**:

3.1 在 `presentation/editor/graph_editor.py` 的 `GraphEditorWidget` 类中，找到 `_setup_ui` 方法的末尾（`layout.addWidget(self._view)` 之后），添加 EventBus 订阅：

```python
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ... 现有的工具栏和场景代码 ...

        # 场景和视图
        self._scene = GraphScene()
        self._view = GraphEditorView(self._scene)
        layout.addWidget(self._view)

        # === 新增: 运行时高亮订阅 ===
        from foundation.event_bus import event_bus
        event_bus.subscribe("feature.ai.node.started", self._on_node_started)
        event_bus.subscribe("feature.ai.node.completed", self._on_node_completed)

    def _on_node_started(self, event) -> None:
        """节点开始执行时高亮"""
        node_id = event.get("node_id", "")
        if node_id and node_id in self._scene._nodes:
            self._scene.set_running_node(node_id)

    def _on_node_completed(self, event) -> None:
        """节点执行完成时取消高亮"""
        self._scene.set_running_node(None)
```

3.2 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.editor.graph_editor import GraphEditorWidget

editor = GraphEditorWidget()

# 加载测试图
graph = {
    'nodes': [
        {'id': 'handle_event', 'type': 'event', 'label': '事件处理', 'position': {'x': 100, 'y': 200}},
        {'id': 'llm_reasoning', 'type': 'llm', 'label': 'LLM 推理', 'position': {'x': 400, 'y': 200}},
    ],
    'edges': [
        {'from': 'handle_event', 'to': 'llm_reasoning'},
    ],
}
editor.load_graph(graph)

# 模拟节点事件
from foundation.event_bus import event_bus, Event

# 节点开始 → 应高亮
event_bus.emit(Event(type='feature.ai.node.started', data={'node_id': 'handle_event'}))
assert editor._scene._nodes['handle_event']._is_running == True
print('✅ 节点高亮: handle_event')

# 节点完成 → 应取消高亮
event_bus.emit(Event(type='feature.ai.node.completed', data={'node_id': 'handle_event'}))
assert editor._scene._nodes['handle_event']._is_running == False
print('✅ 节点取消高亮')

# 不存在的节点 → 不应报错
event_bus.emit(Event(type='feature.ai.node.started', data={'node_id': 'nonexistent'}))
print('✅ 不存在的节点不报错')

print('✅ 运行时高亮接线测试通过')
"
```

**验收**:
- [ ] `GraphEditorWidget` 订阅 `feature.ai.node.started` 和 `feature.ai.node.completed`
- [ ] 节点开始执行时高亮（白色边框）
- [ ] 节点完成时取消高亮
- [ ] 不存在的节点不报错
- [ ] 测试通过

---

### Step 4: 条件边可视化

**目的**: 在图编辑器中支持条件边的渲染和编辑。

**现有代码**:
- `GraphEdgeItem` — 只有 `source` 和 `target`，没有 `condition` 属性
- `GraphScene.add_edge` — 只接受 `source_id` 和 `target_id`
- `GraphScene.load_graph` — 读取 edges 时不处理 `condition` 字段
- `GraphScene.to_dict` — 导出 edges 时不包含 `condition`

**方案**:

4.1 修改 `presentation/editor/graph_editor.py` 中的 `GraphEdgeItem`：

找到 `class GraphEdgeItem(QGraphicsPathItem):`，在 `__init__` 中添加 `condition` 参数：

```python
class GraphEdgeItem(QGraphicsPathItem):
    """图边 — 连接两个节点的曲线"""

    def __init__(self, source: GraphNodeItem, target: GraphNodeItem, condition: str = ""):
        super().__init__()
        self.source = source
        self.target = target
        self.condition = condition  # 新增
        self.setPen(QPen(QColor("#858585"), 2))
        self.setZValue(0)
        self.update_path()
        self._update_style()  # 新增
```

在 `GraphEdgeItem` 中添加 `_update_style` 方法和 `to_dict` 修改：

```python
    def _update_style(self) -> None:
        """根据是否有条件更新样式"""
        if self.condition:
            # 条件边: 红色虚线
            pen = QPen(QColor("#f44747"), 2, Qt.PenStyle.DashLine)
            self.setPen(pen)
        else:
            # 普通边: 灰色实线
            self.setPen(QPen(QColor("#858585"), 2))

    def update_path(self) -> None:
        """更新连线路径"""
        start = self.source.get_output_pos()
        end = self.target.get_input_pos()
        path = QPainterPath()
        path.moveTo(start)
        ctrl_offset = abs(end.x() - start.x()) * 0.5
        path.cubicTo(
            start + QPointF(ctrl_offset, 0),
            end - QPointF(ctrl_offset, 0),
            end,
        )
        self.setPath(path)

        # 如果是条件边，在中间绘制条件标签
        if self.condition:
            # 清除旧标签
            for child in self.childItems():
                if isinstance(child, QGraphicsTextItem):
                    self.scene().removeItem(child) if self.scene() else None
            mid = path.pointAtPercent(0.5)
            label = QGraphicsTextItem(self.condition, self)
            label.setDefaultTextColor(QColor("#f44747"))
            label.setFont(QFont("Microsoft YaHei", 8))
            label.setPos(mid.x() - 30, mid.y() - 15)

    def to_dict(self) -> dict:
        """序列化为字典"""
        result = {
            "from": self.source.node_id,
            "to": self.target.node_id,
        }
        if self.condition:
            result["condition"] = self.condition
        return result
```

4.2 修改 `GraphScene.add_edge`，支持 `condition` 参数：

```python
    def add_edge(self, source_id: str, target_id: str, condition: str = "") -> GraphEdgeItem | None:
        """添加边"""
        source = self._nodes.get(source_id)
        target = self._nodes.get(target_id)
        if not source or not target:
            return None
        edge = GraphEdgeItem(source, target, condition=condition)
        self.addItem(edge)
        self._edges.append(edge)
        return edge
```

4.3 修改 `GraphScene.load_graph`，读取 `condition` 字段：

```python
    def load_graph(self, graph_data: dict) -> None:
        """从字典加载图"""
        self.clear()
        self._nodes.clear()
        self._edges.clear()
        # 添加节点
        for node_data in graph_data.get("nodes", []):
            self.add_node(
                node_id=node_data["id"],
                node_type=node_data.get("type", "custom"),
                label=node_data.get("label", node_data["id"]),
                position=node_data.get("position"),
            )
        # 添加边（包含 condition）
        for edge_data in graph_data.get("edges", []):
            self.add_edge(
                edge_data["from"],
                edge_data["to"],
                condition=edge_data.get("condition", ""),
            )
```

4.4 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.editor.graph_editor import GraphEditorWidget

editor = GraphEditorWidget()

# 测试条件边
graph = {
    'nodes': [
        {'id': 'llm_reasoning', 'type': 'llm', 'label': 'LLM 推理', 'position': {'x': 300, 'y': 200}},
        {'id': 'parse_output', 'type': 'parser', 'label': '命令解析', 'position': {'x': 600, 'y': 150}},
        {'id': 'execute_commands', 'type': 'executor', 'label': '命令执行', 'position': {'x': 600, 'y': 250}},
    ],
    'edges': [
        {'from': 'llm_reasoning', 'to': 'parse_output', 'condition': 'route_after_llm'},
        {'from': 'llm_reasoning', 'to': 'execute_commands'},
    ],
}
editor.load_graph(graph)

# 验证边数量
exported = editor.get_graph()
assert len(exported['edges']) == 2
print(f'✅ 边数量: {len(exported[\"edges\"])}')

# 验证条件边序列化
cond_edge = [e for e in exported['edges'] if e.get('condition')]
assert len(cond_edge) == 1
assert cond_edge[0]['condition'] == 'route_after_llm'
assert cond_edge[0]['from'] == 'llm_reasoning'
assert cond_edge[0]['to'] == 'parse_output'
print(f'✅ 条件边序列化: {cond_edge[0]}')

# 验证普通边
normal_edge = [e for e in exported['edges'] if not e.get('condition')]
assert len(normal_edge) == 1
assert normal_edge[0]['from'] == 'llm_reasoning'
assert normal_edge[0]['to'] == 'execute_commands'
print(f'✅ 普通边序列化: {normal_edge[0]}')

print('✅ 条件边可视化测试通过')
"
```

**验收**:
- [ ] 条件边红色虚线渲染
- [ ] 条件边中间显示条件函数名
- [ ] `load_graph` 读取 `condition` 字段
- [ ] `to_dict` 导出 `condition` 字段
- [ ] 普通边保持灰色实线
- [ ] 测试通过

---

### Step 5: 图编辑器保存时触发编译 + 完善 _save_graph

**目的**: 用户在图编辑器中保存时，自动编译 graph.json 为 StateGraph 并更新 GMAgent。

**现有代码**:
- `graph_editor.py` — `_save_graph` 方法被 `_btn_save.clicked` 连接，但实现不完整
- `project_manager.py` — `save_graph` 只写文件
- `gm_agent.py` — `set_graph` 方法（Step 2 新增）

**方案**:

5.1 完善 `graph_editor.py` 中的 `_save_graph` 方法。

在 `GraphEditorWidget` 类中，找到 `_save_graph` 方法（或 `_btn_save.clicked.connect(self._save_graph)`），确保方法实现如下：

```python
    def _save_graph(self) -> None:
        """保存图定义到 graph.json 并触发编译"""
        from presentation.project.manager import project_manager

        graph_data = self.get_graph()

        # 保存到文件
        try:
            project_manager.save_graph(graph_data)
            self._logger.info(f"图定义已保存 ({len(graph_data['nodes'])} 节点, {len(graph_data['edges'])} 边)")
        except RuntimeError as e:
            self._logger.error(f"保存失败: {e}")
            return

        # 触发编译
        try:
            from feature.ai.graph_compiler import graph_compiler
            compiled = graph_compiler.compile(graph_data)

            # 更新全局 Agent 实例的图
            # 通过 EventBus 通知，让持有 GMAgent 的组件更新
            from foundation.event_bus import event_bus, Event
            event_bus.emit(Event(type="ui.graph.compiled", data={
                "graph_data": graph_data,
                "node_count": len(graph_data["nodes"]),
                "edge_count": len(graph_data["edges"]),
            }))
            self._logger.info("图编译成功，已通过 EventBus 通知")
        except Exception as e:
            self._logger.error(f"图编译失败: {e}")
```

5.2 在 `presentation/project/manager.py` 的 `ProjectManager` 类中，新增 `compile_graph` 方法：

在 `save_graph` 方法之后添加：

```python
    def compile_graph(self) -> Any:
        """编译当前项目的 graph.json 为 StateGraph

        Returns:
            编译好的 CompiledGraph

        Raises:
            RuntimeError: 没有打开的项目
            ValueError: graph.json 无效
        """
        if not self._project_path:
            raise RuntimeError("没有打开的项目")

        graph_data = self.load_graph()
        if not graph_data:
            raise ValueError("graph.json 为空或不存在")

        from feature.ai.graph_compiler import graph_compiler
        compiled = graph_compiler.compile(graph_data)
        logger.info(f"项目图编译成功: {self._current_project.name}")
        return compiled
```

5.3 在 `presentation/main_window.py` 的 `MainWindow` 类中（如果存在），或在 `app.py` 中，订阅 `ui.graph.compiled` 事件并更新 GMAgent：

在 `app.py` 的 `main()` 函数中，`window.show()` 之前添加：

```python
    # 订阅图编译事件，更新 GMAgent
    from foundation.event_bus import event_bus, Event
    _current_agent = None  # 将在 Agent 运行时设置

    def on_graph_compiled(event):
        """图编辑器保存并编译后，更新 Agent 的图"""
        global _current_agent
        if _current_agent is None:
            return
        try:
            graph_data = event.get("graph_data", {})
            from feature.ai.graph_compiler import graph_compiler
            compiled = graph_compiler.compile(graph_data)
            _current_agent.set_graph(compiled, source="json")
            logger.info("GMAgent 图已更新为编辑器版本")
        except Exception as e:
            logger.error(f"更新 Agent 图失败: {e}")

    event_bus.subscribe("ui.graph.compiled", on_graph_compiled)
```

5.4 测试：

```bash
cd 2workbench ; python -c "
import sys, tempfile, shutil
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.project.manager import ProjectManager
from presentation.editor.graph_editor import GraphEditorWidget

# 创建临时项目
tmp_dir = tempfile.mkdtemp()
try:
    pm = ProjectManager(workspace_dir=tmp_dir)
    path = pm.create_project('compile_test', template='trpg', directory=tmp_dir)
    pm.open_project(path)

    # 加载图到编辑器
    graph_data = pm.load_graph()
    editor = GraphEditorWidget()
    editor.load_graph(graph_data)

    # 保存图（应触发编译）
    pm.save_graph(editor.get_graph())
    print('✅ 图保存成功')

    # 编译图
    compiled = pm.compile_graph()
    assert compiled is not None
    print('✅ 图编译成功')

    # 验证编译后的图可用于 GMAgent
    from feature.ai.gm_agent import GMAgent
    agent = GMAgent(world_id=1)
    agent.set_graph(compiled, source='json')
    assert agent._graph_source == 'json'
    print('✅ GMAgent 使用编译后的图')

    pm.close_project()
    print('✅ 项目关闭')

finally:
    shutil.rmtree(tmp_dir)

print('✅ 保存+编译集成测试通过')
"
```

**验收**:
- [ ] `_save_graph` 保存文件 + 触发编译 + 发出 EventBus 事件
- [ ] `ProjectManager.compile_graph()` 方法可用
- [ ] 编译后的图可设置到 GMAgent
- [ ] EventBus 事件 `ui.graph.compiled` 正确发出
- [ ] 测试通过

---

### Step 6: 更新 TRPG 模板 — 添加条件边

**目的**: 更新 `PROJECT_TEMPLATES` 中 TRPG 模板的 graph 定义，添加 `condition` 字段，使其与实际 LangGraph 图结构一致。

**现有代码**: `presentation/project/manager.py` 中 `PROJECT_TEMPLATES["trpg"]["graph"]`

**方案**:

6.1 在 `presentation/project/manager.py` 中，找到 `PROJECT_TEMPLATES["trpg"]["graph"]["edges"]`，替换为：

```python
        "trpg": {
            "name": "TRPG 游戏",
            "description": "桌面角色扮演游戏 Agent",
            "graph": {
                "nodes": [
                    {"id": "handle_event", "type": "event", "label": "事件处理", "position": {"x": 100, "y": 200}},
                    {"id": "build_prompt", "type": "prompt", "label": "Prompt 组装", "position": {"x": 300, "y": 200}},
                    {"id": "llm_reasoning", "type": "llm", "label": "LLM 推理", "position": {"x": 500, "y": 200}},
                    {"id": "parse_output", "type": "parser", "label": "命令解析", "position": {"x": 700, "y": 150}},
                    {"id": "execute_commands", "type": "executor", "label": "命令执行", "position": {"x": 700, "y": 250}},
                    {"id": "update_memory", "type": "memory", "label": "记忆更新", "position": {"x": 900, "y": 200}},
                ],
                "edges": [
                    {"from": "__start__", "to": "handle_event"},
                    {"from": "handle_event", "to": "build_prompt"},
                    {"from": "build_prompt", "to": "llm_reasoning"},
                    {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"},
                    {"from": "llm_reasoning", "to": "execute_commands"},
                    {"from": "parse_output", "to": "execute_commands", "condition": "route_after_parse"},
                    {"from": "parse_output", "to": "update_memory"},
                    {"from": "execute_commands", "to": "update_memory"},
                    {"from": "update_memory", "to": "__end__"},
                ],
            },
            # ... prompts 和 config 不变 ...
```

**注意**: 这里添加了 `__start__` 和 `__end__` 标记，以及两条条件边。同时 `llm_reasoning` 到 `execute_commands` 的直连边也保留了（对应 `route_after_llm` 返回 `"execute_commands"` 的情况）。

6.2 测试：

```bash
cd 2workbench ; python -c "
from presentation.project.manager import PROJECT_TEMPLATES, ProjectManager
from feature.ai.graph_compiler import graph_compiler

# 验证 TRPG 模板有条件边
trpg_edges = PROJECT_TEMPLATES['trpg']['graph']['edges']
cond_edges = [e for e in trpg_edges if e.get('condition')]
assert len(cond_edges) == 2
print(f'✅ TRPG 模板条件边: {len(cond_edges)} 条')
for e in cond_edges:
    print(f'   {e[\"from\"]} --[{e[\"condition\"]}]--> {e[\"to\"]}')

# 验证 __start__ 和 __end__
start_edges = [e for e in trpg_edges if e['from'] == '__start__']
end_edges = [e for e in trpg_edges if e['to'] == '__end__']
assert len(start_edges) == 1
assert len(end_edges) == 1
print(f'✅ START/END 边: {len(start_edges)} 入, {len(end_edges)} 出')

# 编译验证
compiled = graph_compiler.compile(PROJECT_TEMPLATES['trpg']['graph'])
assert compiled is not None
print('✅ TRPG 模板编译成功')

print('✅ TRPG 模板更新测试通过')
"
```

**验收**:
- [ ] TRPG 模板包含 `__start__` 和 `__end__` 标记
- [ ] TRPG 模板包含 2 条条件边（`route_after_llm` 和 `route_after_parse`）
- [ ] TRPG 模板可成功编译为 StateGraph
- [ ] 测试通过

---

### Step 7: 端到端集成测试

**目的**: 验证完整的 graph.json → GraphCompiler → GMAgent → 运行时高亮 数据流。

**方案**:

7.1 创建测试文件 `2workbench/test_p7_integration.py`：

```python
# 2workbench/test_p7_integration.py
"""P7 端到端集成测试 — 验证 graph.json → LangGraph → 运行时高亮 完整数据流"""
import sys
import tempfile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_graph_compiler():
    """测试 GraphCompiler"""
    print("\n=== GraphCompiler ===")
    from feature.ai.graph_compiler import graph_compiler

    trpg = {
        "nodes": [
            {"id": "handle_event", "type": "event", "label": "事件处理", "position": {"x": 100, "y": 200}},
            {"id": "build_prompt", "type": "prompt", "label": "Prompt", "position": {"x": 300, "y": 200}},
            {"id": "llm_reasoning", "type": "llm", "label": "LLM", "position": {"x": 500, "y": 200}},
            {"id": "parse_output", "type": "parser", "label": "解析", "position": {"x": 700, "y": 150}},
            {"id": "execute_commands", "type": "executor", "label": "执行", "position": {"x": 700, "y": 250}},
            {"id": "update_memory", "type": "memory", "label": "记忆", "position": {"x": 900, "y": 200}},
        ],
        "edges": [
            {"from": "__start__", "to": "handle_event"},
            {"from": "handle_event", "to": "build_prompt"},
            {"from": "build_prompt", "to": "llm_reasoning"},
            {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"},
            {"from": "parse_output", "to": "update_memory", "condition": "route_after_parse"},
            {"from": "execute_commands", "to": "update_memory"},
            {"from": "update_memory", "to": "__end__"},
        ],
    }
    compiled = graph_compiler.compile(trpg)
    assert compiled is not None
    print(f"  ✅ 编译成功: {len(trpg['nodes'])} 节点, {len(trpg['edges'])} 边")


def test_gm_agent_dynamic_graph():
    """测试 GMAgent 动态图切换"""
    print("\n=== GMAgent 动态图 ===")
    from feature.ai.gm_agent import GMAgent
    from feature.ai.graph_compiler import graph_compiler

    agent = GMAgent(world_id=1)
    assert agent._graph_source == "default"
    print(f"  ✅ 默认图: {agent._graph_source}")

    graph_data = {
        "nodes": [
            {"id": "handle_event", "type": "event", "label": "事件", "position": {"x": 100, "y": 200}},
            {"id": "build_prompt", "type": "prompt", "label": "Prompt", "position": {"x": 300, "y": 200}},
            {"id": "llm_reasoning", "type": "llm", "label": "LLM", "position": {"x": 500, "y": 200}},
            {"id": "parse_output", "type": "parser", "label": "解析", "position": {"x": 700, "y": 200}},
            {"id": "execute_commands", "type": "executor", "label": "执行", "position": {"x": 700, "y": 300}},
            {"id": "update_memory", "type": "memory", "label": "记忆", "position": {"x": 900, "y": 200}},
        ],
        "edges": [
            {"from": "__start__", "to": "handle_event"},
            {"from": "handle_event", "to": "build_prompt"},
            {"from": "build_prompt", "to": "llm_reasoning"},
            {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"},
            {"from": "parse_output", "to": "update_memory", "condition": "route_after_parse"},
            {"from": "execute_commands", "to": "update_memory"},
            {"from": "update_memory", "to": "__end__"},
        ],
    }
    compiled = graph_compiler.compile(graph_data)
    agent.set_graph(compiled, source="json")
    assert agent._graph_source == "json"
    print(f"  ✅ 切换到 JSON 图: {agent._graph_source}")


def test_runtime_highlight():
    """测试运行时高亮"""
    print("\n=== 运行时高亮 ===")
    from PyQt6.QtWidgets import QApplication
    from presentation.editor.graph_editor import GraphEditorWidget
    from foundation.event_bus import event_bus, Event

    app = QApplication.instance() or QApplication(sys.argv)

    editor = GraphEditorWidget()
    graph = {
        "nodes": [
            {"id": "handle_event", "type": "event", "label": "事件", "position": {"x": 100, "y": 200}},
            {"id": "llm_reasoning", "type": "llm", "label": "LLM", "position": {"x": 400, "y": 200}},
        ],
        "edges": [{"from": "handle_event", "to": "llm_reasoning"}],
    }
    editor.load_graph(graph)

    event_bus.emit(Event(type="feature.ai.node.started", data={"node_id": "handle_event"}))
    assert editor._scene._nodes["handle_event"]._is_running
    print("  ✅ 节点高亮")

    event_bus.emit(Event(type="feature.ai.node.completed", data={"node_id": "handle_event"}))
    assert not editor._scene._nodes["handle_event"]._is_running
    print("  ✅ 节点取消高亮")


def test_conditional_edge():
    """测试条件边可视化"""
    print("\n=== 条件边 ===")
    from PyQt6.QtWidgets import QApplication
    from presentation.editor.graph_editor import GraphEditorWidget

    app = QApplication.instance() or QApplication(sys.argv)

    editor = GraphEditorWidget()
    graph = {
        "nodes": [
            {"id": "llm", "type": "llm", "label": "LLM", "position": {"x": 300, "y": 200}},
            {"id": "parse", "type": "parser", "label": "解析", "position": {"x": 600, "y": 150}},
            {"id": "exec", "type": "executor", "label": "执行", "position": {"x": 600, "y": 250}},
        ],
        "edges": [
            {"from": "llm", "to": "parse", "condition": "route_after_llm"},
            {"from": "llm", "to": "exec"},
        ],
    }
    editor.load_graph(graph)

    exported = editor.get_graph()
    cond = [e for e in exported["edges"] if e.get("condition")]
    assert len(cond) == 1
    assert cond[0]["condition"] == "route_after_llm"
    print(f"  ✅ 条件边: {cond[0]}")


def test_project_workflow():
    """测试项目创建→保存→编译全流程"""
    print("\n=== 项目工作流 ===")
    from presentation.project.manager import ProjectManager
    from feature.ai.graph_compiler import graph_compiler

    tmp_dir = tempfile.mkdtemp()
    try:
        pm = ProjectManager(workspace_dir=tmp_dir)
        path = pm.create_project("p7_test", template="trpg", directory=tmp_dir)
        pm.open_project(path)
        print(f"  ✅ 项目创建: {pm.current_project.name}")

        # 编译项目图
        compiled = pm.compile_graph()
        assert compiled is not None
        print("  ✅ 项目图编译成功")

        # 设置到 GMAgent
        from feature.ai.gm_agent import GMAgent
        agent = GMAgent(world_id=1)
        agent.set_graph(compiled, source="json")
        assert agent._graph_source == "json"
        print("  ✅ GMAgent 使用项目图")

        pm.close_project()
        print("  ✅ 项目关闭")
    finally:
        shutil.rmtree(tmp_dir)


def main():
    print("=" * 60)
    print("P7 LangGraph 可视化集成 — 端到端测试")
    print("=" * 60)

    test_graph_compiler()
    test_gm_agent_dynamic_graph()
    test_runtime_highlight()
    test_conditional_edge()
    test_project_workflow()

    print("\n" + "=" * 60)
    print("✅ P7 全部测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

7.2 执行测试：

```bash
cd 2workbench ; python test_p7_integration.py
```

7.3 测试通过后删除测试文件：

```bash
del 2workbench\test_p7_integration.py
```

**验收**:
- [ ] GraphCompiler 编译 TRPG 图成功
- [ ] GMAgent 动态图切换正常
- [ ] 运行时高亮（started → 高亮, completed → 取消）
- [ ] 条件边可视化（红色虚线 + 序列化）
- [ ] 项目创建→保存→编译全流程
- [ ] 全部测试通过

---

## 修改文件清单

| 文件 | 操作 | 修改内容 |
|------|------|---------|
| `feature/ai/graph_compiler.py` | **新建** | GraphCompiler 类 |
| `feature/ai/gm_agent.py` | **修改** | 动态图支持（`set_graph` + `self._graph`） |
| `feature/ai/__init__.py` | **修改** | 新增导出 `graph_compiler` |
| `presentation/editor/graph_editor.py` | **修改** | 运行时高亮接线 + 条件边 + `_save_graph` 完善 |
| `presentation/project/manager.py` | **修改** | TRPG 模板条件边 + `compile_graph()` 方法 |
| `presentation/main_window.py` 或 `app.py` | **修改** | 订阅 `ui.graph.compiled` 事件 |

## 不修改的文件

| 文件 | 原因 |
|------|------|
| `feature/ai/graph.py` | 保留作为默认回退图 |
| `feature/ai/nodes.py` | 节点事件已正确发出 |
| `core/state.py` | 无需修改 |

---

## 完成检查清单

- [ ] Step 1: GraphCompiler（graph.json → StateGraph）
- [ ] Step 2: GMAgent 改造（动态图支持）
- [ ] Step 3: 运行时高亮接线（EventBus → 图编辑器）
- [ ] Step 4: 条件边可视化（红色虚线 + 序列化）
- [ ] Step 5: 保存时触发编译（_save_graph + compile_graph）
- [ ] Step 6: TRPG 模板更新（条件边 + START/END）
- [ ] Step 7: 端到端集成测试
