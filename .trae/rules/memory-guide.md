# 项目记忆导航

> 本文件引导 AI 渐进式加载 `d:\Game-Master-Agent\.trae\记忆\` 中的项目上下文。
> 遵循 3 层披露：**Index（查表）→ Activation（关键字段）→ Execution（完整加载）**。

---

## 当前项目状态

**当前架构**: PyQt6 Workbench + 四层重构 (P0 Foundation 已完成)
**当前代码位置**: `d:\Game-Master-Agent\2workbench\`
**Agent 核心位置**: `d:\Game-Master-Agent\1agent_core\`

---

## Layer 1: 记忆索引（始终加载）

### 当前有效记忆（PyQt6 版本 + 四层重构）

| 文件 | 阶段 | 说明 | 状态 |
|------|------|------|------|
| `记忆/foundation_p0.md` | **P0** | **Foundation 层**：EventBus/Config/Logger/Database/LLM/Cache/SaveManager | ✅ 已完成 |
| `记忆/core_p1.md` | **P1** | **Core 层**：Pydantic模型/LangGraphState/Repository/纯函数计算器 | ✅ 已完成 |
| `记忆/p2_langgraph_agent.md` | **P2** | **Feature AI 层**：LangGraph StateGraph/GM Agent/CommandParser/PromptBuilder | ✅ 已完成 |
| `记忆/p3_feature_services.md` | **P3** | **Feature Services 层**：Battle/Dialogue/Quest/Item/Exploration/Narration | ✅ 已完成 |
| `记忆/p4_presentation_gui.md` | **P4** | **Presentation 层**：IDE核心编辑器/主题/图编辑器/Prompt/工具管理 | ✅ 已完成 |
| `记忆/p5_gui_ops.md` | **P5** | **Presentation 层**：IDE运营工具集（调试器/评估/知识库/安全/编排/日志/部署） | ✅ 已完成 |
| `记忆/p6_state_api.md` | **P6** | **结构化状态 API**：Widget Tree / 应用状态 / Windows UIA | ✅ **当前** |
| `记忆/workbench_w1w4.md` | W1~W4 | PyQt6 Workbench 重构：新布局、七层导航、多态编辑器 | ✅ 当前 |
| `记忆/workbench_w5w7.md` | W5~W7 | 流程编辑器、底部控制台、Agent-Pack | ✅ 当前 |

### 历史归档记忆（Vue3 版本 - 已弃用）

| 文件 | 阶段 | 说明 | 状态 |
|------|------|------|------|
| `记忆/v2.1.md` | V2 P0 | 清理重构：砍掉tools/plugins，新增memory/skills/adapters | 📦 归档 |
| `记忆/v2.2.md` | V2 P1 | 核心重构：事件驱动GameMaster、CommandParser、PromptBuilder | 📦 归档 |
| `记忆/v2.3.md` | V2 P2 | API扩展：Workspace/Skills/Agent API、SSE流式推送 | 📦 归档 |
| `记忆/v2.4.md` | V2 P3 | Vue3 WorkBench前端（已弃用，参考架构设计） | 📦 归档 |
| `记忆/1.md` ~ `记忆/6.md` | V1 | 早期版本历史 | 📦 归档 |

### 阶段依赖图

```
V1: 1 → 2 → 3 → 4 → 5 → 6
                              ↘
V2:                         v2.1 → v2.2 → v2.3 → v2.4 → v2.5 (Vue3 已弃用)
                                      ↘
PyQt6 WorkBench:                 workbench_w1w4 → workbench_w5w7
                                        ↓
四层重构:                         foundation_p0 (P0) ✅ → core_p1 (P1) ✅ → feature_p2 (P2) ✅ → feature_p3 (P3) ✅ → presentation_p4 (P4) ✅ → presentation_p5 (P5) ✅ → state_api_p6 (P6) ✅
```

---

## Layer 2: 激活规则（按需加载）

### Feature AI 层开发（当前重点）

| 触发关键词 | 加载文件 | 加载层级 |
|-----------|----------|----------|
| GMAgent、gm_graph、StateGraph | `记忆/p2_langgraph_agent.md` §3.7+§3.8 | Activation |
| CommandParser、命令解析、parse_llm_output | `记忆/p2_langgraph_agent.md` §3.2 | Activation |
| PromptBuilder、Prompt组装 | `记忆/p2_langgraph_agent.md` §3.3 | Activation |
| SkillLoader、Skill加载、评分匹配 | `记忆/p2_langgraph_agent.md` §3.4 | Activation |
| Tools、LangGraph Tool、roll_dice | `记忆/p2_langgraph_agent.md` §3.5 | Activation |
| Nodes、节点函数、node_handle_event | `记忆/p2_langgraph_agent.md` §3.6 | Activation |
| Events、事件类型、TURN_START | `记忆/p2_langgraph_agent.md` §3.1 | Activation |

### Presentation 层开发（当前重点）

| 触发关键词 | 加载文件 | 加载层级 |
|-----------|----------|----------|
| Presentation、IDE、GUI、MainWindow | `记忆/p4_presentation_gui.md` §3 | Activation |
| Theme、主题、dark/light、QSS | `记忆/p4_presentation_gui.md` §3.1 | Activation |
| ProjectManager、项目管理、创建项目 | `记忆/p4_presentation_gui.md` §3.3 | Activation |
| GraphEditor、图编辑器、节点、连线 | `记忆/p4_presentation_gui.md` §3.4 | Activation |
| PromptEditor、Prompt管理、变量 | `记忆/p4_presentation_gui.md` §3.5 | Activation |
| ToolManager、工具管理、roll_dice | `记忆/p4_presentation_gui.md` §3.6 | Activation |

### P6 结构化状态 API 开发（当前重点）

| 触发关键词 | 加载文件 | 加载层级 |
|-----------|----------|----------|
| StateAPI、结构化状态、Widget Tree | `记忆/p6_state_api.md` §5 | Activation |
| /api/state、应用状态、get_state | `记忆/p6_state_api.md` §3 | Activation |
| /api/dom、DOM、Widget 树 | `记忆/p6_state_api.md` §2 | Activation |
| /api/uia、UIA、Windows Automation | `记忆/p6_state_api.md` §4 | Activation |
| selector、选择器、查找 Widget | `记忆/p6_state_api.md` §2.3 | Activation |
| gui_ctl.py、state、dom、uia、find | `记忆/p6_state_api.md` §7 | Activation |

### P5 运营工具集开发

| 触发关键词 | 加载文件 | 加载层级 |
|-----------|----------|----------|
| RuntimePanel、调试器、运行时调试 | `记忆/p5_gui_ops.md` §3.1 | Activation |
| ConsoleOutput、控制台、变量监视 | `记忆/p5_gui_ops.md` §3.1 | Activation |
| EventMonitor、事件监视器 | `记忆/p5_gui_ops.md` §3.1 | Activation |
| EvalWorkbench、评估工作台、Prompt评估 | `记忆/p5_gui_ops.md` §3.2 | Activation |
| KnowledgeEditor、知识库、NPC编辑器 | `记忆/p5_gui_ops.md` §3.3 | Activation |
| SafetyPanel、安全护栏、内容过滤 | `记忆/p5_gui_ops.md` §3.4 | Activation |
| MultiAgentOrchestrator、多Agent编排 | `记忆/p5_gui_ops.md` §3.5 | Activation |
| LogViewer、日志追踪 | `记忆/p5_gui_ops.md` §3.6 | Activation |
| DeployManager、部署管理 | `记忆/p5_gui_ops.md` §3.7 | Activation |

### Feature Services 层开发

| 触发关键词 | 加载文件 | 加载层级 |
|-----------|----------|----------|
| BaseFeature、Feature基类、on_enable | `记忆/p3_feature_services.md` §2 | Activation |
| BattleSystem、战斗系统、combat | `记忆/p3_feature_services.md` §3.1 | Activation |
| DialogueSystem、NPC对话、dialogue | `记忆/p3_feature_services.md` §3.2 | Activation |
| QuestSystem、任务系统、quest | `记忆/p3_feature_services.md` §3.3 | Activation |
| ItemSystem、物品系统、inventory | `记忆/p3_feature_services.md` §3.4 | Activation |
| ExplorationSystem、探索系统、exploration | `记忆/p3_feature_services.md` §3.5 | Activation |
| NarrationSystem、叙事系统、narration | `记忆/p3_feature_services.md` §3.6 | Activation |
| FeatureRegistry、注册表、feature_registry | `记忆/p3_feature_services.md` §4 | Activation |
| feature.battle、feature.quest、EventBus命名 | `记忆/p3_feature_services.md` §5 | Activation |

### Core 层开发

| 触发关键词 | 加载文件 | 加载层级 |
|-----------|----------|----------|
| Core、Pydantic、数据模型、entities | `记忆/core_p1.md` §数据模型 | Activation |
| Repository、Repo、数据访问、CRUD | `记忆/core_p1.md` §Repository层 | Activation |
| LangGraph、State、AgentState | `记忆/core_p1.md` §LangGraphState | Activation |
| 计算器、combat、战斗计算、ending | `记忆/core_p1.md` §纯函数计算器 | Activation |
| NPC模板、性格模板、story_templates | `记忆/core_p1.md` §常量定义 | Activation |
| MemoryRepo、统一记忆、SQLite记忆 | `记忆/core_p1.md` §新增表memories | Activation |

### Foundation 层开发

| 触发关键词 | 加载文件 | 加载层级 |
|-----------|----------|----------|
| Foundation、EventBus、事件总线 | `记忆/foundation_p0.md` §2.1 | Activation |
| Config、配置管理、settings | `记忆/foundation_p0.md` §2.2 | Activation |
| Logger、日志、get_logger | `记忆/foundation_p0.md` §2.3 | Activation |
| Database、SQLite、get_db | `记忆/foundation_p0.md` §2.4 | Activation |
| LLM、OpenAI、chat_async、stream | `记忆/foundation_p0.md` §2.5 | Activation |
| ModelRouter、模型路由、路由规则 | `记忆/foundation_p0.md` §2.6 | Activation |
| SaveManager、存档、save_game | `记忆/foundation_p0.md` §2.7 | Activation |
| Cache、LRU、缓存 | `记忆/foundation_p0.md` §2.8 | Activation |
| ResourceManager、资源管理、文件操作 | `记忆/foundation_p0.md` §2.9 | Activation |
| Singleton、单例、interfaces | `记忆/foundation_p0.md` §2.10 | Activation |

### 当前 PyQt6 Workbench 开发

| 触发关键词 | 加载文件 | 加载层级 |
|-----------|----------|----------|
| WorkBench、PyQt6、GUI、主窗口 | `记忆/workbench_w1w4.md` §W1 | Activation |
| 资源树、七层导航、ResourceTree | `记忆/workbench_w1w4.md` §W2 | Activation |
| 多态编辑器、EditorStack、MD编辑器 | `记忆/workbench_w1w4.md` §W3 | Activation |
| YAML工作流、WorkflowEditor | `记忆/workbench_w1w4.md` §W4 | Activation |
| Vue Flow、流程编辑器、节点编辑 | `记忆/workbench_w5w7.md` §W5 | Activation |
| 底部控制台、ConsoleTabs、SSE | `记忆/workbench_w5w7.md` §W6 | Activation |
| Agent-Pack、导入导出、pack | `记忆/workbench_w5w7.md` §W7 | Activation |

### Agent 核心开发（1agent_core）

| 触发关键词 | 加载文件 | 加载层级 |
|-----------|----------|----------|
| CommandParser、命令解析 | `记忆/v2.2.md` §1.1 | Activation |
| PromptBuilder、Prompt组装 | `记忆/v2.2.md` §1.2+§1.3 | Activation |
| GameMaster、事件驱动 | `记忆/v2.2.md` §2.3 | Activation |
| memory、workspace、文件IO | `记忆/v2.1.md` §4 | Activation |
| Skill、技能定义、SKILL.md | `记忆/v2.1.md` §5 | Activation |
| adapter、适配器、TextAdapter | `记忆/v2.1.md` §6 | Activation |
| 数据库、Repository、SQLite | `记忆/2.md` §2 + §4 | Activation |
| NPC、对话、好感度 | `记忆/4.md` §1 | Activation |
| 任务、quest、剧情 | `记忆/4.md` §2 | Activation |
| 战斗、combat、伤害计算 | `记忆/4.md` §3 | Activation |

---

## Layer 3: 执行规则（完整加载）

**以下情况加载完整文件：**

### Foundation 层（P0）
1. **修改 foundation/ 任何文件** → 加载 `记忆/foundation_p0.md` 全文
2. **需要理解四层架构设计** → 加载 `记忆/foundation_p0.md` §1+§3+§5

### Feature AI 层（P2）
3. **修改 feature/ai/ 任何文件** → 加载 `记忆/p2_langgraph_agent.md` 全文
4. **修改 feature/ai/graph.py** → 加载 `记忆/p2_langgraph_agent.md` §3.7
5. **修改 feature/ai/nodes.py** → 加载 `记忆/p2_langgraph_agent.md` §3.6
6. **修改 feature/ai/gm_agent.py** → 加载 `记忆/p2_langgraph_agent.md` §3.8
7. **修改 feature/ai/command_parser.py** → 加载 `记忆/p2_langgraph_agent.md` §3.2
8. **修改 feature/ai/prompt_builder.py** → 加载 `记忆/p2_langgraph_agent.md` §3.3
9. **修改 feature/ai/skill_loader.py** → 加载 `记忆/p2_langgraph_agent.md` §3.4
10. **修改 feature/ai/tools.py** → 加载 `记忆/p2_langgraph_agent.md` §3.5
11. **修改 feature/ai/events.py** → 加载 `记忆/p2_langgraph_agent.md` §3.1

### Core 层（P1）
12. **修改 core/ 任何文件** → 加载 `记忆/core_p1.md` 全文
13. **修改 core/models/entities.py** → 加载 `记忆/core_p1.md` §数据模型
14. **修改 core/models/repository.py** → 加载 `记忆/core_p1.md` §Repository层
15. **修改 core/state.py** → 加载 `记忆/core_p1.md` §LangGraphState
16. **修改 core/calculators/** → 加载 `记忆/core_p1.md` §纯函数计算器
17. **修改 core/constants/** → 加载 `记忆/core_p1.md` §常量定义

### Presentation 层（P4）
22. **修改 presentation/ 任何文件（除 ops/）** → 加载 `记忆/p4_presentation_gui.md` 全文
23. **修改 presentation/main_window.py** → 加载 `记忆/p4_presentation_gui.md` §3.2
24. **修改 presentation/theme/** → 加载 `记忆/p4_presentation_gui.md` §3.1
25. **修改 presentation/project/** → 加载 `记忆/p4_presentation_gui.md` §3.3
26. **修改 presentation/editor/graph_editor.py** → 加载 `记忆/p4_presentation_gui.md` §3.4
27. **修改 presentation/editor/prompt_editor.py** → 加载 `记忆/p4_presentation_gui.md` §3.5
28. **修改 presentation/editor/tool_manager.py** → 加载 `记忆/p4_presentation_gui.md` §3.6

### P6 结构化状态 API
29. **修改 presentation/state_api.py** → 加载 `记忆/p6_state_api.md` 全文
30. **修改 presentation/server.py 添加状态 API 端点** → 加载 `记忆/p6_state_api.md` §6
31. **修改 .trae/skills/workbench-gui/gui_ctl.py** → 加载 `记忆/p6_state_api.md` §7

### P5 运营工具集
32. **修改 presentation/ops/ 任何文件** → 加载 `记忆/p5_gui_ops.md` 全文
33. **修改 presentation/ops/debugger/** → 加载 `记忆/p5_gui_ops.md` §3.1
34. **修改 presentation/ops/evaluator/** → 加载 `记忆/p5_gui_ops.md` §3.2
35. **修改 presentation/ops/knowledge/** → 加载 `记忆/p5_gui_ops.md` §3.3
36. **修改 presentation/ops/safety/** → 加载 `记忆/p5_gui_ops.md` §3.4
37. **修改 presentation/ops/multi_agent/** → 加载 `记忆/p5_gui_ops.md` §3.5
38. **修改 presentation/ops/logger_panel/** → 加载 `记忆/p5_gui_ops.md` §3.6
39. **修改 presentation/ops/deploy/** → 加载 `记忆/p5_gui_ops.md` §3.7

### Feature Services 层（P3）
9. **修改 feature/ 任何文件（除 ai/）** → 加载 `记忆/p3_feature_services.md` 全文
10. **修改 feature/base.py** → 加载 `记忆/p3_feature_services.md` §2
11. **修改 feature/battle/** → 加载 `记忆/p3_feature_services.md` §3.1
12. **修改 feature/dialogue/** → 加载 `记忆/p3_feature_services.md` §3.2
13. **修改 feature/quest/** → 加载 `记忆/p3_feature_services.md` §3.3
14. **修改 feature/item/** → 加载 `记忆/p3_feature_services.md` §3.4
15. **修改 feature/exploration/** → 加载 `记忆/p3_feature_services.md` §3.5
16. **修改 feature/narration/** → 加载 `记忆/p3_feature_services.md` §3.6
17. **修改 feature/registry.py** → 加载 `记忆/p3_feature_services.md` §4

### 当前 PyQt6 Workbench
18. **修改 Workbench GUI 代码** → 加载 `记忆/workbench_w1w4.md` + `记忆/workbench_w5w7.md` 全文
19. **修改 widgets/** → 加载 `记忆/workbench_w1w4.md` §W2+§W3
20. **修改 workflow 相关** → 加载 `记忆/workbench_w1w4.md` §W4 + `记忆/workbench_w5w7.md` §W5
21. **修改 console/bridge** → 加载 `记忆/workbench_w5w7.md` §W6

### Agent Core (1agent_core)
13. **修改 command_parser.py** → 加载 `记忆/v2.2.md` §1.1
14. **修改 prompt_builder.py** → 加载 `记忆/v2.2.md` §1.2+§1.3
15. **修改 game_master.py** → 加载 `记忆/v2.2.md` §2.3
16. **修改 memory/** → 加载 `记忆/v2.1.md` §4（注意：已废弃，参考 `记忆/core_p1.md` §统一记忆）
17. **修改 skills/** → 加载 `记忆/v2.1.md` §5
18. **修改 adapters/** → 加载 `记忆/v2.1.md` §6

### 历史参考（仅当需要理解演变）
19. **需要理解 V1 历史** → 加载 `记忆/1.md` ~ `记忆/6.md`
20. **需要理解 Vue3 架构** → 加载 `记忆/v2.4.md`（参考设计，不用于当前代码）

---

## 快速上下文恢复命令

```
# 新对话开始时，AI 应执行：
1. 读取本文件（已内置在 rules 中，自动加载）
2. 如果用户提到具体功能，按 Layer 2 激活对应文件
3. 如果用户说"继续开发/恢复上下文"，根据当前工作加载对应文件：
   - Foundation 层 (P0) → 加载 foundation_p0.md
   - Core 层 (P1) → 加载 core_p1.md
   - Feature AI 层 (P2) → 加载 p2_langgraph_agent.md
   - Feature Services 层 (P3) → 加载 p3_feature_services.md
   - Presentation 层 (P4) → 加载 p4_presentation_gui.md
   - P5 运营工具集 → 加载 p5_gui_ops.md
   - P6 结构化状态 API → 加载 p6_state_api.md
   - Workbench GUI → 加载 workbench_w1w4.md + workbench_w5w7.md
   - Agent Core (旧版) → 加载 v2.2.md §2.3 + v2.1.md §5+§6（已废弃，仅参考）
```

---

## 项目结构速查

```
d:\Game-Master-Agent\
├── 2workbench/              # PyQt6 Workbench GUI + 四层重构
│   ├── foundation/          # ✅ P0 Foundation 层（已完成）
│   │   ├── event_bus.py
│   │   ├── config.py
│   │   ├── logger.py
│   │   ├── database.py
│   │   ├── llm/
│   │   ├── save_manager.py
│   │   ├── cache.py
│   │   ├── resource_manager.py
│   │   └── base/
│   ├── core/                # ✅ P1 Core 层（已完成）
│   ├── feature/             # ✅ P2+P3 Feature 层（已完成）
│   │   ├── ai/              # LangGraph Agent 核心 (P2)
│   │   │   ├── graph.py
│   │   │   ├── nodes.py
│   │   │   ├── gm_agent.py
│   │   │   ├── command_parser.py
│   │   │   ├── prompt_builder.py
│   │   │   ├── skill_loader.py
│   │   │   ├── tools.py
│   │   │   └── events.py
│   │   ├── base.py          # Feature 基类 (P3)
│   │   ├── registry.py      # Feature 注册表 (P3)
│   │   ├── battle/          # 战斗系统 (P3)
│   │   ├── dialogue/        # NPC对话系统 (P3)
│   │   ├── quest/           # 任务系统 (P3)
│   │   ├── item/            # 物品系统 (P3)
│   │   ├── exploration/     # 探索系统 (P3)
│   │   ├── narration/       # 叙事系统 (P3)
│   │   └── skill/           # 玩家技能系统 (占位)
│   ├── presentation/        # ✅ P4 Presentation 层（已完成）
│   ├── _legacy/             # 旧代码保留供参考
│   ├── widgets/             # UI 组件
│   ├── bridge/              # Agent 通信
│   └── ...
├── 1agent_core/             # Agent 核心逻辑
│   ├── src/
│   │   ├── game_master.py   # 主循环
│   │   ├── command_parser.py
│   │   ├── prompt_builder.py
│   │   ├── memory/          # 记忆系统
│   │   ├── skills/          # 技能系统
│   │   └── adapters/        # 适配器
│   └── ...
└── .trae/记忆/              # 开发记忆
    ├── foundation_p0.md     # ✅ P0 Foundation（已完成）
    ├── core_p1.md           # ✅ P1 Core（已完成）
    ├── p2_langgraph_agent.md # ✅ P2 Feature AI（已完成）
    ├── p3_feature_services.md # ✅ P3 Feature Services（已完成）
    ├── p4_presentation_gui.md # ✅ P4 Presentation（已完成）
    ├── p5_gui_ops.md        # ✅ P5 运营工具集（已完成）
    ├── p6_state_api.md      # ✅ P6 结构化状态 API（当前有效）
    ├── workbench_w1w4.md    # ✅ 当前有效
    ├── workbench_w5w7.md    # ✅ 当前有效
    ├── v2.1.md ~ v2.4.md    # 📦 归档（Vue3版本）
    └── 1.md ~ 6.md          # 📦 归档（V1版本）
```

---

*最后更新: 2026-05-02*
*当前阶段: **P6 结构化状态 API 完成** ✅*
*架构状态: 四层重构完成 (P0 ✅, P1 ✅, P2 ✅, P3 ✅, P4 ✅, P5 ✅, P6 ✅)，已弃用 Vue3，全面转向 PyQt6*
