# 需求1：全面审查 — Trae 执行总表

> 生成日期：2026-05-04
> 审查范围：Game-Master-Agent 78 个 .py 文件
> 执行顺序：严格按阶段 1→2→3→4→5→6 执行，每阶段完成后验证再进入下一阶段

---

## 阶段 1：P0 运行时崩溃修复（必须最先执行）

### 1.1 prompt_tester.py — QLineEdit.getText 崩溃

**文件**：`presentation/editor/prompt_tester.py`（约 389 行）

```python
# 修复前（运行时必定 AttributeError）
name, ok = QLineEdit.getText(self, "保存测试用例", "测试用例名称:")

# 修复后
from PyQt6.QtWidgets import QInputDialog
name, ok = QInputDialog.getText(self, "保存测试用例", "测试用例名称:")
```

**验证**：点击"💾 保存测试用例"按钮，应弹出输入框。

### 1.2 openai_client.py — settings.default_model 不存在

**文件**：`foundation/llm/openai_client.py`（约 63 行）

```python
# 修复前（AttributeError）
self._model = model or settings.default_model

# 修复后
self._model = model or settings.deepseek_model
```

**验证**：启动程序无异常，设置对话框模型列表正常显示。

### 1.3 main_window.py — _on_save 属性名不匹配

**文件**：`presentation/main_window.py`（约 934, 939 行）

```python
# 修复前（保存功能完全失效）
if hasattr(self.center_panel, '_graph_editor'):
    self.center_panel._graph_editor._save_graph()
if hasattr(self.center_panel, '_prompt_editor'):
    self.center_panel._prompt_editor._save_prompt()

# 修复后
if hasattr(self.center_panel, '_graph_viewer'):
    self.center_panel._graph_viewer._save_graph()
if hasattr(self.center_panel, '_prompt_manager'):
    self.center_panel._prompt_manager._save_prompt()
```

**验证**：编辑提示词 → 文件>保存 → 确认文件被更新。

---

## 阶段 2：P1 功能失效修复

### 2.1 Event 访问方式错误（5 个文件，同一 Bug）

**影响文件**（全部执行相同修复）：
- `feature/battle/system.py`
- `feature/dialogue/system.py`
- `feature/exploration/system.py`
- `feature/item/system.py`
- `feature/quest/system.py`

```python
# 修复前（所有 Feature 系统无法接收 AI 命令）
intent = event.get("intent", "")
params = event.get("params", {})

# 修复后
intent = event.data.get("intent", "")
params = event.data.get("params", {})
```

**全局搜索**：在以上 5 个文件中搜索 `event.get(`，全部替换为 `event.data.get(`。

**验证**：运行 Agent → 输入战斗指令 → 事件监控面板确认 battle.system 收到事件。

### 2.2 api_tester.py — 删除 20 秒无意义等待

**文件**：`feature/services/api_tester.py`（约 80-83 行）

```python
# 删除以下代码块：
for _ in range(100):
    if self._cancelled:
        return
    await asyncio.sleep(0.2)
```

**验证**：API 测试按钮响应时间 < 5 秒。

---

## 阶段 3：P2 线程安全与数据完整性

### 3.1 settings_dialog.py — API 测试回调线程安全

**文件**：`presentation/dialogs/settings_dialog.py`

将 `ApiTestWorker` 从 `threading.Thread` 改为 `QThread`，使用信号槽：

```python
from PyQt6.QtCore import QThread, pyqtSignal

class ApiTestWorker(QThread):
    finished = pyqtSignal(object)  # ApiTestResult

    def __init__(self, model, api_key, base_url):
        super().__init__()
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._cancelled = False

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self._run_test())
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(ApiTestResult(success=False, error=str(e)))
        finally:
            loop.close()

    def cancel(self):
        self._cancelled = True
```

调用方连接信号：
```python
worker = ApiTestWorker(model, api_key, base_url)
worker.finished.connect(self._on_test_result)  # 信号槽自动跨线程
worker.start()
```

### 3.2 prompt_editor.py — 移除 QThread.terminate()

**文件**：`presentation/editor/prompt_editor.py`（约 513 行）

```python
# 修复前（不安全）
self._stream_thread.terminate()

# 修复后（协作式停止）
if hasattr(self._stream_thread, 'stop'):
    self._stream_thread.stop()
```

在 `StreamThread` 中添加 `stop()` 方法和 `_should_stop` 标志。

### 3.3 tools/context.py — 全局 ToolContext 线程隔离

**文件**：`feature/ai/tools/context.py`

```python
import threading

# 修复前
_tool_context: Optional[ToolContext] = None

# 修复后
_tool_context = threading.local()
```

### 3.4 knowledge_tools.py — 修复参数丢失

**文件**：`feature/ai/tools/knowledge_tools.py`

- `create_item`：添加 `rarity=rarity` 到 `repo.create()` 调用
- `create_quest`：添加 `quest_type`/`rewards`/`prerequisites` 到 `repo.create()` 调用
- `update_npc_state`：实现 `add_goal`/`remove_goal` 逻辑

### 3.5 skill_manager.py — 修复信号名

**文件**：`presentation/editor/skill_manager.py`（约 308 行）

```python
# 修复前
self.skill_saved.emit()  # 删除后发射"保存"信号，语义错误

# 修复后
self.skill_deleted.emit()  # 如果信号已定义
# 或
self.skill_saved.emit() 改为 self.skill_deleted.emit()
```

---

## 阶段 4：Presentation 层解耦重构

### 4.1 统一 EventBus 事件命名

新增以下 UI 事件（在 `feature/base.py` 或新建 `feature/events.py` 中定义常量）：

```python
# 项目操作
"ui.project.scan"
"ui.project.create"
"ui.project.open"
"ui.project.save"
"ui.project.delete"

# 提示词操作
"ui.prompt.save"
"ui.prompt.load"
"ui.prompt.test"

# 技能操作
"ui.skill.save"
"ui.skill.delete"
"ui.skill.list"
"ui.skill.test_match"

# 图操作
"ui.graph.save"

# 模型操作
"ui.model.add"
"ui.model.update"
"ui.model.delete"
"ui.model.test"

# Agent 操作
"ui.agent.run"
"ui.agent.stop"
```

### 4.2 逐文件解耦（按优先级）

| 优先级 | 文件 | 当前违规 | 改为 |
|--------|------|----------|------|
| 1 | `main_window.py` | `from feature.ai.agent_runner import agent_runner` | EventBus `ui.agent.run` |
| 2 | `prompt_editor.py` | `from feature.project import project_manager` + `from foundation.llm.*` | EventBus `ui.prompt.save` / `ui.prompt.test` |
| 3 | `settings_dialog.py` | 通过兼容层引用 | EventBus `ui.model.*` |
| 4 | `skill_manager.py` | `from feature.project import project_manager` + `from feature.ai.skill_loader import SkillLoader` | EventBus `ui.skill.*` |
| 5 | `graph_editor.py` | `from presentation.project.manager import project_manager` | EventBus `ui.graph.save` |
| 6 | `project_selector.py` | `from feature.project import project_manager` | EventBus `ui.project.*` |
| 7 | `prompt_tester.py` | `from foundation.llm.*` | EventBus `ui.prompt.test` |

### 4.3 Feature 层订阅处理

在对应的 Feature 模块 `__init__` 或 `setup()` 中订阅 UI 事件：

```python
# feature/project/manager.py
event_bus.subscribe("ui.project.save", self._on_save)
event_bus.subscribe("ui.project.scan", self._on_scan)

# feature/ai/skill_loader.py
event_bus.subscribe("ui.skill.save", self._on_save_skill)
event_bus.subscribe("ui.skill.delete", self._on_delete_skill)
```

### 4.4 移除兼容层

解耦完成后删除：
- `presentation/project/manager.py`
- `presentation/dialogs/model_manager.py`

---

## 阶段 5：代码质量清理

### 5.1 删除未使用的 Import（14 处）

| 文件 | 删除 |
|------|------|
| `foundation/cache.py` | `Callable` |
| `foundation/config.py` | `Field`, `field_validator`, `os` |
| `foundation/event_bus.py` | `inspect` |
| `foundation/resource_manager.py` | `os` |
| `foundation/save_manager.py` | `os` |
| `core/models/entities.py` | `datetime` |
| `core/models/repository.py` | `Generic`, `TypeVar`, `T = TypeVar("T")` |
| `feature/ai/gm_agent.py` | `LocationRepo` |
| `feature/ai/prompt_builder.py` | `PromptRepo` |
| `feature/battle/system.py` | `LogRepo` |
| `feature/dialogue/system.py` | `LogRepo`, `MemoryRepo` |
| `feature/item/system.py` | `ItemType`, `ItemRarity` |
| `feature/narration/system.py` | `MemoryCategory` |

### 5.2 删除死代码

| 文件 | 删除内容 |
|------|----------|
| `foundation/event_bus.py` | `_async_handlers` 列表及相关代码 |
| `foundation/llm/openai_client.py` | `_retry_decorator` |
| `foundation/cache.py` | `_make_key()` 方法 |
| `presentation/agent_thread.py` | `stream_chunk` 信号（或加 TODO 注释） |
| `feature/ai/prompt_builder.py` | `_system_prompt_cache`, `_system_prompt_key` |
| `feature/ai/graph.py` | `default_graph` 别名 |

### 5.3 修复异常处理

- `feature/ai/nodes.py`：`except Exception: pass` → `except Exception as e: logger.warning(...)`
- `feature/ai/prompt_builder.py`：批量 `try/except/pass` → 至少记录 warning
- `presentation/ops/log_viewer.py`：`except Exception: pass` → `except Exception as e: logger.debug(...)`

### 5.4 统一代码风格

- `foundation/event_bus.py`：`logging.getLogger` → `from foundation.logger import get_logger`
- `foundation/llm/base.py`：`_prompt_tokens`/`_completion_tokens` 从类变量改为实例变量
- `feature/services/model_manager.py`：`List`/`Dict`/`Tuple` → `list`/`dict`/`tuple`

---

## 阶段 6：目录结构优化

### 6.1 文件移动清单

| 原路径 | 新路径 |
|--------|--------|
| `foundation/base/interfaces.py` | `foundation/interfaces.py` |
| `core/calculators/combat.py` | `core/combat.py` |
| `core/calculators/ending.py` | `core/ending.py` |
| `core/constants/npc_templates.py` | `core/npc_templates.py` |
| `core/constants/story_templates.py` | `core/story_templates.py` |
| `feature/battle/system.py` | `feature/battle_system.py` |
| `feature/dialogue/system.py` | `feature/dialogue_system.py` |
| `feature/exploration/system.py` | `feature/exploration_system.py` |
| `feature/item/system.py` | `feature/item_system.py` |
| `feature/narration/system.py` | `feature/narration_system.py` |
| `feature/quest/system.py` | `feature/quest_system.py` |
| `feature/project/manager.py` | `feature/project_manager.py` |
| `presentation/ops/log_viewer.py` | `presentation/log_viewer.py` |
| `presentation/ops/debugger/event_monitor.py` | `presentation/debugger/event_monitor.py` |
| `presentation/ops/debugger/runtime_panel.py` | `presentation/debugger/runtime_panel.py` |
| `presentation/project/new_dialog.py` | `presentation/new_project_dialog.py` |
| `presentation/theme/manager.py` | `presentation/theme_manager.py` |

### 6.2 删除空目录

移动完成后删除：`foundation/base/`、`core/calculators/`、`core/constants/`、`feature/battle/`、`feature/dialogue/`、`feature/exploration/`、`feature/item/`、`feature/narration/`、`feature/quest/`、`feature/project/`、`presentation/ops/`、`presentation/project/`、`presentation/theme/`

### 6.3 全局 Import 路径更新

移动后全局搜索替换旧路径为新路径（详见 06-目录结构与文件位置优化指导.md）。

---

## 执行检查清单

- [ ] 阶段 1：3 个 P0 Bug 修复完成，程序可正常启动
- [ ] 阶段 2：5 个 Event 访问修复 + API 延迟修复
- [ ] 阶段 3：线程安全修复 + 数据完整性修复
- [ ] 阶段 4：7 个文件解耦完成，兼容层删除
- [ ] 阶段 5：14 处未使用 import + 6 处死代码 + 异常处理 + 风格统一
- [ ] 阶段 6：18 个文件移动 + 13 个空目录删除 + import 路径更新
