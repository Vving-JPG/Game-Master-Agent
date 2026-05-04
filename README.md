# Game Master Agent - PyQt6 Workbench

通用游戏驱动 Agent IDE —— 像 Trae 驱动代码一样驱动游戏。

## 架构

采用四层架构设计，从底层基础设施到上层界面清晰分层：

```
┌─────────────────────────────────────────────────────────────┐
│  P4: Presentation 层 (PyQt6 IDE)                            │
│  ┌──────────┬──────────┬──────────┬──────────────────────┐  │
│  │  Project │  Editor  │   Ops    │   State API Server   │  │
│  │  Manager │  Stack   │  Panels  │   (DOM/UIA/State)    │  │
│  └──────────┴──────────┴──────────┴──────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  P3: Feature Services 层 (游戏系统)                          │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │  Battle  │ Dialogue │  Quest   │   Item   │Narration │   │
│  │  System  │  System  │  System  │  System  │  System  │   │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┤   │
│  │Exploration│ Services │ Registry │  Project │          │   │
│  │  System  │(7 services)│         │ Manager  │          │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
├─────────────────────────────────────────────────────────────┤
│  P2: Feature AI 层 (LangGraph Agent)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  StateGraph: handle_event → build_prompt → llm       │   │
│  │              → parse_output → execute → update_mem   │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  CommandParser │ PromptBuilder │ SkillLoader │ Tools  │   │
│  │  GraphCompiler │  AgentRunner  │  GMAgent   │ Events  │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  P1: Core 层 (数据模型与计算)                                 │
│  ┌────────────────────┬──────────────────────────────────┐  │
│  │  Pydantic Entities │  Repository (CRUD)               │  │
│  ├────────────────────┼──────────────────────────────────┤  │
│  │  LangGraph State   │  Calculators (combat/ending)     │  │
│  ├────────────────────┼──────────────────────────────────┤  │
│  │  NPC Templates     │  Story Templates                 │  │
│  └────────────────────┴──────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  P0: Foundation 层 (基础设施)                                 │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │EventBus  │ Config   │ Database │   LLM    │  Cache   │   │
│  │ Logger   │ SaveMgr  │ Resource │  Router  │  Base    │   │
│  │HotReload │          │          │OpenAI Clt│Interfaces│   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 四层架构说明

| 层级 | 路径 | 职责 | 关键组件 |
|------|------|------|----------|
| **P0 Foundation** | `2workbench/foundation/` | 基础设施 | EventBus, Config, Database, LLM Router, Cache, SaveManager, HotReload, ResourceManager, Interfaces |
| **P1 Core** | `2workbench/core/` | 数据与计算 | Entities (World/Player/NPC/Item/Quest/Location), Repository, AgentState, Calculators, Templates |
| **P2 Feature AI** | `2workbench/feature/ai/` | LangGraph Agent | Graph, Nodes, GM Agent, GraphCompiler, AgentRunner, CommandParser, PromptBuilder, SkillLoader, Tools (5 categories) |
| **P3 Feature Services** | `2workbench/feature/` | 游戏系统 | Battle, Dialogue, Quest, Item, Narration, Exploration, Project Manager, Services (7), Registry |
| **P4 Presentation** | `2workbench/presentation/` | PyQt6 IDE | MainWindow (3-panel), Editors (Graph/Prompt/Skill/PromptTester), Ops Panels (Debugger/EventMonitor/LogViewer), Theme, Server, State API |

### 依赖规则

- **上层可以依赖下层**: Presentation → Feature → Core → Foundation
- **下层绝对不能引用上层**: Foundation 不能引用 Core，Core 不能引用 Feature，以此类推
- **同层模块间仅通过 EventBus 通信**: 禁止直接依赖
- **无循环依赖**: 所有依赖都是单向的

---

## 核心特性

### P0 Foundation 层特性
- **事件总线 (EventBus)**: 全局事件系统，支持同步异步订阅
- **配置管理 (Config)**: Pydantic Settings 驱动，支持 .env 文件
- **结构化日志 (Logger)**: 彩色控制台输出 + 文件日志
- **SQLite 数据库 (Database)**: WAL 模式，线程安全连接池
- **LLM 客户端 (LLM)**: ModelRouter 智能路由 + OpenAI 兼容客户端
- **LRU 缓存 (Cache)**: 带 TTL 支持的内存缓存
- **热重载 (HotReload)**: 开发模式下代码自动重新加载
- **资源管理 (ResourceManager)**: 文件系统扫描与资源加载
- **存档管理 (SaveManager)**: 多槽位存档系统
- **基础接口 (Interfaces)**: IFeature, ITool 等核心抽象

### P1 Core 层特性
- **数据实体 (Entities)**: World, Player, NPC, Item, Quest, Location, Relationship 等 Pydantic 模型
- **数据仓库 (Repository)**: Repository 模式，统一 CRUD 接口
- **LangGraph 状态 (AgentState)**: 完整的 Agent 状态定义
- **纯函数计算器 (Calculators)**: 战斗计算、结局判定等无副作用函数
- **NPC 模板 (NPC Templates)**: Big Five 人格系统 + 预置模板
- **故事模板 (Story Templates)**: TRPG 任务与情节模板

### P2 Feature AI 层特性
- **LangGraph StateGraph**: 可编排的 Agent 工作流
- **图编译器 (GraphCompiler)**: JSON → StateGraph 编译器，支持条件边
- **GM Agent (GMAgent)**: Agent 门面，支持同步异步运行
- **Agent 运行器 (AgentRunner)**: 后台服务，管理 Agent 生命周期
- **命令解析器 (CommandParser)**: 4 级 JSON 解析回退机制
- **Prompt 构建器 (PromptBuilder)**: 动态组装 Prompt 模板
- **Skill 加载器 (SkillLoader)**: Markdown + YAML front matter 格式
- **工具系统 (Tools)**: 5 大类工具，共 20+ 工具函数
  - **核心工具**: roll_dice, check_skill, update_player_stat, get_player_info
  - **物品工具**: give_item, remove_item, get_inventory
  - **知识库工具**: create_npc, search_npcs, create_location, search_locations, create_item, search_items, create_quest, search_quests
  - **世界工具**: update_world, get_world
  - **任务工具**: update_quest, complete_quest
- **事件系统**: TURN_START, NODE_START, NODE_COMPLETED, AGENT_STOP 等事件

### P3 Feature Services 层特性
- **6 大游戏系统**:
  - 战斗系统 (BattleSystem)
  - 对话系统 (DialogueSystem)
  - 任务系统 (QuestSystem)
  - 物品系统 (ItemSystem)
  - 探索系统 (ExplorationSystem)
  - 叙事系统 (NarrationSystem)
- **Feature 基类 (BaseFeature)**: 统一的启用/禁用/事件订阅接口
- **Feature 注册表 (FeatureRegistry)**: 管理所有 Feature 系统
- **项目管理 (ProjectManager)**:
  - 3 种项目模板: 空白项目, TRPG 游戏, 对话机器人
  - 项目创建/打开/保存/打包
- **7 大服务**:
  - KnowledgeService: 知识库管理（物品/任务/地点导入导出）
  - PackagingService: 项目打包为 ZIP
  - ModelManagerService: 模型管理
  - MultiAgentService: 多 Agent 编排
  - SafetyService: 安全审核（正则验证）
  - ApiTesterService: API 测试器
- **工具注册服务 (ToolRegistrationService)**: 统一工具注册

### P4 Presentation 层特性
- **Godot 风格项目选择器**: 最近项目列表 + 新建项目
- **主窗口 (3 面板布局)**:
  - 左侧: 项目管理器 + 文件树
  - 中间: 编辑器栈（图编辑器/Prompt 编辑器/Skill 管理器/Prompt 测试器）
  - 右侧: 运营工具面板（调试器/事件监控/日志查看器）
- **图编辑器 (GraphEditor)**:
  - 拖拽式节点创建
  - 连线支持
  - 节点删除
  - 自动 ID 生成
  - 图保存/加载
- **Prompt 编辑器 (PromptEditor)**:
  - 语法高亮
  - 保存/加载
  - 历史记录
- **Skill 管理器 (SkillManager)**:
  - Skill 文件管理
  - 编辑器集成
- **调试器 (RuntimePanel)**:
  - Agent 运行控制
  - 输入历史
  - 状态显示
  - 统计信息
- **事件监控 (EventMonitor)**: 实时事件流
- **日志查看器 (LogViewer)**:
  - 日志搜索
  - 过滤
  - 文件监控
- **主题管理**: 深色/浅色主题切换
- **HTTP API 服务器**: State API + 操作 API
- **快捷键支持**: Ctrl+S, Ctrl+Z, Ctrl+Y, F5, Shift+F5 等

---

## 快速开始

### 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 配置环境

创建 `.env` 文件（参考 `.env.template`）：

```env
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 启动 IDE

```bash
# 主入口（推荐）
cd 2workbench
python app.py

# 或使用模块方式
python -m 2workbench.app
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--project`, `-p` | 直接打开指定项目路径 |
| `--version`, `-v` | 显示版本号 |
| `--no-gui` | 无头模式（仅测试） |
| `--theme`, `-t` | 主题模式 (dark/light, 默认: dark) |
| `--port` | HTTP 服务器端口 (默认: 18080) |
| `--debug`, `-d` | 调试模式 |
| `--log-level` | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `--skip-selector` | 跳过项目选择器 |
| `--dev` | 开发模式（启用热重载） |

---

## 项目结构

```
Game-Master-Agent/
├── 2workbench/                    # PyQt6 Workbench IDE
│   ├── foundation/                # P0: 基础设施层
│   │   ├── __init__.py            # 层导出
│   │   ├── event_bus.py           # 事件总线（单例）
│   │   ├── config.py              # 配置管理（Pydantic Settings）
│   │   ├── database.py            # SQLite 数据库（WAL 模式）
│   │   ├── logger.py              # 结构化日志系统
│   │   ├── cache.py               # LRU 缓存（带 TTL）
│   │   ├── save_manager.py        # 存档管理器
│   │   ├── resource_manager.py    # 资源管理器
│   │   ├── hot_reload.py          # 热重载（开发模式）
│   │   ├── base/                  # 基类与接口
│   │   │   ├── __init__.py
│   │   │   └── interfaces.py      # IFeature, ITool, ILLMClient
│   │   └── llm/                   # LLM 客户端
│   │       ├── __init__.py
│   │       ├── base.py            # 抽象基类
│   │       ├── model_router.py    # 模型路由器
│   │       └── openai_client.py   # OpenAI 兼容客户端
│   ├── core/                      # P1: 核心数据层
│   │   ├── __init__.py
│   │   ├── state.py               # LangGraph AgentState
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── entities.py        # Pydantic 实体（World/Player/NPC/Item/Quest/Location）
│   │   │   ├── repository.py      # Repository 模式（CRUD）
│   │   │   └── schema.sql         # 数据库架构
│   │   ├── calculators/           # 纯函数计算器
│   │   │   ├── __init__.py
│   │   │   ├── combat.py          # 战斗计算
│   │   │   └── ending.py          # 结局判定
│   │   └── constants/             # 常量定义
│   │       ├── __init__.py
│   │       ├── npc_templates.py   # NPC 模板（Big Five 人格）
│   │       └── story_templates.py # 故事/任务模板
│   ├── feature/                   # P2+P3: 功能层
│   │   ├── __init__.py
│   │   ├── base.py                # BaseFeature 抽象基类
│   │   ├── registry.py            # FeatureRegistry（Feature 管理）
│   │   ├── project/               # 项目管理
│   │   │   ├── __init__.py
│   │   │   └── manager.py         # ProjectManager（3 种模板）
│   │   ├── ai/                    # P2: LangGraph Agent
│   │   │   ├── __init__.py
│   │   │   ├── events.py          # AI 事件定义
│   │   │   ├── command_parser.py  # 命令解析器（4 级回退）
│   │   │   ├── prompt_builder.py  # Prompt 构建器
│   │   │   ├── skill_loader.py    # Skill 加载器
│   │   │   ├── nodes.py           # LangGraph 节点函数
│   │   │   ├── graph.py           # StateGraph 定义
│   │   │   ├── graph_compiler.py  # GraphJSON → StateGraph 编译器
│   │   │   ├── gm_agent.py        # GMAgent（Agent 门面）
│   │   │   ├── agent_runner.py    # AgentRunner（后台服务）
│   │   │   └── tools/             # 工具系统（5 大类）
│   │   │       ├── __init__.py
│   │   │       ├── context.py     # ToolContext（DB 访问）
│   │   │       ├── registry.py    # ToolRegistry
│   │   │       ├── tool_registration_service.py  # 工具注册服务
│   │   │       ├── core_tools.py  # 核心工具（roll_dice 等）
│   │   │       ├── item_tools.py  # 物品工具
│   │   │       ├── knowledge_tools.py  # 知识库工具
│   │   │       ├── quest_tools.py # 任务工具
│   │   │       └── world_tools.py # 世界工具
│   │   ├── services/              # 服务层（7 大服务）
│   │   │   ├── __init__.py
│   │   │   ├── knowledge_service.py  # 知识库管理
│   │   │   ├── packaging_service.py  # 项目打包
│   │   │   ├── model_manager.py   # 模型管理
│   │   │   ├── multi_agent_service.py  # 多 Agent 编排
│   │   │   ├── safety_service.py  # 安全审核
│   │   │   └── api_tester.py      # API 测试器
│   │   ├── battle/                # P3: 战斗系统
│   │   │   ├── __init__.py
│   │   │   └── system.py
│   │   ├── dialogue/              # P3: 对话系统
│   │   │   ├── __init__.py
│   │   │   └── system.py
│   │   ├── quest/                 # P3: 任务系统
│   │   │   ├── __init__.py
│   │   │   └── system.py
│   │   ├── item/                  # P3: 物品系统
│   │   │   ├── __init__.py
│   │   │   └── system.py
│   │   ├── exploration/           # P3: 探索系统
│   │   │   ├── __init__.py
│   │   │   └── system.py
│   │   └── narration/             # P3: 叙事系统
│   │       ├── __init__.py
│   │       └── system.py
│   ├── presentation/              # P4: 表现层
│   │   ├── __init__.py
│   │   ├── main_window.py         # 主窗口（3 面板布局）
│   │   ├── agent_thread.py        # Agent 执行线程
│   │   ├── server.py              # HTTP API 服务器
│   │   ├── state_api.py           # 结构化状态 API
│   │   ├── theme/                 # 主题管理
│   │   │   ├── __init__.py
│   │   │   ├── manager.py         # ThemeManager
│   │   │   ├── dark.qss           # 深色主题
│   │   │   └── light.qss          # 浅色主题
│   │   ├── editor/                # 编辑器组件
│   │   │   ├── __init__.py
│   │   │   ├── graph_editor.py    # 图编辑器（拖拽/连线/删除）
│   │   │   ├── prompt_editor.py   # Prompt 编辑器
│   │   │   ├── prompt_tester.py   # Prompt 测试器
│   │   │   └── skill_manager.py   # Skill 管理器
│   │   ├── ops/                   # 运营工具面板
│   │   │   ├── __init__.py
│   │   │   ├── log_viewer.py      # 日志查看器（搜索/过滤/监控）
│   │   │   └── debugger/          # 调试器
│   │   │       ├── __init__.py
│   │   │       ├── runtime_panel.py  # 运行时面板
│   │   │       └── event_monitor.py  # 事件监控
│   │   ├── project/               # 项目管理（已弃用，移至 feature）
│   │   │   ├── __init__.py
│   │   │   ├── manager.py
│   │   │   └── new_dialog.py
│   │   ├── dialogs/               # 对话框
│   │   │   ├── __init__.py
│   │   │   ├── project_selector.py  # 项目选择器（Godot 风格）
│   │   │   ├── settings_dialog.py  # 设置对话框
│   │   │   └── model_manager.py   # 模型管理器对话框
│   │   └── widgets/               # 通用组件
│   │       ├── __init__.py
│   │       ├── base.py            # BaseWidget
│   │       ├── styled_button.py   # StyledButton
│   │       └── search_bar.py      # SearchBar
│   ├── skills/                    # Skill 定义
│   │   └── world_building/
│   │       └── SKILL.md
│   ├── tests/                     # 测试文件
│   │   ├── test_event_bus.py
│   │   ├── test_foundation_integration.py
│   │   └── test_core_integration.py
│   ├── workflows/                 # 工作流文档
│   │   ├── add_feature.md
│   │   ├── add_tool.md
│   │   ├── debug_agent.md
│   │   ├── hotfix.md
│   │   └── test_layer.md
│   ├── config/                    # 配置文件
│   │   └── model_rules.json
│   ├── app.py                     # 应用入口（推荐）
│   ├── main.py                    # 旧入口（无 qasync）
│   └── .env.template              # 环境变量模板
├── .trae/                         # Trae IDE 配置
│   ├── rules/                     # 项目规则
│   │   ├── 1.md
│   │   └── memory-guide.md
│   ├── skills/                    # Skill 定义
│   │   ├── pyqt6-development/
│   │   └── workbench-gui/
│   └── 记忆/                       # 开发记忆文档（细粒度）
│       ├── p0_*.md                # P0 Foundation 层文档
│       ├── p1_*.md                # P1 Core 层文档
│       ├── p2_*.md                # P2 Feature AI 层文档
│       ├── p3_*.md                # P3 Feature Services 层文档
│       ├── p4_*.md                # P4 Presentation 层文档
│       ├── opt_p*.md              # 优化阶段文档
│       ├── p*_agent_fix.md        # Agent 运行流程优化文档
│       └── *_p*.md                # 完整阶段文档（归档）
├── pyproject.toml                 # 项目配置
├── uv.toml                        # uv 配置
├── uv.lock                        # uv 锁文件
├── .python-version                # Python 版本
├── .gitignore
├── README.md                      # 本文档
└── 0.md                           # 其他文档
```

---

## 测试

```bash
# 运行所有测试
uv run pytest 2workbench/tests/ -v

# 运行特定模块
uv run pytest 2workbench/tests/test_foundation_integration.py -v
uv run pytest 2workbench/tests/test_core_integration.py -v
uv run pytest 2workbench/tests/test_event_bus.py -v
```

---

## 代码质量

```bash
# 代码格式化与检查
uv run ruff check 2workbench/
uv run ruff format 2workbench/

# 类型检查
uv run mypy 2workbench/
```

---

## State API

Workbench 提供结构化状态 API，支持自动化测试和外部工具集成：

```python
# Widget Tree (DOM)
GET /api/dom/tree              # 获取完整 Widget 树
GET /api/dom/find?selector=... # 查找特定 Widget

# Application State
GET /api/state                 # 获取应用状态
GET /api/state/player          # 获取玩家状态

# Windows UIA
GET /api/uia/element           # UIA 元素信息
```

---

## 技术栈

- **GUI**: PyQt6 + qasync
- **后端**: Python 3.11+
- **AI**: LangGraph + LangChain Core + DeepSeek API (OpenAI 兼容)
- **数据**: Pydantic + Pydantic Settings + SQLite
- **包管理**: uv
- **架构**: 四层分层架构
- **测试**: pytest + pytest-asyncio + pytest-qt
- **代码质量**: ruff + mypy

---

## 开发文档

### 细粒度文档（推荐）

详细设计文档位于 `.trae/记忆/`：

#### 基础层文档 (P0)
| 文档 | 内容 |
|------|------|
| `p0_eventbus.md` | EventBus 事件总线 |
| `p0_config.md` | Config 配置管理 |
| `p0_logger.md` | Logger 日志系统 |
| `p0_database.md` | Database 数据库连接 |
| `p0_llm.md` | LLM Client + ModelRouter |
| `p0_save_manager.md` | SaveManager 存档管理 |
| `p0_cache.md` | Cache LRU 缓存 |
| `p0_resource_manager.md` | ResourceManager 资源管理 |
| `p0_base.md` | Base 基类与接口 |

#### 核心层文档 (P1)
| 文档 | 内容 |
|------|------|
| `p1_entities.md` | Entities 数据模型 |
| `p1_repository.md` | Repository 数据访问 |
| `p1_state.md` | LangGraph State |
| `p1_calculators.md` | Calculators 纯函数计算器 |
| `p1_constants.md` | Constants 常量定义 |

#### Feature AI 层文档 (P2)
| 文档 | 内容 |
|------|------|
| `p2_events.md` | Events 事件系统 |
| `p2_command_parser.md` | CommandParser 命令解析器 |
| `p2_prompt_builder.md` | PromptBuilder Prompt 构建器 |
| `p2_tools.md` | Tools LangGraph 工具 |
| `p2_nodes.md` | Nodes 节点函数 |
| `p2_graph.md` | Graph StateGraph 定义 |
| `p2_gm_agent.md` | GMAgent Agent 门面 |

#### Feature Services 层文档 (P3)
| 文档 | 内容 |
|------|------|
| `p3_base_feature.md` | BaseFeature Feature 基类 |
| `p3_feature_systems.md` | 各子系统（战斗/对话/任务/物品/探索/叙事） |
| `p3_registry.md` | FeatureRegistry 注册表 |

#### Presentation 层文档 (P4)
| 文档 | 内容 |
|------|------|
| `p4_main_window.md` | MainWindow 主窗口 |
| `p4_theme.md` | Theme 主题管理 |
| `p4_project_manager.md` | ProjectManager 项目管理 |
| `p4_project_selector.md` | ProjectSelector & NewProjectDialog |

#### 优化阶段文档
| 文档 | 内容 |
|------|------|
| `opt_p1_bugfix.md` | P1 回归 Bug 修复 |
| `opt_p1_datafix.md` | P1 数据 Bug 修复（导入导出、CORS） |
| `opt_p2_quality.md` | P2 代码质量优化 |
| `opt_p2_hardcode_cleanup.md` | P2 硬编码清理（颜色、字体、计数器） |
| `opt_p3_ops_features.md` | P3 运营工具集功能补全 |
| `opt_p3_shortcuts.md` | P3 快捷键优化 |
| `opt_p3_advanced_features.md` | P3 进阶功能（服务启停、保存、Agent 完善） |
| `opt_p4_advanced.md` | P4 高级功能 |

#### Agent 运行流程优化文档
| 文档 | 内容 |
|------|------|
| `p1_agent_fix.md` | P1 Agent 运行流程修复 |
| `p2_editor_fix.md` | P2 编辑器体验修复 |
| `p3_tool_feature_fix.md` | P3 工具与 Feature 打通 |
| `p1_tool_integration.md` | P1 工具系统全量接入 |
| `p2_debugger_integration.md` | P2 调试面板与运行体验打通 |
| `p3_code_quality.md` | P3 代码质量与工程规范 |

### 工作流文档

项目提供了开发工作流文档位于 `2workbench/workflows/`：
- `add_feature.md` - 添加新 Feature
- `add_tool.md` - 添加新工具
- `debug_agent.md` - 调试 Agent
- `hotfix.md` - 热修复流程
- `test_layer.md` - 分层测试

---

## 许可证

MIT
