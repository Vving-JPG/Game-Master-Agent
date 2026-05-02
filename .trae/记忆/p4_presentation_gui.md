# P4: Presentation 层 — IDE 核心编辑器

> 创建时间: 2026-05-02
> 对应代码: `2workbench/presentation/`

---

## 1. 概述

P4 实现 Presentation 层的 IDE 核心编辑器组件，包括：
- 主题系统（Dark/Light）
- 主窗口（三栏布局）
- Agent 项目管理器
- LangGraph 可视化图编辑器
- Prompt 管理器
- 工具/插件管理器

---

## 2. 文件结构

```
2workbench/presentation/
├── __init__.py                    # 入口
├── main_window.py                 # 主窗口
├── theme/
│   ├── __init__.py
│   ├── manager.py                 # 主题管理器
│   ├── dark.qss                   # Dark 主题
│   └── light.qss                  # Light 主题
├── widgets/
│   ├── __init__.py
│   ├── base.py                    # Widget 基类
│   ├── styled_button.py           # 样式按钮
│   └── search_bar.py              # 搜索栏
├── project/
│   ├── __init__.py
│   ├── manager.py                 # 项目管理器
│   └── new_dialog.py              # 新建项目对话框
└── editor/
    ├── __init__.py
    ├── graph_editor.py            # 图编辑器
    ├── prompt_editor.py           # Prompt 管理器
    └── tool_manager.py            # 工具管理器
```

---

## 3. 核心组件

### 3.1 主题系统

**ThemeManager** (`theme/manager.py`)
```python
from presentation.theme.manager import theme_manager

# 切换主题
theme_manager.apply("dark")  # 或 "light"

# 获取颜色
color = theme_manager.get_color("accent")
```

**调色板变量**:
- `bg_primary` - 主背景色
- `bg_secondary` - 次背景色
- `bg_tertiary` - 第三背景色
- `text_primary` - 主文本色
- `accent` - 强调色
- `success/warning/error/info` - 状态色

### 3.2 主窗口

**MainWindow** (`main_window.py`)

三栏布局:
- 左侧: 240px - 项目浏览器
- 中央: flex - 编辑器标签页
- 右侧: 300px - 属性/状态面板

菜单栏: 文件/编辑/视图/Agent/工具/帮助

### 3.3 项目管理器

**ProjectManager** (`project/manager.py`)

```python
from presentation.project.manager import project_manager

# 创建项目
path = project_manager.create_project(
    name="my_agent",
    template="trpg",  # blank/trpg/chatbot
)

# 打开项目
config = project_manager.open_project(path)

# 加载图/graph/prompts
graph = project_manager.load_graph()
prompts = project_manager.list_prompts()
```

**项目模板**:
- `blank` - 空白项目（3节点）
- `trpg` - TRPG游戏（6节点）
- `chatbot` - 对话机器人（4节点）

**项目结构**:
```
<name>.agent/
├── project.json      # 项目配置
├── graph.json        # LangGraph定义
├── config.json       # 运行配置
├── prompts/          # Prompt模板
├── tools/            # 自定义工具
├── knowledge/        # 知识库
├── saves/            # 存档
└── logs/             # 日志
```

### 3.4 图编辑器

**GraphEditorWidget** (`editor/graph_editor.py`)

```python
from presentation.editor.graph_editor import GraphEditorWidget

editor = GraphEditorWidget()
editor.load_graph(graph_data)
editor.set_running_node("node_id")  # 高亮运行节点
graph = editor.get_graph()  # 导出图定义
```

**节点类型颜色**:
- `input/output` - 青色 (#4ec9b0)
- `llm` - 蓝色 (#569cd6)
- `prompt` - 黄色 (#dcdcaa)
- `parser` - 橙色 (#ce9178)
- `executor` - 紫色 (#c586c0)
- `memory` - 绿色 (#6a9955)
- `event` - 灰色 (#d4d4d4)
- `condition` - 红色 (#f44747)
- `custom` - 浅蓝 (#9cdcfe)

### 3.5 Prompt 管理器

**PromptEditorWidget** (`editor/prompt_editor.py`)

```python
from presentation.editor.prompt_editor import PromptEditorWidget

editor = PromptEditorWidget()
editor.load_prompts({"system": "...", "narrative": "..."})
```

**功能**:
- 变量自动提取（正则 `{variable}`）
- 变量值设置和预览
- 版本历史查看
- 重命名/删除

### 3.6 工具管理器

**ToolManagerWidget** (`editor/tool_manager.py`)

```python
from presentation.editor.tool_manager import ToolManagerWidget, BUILTIN_TOOLS

manager = ToolManagerWidget()
enabled = manager.get_enabled_tools()
all_tools = manager.get_all_tools()  # 9个内置工具
```

**内置工具** (9个):
1. `roll_dice` - 掷骰子
2. `start_combat` - 开始战斗
3. `give_item` - 给予物品
4. `npc_talk` - NPC对话
5. `update_quest` - 更新任务
6. `move_to` - 移动
7. `check_skill` - 技能检定
8. `search_area` - 搜索区域
9. `use_item` - 使用物品

---

## 4. 使用示例

### 4.1 启动 IDE

```python
import sys
from PyQt6.QtWidgets import QApplication
from presentation import MainWindow, theme_manager

app = QApplication(sys.argv)
theme_manager.apply("dark")

window = MainWindow()
window.show()

sys.exit(app.exec())
```

### 4.2 创建并打开项目

```python
from presentation.project.manager import project_manager

# 创建 TRPG 项目
path = project_manager.create_project(
    name="my_game",
    template="trpg",
    description="我的 TRPG 游戏"
)

# 打开项目
config = project_manager.open_project(path)

# 加载到编辑器
window.center_panel.show_graph_editor(project_manager.load_graph())

prompts = {name: project_manager.load_prompt(name) 
           for name in project_manager.list_prompts()}
window.center_panel.show_prompt_editor(prompts)
window.center_panel.show_tool_manager()
```

---

## 5. EventBus 事件

Presentation 层发出的事件:

```
ui.project.created    # 项目创建
ui.project.opened     # 项目打开
ui.project.saved      # 项目保存
ui.project.closed     # 项目关闭
```

订阅的 Feature 层事件:

```
feature.ai.turn_start       # Agent 回合开始
feature.ai.turn_end         # Agent 回合结束
feature.ai.agent_error      # Agent 错误
feature.ai.llm_stream_token # LLM 流式输出
```

---

## 6. 架构约束

- ✅ Presentation 层只依赖 Feature、Core、Foundation 层
- ❌ Presentation 层不能被下层 import
- ✅ 通过 EventBus 订阅 Feature 层事件
- ❌ 不直接操作数据库（通过 Core Repository）
- ❌ 不直接调用 LLM（通过 Feature 层）

---

## 7. 依赖关系

```
Presentation (P4)
    ├── theme/manager.py
    │   └── PyQt6.QtWidgets, PyQt6.QtGui
    ├── widgets/base.py
    │   └── foundation.event_bus, foundation.logger
    ├── main_window.py
    │   ├── theme.manager
    │   ├── widgets.base
    │   ├── editor.graph_editor
    │   ├── editor.prompt_editor
    │   ├── editor.tool_manager
    │   └── project.new_dialog
    ├── project/manager.py
    │   └── foundation.event_bus, foundation.logger
    ├── editor/graph_editor.py
    │   └── PyQt6.QtWidgets/QtCore/QtGui
    ├── editor/prompt_editor.py
    │   └── widgets.base, widgets.styled_button
    └── editor/tool_manager.py
        └── widgets.base, widgets.styled_button
```

---

*最后更新: 2026-05-02*
*状态: 已完成 ✅*
