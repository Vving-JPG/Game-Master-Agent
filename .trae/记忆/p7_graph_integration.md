# P7: LangGraph 可视化集成 — GraphCompiler + 运行时高亮 + 图编辑器增强

> 本 Phase 修复 LangGraph 可视化与实际执行之间的**断裂问题**。
> **状态**: ✅ 已完成  
> **日期**: 2026-05-02

---

## 1. 问题背景

### 1.1 修复前的问题

```
graph.json ←→ 图编辑器 ✅ 已连通（可视化编辑）
LangGraph  ←→ GMAgent  ✅ 已连通（Agent 执行）
graph.json ←→ LangGraph ❌ 完全断开
运行时高亮 ←→ EventBus  ❌ 代码写了但没接线
条件边     ←→ graph.json ❌ 不支持 condition 字段
```

### 1.2 修复后的数据流

```
graph.json ←→ GraphCompiler ←→ LangGraph StateGraph ←→ GMAgent
     ↑                                        ↓
  图编辑器                              EventBus 节点事件
     ↓                                        ↓
  保存/加载                           运行时高亮（已接线）
```

---

## 2. 新增/修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `feature/ai/graph_compiler.py` | **新建** | GraphCompiler — graph.json → StateGraph 编译器 |
| `feature/ai/gm_agent.py` | **修改** | 支持动态图切换（`set_graph` + `self._graph`） |
| `feature/ai/__init__.py` | **修改** | 新增导出 `graph_compiler` |
| `presentation/editor/graph_editor.py` | **修改** | 运行时高亮接线 + 条件边可视化 + `_save_graph` 完善 |
| `presentation/project/manager.py` | **修改** | TRPG 模板条件边 + `compile_graph()` 方法 |

---

## 3. GraphCompiler 详解

### 3.1 核心类

```python
# feature/ai/graph_compiler.py
class GraphCompiler:
    """将 graph.json 编译为 LangGraph StateGraph"""

    def compile(self, graph_data: dict) -> CompiledGraph:
        """编译图定义

        Args:
            graph_data: {
                "nodes": [{"id": str, "type": str, "label": str, "position": dict}, ...],
                "edges": [{"from": str, "to": str, "condition": str|None}, ...]
            }
        """
```

### 3.2 节点类型映射

| 节点类型 | 节点函数 | 说明 |
|----------|----------|------|
| `event` | `node_handle_event` | 事件处理 |
| `prompt` | `node_build_prompt` | Prompt 组装 |
| `llm` | `node_llm_reasoning` | LLM 推理 |
| `parser` | `node_parse_output` | 命令解析 |
| `executor` | `node_execute_commands` | 命令执行 |
| `memory` | `node_update_memory` | 记忆更新 |
| `input` | `node_handle_event` | 输入（复用 event） |
| `output` | `node_update_memory` | 输出（复用 memory） |

### 3.3 条件路由映射

| 条件函数 | 返回值 | 目标节点 |
|----------|--------|----------|
| `route_after_llm` | `"execute_commands"` | execute_commands |
| `route_after_llm` | `"parse_output"` | parse_output |
| `route_after_parse` | `"execute_commands"` | execute_commands |
| `route_after_parse` | `"update_memory"` | update_memory |

### 3.4 使用示例

```python
from feature.ai.graph_compiler import graph_compiler

graph_data = {
    "nodes": [
        {"id": "handle_event", "type": "event", "label": "事件处理", "position": {"x": 100, "y": 200}},
        {"id": "llm_reasoning", "type": "llm", "label": "LLM 推理", "position": {"x": 500, "y": 200}},
    ],
    "edges": [
        {"from": "__start__", "to": "handle_event"},
        {"from": "handle_event", "to": "llm_reasoning"},
        {"from": "llm_reasoning", "to": "__end__"},
    ],
}

compiled = graph_compiler.compile(graph_data)
```

---

## 4. GMAgent 动态图支持

### 4.1 API 变更

```python
# feature/ai/gm_agent.py
class GMAgent:
    def __init__(self, world_id=1, ...):
        # 图实例（优先使用 graph.json 编译的图）
        self._graph = _default_gm_graph  # 默认硬编码图
        self._graph_source = "default"   # default / json

    def set_graph(self, compiled_graph: Any, source: str = "json") -> None:
        """动态切换图实例"""
        self._graph = compiled_graph
        self._graph_source = source

    def get_state_snapshot(self) -> dict:
        """状态快照包含 graph_source"""
        return {
            "graph_source": self._graph_source,  # 新增
            ...
        }
```

### 4.2 使用示例

```python
from feature.ai.gm_agent import GMAgent
from feature.ai.graph_compiler import graph_compiler

agent = GMAgent(world_id=1)
assert agent._graph_source == "default"  # 默认使用硬编码图

# 编译 graph.json 并切换
compiled = graph_compiler.compile(graph_data)
agent.set_graph(compiled, source="json")
assert agent._graph_source == "json"
```

---

## 5. 运行时高亮

### 5.1 EventBus 事件

```python
# feature/ai/nodes.py 中每个节点函数已发出:
event_bus.emit(create_node_event("node_id", "started"))   # 节点开始
event_bus.emit(create_node_event("node_id", "completed")) # 节点完成

# 事件类型:
# - feature.ai.node.started
# - feature.ai.node.completed
```

### 5.2 图编辑器订阅

```python
# presentation/editor/graph_editor.py
class GraphEditorWidget:
    def _setup_ui(self):
        # 运行时高亮订阅
        event_bus.subscribe("feature.ai.node.started", self._on_node_started)
        event_bus.subscribe("feature.ai.node.completed", self._on_node_completed)

    def _on_node_started(self, event):
        node_id = event.get("node_id", "")
        self._scene.set_running_node(node_id)  # 高亮

    def _on_node_completed(self, event):
        self._scene.set_running_node(None)  # 取消高亮
```

### 5.3 视觉效果

- 节点运行中: 白色发光边框 (`#ffffff`, 4px)
- 节点空闲: 默认灰色边框 (`#3e3e42`, 2px)

---

## 6. 条件边可视化

### 6.1 graph.json 格式

```json
{
  "edges": [
    {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"},
    {"from": "llm_reasoning", "to": "execute_commands"},
    {"from": "parse_output", "to": "execute_commands", "condition": "route_after_parse"}
  ]
}
```

### 6.2 视觉样式

| 边类型 | 样式 | 标签 |
|--------|------|------|
| 条件边 | 红色虚线 (`#f44747`, DashLine) | 中间显示条件函数名 |
| 普通边 | 灰色实线 (`#858585`, SolidLine) | 无标签 |

### 6.3 GraphEdgeItem API

```python
class GraphEdgeItem(QGraphicsPathItem):
    def __init__(self, source, target, condition: str = ""):
        self.condition = condition  # 条件函数名

    def to_dict(self) -> dict:
        """序列化时包含 condition 字段"""
        result = {"from": ..., "to": ...}
        if self.condition:
            result["condition"] = self.condition
        return result
```

---

## 7. TRPG 模板更新

### 7.1 新的 TRPG 图结构

```json
{
  "nodes": [
    {"id": "handle_event", "type": "event", "label": "事件处理", "position": {"x": 100, "y": 200}},
    {"id": "build_prompt", "type": "prompt", "label": "Prompt 组装", "position": {"x": 300, "y": 200}},
    {"id": "llm_reasoning", "type": "llm", "label": "LLM 推理", "position": {"x": 500, "y": 200}},
    {"id": "parse_output", "type": "parser", "label": "命令解析", "position": {"x": 700, "y": 150}},
    {"id": "execute_commands", "type": "executor", "label": "命令执行", "position": {"x": 700, "y": 250}},
    {"id": "update_memory", "type": "memory", "label": "记忆更新", "position": {"x": 900, "y": 200}}
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
    {"from": "update_memory", "to": "__end__"}
  ]
}
```

### 7.2 条件边说明

- `llm_reasoning` → `parse_output` (`route_after_llm`): LLM 无 tool_calls 时走此边
- `llm_reasoning` → `execute_commands`: LLM 有 tool_calls 时走此边
- `parse_output` → `execute_commands` (`route_after_parse`): 解析出命令时走此边
- `parse_output` → `update_memory`: 无命令时直接更新记忆

---

## 8. 项目工作流

### 8.1 创建项目

```python
from presentation.project.manager import ProjectManager

pm = ProjectManager()
path = pm.create_project("my_trpg", template="trpg")
# 自动创建包含条件边的 graph.json
```

### 8.2 编译项目图

```python
# 加载并编译
pm.open_project(path)
compiled = pm.compile_graph()  # 新增方法

# 设置到 GMAgent
agent = GMAgent(world_id=1)
agent.set_graph(compiled, source="json")
```

### 8.3 保存时自动编译

```python
# presentation/editor/graph_editor.py
def _save_graph(self):
    # 1. 保存到文件
    project_manager.save_graph(graph_data)

    # 2. 触发编译
    compiled = graph_compiler.compile(graph_data)

    # 3. 通知更新
    event_bus.emit(Event(type="ui.graph.compiled", data={...}))
```

---

## 9. 触发关键词（用于 memory-guide.md）

| 关键词 | 说明 |
|--------|------|
| GraphCompiler | graph.json → StateGraph 编译器 |
| graph_compiler | 全局单例实例 |
| compile_graph | ProjectManager 编译方法 |
| set_graph | GMAgent 动态图切换 |
| _graph_source | 图来源标识 (default/json) |
| 运行时高亮 | EventBus 节点事件 → 图编辑器 |
| 条件边 | condition 字段 + 红色虚线 |
| route_after_llm | LLM 后条件路由 |
| route_after_parse | 解析后条件路由 |
| ui.graph.compiled | 图编译完成事件 |

---

## 10. 依赖关系

```
P7 Graph Integration
├── Foundation (P0)
│   ├── event_bus.py (EventBus 事件)
│   └── logger.py (日志)
├── Core (P1)
│   └── state.py (AgentState)
├── Feature AI (P2)
│   ├── graph_compiler.py (新增)
│   ├── gm_agent.py (修改)
│   ├── nodes.py (节点函数)
│   └── graph.py (默认硬编码图)
└── Presentation (P4)
    ├── graph_editor.py (修改)
    └── project/manager.py (修改)
```

---

## 11. 测试验证

```bash
# 1. GraphCompiler 测试
python -c "from feature.ai.graph_compiler import graph_compiler; ..."

# 2. GMAgent 动态图测试
python -c "from feature.ai.gm_agent import GMAgent; ..."

# 3. 运行时高亮测试
python -c "from presentation.editor.graph_editor import GraphEditorWidget; ..."

# 4. 条件边测试
python -c "from presentation.editor.graph_editor import GraphEditorWidget; ..."

# 5. 项目工作流测试
python -c "from presentation.project.manager import ProjectManager; ..."
```

---

*创建: 2026-05-02*  
*关联: P7_GRAPH_INTEGRATION_SKILL.md*
