# P4-01: MainWindow 主窗口

> 模块: `presentation.main_window`
> 文件: `2workbench/presentation/main_window.py`

---

## 布局结构

```
┌─────────────────────────────────────────────────────┐
│ 菜单栏 (File/Edit/View/Agent/Tools/Help)            │
├─────────────────────────────────────────────────────┤
│ 工具栏 (新建/打开/保存/运行/调试/主题切换)           │
├──────────┬──────────────────────────┬───────────────┤
│ 左侧面板  │     中央编辑区           │  右侧面板     │
│ (资源树)  │  (图编辑器/代码/控制台)  │ (属性/状态)   │
│          │                          │               │
│ 240px    │     flex                 │   300px       │
├──────────┴──────────────────────────┴───────────────┤
│ 状态栏 (连接状态/Agent状态/模型/主题)                │
└─────────────────────────────────────────────────────┘
```

---

## 核心类

```python
class MainWindow(QMainWindow):
    """主窗口"""
    
    # 信号
    open_project_requested = pyqtSignal(str, str)
    create_project_requested = pyqtSignal(str, str, str, str)
    
    def __init__(self)
    def _setup_ui(self)           # 设置三栏布局
    def _setup_menu(self)         # 设置菜单栏
    def _setup_toolbar(self)      # 设置工具栏
    def _setup_statusbar(self)    # 设置状态栏
    def _setup_eventbus(self)     # 设置 EventBus 订阅
```

---

## 面板类

### LeftPanel 左侧面板

```python
class LeftPanel(BaseWidget):
    """左侧面板 — 资源树 + Agent 项目浏览器"""
    
    file_open_requested = pyqtSignal(str)  # 文件路径
    
    def load_project_tree(self, project_path: str)
    def _add_tree_items(self, parent_item, path: Path) -> int
```

### CenterPanel 中央编辑区

```python
class CenterPanel(BaseWidget):
    """中央编辑区 — 多标签页编辑器"""
    
    def show_graph_editor(self, graph_data: dict | None = None)
    def show_prompt_editor(self, prompts: dict[str, str] | None = None)
    def show_tool_manager(self, right_panel=None)
    def add_tab(self, widget: QWidget, title: str) -> int
```

### RightPanel 右侧面板

```python
class RightPanel(BaseWidget):
    """右侧面板 — 属性编辑器 + 状态监控"""
    
    def show_node_properties(self, node_data: dict)
    def show_tool_properties(self, tool_data: dict)
    def update_agent_status(self, status: str, turn: int = 0, event: str = "")
    def update_feature_status(self, features: list)
```

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+N | 新建项目 |
| Ctrl+O | 打开项目 |
| Ctrl+S | 保存 |
| Ctrl+W | 关闭标签页 |
| Ctrl+Tab | 下一个标签页 |
| Ctrl+Shift+Tab | 上一个标签页 |
| Ctrl+B | 切换侧边栏 |
| Ctrl+, | 打开设置 |
| Ctrl+Shift+P | 命令面板 |
| F5 | 运行 Agent |
| Shift+F5 | 停止 Agent |
| F11 | 全屏切换 |
