# 优化步骤 P1：打通 Agent 运行流程

> 🔴 紧急 | 2-3 天
>
> **目标：点击"运行"按钮后，Agent 真正执行并显示结果**

---

## 变更说明

相比上次分析，源码已有显著进展：
- ✅ `GMAgent` 已实现 `set_graph()`、`run()`、`run_sync()`
- ✅ `_on_run_agent` 已实现（QThread + asyncio 后台运行）
- ✅ `project_manager.compile_graph()` 已实现
- ✅ `graph_compiler` 已正确导出

但仍存在 **3 个阻塞端到端运行的关键 Bug**，必须修复。

---

## 1.1 [新] 补充 langgraph/langchain-core 依赖

**文件**：`pyproject.toml`

**问题**：代码大量使用 `from langgraph.graph import ...` 和 `from langchain_core...`，但 `pyproject.toml` 的 `dependencies` 中未声明这两个包。`pip install -e .` 后无法运行。

**修复**：

```toml
[project]
dependencies = [
    "openai>=2.32.0",
    "pydantic>=2.13.3",
    "pydantic-settings>=2.14.0",
    "python-frontmatter>=1.1.0",
    "tenacity>=9.1.4",
    "PyQt6>=6.6.0",
    "qasync>=0.27.0",
    "pyyaml>=6.0.1",
    "langgraph>=0.2.0",        # ← 新增
    "langchain-core>=0.3.0",   # ← 新增
]
```

---

## 1.2 [关键] 修复 nodes.py 异步调用 Bug

**文件**：`2workbench/feature/ai/nodes.py:154-182`

**问题**：`node_llm_reasoning` 是同步函数（`def`），但内部使用 `loop.run_until_complete()` 调用异步代码。在 Qt 事件循环中，`loop.is_running()` 为 True 时调用 `run_until_complete()` 会抛出 `RuntimeError: This event loop is already running`。

**修复方案 A（推荐）：将节点函数改为 async**

LangGraph 原生支持异步节点函数，这是最干净的方案：

```python
# nodes.py — 将所有节点函数改为 async def
async def node_handle_event(state: AgentState) -> dict[str, Any]:
    """处理事件（异步）"""
    # ... 逻辑不变 ...

async def node_build_prompt(state: AgentState) -> dict[str, Any]:
    """构建 Prompt（异步）"""
    # ... 逻辑不变 ...

async def node_llm_reasoning(state: AgentState) -> dict[str, Any]:
    """LLM 推理（异步）"""
    messages = state.get("messages", [])
    tools_schema = get_tools_schema() if state.get("tools_enabled") else None

    try:
        client = model_router.get_client()
        full_content = ""
        reasoning_content = ""
        tool_calls = []

        async for event in client.stream(
            messages=messages,
            temperature=state.get("temperature", 0.7),
            tools=tools_schema,
        ):
            if event.type == "reasoning":
                reasoning_content += event.content
            elif event.type == "token":
                full_content += event.content
            elif event.type == "tool_call":
                tool_calls.extend(event.tool_calls)

        updates = {
            "last_response": full_content,
            "messages": messages + [{"role": "assistant", "content": full_content}],
        }
        if tool_calls:
            updates["tool_calls"] = tool_calls
        return updates

    except Exception as e:
        logger.error(f"LLM 推理失败: {e}", exc_info=True)
        return {"execution_state": "error", "error_message": str(e)}

# 其余节点同样改为 async def
async def node_parse_output(state: AgentState) -> dict[str, Any]: ...
async def node_execute_commands(state: AgentState) -> dict[str, Any]: ...
async def node_update_memory(state: AgentState) -> dict[str, Any]: ...

# 路由函数也改为 async
async def route_after_llm(state: AgentState) -> str: ...
async def route_after_parse(state: AgentState) -> str: ...
```

**同时修改 `graph.py` 中的 `build_gm_graph()`**：

无需修改。LangGraph 的 `StateGraph` 自动支持 async 节点函数，`compile()` 后的图可以通过 `ainvoke()` 调用。

**修改 `gm_agent.py` 中的 `run()`**：

`gm_agent.run()` 已经使用 `await self._graph.ainvoke(input_state)`，无需修改。

**验证**：
```python
# 确认 async 节点能正常工作
import asyncio
from feature.ai.graph import gm_graph
from core.state import create_initial_state

async def test():
    state = create_initial_state()
    state["current_event"] = {"type": "player_action", "text": "探索周围"}
    result = await gm_graph.ainvoke(state)
    print(f"✅ 执行成功: {result.get('last_response', '')[:50]}")

asyncio.run(test())
```

---

## 1.3 [关键] 修复 GraphCompiler 条件边编译 Bug

**文件**：`2workbench/feature/ai/graph_compiler.py:164-186`

**问题**：
1. 同一 source 节点有多条条件边时，每条边都调用一次 `add_conditional_edges()`，LangGraph 会报 "already registered" 错误
2. 第 172-175 行的 `pass` 注释表明需要根据 `actual_target` 覆盖默认分支映射，但从未实现

**修复**：

```python
def compile(self, graph_data: dict) -> Any:
    _init_mappings()

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    if not nodes:
        raise ValueError("图定义不能为空：没有节点")

    graph = StateGraph(AgentState)
    node_ids = set()

    # === 添加节点 ===
    for node_data in nodes:
        node_id = node_data["id"]
        node_type = node_data.get("type", "custom")
        node_func = NODE_FUNCTIONS.get(node_type)
        if node_func is None:
            logger.warning(f"未知节点类型 '{node_type}' (节点: {node_id})，跳过")
            continue
        graph.add_node(node_id, node_func)
        node_ids.add(node_id)

    # === 预处理：按 source 分组边 ===
    normal_edges = []
    conditional_groups: dict[str, dict] = {}  # source -> {"route_func": str, "branches": dict}

    for edge_data in edges:
        source = edge_data["from"]
        target = edge_data["to"]
        condition = edge_data.get("condition", "")

        actual_source = START if source in ("START", "__start__") else source
        actual_target = END if target in ("END", "__end__") else target

        if condition:
            key = str(actual_source)
            if key not in conditional_groups:
                conditional_groups[key] = {"route_func": condition, "branches": {}}
            conditional_groups[key]["branches"][str(actual_target)] = actual_target
        else:
            normal_edges.append((actual_source, actual_target))

    # === 添加普通边 ===
    for source, target in normal_edges:
        # 跳过已有条件边的 source（避免 add_edge + add_conditional_edges 冲突）
        if str(source) in conditional_groups:
            logger.warning(f"跳过普通边 {source} -> {target}（该节点已有条件边）")
            continue
        graph.add_edge(source, target)

    # === 添加条件边（每个 source 只调用一次）===
    for source_key, group in conditional_groups.items():
        route_func = CONDITION_FUNCTIONS.get(group["route_func"])
        if route_func is None:
            logger.warning(f"未知条件路由函数: {group['route_func']}")
            continue

        actual_source = START if source_key == str(START) else source_key
        branches = group["branches"]

        if not branches:
            logger.warning(f"条件边 {source_key} 没有分支目标，跳过")
            continue

        graph.add_conditional_edges(actual_source, route_func, branches)
        logger.debug(f"编译条件边: {source_key} --[{group['route_func']}]--> {list(branches.keys())}")

    compiled = graph.compile()
    logger.info(f"图编译完成: {len(node_ids)} 节点, {len(normal_edges)} 普通边, {len(conditional_groups)} 条件边组")
    return compiled
```

---

## 1.4 [新] 修复 TRPG 模板 graph.json 边定义矛盾

**文件**：`2workbench/presentation/project/manager.py:78-119`

**问题**：TRPG 模板的 edges 中，`llm_reasoning` 同时有条件边（到 `parse_output`）和普通边（到 `execute_commands`）。GraphCompiler 会先调用 `add_conditional_edges` 再调用 `add_edge`，LangGraph 不允许这种混合。

**修复**：将所有从条件路由节点出发的边都标记为条件边：

```python
# manager.py — TRPG 模板的 edges 定义
TRPG_TEMPLATE = {
    # ... nodes 不变 ...
    "edges": [
        {"from": "__start__", "to": "handle_event"},
        {"from": "handle_event", "to": "build_prompt"},
        {"from": "build_prompt", "to": "llm_reasoning"},
        # llm_reasoning 的两条出边都是条件边
        {"from": "llm_reasoning", "to": "parse_output", "condition": "route_after_llm"},
        {"from": "llm_reasoning", "to": "execute_commands", "condition": "route_after_llm"},
        # parse_output 的两条出边都是条件边
        {"from": "parse_output", "to": "execute_commands", "condition": "route_after_parse"},
        {"from": "parse_output", "to": "update_memory", "condition": "route_after_parse"},
        # execute_commands 只有一条出边，用普通边
        {"from": "execute_commands", "to": "update_memory"},
        {"from": "update_memory", "to": "__end__"},
    ],
}
```

**注意**：需要同步更新 `route_after_llm` 和 `route_after_parse` 的返回值，使其与 `CONDITION_BRANCHES` 中的分支键一致。

检查 `graph_compiler.py` 中的 `CONDITION_BRANCHES`：

```python
CONDITION_BRANCHES = {
    "route_after_llm": {
        "parse_output": "parse_output",
        "execute_commands": "execute_commands",
    },
    "route_after_parse": {
        "execute_commands": "execute_commands",
        "update_memory": "update_memory",
    },
}
```

路由函数的返回值必须与分支键匹配：

```python
# nodes.py
def route_after_llm(state: AgentState) -> str:
    if state.get("tool_calls"):
        return "execute_commands"  # ← 必须与 CONDITION_BRANCHES 的 key 匹配
    return "parse_output"

def route_after_parse(state: AgentState) -> str:
    commands = state.get("commands", [])
    if commands:
        return "execute_commands"
    return "update_memory"
```

**当前代码已满足此条件** ✅，只需修复模板和编译器。

---

## 1.5 [新] _on_run_agent 使用项目编译的图

**文件**：`2workbench/presentation/main_window.py:1083-1141`

**问题**：`_on_run_agent` 已实现，但每次都创建新的 `GMAgent(world_id=1)` 使用默认硬编码图，没有使用用户在图编辑器中编辑的项目图。

**修复**：

在 `_on_run_agent` 中，创建 GMAgent 后尝试加载项目编译的图：

```python
def _on_run_agent(self, event=None) -> None:
    # ... 现有的检查逻辑 ...

    try:
        from feature.ai.gm_agent import GMAgent
        agent = GMAgent(world_id=1)

        # === 新增：尝试使用项目编译的图 ===
        try:
            compiled = project_manager.compile_graph()
            agent.set_graph(compiled, source="json")
            logger.info("使用项目编译的图运行 Agent")
        except Exception as e:
            logger.warning(f"项目图编译失败，使用默认图: {e}")

        # ... 现有的 QThread 启动逻辑 ...
```

---

## 1.6 初始化 Feature 系统注册

**文件**：`2workbench/main.py`

**问题**：`main()` 函数中没有注册任何 Feature 系统，`feature_registry` 是空的全局单例。

**修复**：

```python
def main():
    app = QApplication(sys.argv)
    theme_manager.apply("dark")

    # === 新增：初始化 Feature 系统 ===
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
    logger.info(f"Feature 系统初始化: {len(features)} 个系统已注册")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

---

## 验证清单

完成 Phase 1 后：

- [ ] `pip install -e .` 不报缺少依赖
- [ ] 打开 TRPG 模板项目 → 点击运行 → Agent 执行并输出叙事（不崩溃）
- [ ] 在图编辑器中修改节点连接 → 保存 → 运行 → Agent 使用新图执行
- [ ] 运行时图编辑器节点高亮（白色边框闪烁）
- [ ] Feature 系统日志显示 "6 个系统已注册"
- [ ] GraphCompiler 编译含条件边的图不报错

---

## 已完成项（无需修改）

以下项在最新代码中已实现，无需优化：

- ✅ `gm_agent.set_graph()` — 已实现
- ✅ `gm_agent.run()` / `run_sync()` — 已实现（QThread + asyncio）
- ✅ `project_manager.compile_graph()` — 已实现
- ✅ `graph_compiler` 导出 — 已实现
- ✅ 图编辑器运行时高亮 — 已接线
- ✅ 图编辑器条件边可视化 — 已实现
- ✅ 图编辑器 `remove_node()` — 已实现
- ✅ 图编辑器保存并编译 — 已实现
