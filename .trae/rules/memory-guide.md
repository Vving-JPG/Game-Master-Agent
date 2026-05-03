# 项目记忆导航

> 本文件引导 AI 渐进式加载 `d:\Game-Master-Agent\.trae\记忆\` 中的项目上下文。
> 遵循 3 层披露：**Index（查表）→ Activation（关键字段）→ Execution（完整加载）**。

---

## 当前项目状态

**当前架构**: PyQt6 Workbench + 四层重构 (P0-P7 全部完成)
**当前代码位置**: `d:\Game-Master-Agent\2workbench\`
**Agent 核心位置**: `d:\Game-Master-Agent\1agent_core\`

---

## Layer 1: 记忆索引（始终加载）

### 细粒度记忆文件（推荐优先使用）

#### P0 Foundation 层

| 文件 | 模块 | 说明 | 状态 |
|------|------|------|------|
| `记忆/p0_eventbus.md` | `foundation.event_bus` | EventBus 事件总线 | ✅ |
| `记忆/p0_config.md` | `foundation.config` | Config 配置管理 | ✅ |
| `记忆/p0_logger.md` | `foundation.logger` | Logger 日志系统 | ✅ |
| `记忆/p0_database.md` | `foundation.database` | Database 数据库连接 | ✅ |
| `记忆/p0_llm.md` | `foundation.llm` | LLM Client + ModelRouter | ✅ |
| `记忆/p0_save_manager.md` | `foundation.save_manager` | SaveManager 存档管理 | ✅ |
| `记忆/p0_cache.md` | `foundation.cache` | Cache LRU 缓存 | ✅ |
| `记忆/p0_resource_manager.md` | `foundation.resource_manager` | ResourceManager 资源管理 | ✅ |
| `记忆/p0_base.md` | `foundation.base` | Base 基类与接口 | ✅ |

#### P1 Core 层

| 文件 | 模块 | 说明 | 状态 |
|------|------|------|------|
| `记忆/p1_entities.md` | `core.models.entities` | Entities 数据模型 | ✅ |
| `记忆/p1_repository.md` | `core.models.repository` | Repository 数据访问 | ✅ |
| `记忆/p1_state.md` | `core.state` | LangGraph State | ✅ |
| `记忆/p1_calculators.md` | `core.calculators` | Calculators 纯函数计算器 | ✅ |
| `记忆/p1_constants.md` | `core.constants` | Constants 常量定义 | ✅ |

#### P2 Feature AI 层

| 文件 | 模块 | 说明 | 状态 |
|------|------|------|------|
| `记忆/p2_events.md` | `feature.ai.events` | Events 事件系统 | ✅ |
| `记忆/p2_command_parser.md` | `feature.ai.command_parser` | CommandParser 命令解析器 | ✅ |
| `记忆/p2_prompt_builder.md` | `feature.ai.prompt_builder` | PromptBuilder Prompt组装器 | ✅ |
| `记忆/p2_tools.md` | `feature.ai.tools` | Tools LangGraph工具 | ✅ |
| `记忆/p2_nodes.md` | `feature.ai.nodes` | Nodes 节点函数 | ✅ |
| `记忆/p2_graph.md` | `feature.ai.graph` | Graph StateGraph定义 | ✅ |
| `记忆/p2_gm_agent.md` | `feature.ai.gm_agent` | GMAgent Agent门面 | ✅ |

#### P3 Feature Services 层

| 文件 | 模块 | 说明 | 状态 |
|------|------|------|------|
| `记忆/p3_base_feature.md` | `feature.base` | BaseFeature Feature基类 | ✅ |
| `记忆/p3_feature_systems.md` | `feature.*.system` | 各子系统(战斗/对话/任务/物品/探索/叙事) | ✅ |
| `记忆/p3_registry.md` | `feature.registry` | FeatureRegistry 注册表 | ✅ |

#### P4 Presentation 层

| 文件 | 模块 | 说明 | 状态 |
|------|------|------|------|
| `记忆/p4_main_window.md` | `presentation.main_window` | MainWindow 主窗口 | ✅ |
| `记忆/p4_theme.md` | `presentation.theme` | Theme 主题管理 | ✅ |
| `记忆/p4_project_manager.md` | `presentation.project.manager` | ProjectManager 项目管理 | ✅ |

### 完整阶段记忆文件（归档参考）

| 文件 | 阶段 | 说明 | 状态 |
|------|------|------|------|
| `记忆/foundation_p0.md` | **P0** | Foundation 层完整文档 | 📦 归档 |
| `记忆/core_p1.md` | **P1** | Core 层完整文档 | 📦 归档 |
| `记忆/p2_langgraph_agent.md` | **P2** | Feature AI 层完整文档 | 📦 归档 |
| `记忆/p3_feature_services.md` | **P3** | Feature Services 层完整文档 | 📦 归档 |
| `记忆/p4_presentation_gui.md` | **P4** | Presentation 层完整文档 | 📦 归档 |
| `记忆/p5_gui_ops.md` | **P5** | 运营工具集完整文档 | 📦 归档 |
| `记忆/p6_state_api.md` | **P6** | 结构化状态 API 完整文档 | 📦 归档 |
| `记忆/p7_graph_integration.md` | **P7** | LangGraph 可视化集成完整文档 | 📦 归档 |
| `记忆/workbench_w1w4.md` | W1~W4 | PyQt6 Workbench 重构 | 📦 归档 |
| `记忆/workbench_w5w7.md` | W5~W7 | 流程编辑器、底部控制台 | 📦 归档 |

### 历史归档记忆（Vue3 版本 - 已弃用）

| 文件 | 阶段 | 说明 | 状态 |
|------|------|------|------|
| `记忆/v2.1.md` | V2 P0 | 清理重构 | 📦 归档 |
| `记忆/v2.2.md` | V2 P1 | 核心重构 | 📦 归档 |
| `记忆/v2.3.md` | V2 P2 | API扩展 | 📦 归档 |
| `记忆/v2.4.md` | V2 P3 | Vue3 WorkBench前端 | 📦 归档 |
| `记忆/1.md` ~ `记忆/6.md` | V1 | 早期版本历史 | 📦 归档 |

### 阶段依赖图

```
V1: 1 → 2 → 3 → 4 → 5 → 6
                              ↘
V2:                         v2.1 → v2.2 → v2.3 → v2.4 → v2.5 (Vue3 已弃用)
                                      ↘
PyQt6 WorkBench:                 workbench_w1w4 → workbench_w5w7
                                        ↓
四层重构:                         foundation_p0 (P0) ✅ → core_p1 (P1) ✅ → feature_p2 (P2) ✅ → feature_p3 (P3) ✅ → presentation_p4 (P4) ✅ → presentation_p5 (P5) ✅ → state_api_p6 (P6) ✅ → graph_integration_p7 (P7) ✅
```

---

## Layer 2: 激活规则（按需加载）

### 细粒度文件触发规则

| 触发关键词 | 加载文件 |
|-----------|----------|
| event_bus, Event, emit, subscribe | `记忆/p0_eventbus.md` |
| config, settings, provider | `记忆/p0_config.md` |
| logger, get_logger, logging | `记忆/p0_logger.md` |
| database, sqlite, get_db | `记忆/p0_database.md` |
| llm, chat_async, model_router | `记忆/p0_llm.md` |
| save, load_game, slot | `记忆/p0_save_manager.md` |
| cache, LRU, ttl | `记忆/p0_cache.md` |
| resource, scan_directory | `记忆/p0_resource_manager.md` |
| singleton, interface, ILLMClient | `记忆/p0_base.md` |
| entities, World, Player, NPC | `记忆/p1_entities.md` |
| repository, Repo, CRUD | `记忆/p1_repository.md` |
| AgentState, state, create_initial_state | `记忆/p1_state.md` |
| calculator, combat, damage | `记忆/p1_calculators.md` |
| template, personality, story | `记忆/p1_constants.md` |
| TURN_START, NODE_COMPLETED, lifecycle | `记忆/p2_events.md` |
| command_parser, parse, JSON | `记忆/p2_command_parser.md` |
| prompt_builder, template, build | `记忆/p2_prompt_builder.md` |
| tools, roll_dice, check_skill | `记忆/p2_tools.md` |
| nodes, node_handle_event, route | `记忆/p2_nodes.md` |
| graph, StateGraph, compile | `记忆/p2_graph.md` |
| GMAgent, run, run_sync | `记忆/p2_gm_agent.md` |
| BaseFeature, on_enable, on_disable | `记忆/p3_base_feature.md` |
| battle, dialogue, quest, item | `记忆/p3_feature_systems.md` |
| registry, feature_registry | `记忆/p3_registry.md` |
| MainWindow, 主窗口, 面板 | `记忆/p4_main_window.md` |
| theme, dark, light, QSS | `记忆/p4_theme.md` |
| project, create_project, open_project | `记忆/p4_project_manager.md` |

### 模块级触发规则（加载细粒度文件组）

| 开发模块 | 加载文件组 |
|----------|-----------|
| Foundation 层开发 | `p0_*.md` (9个文件) |
| Core 层开发 | `p1_*.md` (5个文件) |
| Feature AI 层开发 | `p2_*.md` (7个文件) |
| Feature Services 层开发 | `p3_*.md` (3个文件) |
| Presentation 层开发 | `p4_*.md` (3个文件) |

---

## Layer 3: 执行规则（完整加载）

### 按文件修改触发

| 修改文件 | 加载细粒度记忆 |
|----------|---------------|
| `foundation/event_bus.py` | `p0_eventbus.md` |
| `foundation/config.py` | `p0_config.md` |
| `foundation/logger.py` | `p0_logger.md` |
| `foundation/database.py` | `p0_database.md` |
| `foundation/llm/*.py` | `p0_llm.md` |
| `foundation/save_manager.py` | `p0_save_manager.md` |
| `foundation/cache.py` | `p0_cache.md` |
| `foundation/resource_manager.py` | `p0_resource_manager.md` |
| `foundation/base/*.py` | `p0_base.md` |
| `core/models/entities.py` | `p1_entities.md` |
| `core/models/repository.py` | `p1_repository.md` |
| `core/state.py` | `p1_state.md` |
| `core/calculators/*.py` | `p1_calculators.md` |
| `core/constants/*.py` | `p1_constants.md` |
| `feature/ai/events.py` | `p2_events.md` |
| `feature/ai/command_parser.py` | `p2_command_parser.md` |
| `feature/ai/prompt_builder.py` | `p2_prompt_builder.md` |
| `feature/ai/tools.py` | `p2_tools.md` |
| `feature/ai/nodes.py` | `p2_nodes.md` |
| `feature/ai/graph.py` | `p2_graph.md` |
| `feature/ai/gm_agent.py` | `p2_gm_agent.md` |
| `feature/base.py` | `p3_base_feature.md` |
| `feature/battle/*.py` | `p3_feature_systems.md` |
| `feature/dialogue/*.py` | `p3_feature_systems.md` |
| `feature/quest/*.py` | `p3_feature_systems.md` |
| `feature/item/*.py` | `p3_feature_systems.md` |
| `feature/exploration/*.py` | `p3_feature_systems.md` |
| `feature/narration/*.py` | `p3_feature_systems.md` |
| `feature/registry.py` | `p3_registry.md` |
| `presentation/main_window.py` | `p4_main_window.md` |
| `presentation/theme/*.py` | `p4_theme.md` |
| `presentation/project/manager.py` | `p4_project_manager.md` |

### 按开发任务触发

| 开发任务 | 加载文件 |
|----------|----------|
| 新功能开发 | 相关层的细粒度文件 |
| Bug 修复 | 对应模块的细粒度文件 |
| 代码重构 | 完整阶段文件（归档） |
| 架构设计 | 完整阶段文件（归档） |
| 性能优化 | 相关模块的细粒度文件 |

---

## 快速上下文恢复命令

```
# 新对话开始时，AI 应执行：
1. 读取本文件（已内置在 rules 中，自动加载）
2. 如果用户提到具体功能，按 Layer 2 激活对应细粒度文件
3. 如果用户说"继续开发/恢复上下文"，根据当前工作加载对应细粒度文件：
   - Foundation 层 → 加载 p0_*.md
   - Core 层 → 加载 p1_*.md
   - Feature AI 层 → 加载 p2_*.md
   - Feature Services 层 → 加载 p3_*.md
   - Presentation 层 → 加载 p4_*.md
```

---

## 项目结构速查

```
d:\Game-Master-Agent\
├── 2workbench/              # PyQt6 Workbench GUI + 四层重构
│   ├── foundation/          # ✅ P0 Foundation 层
│   ├── core/                # ✅ P1 Core 层
│   ├── feature/             # ✅ P2+P3 Feature 层
│   │   ├── ai/              # LangGraph Agent 核心 (P2)
│   │   ├── base.py          # Feature 基类 (P3)
│   │   ├── registry.py      # Feature 注册表 (P3)
│   │   ├── battle/          # 战斗系统 (P3)
│   │   ├── dialogue/        # NPC对话系统 (P3)
│   │   ├── quest/           # 任务系统 (P3)
│   │   ├── item/            # 物品系统 (P3)
│   │   ├── exploration/     # 探索系统 (P3)
│   │   └── narration/       # 叙事系统 (P3)
│   ├── presentation/        # ✅ P4 Presentation 层
│   └── ...
├── 1agent_core/             # Agent 核心逻辑
└── .trae/记忆/              # 开发记忆
    ├── p0_*.md              # P0 Foundation 细粒度 (9个)
    ├── p1_*.md              # P1 Core 细粒度 (5个)
    ├── p2_*.md              # P2 Feature AI 细粒度 (7个)
    ├── p3_*.md              # P3 Feature Services 细粒度 (3个)
    ├── p4_*.md              # P4 Presentation 细粒度 (3个)
    ├── *_p*.md              # 完整阶段文档 (归档)
    └── workbench_*.md       # Workbench 文档 (归档)
```

---

*最后更新: 2026-05-03*
*当前阶段: **细粒度记忆重构完成** ✅*
*架构状态: 四层重构完成 (P0 ✅, P1 ✅, P2 ✅, P3 ✅, P4 ✅, P5 ✅, P6 ✅, P7 ✅)，已弃用 Vue3，全面转向 PyQt6*
*记忆文件: 27个细粒度文件 + 11个归档文件*
