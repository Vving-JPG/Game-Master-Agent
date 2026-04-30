# Game Master Agent V2 - WB: PyQt WorkBench 管理界面

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户为 Game Master Agent V2 **创建 PyQt 桌面管理界面 (WorkBench)**。

- **技术**: Python PyQt6 (桌面 GUI)
- **目标**: 纯 Python，一个 exe，双击弹出桌面窗口就是管理界面
- **包管理器**: uv
- **开发IDE**: Trae

### 为什么用 PyQt

- 真正的桌面 GUI 窗口（不是终端、不是浏览器）
- 组件丰富：QSplitter、QTreeWidget、QTabWidget、QGraphicsScene（流程图）
- 直接 import 后端模块，不需要 HTTP API
- PyInstaller 一个 exe 打包
- QSS 样式表支持暗色主题

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

**注意**: WorkBench 直接 import 后端模块，不通过 HTTP API。

### WB 阶段目标

1. **三栏布局** — 左侧资源导航 (18%) + 中间编辑器 (52%) + 右侧辅助面板 (30%)
2. **七层资源树** — Prompt / Memory / Config / Tools / Workflow / Runtime
3. **多态编辑器** — MD / YAML / 键值对 / 流程图，根据文件类型自动切换
4. **流程图编辑器** — QGraphicsScene 节点编排、连线、拖拽
5. **底部控制台** — 执行控制 / 流程视图 / 轮次回溯 / 指令注入 / 强制工具
6. **Agent 交互** — 运行/暂停/单步/重置，实时日志
7. **打包** — PyInstaller 单 exe

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行，每完成一步都验证通过后再进行下一步
2. **先验证再继续**：每个步骤都有"验收标准"，必须验证通过才能继续
3. **主动执行**：用户说"开始"后，你应该主动执行每一步，不需要用户反复催促
4. **遇到错误先尝试解决**：如果某步出错，先尝试自行排查修复，3次失败后再询问用户
5. **每步完成后汇报**：完成一步后，简要汇报结果和下一步计划
6. **代码规范**：
   - 所有文件使用 UTF-8 编码
   - Python 文件使用中文注释
   - 界面文字使用中文
   - 遵循 PEP 8 风格

---

## 参考文档

- `docs/architecture_v2.md` — V2 架构总览
- `docs/memory_system.md` — 记忆系统设计
- `docs/skill_system.md` — Skill 系统设计
- `src/` — 后端源码

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **WorkBench 目录**: `workbench/` (新建，替换之前的 Vue 版本)
- **后端源码**: `src/`
- **Workspace**: `workspace/`
- **Skills**: `skills/`
- **Prompts**: `prompts/`

---

## 步骤

### Step 1: 安装依赖 + 三栏布局骨架

**目的**: 搭建 PyQt 环境，创建三栏布局主窗口。

**方案**:

1.1 安装 PyQt6：

```bash
uv pip install PyQt6
```

1.2 创建目录结构：

```
workbench/
├── __init__.py
├── app.py              # 应用入口
├── main_window.py      # 主窗口 (三栏布局)
├── styles/
│   ├── __init__.py
│   └── dark_theme.qss  # 暗色主题样式
├── widgets/
│   ├── __init__.py
│   ├── resource_tree.py    # 左侧资源导航树
│   ├── editor_stack.py     # 中间多态编辑器栈
│   ├── md_editor.py        # Markdown 编辑器
│   ├── yaml_editor.py      # YAML 编辑器
│   ├── kv_editor.py        # 键值对编辑器
│   ├── workflow_editor.py  # 流程图编辑器 (QGraphicsScene)
│   ├── tool_viewer.py      # 工具查看器 (只读)
│   ├── runtime_viewer.py   # 运行时查看器 (只读)
│   ├── console_tabs.py     # 底部控制台 Tab 容器
│   ├── execution_ctrl.py   # 执行控制面板
│   ├── flow_view.py        # 流程视图 (运行时)
│   ├── turn_timeline.py    # 轮次时间轴
│   ├── inject_panel.py     # 指令注入面板
│   ├── force_tool.py       # 强制工具面板
│   ├── agent_status.py     # Agent 状态面板
│   └── resource_monitor.py # 资源监控面板
├── bridge/
│   ├── __init__.py
│   └── agent_bridge.py     # 后端桥接层
└── resources/
    └── icons/              # 图标资源
```

1.3 创建 `workbench/app.py`：

```python
# workbench/app.py
"""Game Master Agent WorkBench — 应用入口"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from workbench.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Game Master Agent")
    app.setApplicationVersion("2.0")

    # 加载暗色主题
    with open("workbench/styles/dark_theme.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

1.4 创建 `workbench/main_window.py`：

```python
# workbench/main_window.py
"""主窗口 — 三栏布局 + 顶部工具栏 + 底部控制台"""
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QToolBar, QLabel, QComboBox, QDoubleSpinBox,
    QStatusBar,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction

from workbench.widgets.resource_tree import ResourceTree
from workbench.widgets.editor_stack import EditorStack
from workbench.widgets.console_tabs import ConsoleTabs
from workbench.widgets.agent_status import AgentStatusPanel
from workbench.widgets.resource_monitor import ResourceMonitorPanel


class MainWindow(QMainWindow):
    """WorkBench 主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Master Agent WorkBench")
        self.setMinimumSize(1200, 800)
        self.resize(1600, 900)

        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()

    def _setup_toolbar(self):
        """顶部工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # 运行控制按钮
        self.act_run = QAction("▶ 运行", self)
        self.act_run.setShortcut("F5")
        toolbar.addAction(self.act_run)

        self.act_pause = QAction("⏸ 暂停", self)
        self.act_pause.setShortcut("F6")
        toolbar.addAction(self.act_pause)

        self.act_step = QAction("⏯ 单步", self)
        self.act_step.setShortcut("F10")
        toolbar.addAction(self.act_step)

        self.act_reset = QAction("↺ 重置", self)
        toolbar.addAction(self.act_reset)

        toolbar.addSeparator()

        # 模型选择
        toolbar.addWidget(QLabel(" 模型: "))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["deepseek-chat", "deepseek-reasoner"])
        self.model_combo.setMinimumWidth(150)
        toolbar.addWidget(self.model_combo)

        # 温度
        toolbar.addWidget(QLabel(" 温度: "))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(0.7)
        self.temp_spin.setDecimals(1)
        toolbar.addWidget(self.temp_spin)

    def _setup_central_widget(self):
        """中央三栏布局 + 底部控制台"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # 主分割器: 上方三栏 + 下方控制台
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # 上方水平三栏
        h_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: 资源导航 (18%)
        self.resource_tree = ResourceTree()
        h_splitter.addWidget(self.resource_tree)

        # 中间: 编辑器 (52%)
        self.editor_stack = EditorStack()
        h_splitter.addWidget(self.editor_stack)

        # 右侧: 辅助面板 (30%)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.agent_status = AgentStatusPanel()
        self.resource_monitor = ResourceMonitorPanel()
        right_layout.addWidget(self.agent_status, stretch=1)
        right_layout.addWidget(self.resource_monitor, stretch=1)
        h_splitter.addWidget(right_panel)

        # 设置初始比例 18:52:30
        h_splitter.setSizes([290, 830, 480])

        # 下方: 底部控制台
        self.console_tabs = ConsoleTabs()
        self.console_tabs.setMaximumHeight(250)
        self.console_tabs.setMinimumHeight(100)

        main_splitter.addWidget(h_splitter)
        main_splitter.addWidget(self.console_tabs)
        main_splitter.setSizes([650, 250])

        layout.addWidget(main_splitter)

        # 连接信号: 资源树点击 → 编辑器打开文件
        self.resource_tree.file_selected.connect(self.editor_stack.open_file)

    def _setup_statusbar(self):
        """底部状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")
```

1.5 创建 `workbench/styles/dark_theme.qss`：

```css
/* workbench/styles/dark_theme.qss */
/* 暗色主题 — 参考 VS Code Dark+ */

/* 全局 */
QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* 主窗口 */
QMainWindow {
    background-color: #1e1e1e;
}

/* 工具栏 */
QToolBar {
    background-color: #2d2d2d;
    border-bottom: 1px solid #3e3e3e;
    padding: 2px;
    spacing: 4px;
}

QToolBar QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 4px 10px;
    color: #d4d4d4;
}

QToolBar QToolButton:hover {
    background-color: #3e3e3e;
    border-color: #505050;
}

QToolBar QToolButton:pressed {
    background-color: #094771;
}

/* 分割器 */
QSplitter::handle {
    background-color: #3e3e3e;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

/* 树 */
QTreeWidget, QTreeView {
    background-color: #252526;
    alternate-background-color: #2a2a2a;
    border: none;
    padding: 4px;
    outline: none;
}

QTreeWidget::item, QTreeView::item {
    padding: 3px 6px;
    border-radius: 3px;
}

QTreeWidget::item:selected, QTreeView::item:selected {
    background-color: #094771;
    color: #ffffff;
}

QTreeWidget::item:hover, QTreeView::item:hover {
    background-color: #2a2d2e;
}

/* 标签页 */
QTabWidget::pane {
    border: 1px solid #3e3e3e;
    background-color: #1e1e1e;
}

QTabBar::tab {
    background-color: #2d2d2d;
    border: 1px solid #3e3e3e;
    padding: 6px 16px;
    margin-right: 2px;
    color: #969696;
}

QTabBar::tab:selected {
    background-color: #1e1e1e;
    border-bottom-color: #1e1e1e;
    color: #ffffff;
}

/* 文本编辑器 */
QPlainTextEdit, QTextEdit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: none;
    padding: 8px;
    selection-background-color: #264f78;
    selection-color: #ffffff;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #3c3c3c;
    border: 1px solid #3e3e3e;
    border-radius: 3px;
    padding: 4px 8px;
    color: #d4d4d4;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #007acc;
}

/* 按钮 */
QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #3e3e3e;
    border-radius: 3px;
    padding: 5px 16px;
    color: #d4d4d4;
}

QPushButton:hover {
    background-color: #505050;
}

QPushButton:pressed {
    background-color: #094771;
}

QPushButton:disabled {
    background-color: #2d2d2d;
    color: #6e6e6e;
}

/* 状态栏 */
QStatusBar {
    background-color: #007acc;
    color: #ffffff;
}

/* 滚动条 */
QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 10px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #424242;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4f4f4f;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* 下拉框 */
QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    border: 1px solid #3e3e3e;
    selection-background-color: #094771;
}

/* 表格 */
QTableWidget {
    background-color: #1e1e1e;
    gridline-color: #3e3e3e;
    border: none;
}

QTableWidget::item {
    padding: 4px;
}

QHeaderView::section {
    background-color: #2d2d2d;
    border: 1px solid #3e3e3e;
    padding: 4px;
    font-weight: bold;
}
```

1.6 创建占位组件（让布局先跑通）：

```python
# workbench/widgets/resource_tree.py
"""左侧资源导航树"""
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import pyqtSignal


class ResourceTree(QTreeWidget):
    """七层资源导航树"""
    file_selected = pyqtSignal(str)  # 发射文件路径

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self._build_tree()

    def _build_tree(self):
        """构建初始资源树"""
        # 提示词
        prompt_node = QTreeWidgetItem(self, ["🧠 Prompt"])
        QTreeWidgetItem(prompt_node, ["system_prompt.md"])
        skills_node = QTreeWidgetItem(prompt_node, ["📁 Skills"])
        QTreeWidgetItem(skills_node, ["combat/SKILL.md"])
        QTreeWidgetItem(skills_node, ["dialogue/SKILL.md"])
        prompt_node.setExpanded(True)

        # 记忆
        memory_node = QTreeWidgetItem(self, ["📁 Memory"])
        QTreeWidgetItem(memory_node, ["index.md"])
        npcs_node = QTreeWidgetItem(memory_node, ["📁 npcs"])
        QTreeWidgetItem(npcs_node, ["铁匠.md"])
        QTreeWidgetItem(npcs_node, ["药剂师.md"])
        locs_node = QTreeWidgetItem(memory_node, ["📁 locations"])
        QTreeWidgetItem(locs_node, ["铁匠铺.md"])
        memory_node.setExpanded(True)

        # 配置
        config_node = QTreeWidgetItem(self, ["⚙️ Config"])
        QTreeWidgetItem(config_node, [".env"])
        QTreeWidgetItem(config_node, ["adapter.yaml"])

        # 工具
        tools_node = QTreeWidgetItem(self, ["🔧 Tools"])
        QTreeWidgetItem(tools_node, ["combat.initiate"])

        # 工作流
        workflow_node = QTreeWidgetItem(self, ["🔄 Workflow"])
        QTreeWidgetItem(workflow_node, ["main_loop.yaml"])

        # 运行时
        runtime_node = QTreeWidgetItem(self, ["📊 Runtime"])
        QTreeWidgetItem(runtime_node, ["Current Turn"])
        QTreeWidgetItem(runtime_node, ["Turn History"])
        QTreeWidgetItem(runtime_node, ["Event Log"])

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """点击节点"""
        text = item.text(0)
        # 简单判断是否是文件
        if "." in text and not text.endswith("/"):
            self.file_selected.emit(text)
```

```python
# workbench/widgets/editor_stack.py
"""中间多态编辑器栈"""
from PyQt6.QtWidgets import QStackedWidget, QPlainTextEdit, QLabel
from PyQt6.QtCore import pyqtSlot


class EditorStack(QStackedWidget):
    """多态编辑器 — 根据文件类型切换编辑器"""

    def __init__(self):
        super().__init__()
        # 默认占位
        self.placeholder = QLabel("选择左侧资源以打开文件")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.addWidget(self.placeholder)

        # Markdown 编辑器
        self.md_editor = QPlainTextEdit()
        self.md_editor.setPlaceholderText("Markdown 编辑器")
        self.addWidget(self.md_editor)

        # YAML 编辑器
        self.yaml_editor = QPlainTextEdit()
        self.yaml_editor.setPlaceholderText("YAML 编辑器")
        self.addWidget(self.yaml_editor)

    @pyqtSlot(str)
    def open_file(self, path: str):
        """根据文件路径打开对应编辑器"""
        if path.endswith(".md"):
            self.md_editor.setPlainText(f"# {path}\n\n(文件内容将在此显示)")
            self.setCurrentIndex(1)
        elif path.endswith(".yaml") or path.endswith(".yml"):
            self.yaml_editor.setPlainText(f"# {path}\n\n(文件内容将在此显示)")
            self.setCurrentIndex(2)
        else:
            self.md_editor.setPlainText(f"# {path}\n\n(文件内容将在此显示)")
            self.setCurrentIndex(1)
```

```python
# workbench/widgets/console_tabs.py
"""底部控制台 — Tab 容器"""
from PyQt6.QtWidgets import QTabWidget, QPlainTextEdit, QWidget, QVBoxLayout


class ConsoleTabs(QTabWidget):
    """底部控制台 — 5 个 Tab"""

    def __init__(self):
        super().__init__()
        self._build_tabs()

    def _build_tabs(self):
        # Tab 1: 执行控制
        exec_ctrl = QPlainTextEdit("执行控制面板 (待实现)")
        exec_ctrl.setReadOnly(True)
        self.addTab(exec_ctrl, "执行控制")

        # Tab 2: 流程视图
        flow_view = QPlainTextEdit("流程视图 (待实现)")
        flow_view.setReadOnly(True)
        self.addTab(flow_view, "流程视图")

        # Tab 3: 轮次回溯
        turn_timeline = QPlainTextEdit("轮次回溯 (待实现)")
        turn_timeline.setReadOnly(True)
        self.addTab(turn_timeline, "轮次回溯")

        # Tab 4: 指令注入
        inject = QPlainTextEdit("指令注入 (待实现)")
        inject.setReadOnly(True)
        self.addTab(inject, "指令注入")

        # Tab 5: 强制工具
        force_tool = QPlainTextEdit("强制工具 (待实现)")
        force_tool.setReadOnly(True)
        self.addTab(force_tool, "强制工具")
```

```python
# workbench/widgets/agent_status.py
"""Agent 状态面板"""
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel


class AgentStatusPanel(QGroupBox):
    """Agent 状态面板"""

    def __init__(self):
        super().__init__("🤖 Agent 状态")
        layout = QVBoxLayout(self)
        self.status_label = QLabel("状态: IDLE")
        self.model_label = QLabel("模型: deepseek-chat")
        self.token_label = QLabel("Token: 0")
        self.skill_label = QLabel("Skill: 无")
        self.turn_label = QLabel("回合: 0")
        for w in [self.status_label, self.model_label, self.token_label, self.skill_label, self.turn_label]:
            layout.addWidget(w)
```

```python
# workbench/widgets/resource_monitor.py
"""资源监控面板"""
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QProgressBar


class ResourceMonitorPanel(QGroupBox):
    """资源监控面板"""

    def __init__(self):
        super().__init__("📊 资源监控")
        layout = QVBoxLayout(self)
        self.memory_label = QLabel("内存: 0 MB")
        self.cpu_label = QLabel("CPU: 0%")
        self.token_bar = QProgressBar()
        self.token_bar.setRange(0, 100)
        self.token_bar.setValue(0)
        self.token_bar.setFormat("Token 用量: %v%")
        for w in [self.memory_label, self.cpu_label, self.token_bar]:
            layout.addWidget(w)
```

1.7 运行测试：

```bash
cd workbench
python -m app
```

**验收**:
- [ ] `python -m workbench.app` 启动成功
- [ ] 显示三栏布局：左侧资源树 + 中间编辑区 + 右侧状态面板
- [ ] 顶部工具栏显示：运行/暂停/单步/重置/模型选择/温度
- [ ] 底部控制台显示 5 个 Tab
- [ ] 暗色主题生效（深色背景、浅色文字）
- [ ] 点击左侧资源树节点，中间编辑器切换
- [ ] 拖动分割线可以调整三栏比例

---

### Step 2: 左侧资源导航 — 动态扫描 + 七层树

**目的**: 资源树动态扫描磁盘目录，支持右键菜单。

**方案**:

2.1 改造 `workbench/widgets/resource_tree.py`：

- 启动时扫描 `workspace/`、`skills/`、`prompts/`、`workflow/` 目录
- 递归构建树节点，带图标
- 点击文件 → 发射 `file_selected` 信号
- 右键菜单：新建文件、重命名、删除
- Runtime 节点特殊处理（只读，不从磁盘加载）

```python
# workbench/widgets/resource_tree.py
"""左侧资源导航树 — 动态扫描磁盘"""
from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu,
)
from PyQt6.QtCore import pyqtSignal, Qt
from pathlib import Path


# 七层资源定义
RESOURCE_LAYERS = [
    ("🧠 Prompt", "prompts", True),
    ("📁 Memory", "workspace", True),
    ("⚙️ Config", ".", False),   # .env, adapter.yaml
    ("🔧 Tools", "skills", True),
    ("🔄 Workflow", "workflow", True),
    ("📊 Runtime", None, False),  # 运行时，不从磁盘加载
]


class ResourceTree(QTreeWidget):
    """七层资源导航树"""
    file_selected = pyqtSignal(str, str)  # (file_path, resource_type)

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemClicked.connect(self._on_item_clicked)
        self._build_tree()

    def _build_tree(self):
        """构建资源树"""
        for label, dir_path, scan_disk in RESOURCE_LAYERS:
            node = QTreeWidgetItem(self, [label])
            node.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "label": label})

            if scan_disk and dir_path:
                self._scan_dir(node, Path(dir_path))

            if label == "📊 Runtime":
                # 运行时固定节点
                QTreeWidgetItem(node, ["Current Turn"]).setData(0, Qt.ItemDataRole.UserRole, {"type": "runtime", "key": "current_turn"})
                QTreeWidgetItem(node, ["Turn History"]).setData(0, Qt.ItemDataRole.UserRole, {"type": "runtime", "key": "turn_history"})
                QTreeWidgetItem(node, ["Event Log"]).setData(0, Qt.ItemDataRole.UserRole, {"type": "runtime", "key": "event_log"})

            node.setExpanded(True)

    def _scan_dir(self, parent: QTreeWidgetItem, dir_path: Path):
        """递归扫描目录"""
        if not dir_path.exists():
            QTreeWidgetItem(parent, ["(空)"]).setData(0, Qt.ItemDataRole.UserRole, {"type": "empty"})
            return

        items = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        for item in items:
            if item.name.startswith("__") or item.suffix == ".pyc":
                continue
            if item.is_dir():
                child = QTreeWidgetItem(parent, [f"📁 {item.name}/"])
                child.setData(0, Qt.ItemDataRole.UserRole, {"type": "dir", "path": str(item)})
                self._scan_dir(child, item)
            else:
                icon = self._get_icon(item.suffix)
                child = QTreeWidgetItem(parent, [f"{icon} {item.name}"])
                child.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "path": str(item)})
                # 设置字体颜色
                child.setForeground(0, self._get_color(item.suffix))

    def _get_icon(self, suffix: str) -> str:
        return {"md": "📝", "yaml": "⚙️", "yml": "⚙️", "json": "📋", "py": "🐍", "txt": "📄", "env": "🔐"}.get(suffix.lstrip("."), "📄")

    def _get_color(self, suffix: str):
        from PyQt6.QtGui import QColor
        return {"md": QColor("#569cd6"), "yaml": QColor("#ce9178"), "py": QColor("#4ec9b0"), "env": QColor("#dcdcaa")}.get(suffix.lstrip("."), QColor("#d4d4d4"))

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """点击节点"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data.get("type") == "file":
            path = data["path"]
            self.file_selected.emit(path, self._detect_resource_type(path))

    def _detect_resource_type(self, path: str) -> str:
        """检测资源类型"""
        if "prompts" in path:
            return "prompt"
        elif "skills" in path:
            return "skill"
        elif "workspace" in path:
            return "memory"
        elif "workflow" in path:
            return "workflow"
        return "unknown"

    def _show_context_menu(self, position):
        """右键菜单"""
        item = self.itemAt(position)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") not in ("file", "dir"):
            return

        menu = QMenu(self)
        act_open = menu.addAction("打开")
        act_rename = menu.addAction("重命名")
        act_delete = menu.addAction("删除")
        menu.addSeparator()
        act_new_file = menu.addAction("新建文件")
        act_new_dir = menu.addAction("新建文件夹")

        action = menu.exec(self.viewport().mapToGlobal(position))
        if action == act_open:
            self._on_item_clicked(item, 0)
        elif action == act_new_file:
            self._create_new_file(item)
        # TODO: 实现重命名、删除、新建文件夹

    def _create_new_file(self, parent_item: QTreeWidgetItem):
        """在选中目录下新建文件"""
        data = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "dir":
            dir_path = Path(data["path"])
        elif data and data.get("type") == "category":
            dir_path = Path(data.get("dir_path", "."))
        else:
            return
        # 创建新文件
        new_file = dir_path / "untitled.md"
        new_file.write_text("# untitled\n", encoding="utf-8")
        # 刷新树
        self._build_tree()
```

2.2 测试：确保各目录有测试文件。

**验收**:
- [ ] 资源树显示七层分类
- [ ] Prompt/Memory/Workflow 节点展开显示真实文件
- [ ] 点击 .md 文件，中间编辑器显示文件内容
- [ ] 文件名有颜色区分 (.md 蓝色, .yaml 橙色)
- [ ] 右键菜单弹出（打开/重命名/删除/新建）

---

### Step 3: 中间多态编辑器 — MD/YAML/键值对

**目的**: 根据文件类型自动切换编辑器，支持真实文件读写。

**方案**:

3.1 改造 `workbench/widgets/editor_stack.py`：

```python
# workbench/widgets/editor_stack.py
"""中间多态编辑器栈 — 根据文件类型路由"""
from PyQt6.QtWidgets import QStackedWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import pyqtSlot, Qt
from PyQt6.QtGui import QAction, QKeySequence
from pathlib import Path

from workbench.widgets.md_editor import MarkdownEditor
from workbench.widgets.yaml_editor import YamlEditor
from workbench.widgets.kv_editor import KeyValueEditor
from workbench.widgets.tool_viewer import ToolViewer
from workbench.widgets.runtime_viewer import RuntimeViewer


class EditorStack(QStackedWidget):
    """多态编辑器 — 根据资源类型切换"""

    def __init__(self):
        super().__init__()
        self.current_file: str | None = None
        self.is_modified: bool = False

        # 占位页
        self.placeholder = QLabel("选择左侧资源以打开文件")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.addWidget(self.placeholder)

        # 各类型编辑器
        self.md_editor = MarkdownEditor()
        self.yaml_editor = YamlEditor()
        self.kv_editor = KeyValueEditor()
        self.tool_viewer = ToolViewer()
        self.runtime_viewer = RuntimeViewer()

        self.addWidget(self.md_editor)       # index 1
        self.addWidget(self.yaml_editor)     # index 2
        self.addWidget(self.kv_editor)       # index 3
        self.addWidget(self.tool_viewer)     # index 4
        self.addWidget(self.runtime_viewer)  # index 5

        # 监听编辑器修改
        self.md_editor.modificationChanged.connect(self._on_modified)
        self.yaml_editor.modificationChanged.connect(self._on_modified)

    @pyqtSlot(str, str)
    def open_file(self, path: str, resource_type: str = "unknown"):
        """打开文件"""
        # 先保存当前文件（如果有修改）
        if self.is_modified:
            self.save_current()

        self.current_file = path
        self.is_modified = False

        file_path = Path(path)
        if not file_path.exists():
            self.md_editor.setPlainText(f"# 文件不存在\n\n{path}")
            self.setCurrentIndex(1)
            return

        content = file_path.read_text(encoding="utf-8")

        if resource_type == "tool":
            self.tool_viewer.load(content)
            self.setCurrentIndex(4)
        elif resource_type in ("current_turn", "turn_history", "event_log"):
            self.runtime_viewer.load(resource_type, content)
            self.setCurrentIndex(5)
        elif path.endswith(".env") or path.endswith(".cfg"):
            self.kv_editor.load(content, path)
            self.setCurrentIndex(3)
        elif path.endswith(".yaml") or path.endswith(".yml"):
            self.yaml_editor.load(content, path)
            self.setCurrentIndex(2)
        else:
            self.md_editor.load(content, path)
            self.setCurrentIndex(1)

    def save_current(self):
        """保存当前文件"""
        idx = self.currentIndex()
        if idx == 1:
            self.md_editor.save()
        elif idx == 2:
            self.yaml_editor.save()
        elif idx == 3:
            self.kv_editor.save()

    def _on_modified(self, changed: bool):
        """编辑器内容修改"""
        self.is_modified = changed
        if self.current_file:
            name = Path(self.current_file).name
            title = f"{name} ●" if changed else name
            # 更新标签页标题（如果有标签页系统的话）
```

3.2 创建 `workbench/widgets/md_editor.py`：

```python
# workbench/widgets/md_editor.py
"""Markdown 编辑器 — 支持 YAML Front Matter"""
from PyQt6.QtWidgets import (
    QPlainTextEdit, QWidget, QVBoxLayout, QLabel, QSplitter,
)
from PyQt6.QtCore import Qt
from pathlib import Path
import frontmatter


class MarkdownEditor(QWidget):
    """Markdown 编辑器，顶部显示 YAML Front Matter"""

    modificationChanged = None  # 由内部 editor 发射

    def __init__(self):
        super().__init__()
        self.current_file: str | None = None
        self._original_content: str = ""
        self._frontmatter: dict = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # FM 显示区
        self.fm_label = QLabel("")
        self.fm_label.setStyleSheet("background-color: #2d2d2d; padding: 8px; color: #ce9178;")
        self.fm_label.setWordWrap(True)
        self.fm_label.setVisible(False)
        layout.addWidget(self.fm_label)

        # 编辑区
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Markdown 编辑器")
        layout.addWidget(self.editor)

        # 转发信号
        self.modificationChanged = self.editor.modificationChanged

    def load(self, content: str, path: str):
        """加载文件"""
        self.current_file = path
        try:
            post = frontmatter.loads(content)
            self._frontmatter = dict(post.metadata)
            self._original_content = post.content

            if self._frontmatter:
                fm_lines = ["[YAML Front Matter]"]
                for k, v in self._frontmatter.items():
                    fm_lines.append(f"  {k}: {v}")
                self.fm_label.setText("\n".join(fm_lines))
                self.fm_label.setVisible(True)
            else:
                self.fm_label.setVisible(False)

            self.editor.setPlainText(post.content or "")
            self.editor.setModified(False)
        except Exception as e:
            self.editor.setPlainText(f"# 加载失败\n\n{e}")

    def save(self):
        """保存文件"""
        if not self.current_file:
            return
        content = self.editor.toPlainText()
        post = frontmatter.Post(content=content)
        post.metadata = self._frontmatter
        post["version"] = post.get("version", 0) + 1
        Path(self.current_file).write_text(frontmatter.dumps(post), encoding="utf-8")
        self._original_content = content
        self.editor.setModified(False)

    def toPlainText(self):
        return self.editor.toPlainText()

    def setPlainText(self, text: str):
        self.editor.setPlainText(text)
```

3.3 创建 `workbench/widgets/yaml_editor.py`：

```python
# workbench/widgets/yaml_editor.py
"""YAML 编辑器"""
from PyQt6.QtWidgets import QPlainTextEdit, QLabel, QVBoxLayout, QWidget
from pathlib import Path


class YamlEditor(QWidget):
    """YAML 编辑器"""

    modificationChanged = None

    def __init__(self):
        super().__init__()
        self.current_file: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("YAML 编辑器")
        layout.addWidget(self.editor)
        self.modificationChanged = self.editor.modificationChanged

    def load(self, content: str, path: str):
        self.current_file = path
        self.editor.setPlainText(content)
        self.editor.setModified(False)

    def save(self):
        if not self.current_file:
            return
        Path(self.current_file).write_text(self.editor.toPlainText(), encoding="utf-8")
        self.editor.setModified(False)
```

3.4 创建 `workbench/widgets/kv_editor.py`：

```python
# workbench/widgets/kv_editor.py
"""键值对编辑器 — 用于 .env 和配置文件"""
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt
from pathlib import Path


class KeyValueEditor(QWidget):
    """键值对编辑器"""

    modificationChanged = None

    def __init__(self):
        super().__init__()
        self.current_file: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["键", "值"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, 200)
        layout.addWidget(self.table)

        # 添加/删除按钮
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ 添加")
        btn_del = QPushButton("- 删除")
        btn_add.clicked.connect(self._add_row)
        btn_del.clicked.connect(self._del_row)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_del)
        layout.addLayout(btn_layout)

    def load(self, content: str, path: str):
        self.current_file = path
        self.table.setRowCount(0)
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(key.strip()))
                self.table.setItem(row, 1, QTableWidgetItem(value.strip()))

    def save(self):
        if not self.current_file:
            return
        lines = []
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            val_item = self.table.item(row, 1)
            if key_item and val_item:
                lines.append(f"{key_item.text()}={val_item.text()}")
        Path(self.current_file).write_text("\n".join(lines), encoding="utf-8")

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)

    def _del_row(self):
        rows = set(item.row() for item in self.table.selectedItems())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
```

3.5 创建占位的 `tool_viewer.py` 和 `runtime_viewer.py`：

```python
# workbench/widgets/tool_viewer.py
"""工具查看器 (只读)"""
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout


class ToolViewer(QWidget):
    """工具定义查看器"""

    modificationChanged = None

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        layout.addWidget(self.editor)

    def load(self, content: str):
        self.editor.setPlainText(content)
```

```python
# workbench/widgets/runtime_viewer.py
"""运行时查看器 (只读)"""
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout


class RuntimeViewer(QWidget):
    """运行时数据查看器"""

    modificationChanged = None

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        layout.addWidget(self.editor)

    def load(self, key: str, content: str):
        self.editor.setPlainText(f"[{key}]\n\n{content or '(暂无数据)'}")
```

3.6 更新 `main_window.py` 中的信号连接，传递 `resource_type`：

```python
# 在 MainWindow._setup_central_widget 中:
self.resource_tree.file_selected.connect(self.editor_stack.open_file)
```

3.7 添加 Ctrl+S 快捷键保存：

```python
# 在 MainWindow.__init__ 中:
save_action = QAction("保存", self)
save_action.setShortcut("Ctrl+S")
save_action.triggered.connect(self.editor_stack.save_current)
self.addAction(save_action)
```

**验收**:
- [ ] 点击 .md 文件 → Markdown 编辑器打开，顶部显示 YAML FM
- [ ] 点击 .yaml 文件 → YAML 编辑器打开
- [ ] 点击 .env 文件 → 键值对表格编辑器打开
- [ ] 编辑内容后 Ctrl+S 保存成功
- [ ] 重新打开文件，确认保存内容正确
- [ ] .md 文件保存后 version 自增

---

### Step 4: 流程图编辑器 — QGraphicsScene 节点编排

**目的**: 实现可视化工作流编辑器，支持节点拖拽、连线。

**方案**:

4.1 创建 `workbench/widgets/workflow_editor.py`：

```python
# workbench/widgets/workflow_editor.py
"""流程图编辑器 — QGraphicsScene 节点编排"""
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QGraphicsTextItem, QGraphicsRectItem,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QFileDialog, QGraphicsLineItem,
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QPolygonF,
)
import yaml
from pathlib import Path


# 节点类型定义
NODE_TYPES = {
    "start": {"label": "开始", "color": "#4caf50", "shape": "ellipse"},
    "end": {"label": "结束", "color": "#f44336", "shape": "ellipse"},
    "event": {"label": "接收事件", "color": "#2196f3", "shape": "rect"},
    "prompt": {"label": "构建 Prompt", "color": "#ff9800", "shape": "rect"},
    "llm": {"label": "LLM 推理", "color": "#9c27b0", "shape": "rect"},
    "command": {"label": "解析命令", "color": "#00bcd4", "shape": "rect"},
    "memory": {"label": "更新记忆", "color": "#8bc34a", "shape": "rect"},
    "condition": {"label": "条件判断", "color": "#ff5722", "shape": "diamond"},
    "parallel": {"label": "并行执行", "color": "#607d8b", "shape": "rect"},
    "loop": {"label": "循环", "color": "#795548", "shape": "rect"},
}


class WorkflowNode(QGraphicsRectItem):
    """工作流节点"""

    def __init__(self, node_type: str, node_id: str, x: float = 0, y: float = 0):
        super().__init__(QRectF(0, 0, 140, 60))
        self.node_type = node_type
        self.node_id = node_id
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        config = NODE_TYPES.get(node_type, {"label": node_type, "color": "#666", "shape": "rect"})
        self.color = QColor(config["color"])
        self.label = config["label"]

        # 标签
        self.text_item = QGraphicsTextItem(self.label, self)
        self.text_item.setDefaultTextColor(QColor("#ffffff"))
        font = QFont("Microsoft YaHei", 10)
        font.setBold(True)
        self.text_item.setFont(font)
        self.text_item.setPos(20, 18)

        # ID 标签
        self.id_text = QGraphicsTextItem(node_id, self)
        self.id_text.setDefaultTextColor(QColor("#aaaaaa"))
        self.id_text.setFont(QFont("Consolas", 8))
        self.id_text.setPos(20, 38)

    def paint(self, painter: QPainter, option, widget):
        painter.setPen(QPen(self.color, 2))
        painter.setBrush(QBrush(QColor(self.color.red(), self.color.green(), self.color.blue(), 60)))
        painter.drawRoundedRect(self.rect(), 8, 8)

        # 选中高亮
        if self.isSelected():
            painter.setPen(QPen(QColor("#ffffff"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(-2, -2, 2, 2), 10, 10)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # 通知场景更新连线
            scene = self.scene()
            if scene and hasattr(scene, "update_edges"):
                scene.update_edges()
        return super().itemChange(change, value)


class WorkflowEdge(QGraphicsPathItem):
    """工作流连线"""

    def __init__(self, source: WorkflowNode, target: WorkflowNode):
        super().__init__()
        self.source = source
        self.target = target
        self.setPen(QPen(QColor("#666666"), 2))
        self.setZValue(-1)
        self.update_path()

    def update_path(self):
        """更新连线路径"""
        source_rect = self.source.sceneBoundingRect()
        target_rect = self.target.sceneBoundingRect()

        start = QPointF(
            source_rect.right(),
            source_rect.top() + source_rect.height() / 2,
        )
        end = QPointF(
            target_rect.left(),
            target_rect.top() + target_rect.height() / 2,
        )

        path = QPainterPath()
        path.moveTo(start)
        ctrl_x = (start.x() + end.x()) / 2
        path.cubicTo(ctrl_x, start.y(), ctrl_x, end.y(), end.x(), end.y())
        self.setPath(path)


class WorkflowScene(QGraphicsScene):
    """工作流场景"""

    def __init__(self):
        super().__init__()
        self.nodes: dict[str, WorkflowNode] = {}
        self.edges: list[WorkflowEdge] = []
        self.setSceneRect(0, 0, 2000, 1500)

    def add_node(self, node_type: str, node_id: str, x: float, y: float) -> WorkflowNode:
        """添加节点"""
        node = WorkflowNode(node_type, node_id, x, y)
        self.addItem(node)
        self.nodes[node_id] = node
        return node

    def add_edge(self, source_id: str, target_id: str):
        """添加连线"""
        if source_id in self.nodes and target_id in self.nodes:
            edge = WorkflowEdge(self.nodes[source_id], self.nodes[target_id])
            self.addItem(edge)
            self.edges.append(edge)

    def update_edges(self):
        """更新所有连线"""
        for edge in self.edges:
            edge.update_path()

    def clear_all(self):
        """清空所有节点和连线"""
        self.clear()
        self.nodes.clear()
        self.edges.clear()

    def load_from_yaml(self, yaml_content: str):
        """从 YAML 加载工作流"""
        self.clear_all()
        try:
            data = yaml.safe_load(yaml_content)
            if not data:
                return
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])
            for node in nodes:
                self.add_node(
                    node.get("type", "event"),
                    node.get("id", ""),
                    node.get("x", 0),
                    node.get("y", 0),
                )
            for edge in edges:
                self.add_edge(edge.get("from", ""), edge.get("to", ""))
        except Exception as e:
            print(f"加载工作流失败: {e}")

    def to_yaml(self) -> str:
        """导出为 YAML"""
        nodes = []
        for nid, node in self.nodes.items():
            nodes.append({
                "id": nid,
                "type": node.node_type,
                "x": int(node.pos().x()),
                "y": int(node.pos().y()),
            })
        edges = []
        for edge in self.edges:
            edges.append({"from": edge.source.node_id, "to": edge.target.node_id})
        return yaml.dump({"nodes": nodes, "edges": edges}, allow_unicode=True)


class WorkflowEditor(QWidget):
    """流程图编辑器组件"""

    def __init__(self):
        super().__init__()
        self.current_file: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        self.node_combo = QComboBox()
        for ntype, config in NODE_TYPES.items():
            self.node_combo.addItem(f"{config['label']} ({ntype})", ntype)
        btn_add = QPushButton("+ 添加节点")
        btn_add.clicked.connect(self._add_node)
        btn_save = QPushButton("保存")
        btn_save.clicked.connect(self._save)
        btn_load = QPushButton("加载")
        btn_load.clicked.connect(self._load_file_dialog)
        toolbar.addWidget(self.node_combo)
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_save)
        toolbar.addWidget(btn_load)
        layout.addLayout(toolbar)

        # 场景 + 视图
        self.scene = WorkflowScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setStyleSheet("background-color: #1a1a2e; border: none;")
        layout.addWidget(self.view)

        # 加载默认工作流
        self._load_default_workflow()

    def _load_default_workflow(self):
        """加载默认的 Agent 主循环工作流"""
        default_yaml = """
nodes:
  - id: receive_event
    type: event
    x: 50
    y: 200
  - id: build_prompt
    type: prompt
    x: 250
    y: 200
  - id: llm_reasoning
    type: llm
    x: 450
    y: 200
  - id: parse_command
    type: command
    x: 650
    y: 150
  - id: stream_output
    type: event
    x: 650
    y: 300
  - id: update_memory
    type: memory
    x: 850
    y: 150
  - id: send_command
    type: event
    x: 850
    y: 300
  - id: end
    type: end
    x: 1050
    y: 200
edges:
  - from: receive_event
    to: build_prompt
  - from: build_prompt
    to: llm_reasoning
  - from: llm_reasoning
    to: parse_command
  - from: llm_reasoning
    to: stream_output
  - from: parse_command
    to: update_memory
  - from: stream_output
    to: send_command
  - from: update_memory
    to: end
  - from: send_command
    to: end
"""
        self.scene.load_from_yaml(default_yaml)

    def _add_node(self):
        """添加新节点"""
        node_type = self.node_combo.currentData()
        node_id = f"node_{len(self.scene.nodes) + 1}"
        self.scene.add_node(node_type, node_id, 100, 100)

    def _save(self):
        """保存工作流"""
        if not self.current_file:
            self.current_file = "workflow/main_loop.yaml"
        yaml_content = self.scene.to_yaml()
        Path(self.current_file).parent.mkdir(parents=True, exist_ok=True)
        Path(self.current_file).write_text(yaml_content, encoding="utf-8")

    def _load_file_dialog(self):
        """文件对话框加载"""
        path, _ = QFileDialog.getOpenFileName(self, "加载工作流", "workflow/", "YAML (*.yaml *.yml)")
        if path:
            self.current_file = path
            content = Path(path).read_text(encoding="utf-8")
            self.scene.load_from_yaml(content)

    def load_from_file(self, path: str):
        """从文件加载"""
        self.current_file = path
        content = Path(path).read_text(encoding="utf-8")
        self.scene.load_from_yaml(content)
```

4.2 在 `EditorStack` 中集成 WorkflowEditor：

```python
# 在 EditorStack.__init__ 中:
self.workflow_editor = WorkflowEditor()
self.addWidget(self.workflow_editor)  # index 6

# 在 EditorStack.open_file 中:
elif resource_type == "workflow" or path.endswith(".yaml"):
    self.workflow_editor.load_from_file(path)
    self.setCurrentIndex(6)
```

4.3 在 `EditorStack` 中添加 `save_current` 对 workflow 的处理。

**验收**:
- [ ] 点击 workflow/*.yaml 文件 → 流程图编辑器打开
- [ ] 显示默认的 Agent 主循环流程图（8 个节点 + 连线）
- [ ] 节点可拖拽移动，连线自动跟随
- [ ] 点击节点高亮选中
- [ ] 下拉选择节点类型，点击添加，新节点出现
- [ ] 保存后 YAML 文件更新
- [ ] 重新加载 YAML，节点位置正确

---

### Step 5: 底部控制台 — 执行控制 + 流程视图 + 轮次回溯

**目的**: 实现底部 5 个 Tab 面板。

**方案**:

5.1 改造 `workbench/widgets/console_tabs.py`：

```python
# workbench/widgets/console_tabs.py
"""底部控制台 — 5 个 Tab"""
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QListWidget, QListWidgetItem,
    QComboBox, QPlainTextEdit, QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class ExecutionCtrlPanel(QWidget):
    """Tab 1: 执行控制"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 状态显示
        self.status_badge = QLabel("IDLE")
        self.status_badge.setStyleSheet(
            "background-color: #4caf50; color: white; padding: 4px 12px; "
            "border-radius: 4px; font-weight: bold; font-size: 14px;"
        )
        layout.addWidget(self.status_badge)

        # 控制按钮
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("▶ 运行")
        self.btn_pause = QPushButton("⏸ 暂停")
        self.btn_step = QPushButton("⏯ 单步")
        self.btn_reset = QPushButton("↺ 重置")
        for btn in [self.btn_run, self.btn_pause, self.btn_step, self.btn_reset]:
            btn.setMinimumHeight(32)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        # 日志输出
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log)

    def append_log(self, message: str, color: str = "#d4d4d4"):
        """追加日志"""
        self.log.appendHtml(f'<span style="color:{color}">{message}</span>')

    def set_status(self, status: str):
        """更新状态"""
        colors = {
            "IDLE": "#4caf50",
            "RUNNING": "#2196f3",
            "PAUSED": "#ff9800",
            "STEP_WAITING": "#9c27b0",
        }
        color = colors.get(status, "#666")
        self.status_badge.setText(status)
        self.status_badge.setStyleSheet(
            f"background-color: {color}; color: white; padding: 4px 12px; "
            f"border-radius: 4px; font-weight: bold; font-size: 14px;"
        )


class FlowViewPanel(QWidget):
    """Tab 2: 流程视图 — 运行时高亮当前节点"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.view = QLabel("流程视图 — 运行时高亮当前执行节点\n(与流程图编辑器共享场景)")
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.view)

    def highlight_node(self, node_id: str):
        """高亮当前执行节点"""
        self.view.setText(f"当前节点: {node_id}")


class TurnTimelinePanel(QWidget):
    """Tab 3: 轮次回溯"""

    turn_selected = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)

        # 左侧: 轮次列表
        self.turn_list = QListWidget()
        self.turn_list.setMaximumWidth(200)
        self.turn_list.currentRowChanged.connect(self.turn_selected.emit)
        layout.addWidget(self.turn_list)

        # 右侧: 轮次详情
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        layout.addWidget(self.detail)

    def add_turn(self, turn_id: int, status: str, summary: str):
        """添加轮次记录"""
        colors = {"completed": "#4caf50", "failed": "#f44336", "paused": "#ff9800", "current": "#2196f3"}
        item = QListWidgetItem(f"回合 {turn_id} [{status}]")
        item.setForeground(QColor(colors.get(status, "#d4d4d4")))
        self.turn_list.addItem(item)

    def show_turn_detail(self, turn_id: int, detail: str):
        """显示轮次详情"""
        self.detail.setPlainText(detail)


class InjectPanel(QWidget):
    """Tab 4: 指令注入"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 注入级别
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("级别:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["system", "user", "override"])
        level_layout.addWidget(self.level_combo)
        layout.addLayout(level_layout)

        # 描述
        self.level_desc = QLabel("system: 插入 system prompt 末尾\nuser: 模拟玩家输入\noverride: 覆盖下一轮 Prompt")
        self.level_desc.setStyleSheet("color: #969696; font-size: 11px;")
        layout.addWidget(self.level_desc)

        # 输入
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("输入指令内容...")
        self.input.setMaximumHeight(100)
        layout.addWidget(self.input)

        # 发送按钮
        self.btn_send = QPushButton("注入指令")
        layout.addWidget(self.btn_send)


class ForceToolPanel(QWidget):
    """Tab 5: 强制工具"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 工具选择
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(QLabel("工具:"))
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(["combat.initiate", "dialogue.start", "quest.update", "exploration.look"])
        tool_layout.addWidget(self.tool_combo)
        layout.addLayout(tool_layout)

        # 参数 (占位)
        self.params = QPlainTextEdit()
        self.params.setPlaceholderText("工具参数 (JSON)")
        self.params.setMaximumHeight(80)
        layout.addWidget(self.params)

        # 执行按钮
        self.btn_execute = QPushButton("强制执行")
        layout.addWidget(self.btn_execute)

        # 结果
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        self.result.setMaximumHeight(60)
        layout.addWidget(self.result)


class ConsoleTabs(QTabWidget):
    """底部控制台 — 5 个 Tab"""

    def __init__(self):
        super().__init__()
        self.exec_ctrl = ExecutionCtrlPanel()
        self.flow_view = FlowViewPanel()
        self.turn_timeline = TurnTimelinePanel()
        self.inject_panel = InjectPanel()
        self.force_tool = ForceToolPanel()

        self.addTab(self.exec_ctrl, "执行控制")
        self.addTab(self.flow_view, "流程视图")
        self.addTab(self.turn_timeline, "轮次回溯")
        self.addTab(self.inject_panel, "指令注入")
        self.addTab(self.force_tool, "强制工具")
```

**验收**:
- [ ] 底部 5 个 Tab 正常切换
- [ ] 执行控制: 状态徽章显示 IDLE，4 个按钮
- [ ] 轮次回溯: 左侧列表 + 右侧详情
- [ ] 指令注入: 级别选择 + 输入框 + 发送按钮
- [ ] 强制工具: 工具选择 + 参数输入 + 执行按钮

---

### Step 6: 后端桥接层 — Agent 交互

**目的**: WorkBench 直接调用后端模块，实现运行/暂停/单步/重置。

**方案**:

6.1 创建 `workbench/bridge/agent_bridge.py`：

```python
# workbench/bridge/agent_bridge.py
"""WorkBench ↔ 后端桥接层"""
import asyncio
import sys
from pathlib import Path
from typing import Callable
from PyQt6.QtCore import QObject, pyqtSignal


class AgentBridge(QObject):
    """后端桥接层 — 直接 import 后端模块"""

    # 信号
    log_signal = pyqtSignal(str, str)       # (event_type, message)
    status_changed = pyqtSignal(str)        # status string
    turn_completed = pyqtSignal(int, str)   # (turn_id, summary)

    def __init__(self, project_root: str):
        super().__init__()
        self.project_root = Path(project_root)
        self._event_handler = None
        self._memory_manager = None
        self._skill_loader = None
        self._game_master = None
        self._turn_count = 0

    def init_backend(self) -> bool:
        """初始化后端模块"""
        try:
            sys.path.insert(0, str(self.project_root))

            from src.memory.manager import MemoryManager
            from src.skills.loader import SkillLoader

            self._memory_manager = MemoryManager(str(self.project_root / "workspace"))
            self._skill_loader = SkillLoader(str(self.project_root / "skills"))

            self.log_signal.emit("info", "后端模块初始化成功")
            return True
        except ImportError as e:
            self.log_signal.emit("error", f"后端模块导入失败: {e}")
            return False
        except Exception as e:
            self.log_signal.emit("error", f"后端初始化失败: {e}")
            return False

    async def run_agent(self):
        """运行 Agent"""
        self.status_changed.emit("RUNNING")
        self.log_signal.emit("info", "Agent 开始运行...")
        try:
            from src.agent.event_handler import EventHandler

            self._event_handler = EventHandler(
                memory_manager=self._memory_manager,
                skill_loader=self._skill_loader,
            )

            # 示例: 处理一个玩家事件
            event = {
                "type": "player_action",
                "raw_text": "探索铁匠铺",
                "context_hints": ["locations/铁匠铺"],
            }

            response = await self._event_handler.handle_event(event)

            if response.get("narrative"):
                self.log_signal.emit("narrative", response["narrative"][:200])
            if response.get("commands"):
                for cmd in response["commands"]:
                    self.log_signal.emit("command", str(cmd))

            self._turn_count += 1
            self.turn_completed.emit(self._turn_count, "完成")
            self.status_changed.emit("IDLE")

        except Exception as e:
            self.log_signal.emit("error", f"Agent 运行失败: {e}")
            self.status_changed.emit("IDLE")

    def pause(self):
        """暂停 Agent"""
        self.status_changed.emit("PAUSED")
        self.log_signal.emit("info", "Agent 已暂停")

    def step(self):
        """单步执行"""
        self.status_changed.emit("STEP_WAITING")
        self.log_signal.emit("info", "单步执行...")

    def reset(self):
        """重置 Agent"""
        self._turn_count = 0
        self.status_changed.emit("IDLE")
        self.log_signal.emit("info", "Agent 已重置")
```

6.2 在 `MainWindow` 中集成桥接层：

```python
# 在 MainWindow.__init__ 中:
from workbench.bridge.agent_bridge import AgentBridge
self.bridge = AgentBridge(project_root="..")
self.bridge.init_backend()

# 连接信号
self.bridge.log_signal.connect(self._on_bridge_log)
self.bridge.status_changed.connect(self._on_status_changed)

# 工具栏按钮
self.act_run.triggered.connect(lambda: asyncio.create_task(self.bridge.run_agent()))
self.act_pause.triggered.connect(self.bridge.pause)
self.act_step.triggered.connect(self.bridge.step)
self.act_reset.triggered.connect(self.bridge.reset)

def _on_bridge_log(self, event_type: str, message: str):
    colors = {"narrative": "#569cd6", "command": "#dcdcaa", "memory": "#6a9955", "error": "#f44747", "info": "#d4d4d4"}
    self.console_tabs.exec_ctrl.append_log(f"[{event_type}] {message}", colors.get(event_type, "#d4d4d4"))

def _on_status_changed(self, status: str):
    self.console_tabs.exec_ctrl.set_status(status)
    self.agent_status.status_label.setText(f"状态: {status}")
    self.statusbar.showMessage(f"Agent {status}")
```

**验收**:
- [ ] 启动时后端模块初始化成功
- [ ] 点击 ▶ 运行，Agent 处理事件，日志显示 narrative/command
- [ ] 状态徽章从 IDLE → RUNNING → IDLE
- [ ] 点击 ⏸ 暂停，状态变为 PAUSED
- [ ] 点击 ↺ 重置，回合数归零
- [ ] 错误情况红色日志

---

### Step 7: PyInstaller 打包

**目的**: 打包成单个 exe，双击弹出桌面窗口。

**方案**:

7.1 创建 `wb_entry.py`（打包入口）：

```python
# wb_entry.py
"""PyInstaller 打包入口"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workbench.app import main

if __name__ == "__main__":
    main()
```

7.2 创建 `wb.spec`（PyInstaller 配置）：

```python
# wb.spec
# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
PROJECT_ROOT = os.path.abspath('.')

datas = [
    (os.path.join(PROJECT_ROOT, 'workspace'), 'workspace'),
    (os.path.join(PROJECT_ROOT, 'skills'), 'skills'),
    (os.path.join(PROJECT_ROOT, 'prompts'), 'prompts'),
    (os.path.join(PROJECT_ROOT, 'workflow'), 'workflow'),
    (os.path.join(PROJECT_ROOT, 'workbench', 'styles', 'dark_theme.qss'), 'workbench/styles'),
]

hiddenimports = [
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui',
    'frontmatter', 'openai', 'aiosqlite', 'httpx',
    'yaml',
]

a = Analysis(
    ['wb_entry.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'tkinter', 'IPython'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='GameMasterAgent',
    debug=False,
    console=False,  # GUI 程序，不显示控制台
    icon=None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True,
    name='GameMasterAgent',
)
```

7.3 执行打包：

```bash
uv pip install pyinstaller
pyinstaller wb.spec --clean
```

7.4 测试：

```bash
dist\GameMasterAgent\GameMasterAgent.exe
```

**验收**:
- [ ] `dist/GameMasterAgent/GameMasterAgent.exe` 存在
- [ ] 双击 exe 弹出桌面窗口（不是终端）
- [ ] 三栏布局正常显示
- [ ] 暗色主题生效
- [ ] 资源树显示文件
- [ ] 能打开和编辑文件
- [ ] 流程图编辑器正常

---

## 注意事项

### PyQt 踩坑
1. **PyQt6 vs PySide6**: 用 PyQt6，生态更成熟
2. **QSS 样式**: 类 CSS 但不是 CSS，部分属性不支持（如 flexbox）
3. **QGraphicsScene 性能**: 节点 < 100 个没问题，多了需要优化
4. **asyncio + Qt**: Qt 有自己的事件循环，需要用 `qasync` 或在单独线程跑 asyncio
5. **打包体积**: PyQt6 比较大，预计 80-120MB

### 后端对接
1. **直接 import**: 不需要 FastAPI 运行
2. **async 问题**: PyQt 的事件循环和 asyncio 不兼容，建议用 `qasync` 库
   ```bash
   uv pip install qasync
   ```
3. **路径**: 打包后用 `sys._MEIPASS` 处理资源路径

### 文件操作
1. **原子写入**: 保存 .md 文件时使用 `atomic_write()`
2. **YAML Front Matter**: 用 `python-frontmatter` 解析
3. **编码**: 所有文件 UTF-8

---

## 完成检查清单

- [ ] Step 1: PyQt6 安装 + 三栏布局骨架 + 暗色主题
- [ ] Step 2: 七层资源树动态扫描 + 右键菜单
- [ ] Step 3: 多态编辑器 (MD/YAML/键值对) + Ctrl+S 保存
- [ ] Step 4: 流程图编辑器 (QGraphicsScene 节点拖拽连线)
- [ ] Step 5: 底部控制台 (5 Tab: 执行控制/流程视图/轮次回溯/指令注入/强制工具)
- [ ] Step 6: 后端桥接层 (运行/暂停/单步/重置)
- [ ] Step 7: PyInstaller 打包成 exe
