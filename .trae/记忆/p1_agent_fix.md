# P1 修复: 打通 Agent 运行流程

> 修复时间: 2026-05-03
> 关联文件: 优化步骤P1-打通Agent运行流程.md

---

## 1.1 补充 langgraph/langchain-core 依赖

**文件**: `pyproject.toml`

**问题**: 代码使用 `langgraph` 和 `langchain-core` 但依赖未声明

**修复**:
```toml
[project]
dependencies = [
    # ... 现有依赖
    # LangGraph 依赖
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
]
```

---

## 1.2 修复 nodes.py 异步调用 Bug

**文件**: `2workbench/feature/ai/nodes.py`

**问题**: `node_llm_reasoning` 是同步函数但内部调用异步代码，在 Qt 事件循环中会抛出 `RuntimeError: This event loop is already running`

**修复**: 将所有节点函数改为 `async def`

```python
# 修改前
def node_handle_event(state: AgentState) -> dict[str, Any]:
def node_build_prompt(state: AgentState) -> dict[str, Any]:
def node_llm_reasoning(state: AgentState) -> dict[str, Any]:
    # 使用 loop.run_until_complete() 调用异步代码 - 会崩溃
    
def node_parse_output(state: AgentState) -> dict[str, Any]:
def node_execute_commands(state: AgentState) -> dict[str, Any]:
def node_update_memory(state: AgentState) -> dict[str, Any]:
def route_after_llm(state: AgentState) -> str:
def route_after_parse(state: AgentState) -> str:

# 修改后
async def node_handle_event(state: AgentState) -> dict[str, Any]:
async def node_build_prompt(state: AgentState) -> dict[str, Any]:
async def node_llm_reasoning(state: AgentState) -> dict[str, Any]:
    # 直接使用 async for - 正常工作
    async for event in client.stream(...):
        ...
        
async def node_parse_output(state: AgentState) -> dict[str, Any]:
async def node_execute_commands(state: AgentState) -> dict[str, Any]:
async def node_update_memory(state: AgentState) -> dict[str, Any]:
async def route_after_llm(state: AgentState) -> str:
async def route_after_parse(state: AgentState) -> str:
```

**关键变更**:
- 移除 `loop.run_until_complete()` 调用
- 直接使用 `async for` 进行流式调用
- LangGraph 原生支持异步节点函数

---

## 1.3 修复 GraphCompiler 条件边编译 Bug

**文件**: `2workbench/feature/ai/graph_compiler.py`

**问题**:
1. 同一 source 节点有多条条件边时，每条边都调用 `add_conditional_edges()`，LangGraph 报 "already registered" 错误
2. 普通边和条件边混用导致冲突

**修复**: 按 source 分组条件边

```python
def compile(self, graph_data: dict) -> Any:
    # ... 添加节点 ...
    
    # === 预处理：按 source 分组边 ===
    normal_edges = []
    conditional_groups: dict[str, dict] = {}  # source -> {"route_func": str, "branches": dict}

    for edge_data in edges:
        source = edge_data["from"]
        target = edge_data["to"]
        condition = edge_data.get("condition", "")

        actual_source = START if source in ("START", "__start__") else source
        actual_target = END if target in ("END", "__end__") else target

        if condition and condition in CONDITION_FUNCTIONS:
            key = str(actual_source)
            if key not in conditional_groups:
                conditional_groups[key] = {"route_func": condition, "branches": {}}
            conditional_groups[key]["branches"][str(actual_target)] = actual_target
        else:
            normal_edges.append((actual_source, actual_target))

    # === 添加普通边 ===
    for source, target in normal_edges:
        # 跳过已有条件边的 source
        if str(source) in conditional_groups:
            logger.warning(f"跳过普通边 {source} -> {target}（该节点已有条件边）")
            continue
        graph.add_edge(source, target)

    # === 添加条件边（每个 source 只调用一次）===
    for source_key, group in conditional_groups.items():
        route_func = CONDITION_FUNCTIONS.get(group["route_func"])
        if route_func is None:
            continue

        actual_source = START if source_key == str(START) else source_key
        branches = group["branches"]

        if not branches:
            continue

        graph.add_conditional_edges(actual_source, route_func, branches)
```

---

## 1.4 修复 TRPG 模板 graph.json 边定义矛盾

**文件**: `2workbench/presentation/project/manager.py`

**问题**: `llm_reasoning` 同时有条件边和普通边，LangGraph 不允许混用

**修复**: 将所有从条件路由节点出发的边都标记为条件边

```python
# 修改前
"edges": [
    {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"},
    {"from": "llm_reasoning", "to": "execute_commands"},  # 普通边 - 冲突！
    {"from": "parse_output", "to": "execute_commands", "condition": "route_after_parse"},
    {"from": "parse_output", "to": "update_memory"},  # 普通边 - 冲突！
]

# 修改后
"edges": [
    {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"},
    {"from": "llm_reasoning", "to": "execute_commands", "condition": "route_after_llm"},
    {"from": "parse_output", "to": "execute_commands", "condition": "route_after_parse"},
    {"from": "parse_output", "to": "update_memory", "condition": "route_after_parse"},
]
```

---

## 1.5 _on_run_agent 使用项目编译的图

**文件**: `2workbench/presentation/main_window.py`

**问题**: `_on_run_agent` 每次都创建新的 `GMAgent` 使用默认硬编码图，没有使用用户在图编辑器中编辑的项目图

**修复**: 创建 GMAgent 后加载项目编译的图

```python
def _on_run_agent(self) -> None:
    # ... 检查项目是否打开 ...
    
    # 创建 Agent 实例
    self._current_agent = GMAgent(world_id=1)

    # === 使用项目编译的图 ===
    try:
        compiled_graph = project_manager.compile_graph()
        self._current_agent.set_graph(compiled_graph, source="json")
        logger.info("使用项目编译的图运行 Agent")
    except Exception as e:
        logger.warning(f"项目图编译失败，使用默认图: {e}")
    
    # ... 启动线程运行 Agent ...
```

---

## 1.6 初始化 Feature 系统注册

**文件**: `2workbench/main.py`

**问题**: `main()` 函数中没有注册任何 Feature 系统，`feature_registry` 是空的全局单例

**修复**: 在应用启动时注册所有 Feature 系统

```python
def main() -> None:
    # ... 创建 QApplication ...

    # === 初始化 Feature 系统 ===
    from feature.registry import feature_registry
    from feature.battle.system import BattleSystem
    from feature.dialogue.system import DialogueSystem
    from feature.quest.system import QuestSystem
    from feature.item.system import ItemSystem
    from feature.exploration.system import ExplorationSystem
    from feature.narration.system import NarrationSystem
    from foundation.config import settings

    db_path = settings.database_path
    features = [
        BattleSystem(db_path=db_path),
        DialogueSystem(db_path=db_path),
        QuestSystem(db_path=db_path),
        ItemSystem(db_path=db_path),
        ExplorationSystem(db_path=db_path),
        NarrationSystem(db_path=db_path),
    ]
    for f in features:
        feature_registry.register(f)
    feature_registry.enable_all()
    logger.info(f"Feature 系统初始化完成: {len(features)} 个系统已注册")

    # ... 创建主窗口 ...
```

---

## 验证清单

- [x] `pip install -e .` 不报缺少依赖
- [x] 异步节点函数可正常导入
- [x] GraphCompiler 编译含条件边的图不报错
- [x] TRPG 模板边定义无冲突
- [x] `_on_run_agent` 使用项目编译的图
- [x] Feature 系统日志显示 "6 个系统已注册"

---

## 关联记忆

- `p2_editor_fix.md` - P2 编辑器体验修复
- `p3_tool_feature_fix.md` - P3 工具与 Feature 打通
