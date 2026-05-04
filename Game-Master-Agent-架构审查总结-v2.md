# Game-Master-Agent 架构审查总结（v2 更新版）

> 初次审查：2026-05-04 | 更新审查：2026-05-04
> 项目地址：https://github.com/Vving-JPG/Game-Master-Agent
> 审查范围：`2workbench/` 目录下全部四层架构代码

---

## 一、更新概况

代码已进行了一轮重大更新，主要变更：

| 变更项 | 状态 |
|--------|------|
| `_legacy/` 目录 | ✅ 已删除 |
| `feature/ai/tools.py` (835行) | ✅ 已拆分为 `feature/ai/tools/` 包（8个文件） |
| `presentation/project/manager.py` | ✅ 已移至 `feature/project/manager.py`，原位保留兼容层 |
| `presentation/dialogs/model_manager.py` | ✅ 已移至 `feature/services/model_manager.py`，原位保留兼容层 |
| `presentation/agent_thread.py` | ✅ 新增，从 main_window 提取 |
| `feature/ai/agent_runner.py` | ✅ 新增，Agent 运行准备器 |
| `presentation/ops/` 单文件子目录 | ✅ 已扁平化（deploy/evaluator/knowledge/logger_panel/multi_agent/safety） |
| `config/model_rules.json` | ✅ 新增，模型路由规则外置 |
| `foundation/database.py` schema_path | ✅ 已参数化 |
| `foundation/base/singleton.py` | ✅ 已删除 |
| `foundation/base/interfaces.py` ILLMClient | ✅ 已删除 |
| `foundation/llm/model_router.py` 业务关键词 | ✅ 已外置到配置文件 |
| `feature/services/api_tester.py` PyQt6 | ✅ 已改为 threading |
| `feature/ai/gm_agent.py` qasync | ✅ 已移除 |
| `foundation/llm/openai_client.py` temperature bug | ✅ 已修复 |
| `presentation/ops/debugger/event_monitor.py` monkey-patch | ✅ 已改为通配符订阅 |
| `presentation/dialogs/project_selector.py` 文件操作 | ✅ 已改为调用 project_manager |

---

## 二、四层架构合规性评分（更新后）

| 层 | 上次评分 | 本次评分 | 变化 |
|---|---------|---------|------|
| **Foundation** | ⭐⭐⭐⭐ (8/10) | ⭐⭐⭐⭐⭐ (9/10) | +1 修复了跨层路径、业务泄漏、死接口、temperature bug |
| **Core** | ⭐⭐⭐⭐ (8/10) | ⭐⭐⭐⭐ (8/10) | 无变化，P2 清理未执行 |
| **Feature** | ⭐⭐⭐ (6/10) | ⭐⭐⭐⭐ (8/10) | +2 修复了 PyQt6/qasync 泄漏，tools 已拆分 |
| **Presentation** | ⭐⭐ (4/10) | ⭐⭐⭐ (6/10) | +2 ProjectManager/ModelManager 已移走，部分解耦 |

---

## 三、问题追踪总表

### ✅ 已修复（14项）

| # | 原编号 | 问题 | 修复方式 |
|---|--------|------|---------|
| 1 | P0-1 | Feature 层引用 PyQt6 | api_tester.py 改用 threading.Thread |
| 2 | P0-2 | Feature 层引用 qasync | gm_agent.py 移除 qasync |
| 3 | P0-3 | Foundation 硬编码 Core 层路径 | database.py schema_path 参数化 |
| 4 | P0-4 | Foundation 包含业务关键词 | model_router.py 规则外置到 config/model_rules.json |
| 5 | P0-5 | ProjectManager 位于错误层 | 移至 feature/project/，原位保留兼容层 |
| 6 | P0-6 | ModelManager 位于错误层 | 移至 feature/services/，原位保留兼容层 |
| 7 | P1-2 | AgentThread 内嵌于 main_window | 提取到 presentation/agent_thread.py |
| 8 | P1-6 | project_selector 直接操作文件系统 | 改为调用 project_manager 方法 |
| 9 | P1-13 | EventBus monkey-patching | 改为通配符订阅 `subscribe("*")` |
| 10 | P2-14 | ILLMClient 死接口 | 已删除 |
| 11 | P2-16 | temperature=0 被 or 忽略 | 改为 `is not None` 判断 |
| 12 | P3-1 | _legacy 目录 | 已删除 |
| 13 | P3-2 | ops/ 单文件子目录 | 已扁平化 |
| 14 | P3-3 | tools.py 文件过大 | 已拆分为 tools/ 包 |

### ❌ 未修复（25项）

#### 🔴 仍需修复的架构问题（5项）

| # | 原编号 | 问题 | 文件 |
|---|--------|------|------|
| 1 | P1-1 | MainWindow 直接创建 GMAgent | `presentation/main_window.py:1283` |
| 2 | P1-3 | MainWindow 直接调用 project_manager 保存 | `presentation/main_window.py:1069` |
| 3 | P1-4 | GraphEditor 直接调用 project_manager 保存 | `presentation/editor/graph_editor.py:660` |
| 4 | P1-5 | ToolManager 直接调用 register_tool | `presentation/editor/tool_manager.py:399` |
| 5 | 架构 | tools 包绕过 Feature 子模块直接操作数据库 | `feature/ai/tools/*.py` |

#### 🟡 解耦未完成（5项）

| # | 原编号 | 问题 | 文件 |
|---|--------|------|------|
| 6 | P1-7 | DeployManager 内嵌 ZIP 打包逻辑 | `presentation/ops/deploy_manager.py:146` |
| 7 | P1-8 | KnowledgeEditor 数据与 UI 混合 | `presentation/ops/knowledge_editor.py` |
| 8 | P1-9 | MultiAgentOrchestrator 内嵌数据类和图算法 | `presentation/ops/multi_agent_orchestrator.py` |
| 9 | P1-10 | SafetyPanel 内嵌过滤逻辑 | `presentation/ops/safety_panel.py` |
| 10 | P1-12 | settings_dialog 直接导入 ApiTester | `presentation/dialogs/settings_dialog.py`（已改善但仍直接导入） |

#### 🟢 代码质量未清理（15项）

| # | 问题 | 文件 |
|---|------|------|
| 11 | `emit_async()` target 过滤仍用 `__qualname__`（emit 已修复但不一致） | `foundation/event_bus.py:241` |
| 12 | `self._retry_decorator` 未使用 | `foundation/llm/openai_client.py:78` |
| 13 | `_make_key` 方法未使用 | `foundation/cache.py:63` |
| 14 | `from foundation.database import get_db` 未使用 | `foundation/save_manager.py:20` |
| 15 | `deepseek_base_url_anthropic` 字段未使用 | `foundation/config.py:69` |
| 16 | `database_path` 默认值三处不一致 | `config.py` / `database.py` / `tools/context.py` |
| 17 | `StructuredFormatter` 硬编码业务字段名 | `foundation/logger.py:49` |
| 18 | `calculate_attack_bonus`/`calculate_ac` 未使用 | `core/calculators/combat.py:65` |
| 19 | calculators 用 dataclass 而非 Pydantic | `core/calculators/combat.py`, `ending.py` |
| 20 | `PersonalityTrait` 枚举未使用 | `core/models/entities.py:90` |
| 21 | `from datetime import datetime` 未使用 | `core/models/entities.py:13` |
| 22 | `Generic`/`TypeVar`/`T` 未使用 | `core/models/repository.py:19` |
| 23 | 玩家初始属性硬编码 | `core/state.py:87` |
| 24 | `apply_template` 浅拷贝 | `core/constants/npc_templates.py:87` |
| 25 | 10处未使用的导入（详见下方清单） | 多个 feature 文件 |

### 🆕 新发现的问题（5项）

| # | 严重程度 | 问题 | 文件 |
|---|---------|------|------|
| 1 | 🔴 Bug | `Event` 类未导入但被使用 → 运行时 NameError | `presentation/editor/graph_editor.py:669` |
| 2 | 🔴 Bug | `json` 模块未导入但被使用 → 运行时 NameError | `presentation/dialogs/project_selector.py:654` |
| 3 | 🔴 Bug | 测试文件引用已删除的 `ILLMClient` → ImportError | `tests/test_foundation_integration.py:128` |
| 4 | 🟡 不一致 | `emit()` 与 `emit_async()` target 过滤逻辑不一致 | `foundation/event_bus.py:197 vs 241` |
| 5 | 🟡 不一致 | `knowledge_tools.py` 与其他 tools 文件数据库访问模式不同 | `feature/ai/tools/knowledge_tools.py` |

### 未使用导入详细清单

| 文件 | 未使用导入 |
|------|-----------|
| `feature/ai/events.py` | `COMMAND_PARSED`, `COMMAND_EXECUTED`, `MEMORY_STORED` 常量（被导入但未使用） |
| `feature/ai/graph.py` | `default_graph = gm_graph` 兼容别名 |
| `feature/ai/nodes.py` | `handle_event` 兼容别名；函数内重复导入 `ALL_TOOLS` |
| `feature/ai/prompt_builder.py` | `_system_prompt_cache`, `_system_prompt_key` 属性 |
| `feature/ai/gm_agent.py` | 重复导入 `get_logger`（第69行） |
| `feature/dialogue/system.py` | `LogRepo`, `MemoryRepo` |
| `feature/item/system.py` | `Item`, `ItemType`, `ItemRarity` |
| `feature/narration/system.py` | `MemoryCategory` |
| `feature/ai/tools/core_tools.py` | `check_quest_prerequisites` 空实现 |

---

## 四、改进路线图（更新）

### Phase 1：紧急修复（新发现的 Bug）

1. 修复 `graph_editor.py` 缺少 `Event` 导入
2. 修复 `project_selector.py` 缺少 `json` 导入
3. 修复 `test_foundation_integration.py` 引用已删除的 `ILLMClient`
4. 同步 `emit_async()` 的 target 过滤逻辑与 `emit()` 一致

### Phase 2：继续解耦（P1 剩余）

5. MainWindow 改为通过 EventBus 请求 Agent 运行
6. GraphEditor/ToolManager 保存和注册改为 EventBus
7. DeployManager 打包逻辑提取到 Feature 层
8. KnowledgeEditor/MultiAgentOrchestrator/SafetyPanel 数据分离

### Phase 3：代码质量（P2 剩余）

9. 清理全部 25 项未修复的代码质量问题
10. 统一 dataclass → Pydantic
11. 提取硬编码为配置项

### Phase 4：tools 架构改进

12. tools 包改为通过 EventBus 调用 Feature 子模块
13. 统一 knowledge_tools.py 的数据库访问模式

---

## 五、配套指导文档

| 文档 | 适用性 |
|------|--------|
| `01-P0-架构违规修复指导.md` | **大部分已完成**，仅剩 tools EventBus 改造未执行 |
| `02-P1-Presentation解耦重构指导.md` | **部分完成**，#1 AgentThread/#6 project_selector/#9 event_monitor/#13 model_manager/#14 project_manager 已完成；其余待执行 |
| `03-P2-代码质量清理指导.md` | **未开始**，25项待清理 |
| `04-P3-目录结构优化指导.md` | **大部分已完成**，_legacy 删除、ops 扁平化、tools 拆分已完成 |
