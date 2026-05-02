---
name: "workbench-gui"
description: "Game Master Agent IDE 四层架构操作指南。Invoke when user needs to understand project structure, start the application, run tests, or perform development workflows."
---

# Game Master Agent IDE — Trae Skill

> 本 Skill 指引 Trae AI 助手理解和操作 Game Master Agent IDE 项目。
> 渐进式披露结构：Layer 1(概览) → Layer 2(操作) → Layer 3(规范)

---

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
│   │   ├── entities.py       # 所有实体定义
│   │   └── repository.py     # 所有 Repository
│   ├── state.py              # AgentState (LangGraph)
│   ├── calculators/          # 战斗/结局纯函数
│   │   ├── combat.py
│   │   └── ending.py
│   └── constants/            # NPC/故事模板
│       ├── npc_templates.py
│       └── story_templates.py
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
├── workflows/                # 开发工作流模板
│   ├── add_feature.md        # 添加新 Feature
│   ├── add_tool.md           # 添加新 LangGraph Tool
│   ├── debug_agent.md        # 调试 Agent
│   ├── test_layer.md         # 测试指定层
│   └── hotfix.md             # 热修复流程
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

---

## HTTP CLI 控制工具 (gui_ctl.py)

### 基本用法
```bash
# 先启动 IDE
cd 2workbench && python app.py

# 然后在另一个终端使用 gui_ctl.py
python .trae/skills/workbench-gui/gui_ctl.py --help
```

### 结构化状态 API (推荐)

#### 获取应用状态
```bash
python .trae/skills/workbench-gui/gui_ctl.py state

# 输出示例：
# 📁 项目: my_agent (已打开)
# 🤖 Agent: idle | 回合: 5 | 模型: deepseek-chat
# ⚡ Features (3 启用): battle, dialogue, quest
# 📝 编辑器: graph_editor
# 🎨 主题: dark | 窗口: 1920x1080
```

#### 获取 Widget DOM 树
```bash
# 获取完整 DOM 树
python .trae/skills/workbench-gui/gui_ctl.py dom

# 获取特定区域
python .trae/skills/workbench-gui/gui_ctl.py dom --selector console
python .trae/skills/workbench-gui/gui_ctl.py dom --selector editor

# 只显示变化部分
python .trae/skills/workbench-gui/gui_ctl.py dom --diff
```

#### 查找 Widget
```bash
# 按 ID 查找
python .trae/skills/workbench-gui/gui_ctl.py find --id run_button

# 按类和文本查找
python .trae/skills/workbench-gui/gui_ctl.py find --class QPushButton --text "运行"
```

#### 获取 Windows UIA 树
```bash
python .trae/skills/workbench-gui/gui_ctl.py uia
```

### 截图功能
```bash
# 截图（自动前台、DPI 感知、自动最小化）
python .trae/skills/workbench-gui/gui_ctl.py screenshot
```

### Agent 控制
```bash
# 获取状态
python .trae/skills/workbench-gui/gui_ctl.py status

# 运行 Agent
python .trae/skills/workbench-gui/gui_ctl.py run --event "攻击哥布林"

# 控制 Agent
python .trae/skills/workbench-gui/gui_ctl.py control pause|resume|step|reset

# 查看最近回合
python .trae/skills/workbench-gui/gui_ctl.py turns --last 5
```

### 项目操作
```bash
# 创建项目
python .trae/skills/workbench-gui/gui_ctl.py project create --name my_agent --template trpg

# 打开项目
python .trae/skills/workbench-gui/gui_ctl.py project open --path data/my_agent.agent

# 获取项目信息
python .trae/skills/workbench-gui/gui_ctl.py project info
```

### Feature 管理
```bash
# 列出所有 Feature
python .trae/skills/workbench-gui/gui_ctl.py feature list

# 启用/禁用 Feature
python .trae/skills/workbench-gui/gui_ctl.py feature enable battle
python .trae/skills/workbench-gui/gui_ctl.py feature disable battle

# 获取 Feature 状态
python .trae/skills/workbench-gui/gui_ctl.py feature state battle
```

### 文件操作
```bash
# 打开文件
python .trae/skills/workbench-gui/gui_ctl.py open --path prompts/system.md

# 保存
python .trae/skills/workbench-gui/gui_ctl.py save

# 刷新
python .trae/skills/workbench-gui/gui_ctl.py refresh

# 查看目录树
python .trae/skills/workbench-gui/gui_ctl.py tree --path workspace

# 查看文件内容
python .trae/skills/workbench-gui/gui_ctl.py cat --path prompts/system.md

# 编辑文件
python .trae/skills/workbench-gui/gui_ctl.py edit --path file.md --content "# 新内容"

# 创建文件
python .trae/skills/workbench-gui/gui_ctl.py create --path file.md --content "# 新文件"

# 删除文件
python .trae/skills/workbench-gui/gui_ctl.py delete --path file.md
```

### 自动化测试
```bash
# 运行自动化测试循环
python .trae/skills/workbench-gui/gui_ctl.py loop -n 10
```

---

## GUI 自动化工具 (gui_automation.py)

位于 `2workbench/gui_automation.py`，提供鼠标键盘自动化功能。

### 截图
```bash
python gui_automation.py screenshot
python gui_automation.py screenshot -o custom.png
```

### 鼠标操作
```bash
# 点击指定位置
python gui_automation.py click 100 200

# 点击图像
python gui_automation.py click-on screenshot.png

# 移动鼠标
python gui_automation.py move 500 500

# 获取鼠标位置
python gui_automation.py pos

# 滚动
python gui_automation.py scroll 3
```

### 键盘操作
```bash
# 输入文本
python gui_automation.py type "Hello World"

# 按键
python gui_automation.py key enter
python gui_automation.py key ctrl+n
```

### 等待图像
```bash
python gui_automation.py wait screenshot.png --timeout 10
```

---

## API 端点参考

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | IDE 状态 |
| `/api/state` | GET | 应用结构化状态 |
| `/api/dom` | GET | Widget DOM 树 |
| `/api/dom?selector={}` | GET | 特定区域 DOM |
| `/api/dom?diff=true` | GET | DOM 变化 |
| `/api/uia` | GET | Windows UIA 树 |
| `/api/find` | GET | 查找 Widget |
| `/api/screenshot` | GET | 截图（DPI 感知+前台最小化） |
| `/api/project/create` | POST | 创建项目 |
| `/api/project/open` | POST | 打开项目 |
| `/api/project/close` | POST | 关闭项目 |
| `/api/graph` | GET | 获取图定义 |
| `/api/graph/save` | POST | 保存图定义 |
| `/api/agent/run` | POST | 运行 Agent |
| `/api/agent/stop` | POST | 停止 Agent |
| `/api/features` | GET | Feature 列表 |
| `/api/features/{name}/enable` | POST | 启用 Feature |
| `/api/features/{name}/disable` | POST | 禁用 Feature |

---

## 更新日志

- **2026-05-02**: 
  - 更新为四层架构版本
  - 添加结构化状态 API (state/dom/find/uia)
  - 截图功能支持 DPI 感知和自动前台/最小化
  - 整合 gui_automation.py 鼠标键盘自动化
- **2026-05-01**: 创建 Skill，整合基础截图、点击、状态获取功能
