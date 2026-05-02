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
| **P0 Foundation** | `2workbench/foundation/` | 基础设施 | EventBus, Config, Database, LLM, Cache, SaveManager |
| **P1 Core** | `2workbench/core/` | 数据与计算 | Entities, Repository, State, Calculators |
| **P2 Feature AI** | `2workbench/feature/ai/` | LangGraph Agent | Graph, Nodes, GM Agent, CommandParser, PromptBuilder |
| **P3 Feature Services** | `2workbench/feature/` | 游戏系统 | Battle, Dialogue, Quest, Item, Narration |
| **P4 Presentation** | `2workbench/presentation/` | PyQt6 IDE | MainWindow, Editors, Ops Panels, State API |

### 核心特性

- **LangGraph StateGraph**: 基于状态图的 Agent 工作流
- **四层架构**: 清晰的分层设计，便于扩展和维护
- **PyQt6 IDE**: 完整的图形化开发环境
- **State API**: 结构化状态访问（Widget Tree / UIA / App State）
- **Skill 系统**: 基于 SKILL.md 的可扩展技能

## 快速开始

### 安装依赖

```bash
# 使用 pip
pip install -e .

# 或使用 uv
uv sync
```

### 配置环境

创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 启动 IDE

```bash
# 主入口（推荐）
python -m 2workbench

# 或使用 main.py
python 2workbench/main.py
```

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
│   │   └── resource_manager.py    # 资源管理
│   ├── core/                      # P1: 核心数据层
│   │   ├── models/
│   │   │   ├── entities.py        # Pydantic 实体
│   │   │   └── repository.py      # 数据仓库
│   │   ├── state.py               # LangGraph State
│   │   ├── calculators/           # 纯函数计算器
│   │   └── constants/             # 常量定义
│   ├── feature/                   # P2+P3: 功能层
│   │   ├── ai/                    # P2: LangGraph Agent
│   │   │   ├── graph.py           # StateGraph 定义
│   │   │   ├── nodes.py           # 节点函数
│   │   │   ├── gm_agent.py        # GM Agent
│   │   │   ├── command_parser.py  # 命令解析
│   │   │   ├── prompt_builder.py  # Prompt 构建
│   │   │   ├── skill_loader.py    # Skill 加载
│   │   │   ├── tools.py           # 工具函数
│   │   │   └── events.py          # 事件定义
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
│   │   ├── ops/                   # 运营工具面板
│   │   ├── project/               # 项目管理
│   │   └── dialogs/               # 对话框
│   ├── tests/                     # 测试文件
│   ├── data/                      # 项目数据
│   └── _legacy/                   # 旧代码参考
├── 1agent_core/                   # (旧版) Agent 核心
├── .trae/                         # Trae IDE 配置
│   └── 记忆/                       # 开发记忆文档
└── pyproject.toml                 # 项目配置
```

## 测试

```bash
# 运行所有测试
pytest 2workbench/tests/ -v

# 运行特定模块
pytest 2workbench/tests/test_foundation_integration.py -v
pytest 2workbench/tests/test_core_integration.py -v
pytest 2workbench/tests/test_event_bus.py -v
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

- **GUI**: PyQt6
- **后端**: Python 3.11+
- **AI**: LangGraph + DeepSeek API (OpenAI 兼容)
- **数据**: Pydantic + SQLite
- **架构**: 四层分层架构

## 开发文档

详细设计文档位于 `.trae/记忆/`：

| 文档 | 内容 |
|------|------|
| `foundation_p0.md` | P0 Foundation 层设计 |
| `core_p1.md` | P1 Core 层设计 |
| `p2_langgraph_agent.md` | P2 Feature AI 层设计 |
| `p3_feature_services.md` | P3 Feature Services 层设计 |
| `p4_presentation_gui.md` | P4 Presentation 层设计 |
| `p5_gui_ops.md` | P5 运营工具集设计 |
| `p6_state_api.md` | P6 结构化状态 API 设计 |

## 许可证

MIT
