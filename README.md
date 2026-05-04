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
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
├─────────────────────────────────────────────────────────────┤
│  P2: Feature AI 层 (LangGraph Agent)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  StateGraph: handle_event → build_prompt → llm       │   │
│  │              → parse_output → execute → update_mem   │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  CommandParser │ PromptBuilder │ SkillLoader │ Tools  │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  P1: Core 层 (数据模型与计算)                                 │
│  ┌────────────────────┬──────────────────────────────────┐  │
│  │  Pydantic Entities │  Repository (CRUD)               │  │
│  ├────────────────────┼──────────────────────────────────┤  │
│  │  LangGraph State   │  Calculators (combat/ending)     │  │
│  └────────────────────┴──────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  P0: Foundation 层 (基础设施)                                 │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │EventBus  │ Config   │ Database │   LLM    │  Cache   │   │
│  │ Logger   │ SaveMgr  │ Resource │  Router  │  Base    │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 四层架构说明

| 层级 | 路径 | 职责 | 关键组件 |
|------|------|------|----------|
| **P0 Foundation** | `2workbench/foundation/` | 基础设施 | EventBus, Config, Database, LLM, Cache, SaveManager, HotReload |
| **P1 Core** | `2workbench/core/` | 数据与计算 | Entities, Repository, State, Calculators |
| **P2 Feature AI** | `2workbench/feature/ai/` | LangGraph Agent | Graph, Nodes, GM Agent, CommandParser, PromptBuilder, Tools |
| **P3 Feature Services** | `2workbench/feature/` | 游戏系统 | Battle, Dialogue, Quest, Item, Narration, Exploration |
| **P4 Presentation** | `2workbench/presentation/` | PyQt6 IDE | MainWindow, Editors, Ops Panels, State API, Theme |

### 核心特性

- **LangGraph StateGraph**: 基于状态图的 Agent 工作流
- **四层架构**: 清晰的分层设计，便于扩展和维护
- **PyQt6 IDE**: 完整的图形化开发环境
- **Godot 风格项目选择器**: 友好的项目管理界面
- **可视化图编辑器**: 拖拽式编排 Agent 工作流
- **实时调试面板**: 事件监控、运行时状态、日志查看
- **知识库管理**: 物品、任务、地点的导入导出
- **多 Agent 编排**: 支持复杂的 Agent 协作
- **热重载**: 开发模式下的代码热更新
- **State API**: 结构化状态访问（Widget Tree / UIA / App State）
- **Skill 系统**: 基于 SKILL.md 的可扩展技能
- **安全审核**: 正则表达式验证与内容安全检查

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

## 项目结构

```
Game-Master-Agent/
├── 2workbench/                    # PyQt6 Workbench IDE
│   ├── foundation/                # P0: 基础设施层
│   │   ├── event_bus.py           # 事件总线
│   │   ├── config.py              # 配置管理
│   │   ├── database.py            # SQLite 数据库
│   │   ├── logger.py              # 日志系统
│   │   ├── llm/                   # LLM 客户端
│   │   ├── cache.py               # LRU 缓存
│   │   ├── save_manager.py        # 存档管理
│   │   ├── resource_manager.py    # 资源管理
│   │   ├── hot_reload.py          # 热重载
│   │   └── base/                  # 基类与接口
│   ├── core/                      # P1: 核心数据层
│   │   ├── models/
│   │   │   ├── entities.py        # Pydantic 实体
│   │   │   ├── repository.py      # 数据仓库
│   │   │   └── schema.sql         # 数据库架构
│   │   ├── state.py               # LangGraph State
│   │   ├── calculators/           # 纯函数计算器
│   │   └── constants/             # 常量定义
│   ├── feature/                   # P2+P3: 功能层
│   │   ├── ai/                    # P2: LangGraph Agent
│   │   │   ├── tools/             # 工具系统
│   │   │   ├── graph.py           # StateGraph 定义
│   │   │   ├── graph_compiler.py  # 图编译器
│   │   │   ├── nodes.py           # 节点函数
│   │   │   ├── gm_agent.py        # GM Agent
│   │   │   ├── agent_runner.py    # Agent 运行器
│   │   │   ├── command_parser.py  # 命令解析
│   │   │   ├── prompt_builder.py  # Prompt 构建
│   │   │   ├── skill_loader.py    # Skill 加载
│   │   │   └── events.py          # 事件定义
│   │   ├── services/              # 服务层
│   │   ├── battle/system.py       # P3: 战斗系统
│   │   ├── dialogue/system.py     # P3: 对话系统
│   │   ├── quest/system.py        # P3: 任务系统
│   │   ├── item/system.py         # P3: 物品系统
│   │   ├── exploration/system.py  # P3: 探索系统
│   │   ├── narration/system.py    # P3: 叙事系统
│   │   ├── base.py                # Feature 基类
│   │   └── registry.py            # Feature 注册表
│   ├── presentation/              # P4: 表现层
│   │   ├── main_window.py         # 主窗口
│   │   ├── server.py              # HTTP API 服务器
│   │   ├── state_api.py           # 结构化状态 API
│   │   ├── theme/                 # 主题管理
│   │   ├── editor/                # 编辑器组件
│   │   │   ├── graph_editor.py    # 图编辑器
│   │   │   ├── prompt_editor.py   # Prompt 编辑器
│   │   │   ├── prompt_tester.py   # Prompt 测试器
│   │   │   └── skill_manager.py   # Skill 管理器
│   │   ├── ops/                   # 运营工具面板
│   │   │   ├── debugger/          # 调试面板
│   │   │   └── log_viewer.py      # 日志查看器
│   │   ├── project/               # 项目管理
│   │   ├── dialogs/               # 对话框
│   │   └── widgets/               # 通用组件
│   ├── skills/                    # Skill 定义
│   ├── tests/                     # 测试文件
│   ├── workflows/                 # 工作流文档
│   ├── config/                    # 配置文件
│   ├── app.py                     # 应用入口
│   └── main.py                    # 旧入口
├── .trae/                         # Trae IDE 配置
│   ├── rules/                     # 项目规则
│   ├── skills/                    # Skill 定义
│   └── 记忆/                       # 开发记忆文档
├── pyproject.toml                 # 项目配置
├── uv.toml                        # uv 配置
└── README.md                      # 本文档
```

## 测试

```bash
# 运行所有测试
uv run pytest 2workbench/tests/ -v

# 运行特定模块
uv run pytest 2workbench/tests/test_foundation_integration.py -v
uv run pytest 2workbench/tests/test_core_integration.py -v
uv run pytest 2workbench/tests/test_event_bus.py -v
```

## 代码质量

```bash
# 代码格式化与检查
uv run ruff check 2workbench/
uv run ruff format 2workbench/

# 类型检查
uv run mypy 2workbench/
```

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

## 技术栈

- **GUI**: PyQt6 + qasync
- **后端**: Python 3.11+
- **AI**: LangGraph + LangChain Core + DeepSeek API (OpenAI 兼容)
- **数据**: Pydantic + Pydantic Settings + SQLite
- **包管理**: uv
- **架构**: 四层分层架构
- **测试**: pytest + pytest-asyncio + pytest-qt
- **代码质量**: ruff + mypy

## 开发文档

详细设计文档位于 `.trae/记忆/`（细粒度文档）：

### 基础层文档 (P0)
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

### 核心层文档 (P1)
| 文档 | 内容 |
|------|------|
| `p1_entities.md` | Entities 数据模型 |
| `p1_repository.md` | Repository 数据访问 |
| `p1_state.md` | LangGraph State |
| `p1_calculators.md` | Calculators 纯函数计算器 |
| `p1_constants.md` | Constants 常量定义 |

### Feature AI 层文档 (P2)
| 文档 | 内容 |
|------|------|
| `p2_events.md` | Events 事件系统 |
| `p2_command_parser.md` | CommandParser 命令解析器 |
| `p2_prompt_builder.md` | PromptBuilder Prompt 构建器 |
| `p2_tools.md` | Tools LangGraph 工具 |
| `p2_nodes.md` | Nodes 节点函数 |
| `p2_graph.md` | Graph StateGraph 定义 |
| `p2_gm_agent.md` | GMAgent Agent 门面 |

### Feature Services 层文档 (P3)
| 文档 | 内容 |
|------|------|
| `p3_base_feature.md` | BaseFeature Feature 基类 |
| `p3_feature_systems.md` | 各子系统（战斗/对话/任务/物品/探索/叙事） |
| `p3_registry.md` | FeatureRegistry 注册表 |

### Presentation 层文档 (P4)
| 文档 | 内容 |
|------|------|
| `p4_main_window.md` | MainWindow 主窗口 |
| `p4_theme.md` | Theme 主题管理 |
| `p4_project_manager.md` | ProjectManager 项目管理 |
| `p4_project_selector.md` | ProjectSelector & NewProjectDialog |

### 优化阶段文档
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

### Agent 运行流程优化文档
| 文档 | 内容 |
|------|------|
| `p1_agent_fix.md` | P1 Agent 运行流程修复 |
| `p2_editor_fix.md` | P2 编辑器体验修复 |
| `p3_tool_feature_fix.md` | P3 工具与 Feature 打通 |
| `p1_tool_integration.md` | P1 工具系统全量接入 |
| `p2_debugger_integration.md` | P2 调试面板与运行体验打通 |
| `p3_code_quality.md` | P3 代码质量与工程规范 |

## 工作流

项目提供了开发工作流文档位于 `2workbench/workflows/`：
- `add_feature.md` - 添加新 Feature
- `add_tool.md` - 添加新工具
- `debug_agent.md` - 调试 Agent
- `hotfix.md` - 热修复流程
- `test_layer.md` - 分层测试

## 许可证

MIT
