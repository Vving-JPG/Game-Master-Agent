# Game Master Agent V2 - TUI: Textual 终端管理界面

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户为 Game Master Agent V2 **创建终端管理界面 (TUI)**，替代之前的 Vue 前端。

- **技术**: Python Textual 框架 (终端 UI)
- **目标**: 纯 Python，一个 exe，双击弹出终端窗口就是管理界面
- **包管理器**: uv
- **开发IDE**: Trae

### 为什么用 Textual

- 纯 Python，不需要 JS/Vue/Node.js
- 直接 import 后端模块（MemoryManager、SkillLoader 等），不需要 API 对接
- 组件丰富：Tree、Tabs、TextArea、DataTable、Log、Input
- 支持 CSS 样式
- PyInstaller 一个 exe 打包前后端

### 前置条件

**后端 (P0-P4) 已完成**：
- `src/memory/` — 记忆系统 (file_io + loader + manager)
- `src/skills/` — Skill 系统 (loader + 内置 SKILL.md)
- `src/adapters/` — 引擎适配层 (base + text_adapter)
- `src/agent/` — Agent 核心 (command_parser + prompt_builder + game_master + event_handler)
- `src/services/llm_client.py` — AsyncOpenAI + stream()
- `src/api/` — FastAPI 路由 + SSE
- `prompts/system_prompt.md` — Agent 主提示词
- 226+ 测试通过

**注意**: TUI 不通过 HTTP API 和后端通信，而是**直接 import 后端模块**。所以不需要 FastAPI 运行。

### TUI 阶段目标

1. **三栏布局** — 左侧资源树、中间编辑器、底部日志+输入
2. **文件管理** — 浏览 workspace/ 和 skills/，打开编辑保存
3. **Agent 交互** — 发送事件、查看输出、实时日志
4. **配置管理** — 模型参数、提示词编辑
5. **打包** — PyInstaller 单 exe

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行，每完成一步都验证通过后再进行下一步
2. **先验证再继续**：每个步骤都有"验收标准"，必须验证通过才能继续
3. **主动执行**：用户说"开始"后，你应该主动执行每一步，不需要用户反复催促
4. **遇到错误先尝试解决**：如果某步出错，先尝试自行排查修复，3次失败后再询问用户
5. **每步完成后汇报**：完成一步后，简要汇报结果和下一步计划
6. **代码规范**：
   - 所有文件使用 UTF-8 编码
   - Python 文件使用中文注释
   - TUI 界面文字使用中文
   - 遵循 PEP 8 风格

---

## 参考文档

- `docs/architecture_v2.md` — V2 架构总览
- `docs/memory_system.md` — 记忆系统设计
- `docs/skill_system.md` — Skill 系统设计
- `src/` — 后端源码

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **TUI 目录**: `tui/` (新建)
- **后端源码**: `src/`
- **Workspace**: `workspace/`
- **Skills**: `skills/`
- **Prompts**: `prompts/`

---

## 步骤

### Step 1: 安装依赖 + 创建 TUI 目录

**目的**: 搭建 TUI 开发环境。

**方案**:

1.1 安装 Textual：

```bash
uv pip install textual rich
```

1.2 创建目录结构：

```
tui/
├── __init__.py
├── app.py          # TUI 主应用
├── screens/        # 各页面
│   ├── __init__.py
│   ├── main.py     # 主界面 (三栏布局)
│   └── settings.py # 设置页面
├── widgets/        # 自定义组件
│   ├── __init__.py
│   ├── resource_tree.py   # 资源树
│   ├── file_editor.py     # 文件编辑器
│   ├── agent_log.py       # Agent 日志面板
│   ├── chat_input.py      # 聊天输入框
│   └── status_bar.py      # 状态栏
└── styles.css      # 全局样式
```

1.3 验证 Textual 安装：

```python
# 验证脚本
python -c "from textual.app import App; print('Textual OK')"
python -c "from rich.markdown import Markdown; print('Rich OK')"
```

**验收**:
- [ ] `textual` 和 `rich` 安装成功
- [ ] `tui/` 目录结构创建完毕
- [ ] import 验证通过

---

### Step 2: TUI 主框架 + 三栏布局

**目的**: 创建 TUI 主界面，实现三栏布局。

**方案**:

2.1 创建 `tui/app.py`：

```python
# tui/app.py
"""Game Master Agent - TUI 管理界面"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from tui.screens.main import MainScreen


class GameMasterApp(App):
    """Game Master Agent 终端管理界面"""

    CSS_PATH = "styles.css"
    TITLE = "Game Master Agent"
    SUB_TITLE = "v2.0"

    BINDINGS = [
        ("q", "quit", "退出"),
        ("s", "toggle_sidebar", "侧边栏"),
        ("ctrl+s", "save_file", "保存"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield MainScreen()
        yield Footer()

    def action_toggle_sidebar(self) -> None:
        """切换侧边栏显示"""
        main_screen = self.query_one(MainScreen)
        main_screen.toggle_sidebar()

    def action_save_file(self) -> None:
        """保存当前文件"""
        main_screen = self.query_one(MainScreen)
        main_screen.save_current_file()


if __name__ == "__main__":
    app = GameMasterApp()
    app.run()
```

2.2 创建 `tui/screens/main.py`：

```python
# tui/screens/main.py
"""主界面 — 三栏布局"""
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import TabbedContent, TabPane, Static
from textual.reactive import reactive

from tui.widgets.resource_tree import ResourceTree
from tui.widgets.file_editor import FileEditor
from tui.widgets.agent_log import AgentLog
from tui.widgets.chat_input import ChatInput
from tui.widgets.status_bar import StatusBar


class MainScreen(Horizontal):
    """主界面：左侧资源树 + 右侧编辑器/日志"""

    sidebar_visible: reactive[bool] = reactive(True)

    def compose(self) -> ComposeResult:
        # 左侧：资源树
        with Vertical(classes="sidebar") as self.sidebar_container:
            yield ResourceTree(classes="resource-tree")

        # 右侧：编辑器 + 日志
        with Vertical(classes="main-content"):
            # 上半部分：标签页编辑区
            with TabbedContent(classes="editor-area", initial="editor"):
                with TabPane("编辑器", id="editor"):
                    yield FileEditor(classes="file-editor")
                with TabPane("Agent 状态", id="status"):
                    yield StatusBar(classes="status-panel")
                with TabPane("设置", id="settings"):
                    yield Static("设置面板 (待实现)", classes="settings-panel")

            # 下半部分：日志 + 输入
            with Vertical(classes="log-area"):
                yield AgentLog(classes="agent-log")
                yield ChatInput(classes="chat-input")

    def toggle_sidebar(self) -> None:
        """切换侧边栏"""
        self.sidebar_visible = not self.sidebar_visible
        self.sidebar_container.display = self.sidebar_visible

    def save_current_file(self) -> None:
        """保存当前编辑的文件"""
        editor = self.query_one(FileEditor)
        editor.save()
```

2.3 创建 `tui/styles.css`：

```css
/* tui/styles.css */

/* 全局 */
Screen {
    layout: horizontal;
}

/* 侧边栏 */
.sidebar {
    width: 25;
    dock: left;
    background: $surface;
    border-right: solid $primary;
}

.resource-tree {
    height: 1fr;
}

/* 主内容区 */
.main-content {
    width: 1fr;
    layout: vertical;
}

/* 编辑器区域 */
.editor-area {
    height: 3fr;
    padding: 0 1;
}

.file-editor {
    height: 1fr;
}

.status-panel, .settings-panel {
    height: 1fr;
    padding: 1;
}

/* 日志区域 */
.log-area {
    height: 2fr;
    border-top: solid $primary;
}

.agent-log {
    height: 1fr;
    padding: 0 1;
}

.chat-input {
    height: 3;
    border-top: solid $primary;
}
```

2.4 创建占位组件（先让布局跑通）：

```python
# tui/widgets/resource_tree.py
"""资源树组件"""
from textual.widgets import Tree
from textual import events


class ResourceTree(Tree):
    """左侧资源导航树"""

    def on_mount(self) -> None:
        self.root.set_label("资源")
        # 提示词
        prompts_node = self.root.add("提示词", data={"type": "prompts"})
        prompts_node.add("system_prompt.md", data={"type": "file", "path": "prompts/system_prompt.md"})
        # 记忆
        memory_node = self.root.add("记忆", data={"type": "memory"})
        memory_node.add("npcs/", data={"type": "dir", "path": "workspace/npcs"})
        memory_node.add("locations/", data={"type": "dir", "path": "workspace/locations"})
        memory_node.add("story/", data={"type": "dir", "path": "workspace/story"})
        # 技能
        skills_node = self.root.add("技能", data={"type": "skills"})
        skills_node.add("combat", data={"type": "dir", "path": "skills/builtin/combat"})
        skills_node.add("dialogue", data={"type": "dir", "path": "skills/builtin/dialogue"})
        # 配置
        self.root.add("配置", data={"type": "config"})
        # 工作流
        self.root.add("工作流", data={"type": "workflow"})

        self.root.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """点击节点时，在编辑器中打开对应文件"""
        node_data = event.node.data
        if node_data and node_data.get("type") == "file":
            path = node_data["path"]
            # 通知编辑器打开文件
            self.app.query_one("#file-editor").load_file(path)
```

```python
# tui/widgets/file_editor.py
"""文件编辑器组件"""
from textual.widgets import TextArea, Static
from textual import work
from pathlib import Path


class FileEditor(TextArea):
    """Markdown / YAML / 文本文件编辑器"""

    current_file: str | None = None

    def load_file(self, path: str) -> None:
        """加载文件到编辑器"""
        file_path = Path(path)
        if not file_path.exists():
            self.clear()
            self.insert(f"# 文件不存在: {path}")
            return

        content = file_path.read_text(encoding="utf-8")
        self.clear()
        self.insert(content)
        self.current_file = path
        # 根据文件扩展名设置语言
        if path.endswith(".md"):
            self.language = "markdown"
        elif path.endswith(".yaml") or path.endswith(".yml"):
            self.language = "yaml"
        else:
            self.language = "plain text"

    def save(self) -> None:
        """保存当前文件"""
        if not self.current_file:
            self.app.notify("没有打开的文件", severity="warning")
            return
        content = self.text
        Path(self.current_file).write_text(content, encoding="utf-8")
        self.app.notify(f"已保存: {self.current_file}")
```

```python
# tui/widgets/agent_log.py
"""Agent 日志面板"""
from textual.widgets import RichLog
from textual import work
from datetime import datetime


class AgentLog(RichLog):
    """Agent 实时日志"""

    def on_mount(self) -> None:
        self.border_title = "Agent 日志"
        self.write(f"[dim]{datetime.now().strftime('%H:%M:%S')} | 等待 Agent 启动...[/dim]")
        self.auto_scroll = True

    def log_event(self, event_type: str, message: str) -> None:
        """记录 Agent 事件"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "narrative": "cyan",
            "command": "yellow",
            "memory": "green",
            "skill": "magenta",
            "error": "red",
            "info": "white",
        }
        color = colors.get(event_type, "white")
        self.write(f"[{color}]{timestamp} | [{event_type}] {message}[/{color}]")
```

```python
# tui/widgets/chat_input.py
"""聊天输入框"""
from textual.widgets import Input
from textual import events


class ChatInput(Input):
    """发送事件给 Agent 的输入框"""

    def __init__(self, **kwargs):
        super().__init__(placeholder="输入事件 (如: player_action 攻击铁匠)", **kwargs)

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter" and self.value.strip():
            self._send_event()
            event.prevent_default()

    def _send_event(self) -> None:
        """发送事件到 Agent"""
        text = self.value.strip()
        log = self.app.query_one("#agent-log")
        log.log_event("info", f"发送事件: {text}")
        # TODO: 调用 Agent 处理事件
        self.value = ""
```

```python
# tui/widgets/status_bar.py
"""Agent 状态面板"""
from textual.widgets import Static


class StatusBar(Static):
    """显示 Agent 当前状态"""

    def on_mount(self) -> None:
        self.update(
            "[bold]Agent 状态[/bold]\n\n"
            "状态: IDLE\n"
            "模型: deepseek-chat\n"
            "Token 用量: 0\n"
            "当前 Skill: 无\n"
            "当前回合: 0"
        )

    def update_status(self, state: dict) -> None:
        """更新状态显示"""
        self.update(
            f"[bold]Agent 状态[/bold]\n\n"
            f"状态: {state.get('status', 'IDLE')}\n"
            f"模型: {state.get('model', 'deepseek-chat')}\n"
            f"Token 用量: {state.get('tokens', 0)}\n"
            f"当前 Skill: {state.get('skill', '无')}\n"
            f"当前回合: {state.get('turn', 0)}"
        )
```

2.5 创建 `tui/__init__.py` 和 `tui/screens/__init__.py`、`tui/widgets/__init__.py`（空文件）。

2.6 运行测试：

```bash
cd tui
python -m app
```

**验收**:
- [ ] `python -m tui.app` 启动成功，显示三栏布局
- [ ] 左侧资源树显示：提示词、记忆、技能、配置、工作流
- [ ] 点击资源树节点，右侧编辑器显示文件内容
- [ ] 底部日志面板显示 "等待 Agent 启动..."
- [ ] 底部输入框可以输入文字
- [ ] 按 `q` 退出
- [ ] 按 `ctrl+s` 保存文件

---

### Step 3: 资源树 — 动态加载 workspace/ 和 skills/

**目的**: 资源树能动态扫描磁盘目录，展开显示真实文件。

**方案**:

3.1 改造 `tui/widgets/resource_tree.py`：

- 启动时扫描 `workspace/`、`skills/`、`prompts/` 目录
- 递归构建树节点
- 点击 `.md` 文件 → 编辑器打开
- 点击目录 → 展开/折叠子文件
- 支持右键菜单（新建文件、删除、重命名）— 可选

```python
# tui/widgets/resource_tree.py
"""资源树组件 — 动态扫描磁盘"""
from textual.widgets import Tree
from textual import work
from pathlib import Path


class ResourceTree(Tree):
    """左侧资源导航树 — 动态加载"""

    # 扫描的根目录
    SCAN_DIRS = {
        "提示词": "prompts",
        "记忆": "workspace",
        "技能": "skills",
        "工作流": "workflow",
    }

    def on_mount(self) -> None:
        self.root.set_label("资源")
        self.root.expand()
        self._load_all()

    @work(exclusive=True)
    async def _load_all(self) -> None:
        """扫描所有目录，构建树"""
        for label, dir_path in self.SCAN_DIRS.items():
            node = self.root.add(label, data={"type": "dir", "path": dir_path})
            self._scan_dir(node, Path(dir_path))
            node.expand()

    def _scan_dir(self, parent_node: Tree.Node, dir_path: Path) -> None:
        """递归扫描目录"""
        if not dir_path.exists():
            parent_node.add("(空)", data={"type": "empty"})
            return

        # 排序: 目录在前，文件在后
        items = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        for item in items:
            # 跳过 __pycache__、.pyc 等
            if item.name.startswith("__") or item.suffix == ".pyc":
                continue
            if item.is_dir():
                child = parent_node.add(f"📁 {item.name}/", data={"type": "dir", "path": str(item)})
                self._scan_dir(child, item)
            else:
                icon = self._get_icon(item.suffix)
                child = parent_node.add(f"{icon} {item.name}", data={"type": "file", "path": str(item)})

    def _get_icon(self, suffix: str) -> str:
        """根据文件后缀返回图标"""
        icons = {
            ".md": "📝",
            ".yaml": "⚙️",
            ".yml": "⚙️",
            ".json": "📋",
            ".py": "🐍",
            ".txt": "📄",
        }
        return icons.get(suffix, "📄")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """点击节点"""
        node_data = event.node.data
        if not node_data:
            return

        if node_data.get("type") == "file":
            path = node_data["path"]
            try:
                editor = self.app.query_one("FileEditor")
                editor.load_file(path)
            except Exception:
                self.app.notify(f"无法打开: {path}", severity="error")
```

3.2 测试：确保 workspace/ 和 skills/ 目录下有测试文件：

```bash
# 如果没有测试文件，创建一些
mkdir -p workspace/npcs workspace/locations workspace/story
echo "# 铁匠" > workspace/npcs/铁匠.md
echo "# 铁匠铺" > workspace/locations/铁匠铺.md
```

**验收**:
- [ ] 资源树动态显示 workspace/、skills/、prompts/ 下的真实文件
- [ ] 目录可展开/折叠
- [ ] 点击 .md 文件，编辑器显示文件内容
- [ ] 空目录显示 "(空)"

---

### Step 4: 文件编辑器 — 编辑 + 保存 + YAML Front Matter 支持

**目的**: 编辑器能正确编辑和保存 .md 文件，支持 YAML Front Matter。

**方案**:

4.1 改造 `tui/widgets/file_editor.py`：

- 加载文件时解析 YAML Front Matter，在顶部单独显示
- 编辑区只编辑 Markdown body
- 保存时合并 FM + body 写回
- 显示文件路径、修改状态

```python
# tui/widgets/file_editor.py
"""文件编辑器 — 支持 YAML Front Matter"""
from textual.widgets import TextArea, Static
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from pathlib import Path
import frontmatter


class FileEditor(Vertical):
    """Markdown 文件编辑器，支持 YAML Front Matter"""

    current_file: reactive[str | None] = reactive(None)
    is_modified: reactive[bool] = reactive(False)
    _frontmatter: dict = {}
    _original_content: str = ""

    def compose(self) -> None:
        # 顶部：文件路径 + 状态
        with Horizontal(classes="editor-header"):
            self.path_label = Static("未打开文件", classes="path-label")
            self.status_label = Static("", classes="status-label")
        # FM 显示区
        self.fm_display = Static("", classes="fm-display")
        # 编辑区
        self.text_area = TextArea(language="markdown", classes="text-area")

    def watch_current_file(self, old_path: str | None, new_path: str | None) -> None:
        """文件路径变化时更新显示"""
        if new_path:
            self.path_label.update(f"📄 {Path(new_path).name}")
        else:
            self.path_label.update("未打开文件")

    def watch_is_modified(self, old_val: bool, new_val: bool) -> None:
        """修改状态变化"""
        self.status_label.update("● 已修改" if new_val else "")

    def load_file(self, path: str) -> None:
        """加载文件"""
        file_path = Path(path)
        if not file_path.exists():
            self.text_area.clear()
            self.text_area.insert(f"# 文件不存在\n\n{path}")
            self.fm_display.update("")
            self._frontmatter = {}
            self.current_file = None
            self.is_modified = False
            return

        try:
            post = frontmatter.load(str(file_path))
            self._frontmatter = dict(post.metadata)
            self._original_content = post.content

            # 显示 FM
            if self._frontmatter:
                fm_lines = ["[bold]YAML Front Matter:[/bold]"]
                for key, value in self._frontmatter.items():
                    fm_lines.append(f"  {key}: {value}")
                self.fm_display.update("\n".join(fm_lines))
            else:
                self.fm_display.update("")

            # 加载 body 到编辑区
            self.text_area.clear()
            self.text_area.insert(post.content or "")
            self.text_area.language = "markdown" if path.endswith(".md") else "yaml" if path.endswith(".yaml") else "plain text"

            self.current_file = path
            self.is_modified = False
        except Exception as e:
            self.text_area.clear()
            self.text_area.insert(f"# 加载失败\n\n{e}")

    def save(self) -> None:
        """保存文件"""
        if not self.current_file:
            self.app.notify("没有打开的文件", severity="warning")
            return

        try:
            file_path = Path(self.current_file)
            content = self.text_area.text

            # 合并 FM + body
            post = frontmatter.Post(content=content)
            post.metadata = self._frontmatter
            post["version"] = post.get("version", 0) + 1

            file_path.write_text(frontmatter.dumps(post), encoding="utf-8")
            self._original_content = content
            self.is_modified = False
            self.app.notify(f"已保存: {file_path.name}")
        except Exception as e:
            self.app.notify(f"保存失败: {e}", severity="error")

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """编辑内容变化时标记为已修改"""
        if self.text_area.text != self._original_content:
            self.is_modified = True
        else:
            self.is_modified = False
```

4.2 更新 `tui/styles.css` 添加编辑器样式：

```css
/* 编辑器 */
.editor-header {
    height: 1;
    padding: 0 1;
    background: $surface-darken-1;
}

.path-label {
    width: 1fr;
}

.status-label {
    color: $warning;
    text-style: bold;
}

.fm-display {
    height: auto;
    max-height: 5;
    padding: 0 1;
    background: $surface-darken-2;
    border-bottom: solid $primary;
    overflow-y: auto;
}

.text-area {
    width: 1fr;
    height: 1fr;
}
```

**验收**:
- [ ] 打开 .md 文件，顶部显示 YAML Front Matter
- [ ] 编辑区只显示 Markdown body
- [ ] 编辑后状态栏显示 "● 已修改"
- [ ] Ctrl+S 保存成功，version 自增
- [ ] 打开不存在的文件显示提示

---

### Step 5: Agent 交互 — 发送事件 + 实时日志

**目的**: 能通过 TUI 发送事件给 Agent，实时查看 Agent 输出。

**方案**:

5.1 改造 `tui/widgets/chat_input.py`：

- 支持多种事件类型选择（Tab 切换）
- 输入事件内容，回车发送
- 发送后清空输入框

```python
# tui/widgets/chat_input.py
"""聊天输入框 — 支持事件类型选择"""
from textual.widgets import Input, Button
from textual.containers import Horizontal
from textual import events


class ChatInput(Horizontal):
    """Agent 事件输入框"""

    event_types = ["player_action", "system_event", "npc_event", "custom"]

    def __init__(self, **kwargs):
        super().__init__(classes="chat-input", **kwargs)

    def compose(self) -> None:
        # 事件类型标签
        self.type_label = Static("[事件类型: player_action]", classes="event-type-label")
        yield self.type_label
        # 输入框
        self.input = Input(placeholder="输入事件内容...", classes="event-input")
        yield self.input
        # 发送按钮
        yield Button("发送", variant="primary", classes="send-btn")

    def on_mount(self) -> None:
        self.input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """点击发送按钮"""
        if event.button.classes and "send-btn" in event.button.classes:
            self._send_event()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """回车发送"""
        self._send_event()

    def _send_event(self) -> None:
        """发送事件到 Agent"""
        text = self.input.value.strip()
        if not text:
            return

        log = self.app.query_one("AgentLog")
        log.log_event("info", f"[player_action] {text}")

        # TODO: 直接调用 Agent 模块处理事件
        # from src.agent.event_handler import EventHandler
        # result = await event_handler.handle_event({"type": "player_action", "raw_text": text})

        self.input.value = ""

    def action_cycle_event_type(self) -> None:
        """切换事件类型"""
        current = self.type_label.renderable.plain
        idx = self.event_types.index(current) if current in self.event_types else 0
        next_type = self.event_types[(idx + 1) % len(self.event_types)]
        self.type_label.update(f"[事件类型: {next_type}]")
```

5.2 改造 `tui/widgets/agent_log.py`：

- 支持不同颜色的事件类型
- 支持清除日志
- 支持自动滚动
- 支持 token 计数显示

```python
# tui/widgets/agent_log.py
"""Agent 日志面板"""
from textual.widgets import RichLog, Button
from textual.containers import Horizontal
from datetime import datetime


class AgentLog(Horizontal):
    """Agent 实时日志"""

    def compose(self) -> None:
        with Vertical(classes="log-container"):
            self.log = RichLog(highlight=True, markup=True, classes="log-content")
            yield self.log
        with Vertical(classes="log-actions"):
            yield Button("清除", variant="default", classes="clear-btn")

    def on_mount(self) -> None:
        self.log.border_title = "Agent 日志"
        self.log.auto_scroll = True
        self.log_event("info", "TUI 已启动，等待事件...")

    def log_event(self, event_type: str, message: str) -> None:
        """记录 Agent 事件"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "narrative": "cyan",
            "command": "yellow",
            "memory": "green",
            "skill": "magenta",
            "error": "red",
            "info": "dim",
            "token": "blue",
        }
        color = colors.get(event_type, "white")
        self.log.write(f"[{color}]{timestamp} | [{event_type}] {message}[/{color}]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """清除日志"""
        if event.button.classes and "clear-btn" in event.button.classes:
            self.log.clear()
            self.log_event("info", "日志已清除")
```

**验收**:
- [ ] 输入框输入文字，回车发送，日志显示事件
- [ ] 日志自动滚动到最新
- [ ] 清除按钮能清空日志
- [ ] 不同事件类型显示不同颜色

---

### Step 6: 对接后端模块

**目的**: TUI 直接调用后端 Python 模块，不通过 HTTP API。

**方案**:

6.1 创建 `tui/agent_bridge.py` — TUI 和后端之间的桥接层：

```python
# tui/agent_bridge.py
"""TUI ↔ 后端桥接层 — 直接调用后端模块"""
import asyncio
from pathlib import Path
from typing import Callable


class AgentBridge:
    """TUI 和后端之间的桥接"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self._event_handler = None
        self._memory_manager = None
        self._skill_loader = None
        self._log_callback: Callable | None = None

    def set_log_callback(self, callback: Callable) -> None:
        """设置日志回调"""
        self._log_callback = callback

    def _log(self, event_type: str, message: str) -> None:
        """发送日志"""
        if self._log_callback:
            self._log_callback(event_type, message)

    def init_backend(self) -> None:
        """初始化后端模块"""
        try:
            import sys
            sys.path.insert(0, str(self.project_root))

            from src.memory.manager import MemoryManager
            from src.skills.loader import SkillLoader

            workspace_path = str(self.project_root / "workspace")
            skills_path = str(self.project_root / "skills")

            self._memory_manager = MemoryManager(workspace_path)
            self._skill_loader = SkillLoader(skills_path)

            self._log("info", "后端模块初始化成功")
            self._log("info", f"记忆目录: {workspace_path}")
            self._log("info", f"技能目录: {skills_path}")
        except ImportError as e:
            self._log("error", f"后端模块导入失败: {e}")
        except Exception as e:
            self._log("error", f"后端初始化失败: {e}")

    async def send_event(self, event_type: str, content: str) -> dict:
        """发送事件到 Agent"""
        self._log("info", f"[{event_type}] {content}")

        try:
            from src.agent.event_handler import EventHandler

            if self._event_handler is None:
                self._event_handler = EventHandler(
                    memory_manager=self._memory_manager,
                    skill_loader=self._skill_loader,
                )

            event = {
                "type": event_type,
                "raw_text": content,
                "context_hints": [],
            }

            # 调用 Agent 处理事件
            response = await self._event_handler.handle_event(event)

            # 记录响应
            if response.get("narrative"):
                self._log("narrative", response["narrative"][:200])
            if response.get("commands"):
                for cmd in response["commands"]:
                    self._log("command", str(cmd))
            if response.get("memory_updates"):
                for upd in response["memory_updates"]:
                    self._log("memory", f"{upd.get('file', '?')}: +{len(upd.get('content', ''))} chars")

            return response
        except Exception as e:
            self._log("error", f"Agent 处理失败: {e}")
            return {"error": str(e)}

    def get_agent_status(self) -> dict:
        """获取 Agent 状态"""
        return {
            "status": "IDLE",
            "model": "deepseek-chat",
            "tokens": 0,
            "skill": "无",
            "turn": 0,
        }

    def load_memory_index(self) -> str:
        """加载记忆索引"""
        try:
            if self._memory_manager:
                return self._memory_manager.load_index()
        except Exception as e:
            self._log("error", f"加载记忆索引失败: {e}")
        return "无记忆数据"

    def list_skills(self) -> list[dict]:
        """列出所有技能"""
        try:
            if self._skill_loader:
                return self._skill_loader.list_all()
        except Exception as e:
            self._log("error", f"列出技能失败: {e}")
        return []
```

6.2 在 `tui/app.py` 中初始化桥接层：

```python
# 在 GameMasterApp.__init__ 中添加:
from tui.agent_bridge import AgentBridge

class GameMasterApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bridge = AgentBridge(project_root="..")  # 项目根目录

    def on_mount(self) -> None:
        self.bridge.set_log_callback(self._on_bridge_log)
        self.bridge.init_backend()

    def _on_bridge_log(self, event_type: str, message: str) -> None:
        """桥接层日志回调"""
        log = self.query_one("AgentLog")
        log.log_event(event_type, message)
```

6.3 修改 `ChatInput._send_event()` 使用桥接层：

```python
def _send_event(self) -> None:
    text = self.input.value.strip()
    if not text:
        return

    app = self.app
    asyncio.create_task(app.bridge.send_event("player_action", text))
    self.input.value = ""
```

**验收**:
- [ ] TUI 启动时后端模块初始化成功
- [ ] 日志显示 "后端模块初始化成功"
- [ ] 发送事件后，Agent 处理并返回结果
- [ ] 日志显示 narrative、commands、memory_updates
- [ ] 错误情况有红色错误日志

---

### Step 7: 配置管理页面

**目的**: 在 TUI 中管理模型参数和提示词。

**方案**:

7.1 创建 `tui/screens/settings.py`：

```python
# tui/screens/settings.py
"""设置页面"""
from textual.containers import Vertical, Horizontal, Grid
from textual.widgets import Static, Input, Button, Select, TextArea
from textual import events
from pathlib import Path
import json


class SettingsScreen(Vertical):
    """Agent 配置管理"""

    def compose(self) -> None:
        yield Static("[bold]Agent 配置[/bold]", classes="title")

        # 模型设置
        with Vertical(classes="settings-section"):
            yield Static("[bold]模型设置[/bold]")
            with Grid(classes="settings-grid"):
                yield Static("模型:", classes="label")
                yield Select(
                    [("deepseek-chat", "deepseek-chat"), ("deepseek-reasoner", "deepseek-reasoner")],
                    value="deepseek-chat",
                    id="model-select",
                )
                yield Static("Temperature:", classes="label")
                yield Input(value="0.7", id="temperature-input", type="number")
                yield Static("Max Tokens:", classes="label")
                yield Input(value="4096", id="max-tokens-input", type="number")

        # 保存按钮
        yield Button("保存配置", variant="primary", id="save-config-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-config-btn":
            self._save_config()

    def _save_config(self) -> None:
        """保存配置到 .env 文件"""
        model = self.query_one("#model-select", Select).value
        temp = self.query_one("#temperature-input", Input).value
        max_tokens = self.query_one("#max-tokens-input", Input).value

        config = {
            "model": model,
            "temperature": float(temp),
            "max_tokens": int(max_tokens),
        }

        config_path = Path(".env")
        lines = [f"DEEPSEEK_MODEL={config['model']}", f"TEMPERATURE={config['temperature']}", f"MAX_TOKENS={config['max_tokens']}"]
        config_path.write_text("\n".join(lines), encoding="utf-8")

        self.app.notify("配置已保存")
```

7.2 在主界面的 TabPane 中集成：

```python
# 在 MainScreen.compose() 的 "设置" TabPane 中:
with TabPane("设置", id="settings"):
    yield SettingsScreen()
```

**验收**:
- [ ] 设置页面显示模型选择、Temperature、Max Tokens
- [ ] 可以修改参数
- [ ] 保存后 .env 文件更新
- [ ] 通知 "配置已保存"

---

### Step 8: PyInstaller 打包

**目的**: 打包成单个 exe，双击弹出终端窗口。

**方案**:

8.1 创建 `tui_entry.py`（打包入口）：

```python
# tui_entry.py
"""PyInstaller 打包入口"""
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tui.app import GameMasterApp

if __name__ == "__main__":
    app = GameMasterApp()
    app.run()
```

8.2 创建 `tui.spec`（PyInstaller 配置）：

```python
# tui.spec
# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

PROJECT_ROOT = os.path.abspath('.')

datas = [
    # workspace
    (os.path.join(PROJECT_ROOT, 'workspace'), 'workspace'),
    # skills
    (os.path.join(PROJECT_ROOT, 'skills'), 'skills'),
    # prompts
    (os.path.join(PROJECT_ROOT, 'prompts'), 'prompts'),
    # tui 样式
    (os.path.join(PROJECT_ROOT, 'tui', 'styles.css'), 'tui'),
    # workflow
    (os.path.join(PROJECT_ROOT, 'workflow'), 'workflow'),
]

hiddenimports = [
    'textual',
    'rich',
    'frontmatter',
    'openai',
    'aiosqlite',
    'httpx',
    'uvicorn',
    'sse_starlette',
]

a = Analysis(
    ['tui_entry.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'IPython', 'jupyter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GameMasterAgent',
    debug=False,
    console=True,  # TUI 需要控制台
    strip=False,
    upx=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='GameMasterAgent',
)
```

8.3 执行打包：

```bash
uv pip install pyinstaller
pyinstaller tui.spec --clean
```

8.4 测试打包产物：

```bash
dist\GameMasterAgent\GameMasterAgent.exe
```

**验收**:
- [ ] `dist/GameMasterAgent/GameMasterAgent.exe` 存在
- [ ] 双击 exe 弹出终端窗口，显示 TUI 界面
- [ ] 资源树正常显示
- [ ] 能打开和编辑文件
- [ ] 能发送事件

---

### Step 9: 最终验证

**目的**: 完整功能验证。

**方案**:

9.1 完整流程测试：

```
1. 启动 TUI (python tui_entry.py)
2. 检查资源树是否显示所有目录
3. 点击 prompts/system_prompt.md → 编辑器显示内容
4. 编辑内容 → Ctrl+S 保存 → 重新打开确认保存成功
5. 点击 workspace/npcs/ 下的文件 → 编辑器显示
6. 切换到 Agent 状态标签 → 显示状态信息
7. 切换到设置标签 → 修改模型参数 → 保存
8. 在底部输入框输入事件 → 回车发送 → 日志显示
9. 按 q 退出
```

9.2 打包后测试：

```
1. pyinstaller tui.spec --clean
2. 运行 dist/GameMasterAgent/GameMasterAgent.exe
3. 重复 9.1 的所有测试
```

**验收**:
- [ ] 9.1 所有步骤通过
- [ ] 9.2 打包后所有步骤通过
- [ ] 无报错、无崩溃

---

## 注意事项

### Textual 踩坑
1. **CSS 路径**: `CSS_PATH = "styles.css"` 是相对于 app.py 的路径
2. **组件查询**: `self.query_one("FileEditor")` 用类名，`self.query_one("#my-id")` 用 id
3. **异步**: Textual 支持 async，但要注意 `@work` 装饰器用于后台任务
4. **Windows 终端**: Windows Terminal 比 cmd 好看得多，建议用 Windows Terminal
5. **编码**: 所有文件 UTF-8，Windows 下注意 `chcp 65001`

### 后端对接
1. **直接 import**: TUI 和后端在同一个 Python 进程，不需要 HTTP
2. **async**: 后端用 asyncio，TUI 也支持 async，注意事件循环
3. **路径**: 打包后路径变化，用 `sys._MEIPASS` 处理
4. **.env 加载**: 配置文件路径要注意打包后的位置

### PyInstaller 打包
1. **console=True**: TUI 必须显示控制台，不能设为 False
2. **datas**: workspace/、skills/、prompts/ 必须打包进去
3. **hiddenimports**: textual 和 rich 有动态导入，需要列出
4. **体积**: 预计 30-50MB（比 Electron 小很多）

---

## 完成检查清单

- [ ] Step 1: Textual 安装 + TUI 目录创建
- [ ] Step 2: 三栏布局跑通（资源树 + 编辑器 + 日志 + 输入）
- [ ] Step 3: 资源树动态扫描 workspace/、skills/、prompts/
- [ ] Step 4: 文件编辑器支持 YAML Front Matter + 保存
- [ ] Step 5: Agent 交互（发送事件 + 实时日志）
- [ ] Step 6: 对接后端模块（直接 import）
- [ ] Step 7: 配置管理页面（模型参数 + 保存）
- [ ] Step 8: PyInstaller 打包成 exe
- [ ] Step 9: 完整功能验证通过
