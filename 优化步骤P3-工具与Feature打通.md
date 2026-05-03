# 优化步骤 P3：工具与 Feature 打通

> 🟡 中 | 3-4 天
>
> **目标：Agent 的命令能真正改变游戏状态**

## 变更说明

以下问题在最新代码中**仍未修复**，P3 的修复方案仍然适用：
- ❌ `tools.py` 所有工具仍为模拟实现（返回字符串，不操作数据库）
- ❌ 工具管理器与 `tools.py` 两套独立体系
- ❌ 工具测试面板仍为模拟调用
- ❌ Feature 系统仍未初始化注册

以下项已移至 P1（因为阻塞 Agent 运行）：
- → `langgraph`/`langchain-core` 依赖补充 → P1.1
- → Feature 系统初始化注册 → P1.6

---

## 3.1 统一工具管理器与 tools.py 的工具定义

**当前问题**：
- `tool_manager.py` 中的 `ToolDefinition` 是 UI 展示数据（名称、描述、JSON Schema）
- `tools.py` 中的 `@tool` 函数是 LangChain 工具（可被 Agent 调用）
- 两套体系完全独立，工具管理器的启用/禁用不影响 Agent 的工具集

**修复方案**：

### 3.1.1 让 tools.py 从 ToolDefinition 动态生成

在 `tools.py` 中添加工具注册机制：

```python
# feature/ai/tools.py
from langchain_core.tools import tool
from typing import Any

# === 工具注册表 ===
_REGISTERED_TOOLS: dict[str, dict] = {}

def register_tool(name: str, description: str, parameters_schema: dict,
                   handler: callable):
    """注册一个工具

    Args:
        name: 工具名称
        description: 工具描述（会作为 LLM 的 tool description）
        parameters_schema: JSON Schema 格式的参数定义
        handler: 实际执行函数
    """
    _REGISTERED_TOOLS[name] = {
        "name": name,
        "description": description,
        "parameters_schema": parameters_schema,
        "handler": handler,
    }

def get_all_tools() -> list:
    """获取所有已注册的工具（包括内置和动态注册的）"""
    tools = list(BUILTIN_TOOLS.values())
    for name, tool_def in _REGISTERED_TOOLS.items():
        # 动态创建 @tool 装饰的函数
        func = _create_tool_function(name, tool_def)
        tools.append(func)
    return tools

def _create_tool_function(name: str, tool_def: dict):
    """从注册信息动态创建 LangChain Tool"""
    handler = tool_def["handler"]

    # 创建带正确元数据的函数
    func = lambda **kwargs: handler(**kwargs)
    func.__name__ = name
    func.__doc__ = tool_def["description"]

    # 使用 @tool 装饰
    return tool(func)

# === 内置工具（保留现有实现，后续逐步连接到 Feature 系统）===
BUILTIN_TOOLS: dict[str, Any] = {}

# ... 保留现有的 @tool 定义 ...
```

### 3.1.2 工具管理器保存时同步到 tools.py

在 `tool_manager.py` 中，保存自定义工具时注册到 `tools.py`：

```python
class ToolManagerWidget(BaseWidget):
    def _save_custom_tool(self, tool_def: ToolDefinition) -> None:
        """保存自定义工具并注册到 Agent 工具集"""
        # 1. 保存到项目文件
        from presentation.project.manager import project_manager
        project_manager.save_tool(tool_def.to_dict())

        # 2. 注册到 Agent 工具集
        from feature.ai.tools import register_tool
        handler = self._create_handler(tool_def)  # 根据工具定义生成执行函数
        register_tool(
            name=tool_def.name,
            description=tool_def.description,
            parameters_schema=tool_def.parameters,
            handler=handler,
        )

        self.emit_event("ui.tools.changed", {"tool_name": tool_def.name})
        self._logger.info(f"工具已注册: {tool_def.name}")
```

---

## 3.2 tools.py 工具连接到 Feature 系统/Repository

**文件**：`2workbench/feature/ai/tools.py`

**当前问题**：
9 个内置工具全部返回描述字符串，不操作实际数据库。

**修复方案**：

引入工具上下文，让工具能访问数据库：

```python
# feature/ai/tools.py
from core.models.repository import (
    PlayerRepo, ItemRepo, LocationRepo, QuestRepo, NPCRepo, LogRepo
)

class ToolContext:
    """工具执行上下文"""
    def __init__(self, db_path: str, world_id: str, player_id: int):
        self.db_path = db_path
        self.world_id = world_id
        self.player_id = player_id
        self._repos: dict[str, Any] = {}

    def get_repo(self, repo_class) -> Any:
        if repo_class.__name__ not in self._repos:
            self._repos[repo_class.__name__] = repo_class(self.db_path)
        return self._repos[repo_class.__name__]

_tool_context: ToolContext | None = None

def set_tool_context(ctx: ToolContext | None):
    global _tool_context
    _tool_context = ctx

def get_tool_context() -> ToolContext | None:
    return _tool_context
```

**改造内置工具**（以 `update_player_stat` 为例）：

```python
@tool
def update_player_stat(stat: str, value: int) -> str:
    """更新玩家属性值。
    Args:
        stat: 属性名 (hp/max_hp/mp/max_mp/attack/defense/speed/level/exp/gold)
        value: 变化值（正数增加，负数减少）
    """
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"

    valid_stats = {"hp", "max_hp", "mp", "max_mp", "attack", "defense",
                   "speed", "level", "exp", "gold"}
    if stat not in valid_stats:
        return f"错误：无效属性 '{stat}'"

    repo = ctx.get_repo(PlayerRepo)
    player = repo.get_by_id(ctx.player_id)
    if not player:
        return "错误：玩家不存在"

    current = getattr(player, stat, 0)
    new_value = max(0, current + value)

    # HP/MP 不超过上限
    if stat in ("hp", "mp"):
        max_val = getattr(player, f"max_{stat}", 999)
        new_value = min(new_value, max_val)

    repo.update(ctx.player_id, **{stat: new_value})

    # 记录日志
    log_repo = ctx.get_repo(LogRepo)
    log_repo.create(
        world_id=ctx.world_id,
        event_type="stat_change",
        description=f"玩家 {stat} {value:+d} → {new_value}",
    )

    return f"玩家 {stat}: {current} → {new_value}（{value:+d}）"
```

**在 GMAgent.run() 中设置工具上下文**：

```python
# gm_agent.py
class GMAgent:
    async def run(self, event: dict) -> dict:
        # 设置工具上下文
        from feature.ai.tools import set_tool_context, ToolContext
        ctx = ToolContext(
            db_path=self._db_path,
            world_id=str(self._world_id),
            player_id=self._initial_state.get("player", {}).get("id", 1),
        )
        set_tool_context(ctx)

        try:
            result = await self._graph.ainvoke(input_state)
            return result
        finally:
            set_tool_context(None)  # 清理
```

**其他工具类似改造**：

| 工具 | 连接到 |
|------|--------|
| `give_item` | `ItemRepo.create()` + `PlayerRepo.add_item()` |
| `remove_item` | `PlayerRepo.remove_item()` |
| `move_to_location` | `LocationRepo.search()` + `PlayerRepo.update(current_location_id)` |
| `talk_to_npc` | `NPCRepo.get_by_id()` + EventBus emit |
| `start_combat` | `BattleSystem.start_combat()` via EventBus |
| `update_quest` | `QuestRepo.update()` |
| `roll_dice` | `random.randint()`（纯计算，无需 DB） |
| `get_player_info` | `PlayerRepo.get_by_id()` |
| `get_location_info` | `LocationRepo.get_by_id()` |

---

## 3.3 工具测试面板真实调用

**文件**：`2workbench/presentation/editor/tool_manager.py:377-393`

**当前问题**：
`_run_test` 是模拟调用。

**修复方案**：

```python
class ToolManagerWidget(BaseWidget):
    def _run_test(self) -> None:
        """真实调用选中的工具"""
        tool = self._get_selected_tool()
        if not tool:
            self._test_output.setPlainText("请先选择一个工具")
            return

        try:
            # 解析参数
            params = json.loads(self._test_params.toPlainText() or "{}")

            # 查找并调用实际工具函数
            from feature.ai.tools import get_all_tools, set_tool_context, ToolContext
            from foundation.config import settings

            # 设置临时工具上下文
            ctx = ToolContext(
                db_path=settings.database_path,
                world_id="test",
                player_id=1,
            )
            set_tool_context(ctx)

            # 查找匹配的工具
            all_tools = get_all_tools()
            for t in all_tools:
                if t.name == tool.name:
                    result = t.invoke(params)
                    self._test_output.setPlainText(f"✅ 调用成功:\n{result}")
                    return

            self._test_output.setPlainText(f"❌ 未找到工具: {tool.name}")

        except json.JSONDecodeError as e:
            self._test_output.setPlainText(f"❌ JSON 格式错误: {e}")
        except Exception as e:
            self._test_output.setPlainText(f"❌ 调用失败: {e}")
        finally:
            set_tool_context(None)
```

---

## 3.4 Feature 系统事件订阅完善

**文件**：各 Feature 系统的 `system.py`

**当前问题**：
部分 Feature 系统（ExplorationSystem、ItemSystem）没有在 `on_enable()` 中订阅事件，AI 层无法通过 EventBus 触发这些系统。

**修复方案**：

```python
# feature/exploration/system.py
class ExplorationSystem(BaseFeature):
    name = "exploration"

    def on_enable(self):
        self.subscribe("feature.ai.command.executed", self._on_command_executed)

    def _on_command_executed(self, event):
        intent = event.get("intent", "")
        params = event.get("params", {})
        if intent == "move_to_location":
            self.move_player(params.get("location_name", ""))
        elif intent == "explore":
            self.explore_location()
```

```python
# feature/item/system.py
class ItemSystem(BaseFeature):
    name = "item"

    def on_enable(self):
        self.subscribe("feature.ai.command.executed", self._on_command_executed)

    def _on_command_executed(self, event):
        intent = event.get("intent", "")
        params = event.get("params", {})
        if intent == "give_item":
            self.give_item(params.get("item_name", ""), params.get("quantity", 1))
        elif intent == "remove_item":
            self.remove_item(params.get("item_name", ""))
        elif intent == "use_item":
            self.use_item(params.get("item_name", ""))
```

---

## 3.5 补充 langgraph 依赖

> ⚠️ 已移至 P1.1（阻塞 Agent 运行，优先级更高）

---

## 验证清单

完成 Phase 3 后：

- [ ] Agent 运行后调用 `update_player_stat("hp", -10)` → 数据库中玩家 HP 实际减少
- [ ] Agent 调用 `give_item("治疗药水")` → 数据库中玩家背包出现物品
- [ ] Agent 调用 `move_to_location("暗黑洞穴")` → 数据库中玩家位置更新
- [ ] 工具管理器中点击"测试" → 实际调用工具并显示真实结果
- [ ] 工具管理器中添加自定义工具 → Agent 可调用该工具
- [ ] Feature 系统日志显示事件被正确接收
- [ ] `pip install -e .` 不报缺少依赖
