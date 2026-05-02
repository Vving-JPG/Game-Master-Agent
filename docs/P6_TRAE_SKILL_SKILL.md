# P6: Trae Skill 集成 — 开发循环与最终收尾

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。
> **前置条件**: P0 Foundation + P1 Core + P2 LangGraph + P3 Feature + P4 GUI Editor + P5 GUI Ops 已全部完成。

## 项目概述

你正在帮助用户将 **Game Master Agent V2** 的 `2workbench/` 目录重构为**四层架构**。

- **技术**: Python 3.11+ / PyQt6 / SQLite / LangGraph / uv
- **包管理器**: uv
- **开发 IDE**: Trae
- **本 Phase 目标**: 完成 Trae Skill 集成（SKILL.md + gui_ctl.py），建立开发循环工作流，执行全量集成测试，清理遗留代码，更新入口文件，完成项目收尾。

### 架构约束

```
入口层 → Presentation (表现层) → Feature (功能层) → Core (核心层) → Foundation (基础层)
```

- ✅ 所有层已完成，本 Phase 专注于**集成、工具链和收尾**
- ✅ Trae Skill 格式遵循 `.trae/skills/` 目录规范
- ✅ `gui_ctl.py` 作为 HTTP CLI 工具控制 IDE

### 本 Phase (P6) 范围

1. **Trae Skill 定义** — 更新 SKILL.md（三层渐进式指引）
2. **gui_ctl.py 更新** — HTTP CLI 工具适配新架构
3. **入口文件更新** — `app.py` + `main_window.py` 启动流程
4. **开发循环工作流** — 日常开发/调试/测试的 Prompt 模板
5. **全量集成测试** — 端到端验证所有层
6. **清理与收尾** — 删除临时文件、更新文档

### 现有代码参考

| 现有文件 | 参考内容 | 改进方向 |
|---------|---------|---------|
| `.trae/skills/workbench-gui/SKILL.md` | Trae Skill 格式 | 更新为新架构指引 |
| `.trae/skills/workbench-gui/gui_ctl.py` | HTTP CLI 工具 | 适配新四层架构 API |
| `_legacy/app.py` | QApplication 入口 | 更新启动流程 |

### P0-P5 产出（本 Phase 依赖）

```python
# Foundation
from foundation.event_bus import event_bus, Event
from foundation.config import settings
from foundation.logger import get_logger
from foundation.database import init_db, get_db
from foundation.llm import BaseLLMClient, LLMMessage, LLMResponse
from foundation.llm.model_router import model_router
from foundation.cache import llm_cache
from foundation.resource_manager import ResourceManager

# Core
from core.state import AgentState, create_initial_state
from core.models import (
    World, Player, NPC, Memory, Quest, Item, Location,
    WorldRepo, PlayerRepo, NPCRepo, MemoryRepo, ItemRepo,
    QuestRepo, LogRepo, MetricsRepo, PromptRepo,
)
from core.calculators import roll_dice, attack, combat_round
from core.constants import NPC_TEMPLATES, STORY_TEMPLATES

# Feature
from feature.base import BaseFeature
from feature.registry import feature_registry
from feature.battle import BattleSystem
from feature.dialogue import DialogueSystem
from feature.quest import QuestSystem
from feature.item import ItemSystem
from feature.exploration import ExplorationSystem
from feature.narration import NarrationSystem
from feature.ai import GMAgent

# Presentation
from presentation.main_window import MainWindow
from presentation.theme.manager import theme_manager
from presentation.project.manager import project_manager
from presentation.editor.graph_editor import GraphEditorWidget
from presentation.editor.prompt_editor import PromptEditorWidget
from presentation.editor.tool_manager import ToolManagerWidget
from presentation.ops.debugger import RuntimePanel, EventMonitor
from presentation.ops.evaluator import EvalWorkbench
from presentation.ops.knowledge import KnowledgeEditor
from presentation.ops.safety import SafetyPanel
from presentation.ops.multi_agent import MultiAgentOrchestrator
from presentation.ops.logger_panel import LogViewer
from presentation.ops.deploy import DeployManager
```

---

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始"后，主动执行
4. **遇到错误先尝试修复**：3 次失败后再询问
5. **代码规范**：UTF-8，中文注释，PEP 8，类型注解
6. **Windows 兼容**：使用 `New-Item -ItemType Directory -Force` 替代 `mkdir -p`
7. **测试文件**：复杂测试写成独立 `.py` 文件，执行后删除

---

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **工作目录**: `2workbench/`
- **Trae Skill 目录**: `.trae/skills/workbench-gui/`

---

## 步骤

### Step 1: Trae Skill 定义 — SKILL.md

**目的**: 更新 Trae Skill 的 SKILL.md，提供三层渐进式指引，让 Trae 能理解项目结构和执行常见操作。

**参考**: `.trae/skills/workbench-gui/SKILL.md`

**方案**:

1.1 创建/更新 `.trae/skills/workbench-gui/SKILL.md`：

```markdown
# Game Master Agent IDE — Trae Skill

> 本 Skill 指引 Trae AI 助手理解和操作 Game Master Agent IDE 项目。

## Layer 1: 项目概览

### 项目名称
Game Master Agent V2 — Agent 集成开发环境

### 技术栈
- Python 3.11+ / PyQt6 / SQLite / LangGraph / uv
- 四层架构: Foundation → Core → Feature → Presentation

### 目录结构
```
2workbench/
├── app.py                    # 应用入口
├── main.py                   # 备用入口
├── pyproject.toml            # 项目配置
├── foundation/               # 基础层 — 工具/单例
│   ├── event_bus.py          # EventBus 事件系统
│   ├── config.py             # 配置管理（多模型）
│   ├── logger.py             # 日志
│   ├── database.py           # SQLite WAL
│   ├── llm/                  # LLM 客户端
│   │   ├── base.py           # BaseLLMClient ABC
│   │   ├── openai_client.py  # OpenAI 兼容客户端
│   │   └── model_router.py   # 模型路由
│   ├── cache.py              # LRU + TTL 缓存
│   ├── save_manager.py       # 存档管理
│   └── resource_manager.py   # 资源管理
├── core/                     # 核心层 — 纯数据/规则
│   ├── models/               # Pydantic 模型 + Repository
│   │   ├── world.py          # WorldRepo
│   │   ├── player.py         # PlayerRepo
│   │   ├── npc.py            # NPCRepo
│   │   ├── item.py           # ItemRepo
│   │   ├── quest.py          # QuestRepo
│   │   ├── memory.py         # MemoryRepo
│   │   ├── location.py       # LocationRepo
│   │   ├── log.py            # LogRepo
│   │   ├── metrics.py        # MetricsRepo
│   │   └── prompt.py         # PromptRepo
│   ├── state.py              # AgentState (LangGraph)
│   ├── calculators.py        # 战斗/结局纯函数
│   ├── constants.py          # NPC/故事模板
│   └── schema.sql            # 数据库 Schema
├── feature/                  # 功能层 — 业务系统
│   ├── base.py               # BaseFeature 基类
│   ├── registry.py           # Feature 注册表
│   ├── ai/                   # LangGraph Agent 核心
│   │   ├── events.py         # 事件定义
│   │   ├── command_parser.py # 4级容错解析
│   │   ├── prompt_builder.py # Prompt 组装
│   │   ├── skill_loader.py   # Skill 评分匹配
│   │   ├── tools.py          # 9个 LangGraph 工具
│   │   ├── nodes.py          # 6个节点函数
│   │   ├── graph.py          # StateGraph 定义
│   │   └── gm_agent.py       # GM Agent 门面
│   ├── battle/               # 战斗系统
│   ├── dialogue/             # NPC 对话系统
│   ├── quest/                # 任务系统
│   ├── item/                 # 物品系统
│   ├── exploration/          # 探索系统
│   └── narration/            # 叙事系统
├── presentation/             # 表现层 — UI
│   ├── main_window.py        # 主窗口
│   ├── theme/                # 主题系统
│   │   ├── manager.py        # ThemeManager
│   │   ├── dark.qss          # Dark 主题
│   │   └── light.qss         # Light 主题
│   ├── widgets/              # 通用组件
│   │   ├── base.py           # BaseWidget
│   │   ├── styled_button.py  # 样式按钮
│   │   └── search_bar.py     # 搜索栏
│   ├── project/              # 项目管理
│   │   ├── manager.py        # ProjectManager
│   │   └── new_dialog.py     # 新建对话框
│   ├── editor/               # 编辑器
│   │   ├── graph_editor.py   # LangGraph 图编辑器
│   │   ├── prompt_editor.py  # Prompt 管理器
│   │   └── tool_manager.py   # 工具管理器
│   └── ops/                  # 运营工具
│       ├── debugger/         # 运行时调试器
│       ├── evaluator/        # 评估工作台
│       ├── knowledge/        # 知识库编辑器
│       ├── safety/           # 安全护栏
│       ├── multi_agent/      # 多 Agent 编排
│       ├── logger_panel/     # 日志追踪
│       └── deploy/           # 部署管理
└── _legacy/                  # 旧代码（参考用）
```

### 架构规则
- 上层依赖下层，禁止反向依赖
- 同层模块仅通过 EventBus 通信
- Presentation 层不直接操作数据库或调用 LLM

---

## Layer 2: 常见操作

### 启动应用
```bash
cd 2workbench ; python app.py
```

### 运行测试
```bash
cd 2workbench ; python -m pytest tests/ -v
```

### 创建新 Agent 项目
通过 IDE: File > New Agent Project
或通过代码:
```python
from presentation.project.manager import project_manager
path = project_manager.create_project('my_agent', template='trpg')
project_manager.open_project(path)
```

### 运行 Agent
```python
from feature.ai import GMAgent
agent = GMAgent(world_id=1)
result = agent.run_sync("玩家说: 我要探索幽暗森林")
```

### 添加新 Feature
1. 创建 `feature/my_feature/system.py`，继承 `BaseFeature`
2. 实现 `on_enable()` / `on_disable()` 生命周期
3. 通过 `self.subscribe()` 订阅 EventBus 事件
4. 通过 `self.emit()` 发出事件
5. 在 `feature/registry.py` 中注册
6. 更新 `feature/__init__.py` 导出

### 添加新 LangGraph Tool
1. 在 `feature/ai/tools.py` 中定义工具函数
2. 添加 `@tool` 装饰器
3. 在 `graph.py` 的 `gm_graph` 中绑定工具
4. 在 `presentation/editor/tool_manager.py` 的 `BUILTIN_TOOLS` 中添加定义

---

## Layer 3: 开发规范

### 代码规范
- UTF-8 编码，中文注释
- PEP 8，类型注解
- 文件头注释说明职责和来源

### EventBus 事件命名
```
feature.{system}.{action}     # Feature 层事件
ui.{component}.{action}       # Presentation 层事件
foundation.{module}.{action}  # Foundation 层事件
```

### 数据库操作
- 使用 Repository 类，不直接写 SQL
- 所有 Repo 方法接受 `db_path` 参数
- 使用 `with` 上下文管理事务

### LLM 调用
- 通过 `model_router.route()` 获取客户端
- 支持 DeepSeek / OpenAI / Anthropic
- 流式输出通过 EventBus 推送 `LLM_STREAM_TOKEN` 事件

### Windows 兼容
- 使用 `New-Item -ItemType Directory -Force -Path` 创建目录
- 使用 `;` 替代 `&&` 连接命令
- 复杂 Python 测试写成独立文件再执行
```

1.2 验证文件已创建：

```bash
cd .trae/skills/workbench-gui ; dir SKILL.md
```

**验收**:
- [ ] `.trae/skills/workbench-gui/SKILL.md` 创建/更新完成
- [ ] 三层渐进式结构（概览/操作/规范）
- [ ] 完整目录结构
- [ ] 架构规则说明
- [ ] 常见操作示例

---

### Step 2: gui_ctl.py 更新

**目的**: 更新 HTTP CLI 工具，适配新的四层架构 API。

**参考**: `.trae/skills/workbench-gui/gui_ctl.py`

**方案**:

2.1 读取现有 gui_ctl.py 了解结构：

```bash
# 先查看现有文件
python -c "with open('.trae/skills/workbench-gui/gui_ctl.py', 'r', encoding='utf-8') as f: print(f.read()[:2000])"
```

2.2 更新 `.trae/skills/workbench-gui/gui_ctl.py`，适配新架构：

核心变更点：
- `/api/project/*` 路由适配 `ProjectManager`
- `/api/agent/*` 路由适配 `GMAgent`
- `/api/graph/*` 路由适配 `GraphEditorWidget`
- `/api/features/*` 路由适配 `feature_registry`
- `/api/tools/*` 路由适配工具管理

```python
# .trae/skills/workbench-gui/gui_ctl.py
"""Game Master Agent IDE — HTTP CLI 控制工具

通过 HTTP API 控制 IDE 的各项功能。
适配四层架构 (Foundation/Core/Feature/Presentation)。

用法:
    python gui_ctl.py [--port 18265] [--host 127.0.0.1]

API 端点:
    GET  /api/status                    — IDE 状态
    POST /api/project/create            — 创建项目
    POST /api/project/open              — 打开项目
    POST /api/project/close             — 关闭项目
    GET  /api/project/info              — 项目信息
    GET  /api/graph                     — 获取图定义
    POST /api/graph/save                — 保存图定义
    GET  /api/prompts                   — 列出 Prompt
    GET  /api/prompts/<name>            — 获取 Prompt
    POST /api/prompts/<name>            — 保存 Prompt
    POST /api/agent/run                 — 运行 Agent
    POST /api/agent/stop                — 停止 Agent
    GET  /api/agent/state               — Agent 状态
    GET  /api/features                  — Feature 列表
    POST /api/features/<name>/enable    — 启用 Feature
    POST /api/features/<name>/disable   — 禁用 Feature
    GET  /api/tools                     — 工具列表
    GET  /api/screenshot                — 截图
"""
```

**注意**: gui_ctl.py 是一个较大的文件（约 400+ 行），请基于现有文件进行增量修改，主要更新 API 路由处理函数中的调用逻辑：

```python
# 关键修改示例

# 旧: 直接操作数据库
# 新: 通过 ProjectManager
from presentation.project.manager import project_manager

# 旧: 通过 agent_bridge
# 新: 通过 GMAgent
from feature.ai import GMAgent

# 旧: 直接 import service
# 新: 通过 feature_registry
from feature.registry import feature_registry
```

2.3 测试 gui_ctl.py 启动：

```bash
cd .trae/skills/workbench-gui ; python gui_ctl.py --port 18265
```

验证 API 可访问：

```bash
curl http://127.0.0.1:18265/api/status
```

**验收**:
- [ ] gui_ctl.py 更新完成
- [ ] `/api/status` 返回 IDE 状态
- [ ] `/api/project/*` 路由正常
- [ ] `/api/agent/*` 路由正常
- [ ] `/api/features/*` 路由正常
- [ ] HTTP 服务可启动

---

### Step 3: 入口文件更新

**目的**: 更新 `app.py` 和创建 `main.py` 入口，确保应用能正常启动。

**参考**: `_legacy/app.py`

**方案**:

3.1 更新 `2workbench/app.py`：

```python
# 2workbench/app.py
"""Game Master Agent IDE — 应用入口

启动流程:
1. 初始化 QApplication
2. 应用主题
3. 初始化数据库
4. 启用 Feature 系统
5. 创建并显示主窗口
6. 启动 qasync 事件循环
"""
from __future__ import annotations

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    """主入口"""
    from PyQt6.QtWidgets import QApplication
    import qasync

    # 1. 创建 QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Game Master Agent IDE")
    app.setOrganizationName("GMA")

    # 2. 应用主题
    from presentation.theme.manager import theme_manager
    theme_manager.apply("dark")

    # 3. 初始化数据库
    from foundation.config import settings
    from foundation.database import init_db
    db_path = PROJECT_ROOT / "data" / "default.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    init_db(db_path=str(db_path))

    # 4. 启用 Feature 系统
    from feature import (
        feature_registry,
        BattleSystem, DialogueSystem, QuestSystem,
        ItemSystem, ExplorationSystem, NarrationSystem,
    )
    feature_registry.register(BattleSystem())
    feature_registry.register(DialogueSystem())
    feature_registry.register(QuestSystem())
    feature_registry.register(ItemSystem())
    feature_registry.register(ExplorationSystem())
    feature_registry.register(NarrationSystem())
    feature_registry.enable_all()

    # 5. 创建主窗口
    from presentation.main_window import MainWindow
    window = MainWindow()
    window.show()

    # 6. 启动事件循环
    from foundation.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Game Master Agent IDE 启动完成")

    loop = qasync.QEventLoop(app)
    qasync.setEventLoop(loop)

    with loop:
        sys.exit(loop.run_forever())


if __name__ == "__main__":
    main()
```

3.2 创建 `2workbench/main.py`（备用入口，不带 qasync）：

```python
# 2workbench/main.py
"""备用入口 — 不使用 qasync（用于简单测试）"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("Game Master Agent IDE")

    from presentation.theme.manager import theme_manager
    theme_manager.apply("dark")

    from presentation.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

3.3 测试入口文件：

```bash
cd 2workbench ; python -c "
import sys
from pathlib import Path

# 测试模块导入链
PROJECT_ROOT = Path('.')
sys.path.insert(0, str(PROJECT_ROOT))

# Foundation
from foundation.event_bus import event_bus
from foundation.config import settings
from foundation.logger import get_logger
from foundation.database import init_db
print('✅ Foundation 层导入成功')

# Core
from core.state import AgentState, create_initial_state
from core.models import WorldRepo, PlayerRepo, NPCRepo
print('✅ Core 层导入成功')

# Feature
from feature.registry import feature_registry
from feature.ai import GMAgent
print('✅ Feature 层导入成功')

# Presentation
from presentation.theme.manager import theme_manager
from presentation.project.manager import project_manager
print('✅ Presentation 层导入成功')

print('✅ 所有层导入成功 — 入口文件就绪')
"
```

**验收**:
- [ ] `app.py` 更新完成（含 qasync + Feature 初始化）
- [ ] `main.py` 创建完成（备用入口）
- [ ] 所有层导入链正常
- [ ] 无循环依赖

---

### Step 4: 开发循环工作流 Prompt

**目的**: 创建日常开发中常用的 Prompt 模板文件，方便用户快速执行常见操作。

**方案**:

4.1 创建 `2workbench/workflows/` 目录：

```
2workbench/workflows/
├── add_feature.md        # 添加新 Feature
├── add_tool.md           # 添加新 LangGraph Tool
├── add_prompt.md         # 添加新 Prompt 模板
├── debug_agent.md        # 调试 Agent
├── test_layer.md         # 测试指定层
└── hotfix.md             # 热修复流程
```

4.2 创建 `2workbench/workflows/add_feature.md`：

```markdown
# 工作流: 添加新 Feature 模块

## 步骤

1. **创建目录**:
```
New-Item -ItemType Directory -Force -Path feature/<feature_name>
```

2. **创建 system.py**:
```python
# feature/<feature_name>/system.py
"""<中文名称>系统"""
from __future__ import annotations
from typing import Any
from foundation.logger import get_logger
from feature.base import BaseFeature

logger = get_logger(__name__)

class <ClassName>System(BaseFeature):
    name = "<feature_name>"

    def on_enable(self) -> None:
        super().on_enable()
        self.subscribe("feature.ai.command.executed", self._on_command)

    def _on_command(self, event) -> None:
        intent = event.get("intent", "")
        if intent == "<your_intent>":
            self.handle_<action>(event.get("params", {}))

    def get_state(self) -> dict[str, Any]:
        return super().get_state()
```

3. **创建 __init__.py**:
```python
from feature.<feature_name>.system import <ClassName>System
__all__ = ["<ClassName>System"]
```

4. **注册到 feature_registry**:
在 `feature/__init__.py` 中添加导入和导出。

5. **添加 EventBus 事件**:
在 `feature/ai/events.py` 中定义相关事件常量。

6. **测试**:
```bash
cd 2workbench ; python -c "
from feature.<feature_name> import <ClassName>System
sys = <ClassName>System()
sys.on_enable()
assert sys.enabled
sys.on_disable()
print('✅ <ClassName>System 测试通过')
"
```
```

4.3 创建 `2workbench/workflows/add_tool.md`：

```markdown
# 工作流: 添加新 LangGraph Tool

## 步骤

1. **在 feature/ai/tools.py 中添加工具函数**:
```python
from langchain_core.tools import tool

@tool
def your_tool_name(param1: str, param2: int = 0) -> str:
    """工具描述（会被 LLM 看到）"""
    # 实现逻辑
    return "结果"
```

2. **在 graph.py 中绑定工具**:
在 `create_tools()` 函数中添加新工具。

3. **在 nodes.py 的 execute_commands 节点中处理**:
如果需要特殊处理，在命令执行逻辑中添加分支。

4. **在 tool_manager.py 中添加 UI 定义**:
在 `BUILTIN_TOOLS` 列表中添加 `ToolDefinition`。

5. **测试**:
```bash
cd 2workbench ; python -c "
from feature.ai.tools import your_tool_name
result = your_tool_name.invoke({'param1': 'test'})
print(f'结果: {result}')
print('✅ 工具测试通过')
"
```
```

4.4 创建 `2workbench/workflows/debug_agent.md`：

```markdown
# 工作流: 调试 Agent

## 常见问题排查

### 1. Agent 无响应
```bash
cd 2workbench ; python -c "
from foundation.config import settings
print(f'API Key: {settings.deepseek_api_key[:10]}...')
print(f'Base URL: {settings.deepseek_base_url}')
print(f'Model: {settings.default_model}')
"
```

### 2. EventBus 事件未触发
```bash
cd 2workbench ; python -c "
from foundation.event_bus import event_bus, Event
result = event_bus.emit(Event(type='test.debug', data={'key': 'value'}))
print(f'订阅者数量: {len(result)}')
"
```

### 3. 数据库连接问题
```bash
cd 2workbench ; python -c "
from foundation.database import init_db, get_db
import tempfile, os
tmp = tempfile.mktemp(suffix='.db')
init_db(db_path=tmp)
db = get_db(db_path=tmp)
tables = db.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print(f'表: {[t[0] for t in tables]}')
os.unlink(tmp)
"
```

### 4. LangGraph 图编译问题
```bash
cd 2workbench ; python -c "
from feature.ai.graph import create_gm_graph
graph = create_gm_graph()
print(f'节点: {list(graph.nodes)}')
print(f'边: {list(graph.edges)}')
"
```

### 5. Feature 未启用
```bash
cd 2workbench ; python -c "
from feature.registry import feature_registry
print(f'已注册: {feature_registry.list_features()}')
states = feature_registry.get_all_states()
for name, state in states.items():
    print(f'  {name}: enabled={state[\"enabled\"]}')
"
```
```

4.5 创建 `2workbench/workflows/test_layer.md`：

```markdown
# 工作流: 测试指定层

## Foundation 层测试
```bash
cd 2workbench ; python -c "
from foundation.event_bus import event_bus, Event
from foundation.config import settings
from foundation.logger import get_logger
from foundation.database import init_db
from foundation.cache import llm_cache
import tempfile, os

# EventBus
event_bus.emit(Event(type='test', data={}))

# Config
print(f'Model: {settings.default_model}')

# Database
tmp = tempfile.mktemp(suffix='.db')
init_db(db_path=tmp)
os.unlink(tmp)

# Cache
llm_cache.set('test_key', 'test_value', ttl=60)
assert llm_cache.get('test_key') == 'test_value'

print('✅ Foundation 层测试通过')
"
```

## Core 层测试
```bash
cd 2workbench ; python -c "
import tempfile, os
from foundation.database import init_db
from core.models import WorldRepo, PlayerRepo, NPCRepo, ItemRepo
from core.state import create_initial_state
from core.calculators import roll_dice

tmp = tempfile.mktemp(suffix='.db')
init_db(db_path=tmp)

# Repository
repo = WorldRepo()
w = repo.create(name='测试世界', db_path=tmp)
assert w.id > 0

# State
state = create_initial_state(world_id=1)
assert 'messages' in state

# Calculator
result = roll_dice('2d6')
assert 2 <= result <= 12

os.unlink(tmp)
print('✅ Core 层测试通过')
"
```

## Feature 层测试
```bash
cd 2workbench ; python -c "
from feature.registry import feature_registry
from feature.battle import BattleSystem
from feature.dialogue import DialogueSystem
from feature.ai import GMAgent

feature_registry.register(BattleSystem())
feature_registry.register(DialogueSystem())
feature_registry.enable_all()

assert 'battle' in feature_registry.list_features()
print('✅ Feature 层测试通过')
"
```

## Presentation 层测试
```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)

from presentation.theme.manager import theme_manager
theme_manager.apply('dark')

from presentation.project.manager import ProjectManager
pm = ProjectManager()
print('✅ Presentation 层测试通过')
"
```
```

4.6 创建 `2workbench/workflows/hotfix.md`：

```markdown
# 工作流: 热修复流程

## 快速修复步骤

1. **定位问题**: 使用 `debug_agent.md` 中的排查方法
2. **修改代码**: 直接修改对应层的文件
3. **验证修复**: 运行对应层的测试
4. **回归测试**: 运行全量集成测试

## 注意事项

- 修改 Foundation 层可能影响所有上层，修改后需全量测试
- 修改 Core 层需验证所有 Repository 方法
- 修改 Feature 层需验证 EventBus 事件流
- 修改 Presentation 层风险最低，通常只需重启 UI

## 回滚

如果修复导致问题，可以从 `_legacy/` 目录参考原始实现。
```

**验收**:
- [ ] 6 个工作流 Prompt 文件创建完成
- [ ] `add_feature.md` — Feature 添加模板
- [ ] `add_tool.md` — Tool 添加模板
- [ ] `debug_agent.md` — 调试排查指南
- [ ] `test_layer.md` — 各层测试命令
- [ ] `hotfix.md` — 热修复流程

---

### Step 5: 全量集成测试

**目的**: 执行端到端集成测试，验证所有层协同工作。

**方案**:

5.1 创建测试文件 `2workbench/test_full_integration.py`：

```python
# 2workbench/test_full_integration.py
"""全量集成测试 — 验证四层架构协同工作"""
from __future__ import annotations

import sys
import tempfile
import os
import random
from pathlib import Path

# 确保项目路径
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

random.seed(42)


def test_foundation():
    """测试 Foundation 层"""
    print("\n=== Foundation 层 ===")
    from foundation.event_bus import event_bus, Event
    from foundation.config import settings
    from foundation.logger import get_logger
    from foundation.database import init_db
    from foundation.cache import llm_cache

    # EventBus
    received = []
    def handler(e): received.append(e)
    event_bus.subscribe("test.integration", handler)
    event_bus.emit(Event(type="test.integration", data={"key": "value"}))
    event_bus.unsubscribe("test.integration", handler)
    assert len(received) == 1
    print("  ✅ EventBus")

    # Config
    assert settings.default_model
    print(f"  ✅ Config (model={settings.default_model})")

    # Database
    tmp = tempfile.mktemp(suffix=".db")
    init_db(db_path=tmp)
    os.unlink(tmp)
    print("  ✅ Database")

    # Cache
    llm_cache.set("test", "value", ttl=60)
    assert llm_cache.get("test") == "value"
    print("  ✅ Cache")


def test_core(db_path: str):
    """测试 Core 层"""
    print("\n=== Core 层 ===")
    from core.models import (
        WorldRepo, PlayerRepo, NPCRepo, ItemRepo,
        QuestRepo, MemoryRepo, LocationRepo, LogRepo,
    )
    from core.state import create_initial_state
    from core.calculators import roll_dice, attack, combat_round

    # Repository CRUD
    world_repo = WorldRepo()
    world = world_repo.create(name="测试世界", db_path=db_path)
    assert world.id > 0
    print(f"  ✅ WorldRepo (id={world.id})")

    player_repo = PlayerRepo()
    player = player_repo.create(world_id=world.id, name="冒险者", db_path=db_path)
    assert player.id > 0
    print(f"  ✅ PlayerRepo (id={player.id})")

    npc_repo = NPCRepo()
    npc = npc_repo.create(world_id=world.id, name="老村长", db_path=db_path)
    assert npc.id > 0
    print(f"  ✅ NPCRepo (id={npc.id})")

    # State
    state = create_initial_state(world_id=world.id)
    assert "messages" in state
    print("  ✅ AgentState")

    # Calculators
    dice = roll_dice("2d6")
    assert 2 <= dice <= 12
    print(f"  ✅ Calculators (dice={dice})")


def test_feature(db_path: str):
    """测试 Feature 层"""
    print("\n=== Feature 层 ===")
    from feature.registry import feature_registry
    from feature.battle import BattleSystem
    from feature.dialogue import DialogueSystem
    from feature.quest import QuestSystem
    from feature.item import ItemSystem
    from feature.exploration import ExplorationSystem
    from feature.narration import NarrationSystem
    from feature.ai import GMAgent, parse_llm_output

    # 注册所有 Feature
    feature_registry.register(BattleSystem(db_path=db_path))
    feature_registry.register(DialogueSystem(db_path=db_path))
    feature_registry.register(QuestSystem(db_path=db_path))
    feature_registry.register(ItemSystem(db_path=db_path))
    feature_registry.register(ExplorationSystem(db_path=db_path))
    feature_registry.register(NarrationSystem(db_path=db_path))
    feature_registry.enable_all()

    assert len(feature_registry.list_features()) == 6
    print(f"  ✅ FeatureRegistry ({len(feature_registry.list_features())} features)")

    # BattleSystem
    battle = feature_registry.get("battle")
    state = battle.start_combat({
        "player": {"name": "冒险者", "hp": 100, "max_hp": 100, "attack_bonus": 5, "damage_dice": "1d10", "ac": 16},
        "enemies": [{"name": "史莱姆", "hp": 10, "max_hp": 10, "attack_bonus": 0, "damage_dice": "1d4", "ac": 8}],
    })
    while state.active:
        battle.execute_round()
    print(f"  ✅ BattleSystem (victory={state.victory}, rounds={state.round_num})")

    # CommandParser
    parsed = parse_llm_output('{"narrative": "测试", "commands": []}')
    assert parsed.narrative == "测试"
    print("  ✅ CommandParser")

    # NarrationSystem
    narr = feature_registry.get("narration")
    count = narr.extract_and_store("测试记忆内容", world_id=1, turn=1, db_path=db_path)
    assert count == 1
    print("  ✅ NarrationSystem")

    feature_registry.disable_all()


def test_presentation():
    """测试 Presentation 层"""
    print("\n=== Presentation 层 ===")
    from PyQt6.QtWidgets import QApplication
    from presentation.theme.manager import theme_manager
    from presentation.project.manager import ProjectManager

    # Theme
    theme_manager.apply("dark")
    assert theme_manager.current_theme == "dark"
    theme_manager.apply("light")
    assert theme_manager.current_theme == "light"
    theme_manager.apply("dark")
    print("  ✅ ThemeManager")

    # ProjectManager
    pm = ProjectManager()
    print("  ✅ ProjectManager")


def test_project_workflow():
    """测试项目完整工作流"""
    print("\n=== 项目工作流 ===")
    from presentation.project.manager import project_manager

    tmp_dir = tempfile.mkdtemp()

    try:
        # 创建项目
        path = project_manager.create_project("integration_test", template="trpg", directory=tmp_dir)
        assert path.exists()
        print(f"  ✅ 项目创建: {path}")

        # 打开项目
        config = project_manager.open_project(path)
        assert config.name == "integration_test"
        assert config.template == "trpg"
        print(f"  ✅ 项目打开: {config.name}")

        # 加载图定义
        graph = project_manager.load_graph()
        assert len(graph["nodes"]) == 6
        print(f"  ✅ 图定义: {len(graph['nodes'])} 节点")

        # Prompt 管理
        prompts = {}
        for name in project_manager.list_prompts():
            prompts[name] = project_manager.load_prompt(name)
        assert len(prompts) >= 3
        print(f"  ✅ Prompt 管理: {len(prompts)} 个")

        # 保存 Prompt
        project_manager.save_prompt("test_workflow", "工作流测试 Prompt")
        assert project_manager.load_prompt("test_workflow") == "工作流测试 Prompt"
        print("  ✅ Prompt 保存/加载")

        # 保存项目
        project_manager.save_project()
        print("  ✅ 项目保存")

        # 关闭项目
        project_manager.close_project()
        assert not project_manager.is_open
        print("  ✅ 项目关闭")

    finally:
        import shutil
        shutil.rmtree(tmp_dir)


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Game Master Agent IDE — 全量集成测试")
    print("=" * 60)

    # 创建临时数据库
    tmp_db = tempfile.mktemp(suffix=".db")

    try:
        from foundation.database import init_db
        init_db(db_path=tmp_db)

        test_foundation()
        test_core(tmp_db)
        test_feature(tmp_db)
        test_presentation()
        test_project_workflow()

        print("\n" + "=" * 60)
        print("✅ 全量集成测试通过！")
        print("=" * 60)

    finally:
        if os.path.exists(tmp_db):
            os.unlink(tmp_db)


if __name__ == "__main__":
    main()
```

5.2 执行测试：

```bash
cd 2workbench ; python test_full_integration.py
```

5.3 测试通过后删除测试文件：

```bash
del 2workbench\test_full_integration.py
```

**验收**:
- [ ] Foundation 层测试通过（EventBus/Config/Database/Cache）
- [ ] Core 层测试通过（Repository CRUD/State/Calculators）
- [ ] Feature 层测试通过（6 个 Feature 注册 + Battle + Parser + Narration）
- [ ] Presentation 层测试通过（Theme/ProjectManager）
- [ ] 项目工作流测试通过（创建→打开→图→Prompt→保存→关闭）
- [ ] 全量测试通过

---

### Step 6: 清理与收尾

**目的**: 清理临时文件、更新文档、完成项目收尾。

**方案**:

6.1 确认 `_legacy/` 目录完整性：

```bash
cd 2workbench ; dir _legacy
```

确保旧代码全部在 `_legacy/` 中，没有遗漏在主目录。

6.2 清理临时测试文件：

```bash
# 检查并删除所有 test_*.py 临时文件
cd 2workbench ; dir test_*.py
# 如果有残留，逐个删除
```

6.3 验证 `pyproject.toml` 依赖完整：

```bash
cd 2workbench ; python -c "
try:
    import PyQt6; print('✅ PyQt6')
except: print('❌ PyQt6 缺失')

try:
    from langgraph.graph import StateGraph; print('✅ LangGraph')
except: print('❌ LangGraph 缺失')

try:
    from langchain_core.tools import tool; print('✅ langchain-core')
except: print('❌ langchain-core 缺失')

try:
    import qasync; print('✅ qasync')
except: print('❌ qasync 缺失')

try:
    from pydantic import BaseModel; print('✅ pydantic')
except: print('❌ pydantic 缺失')
"
```

6.4 验证最终目录结构：

```bash
cd 2workbench ; dir
```

确认以下顶层目录存在：
- `foundation/` ✅
- `core/` ✅
- `feature/` ✅
- `presentation/` ✅
- `_legacy/` ✅
- `workflows/` ✅
- `app.py` ✅
- `main.py` ✅
- `pyproject.toml` ✅

6.5 最终导入验证：

```bash
cd 2workbench ; python -c "
# 四层全量导入
from foundation.event_bus import event_bus
from foundation.config import settings
from foundation.logger import get_logger
from foundation.database import init_db

from core.state import AgentState, create_initial_state
from core.models import WorldRepo, PlayerRepo, NPCRepo, MemoryRepo
from core.calculators import roll_dice
from core.constants import NPC_TEMPLATES

from feature.base import BaseFeature
from feature.registry import feature_registry
from feature.ai import GMAgent, parse_llm_output
from feature.battle import BattleSystem
from feature.dialogue import DialogueSystem

from presentation.main_window import MainWindow
from presentation.theme.manager import theme_manager
from presentation.project.manager import project_manager
from presentation.editor.graph_editor import GraphEditorWidget
from presentation.editor.prompt_editor import PromptEditorWidget
from presentation.editor.tool_manager import ToolManagerWidget
from presentation.ops.debugger import RuntimePanel
from presentation.ops.evaluator import EvalWorkbench
from presentation.ops.knowledge import KnowledgeEditor
from presentation.ops.safety import SafetyPanel
from presentation.ops.multi_agent import MultiAgentOrchestrator
from presentation.ops.logger_panel import LogViewer
from presentation.ops.deploy import DeployManager

print()
print('=' * 60)
print('✅ Game Master Agent IDE — 四层架构重构完成')
print('=' * 60)
print()
print('Foundation: event_bus, config, logger, database, llm, cache')
print('Core:        models, state, calculators, constants')
print('Feature:     ai, battle, dialogue, quest, item, exploration, narration')
print('Presentation: main_window, theme, project, editor, ops')
print()
print('启动命令: cd 2workbench && python app.py')
print('=' * 60)
"
```

**验收**:
- [ ] `_legacy/` 目录完整
- [ ] 无残留临时测试文件
- [ ] 所有依赖已安装
- [ ] 目录结构正确
- [ ] 四层全量导入无错误
- [ ] 启动命令可用

---

## 注意事项

### Windows 兼容性

- **创建目录**: 使用 `New-Item -ItemType Directory -Force -Path` 替代 `mkdir -p`
- **命令连接**: 使用 `;` 替代 `&&`
- **删除文件**: 使用 `del` 替代 `rm`
- **路径分隔**: Windows 使用 `\`，Python 中使用 `/` 或 `Path`

### 测试策略

- **简单测试**: 内联 `python -c "..."` 执行
- **复杂测试**: 写成独立 `.py` 文件，执行后删除
- **引号问题**: 内联测试中的 JSON 字符串使用转义或独立文件

### 文件编码

- 所有文件使用 UTF-8 编码
- QSS 文件中的中文字体: `"Microsoft YaHei"`
- Python 文件头注释使用中文

### 后续扩展方向

- **P7+**: 多 Agent 实际编排执行、FastAPI 服务导出、Docker 部署
- **评估系统**: 接入真实 LLM 进行 Prompt 评估
- **插件系统**: 动态加载第三方 Feature 模块
- **远程调试**: WebSocket 连接远程 Agent 运行时

---

## 完成检查清单

- [ ] Step 1: Trae Skill 定义（SKILL.md 三层渐进式指引）
- [ ] Step 2: gui_ctl.py 更新（HTTP CLI 适配新架构）
- [ ] Step 3: 入口文件更新（app.py + main.py）
- [ ] Step 4: 开发循环工作流 Prompt（6 个模板）
- [ ] Step 5: 全量集成测试（四层 + 项目工作流）
- [ ] Step 6: 清理与收尾（临时文件/依赖/结构验证）
