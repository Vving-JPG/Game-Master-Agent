# P3: 交互与快捷键完善

> 优先级: 🟡 中 | 状态: ✅ 已完成
> 实现核心快捷键功能

---

## Step 3.1: KEY-001 Ctrl+Z/Y 撤销重做

**文件**: `2workbench/presentation/main_window.py`

**添加 Edit 菜单**:
```python
# Edit 菜单
edit_menu = menubar.addMenu("编辑(&E)")

# 撤销/重做
undo_action = QAction("撤销(&U)", self)
undo_action.setShortcut("Ctrl+Z")
undo_action.triggered.connect(self._on_undo)
edit_menu.addAction(undo_action)

redo_action = QAction("重做(&R)", self)
redo_action.setShortcut("Ctrl+Y")
redo_action.triggered.connect(self._on_redo)
edit_menu.addAction(redo_action)
```

**实现方法**:
```python
def _on_undo(self) -> None:
    """撤销操作"""
    current = self.center_panel.tab_widget.currentWidget()
    if hasattr(current, 'undo'):
        current.undo()
    elif hasattr(current, 'textCursor'):
        current.undo()

def _on_redo(self) -> None:
    """重做操作"""
    current = self.center_panel.tab_widget.currentWidget()
    if hasattr(current, 'redo'):
        current.redo()
    elif hasattr(current, 'textCursor'):
        current.redo()
```

---

## Step 3.2: KEY-002 Ctrl+S 保存功能

**状态**: ✅ 已实现

**实现位置**: `_on_save()` 方法

**功能**:
- 保存当前文本编辑器内容
- 保存图编辑器
- 保存 Prompt 编辑器
- 保存项目元数据

---

## Step 3.3: KEY-003 F5/Shift+F5 运行/停止

**状态**: ✅ 已实现

**Agent 菜单**:
```python
agent_menu = menubar.addMenu("Agent(&A)")

run_action = QAction("运行 Agent(&R)", self)
run_action.setShortcut("F5")
run_action.triggered.connect(self._on_run_agent)
agent_menu.addAction(run_action)

stop_action = QAction("停止(&X)", self)
stop_action.setShortcut("Shift+F5")
stop_action.triggered.connect(self._on_stop_agent)
agent_menu.addAction(stop_action)
```

---

## Step 3.4: KEY-004 Ctrl+N/O 功能整理

**状态**: ✅ 已实现

**File 菜单**:
```python
new_action = QAction("新建 Agent 项目(&N)", self)
new_action.setShortcut("Ctrl+N")
new_action.triggered.connect(self._on_new_project)

open_action = QAction("打开项目(&O)", self)
open_action.setShortcut("Ctrl+O")
open_action.triggered.connect(self._on_open_project)
```

---

## Step 3.5: KEY-005 其他快捷键

**添加的快捷键**:

| 快捷键 | 功能 | 方法 |
|--------|------|------|
| Ctrl+X | 剪切 | `_on_cut()` |
| Ctrl+C | 复制 | `_on_copy()` |
| Ctrl+V | 粘贴 | `_on_paste()` |
| Ctrl+A | 全选 | `_on_select_all()` |
| Ctrl+F | 查找 | `_on_find()` |

**实现**:
```python
def _on_cut(self) -> None:
    current = self.center_panel.tab_widget.currentWidget()
    if hasattr(current, 'cut'):
        current.cut()

def _on_copy(self) -> None:
    current = self.center_panel.tab_widget.currentWidget()
    if hasattr(current, 'copy'):
        current.copy()

def _on_paste(self) -> None:
    current = self.center_panel.tab_widget.currentWidget()
    if hasattr(current, 'paste'):
        current.paste()

def _on_select_all(self) -> None:
    current = self.center_panel.tab_widget.currentWidget()
    if hasattr(current, 'selectAll'):
        current.selectAll()

def _on_find(self) -> None:
    current = self.center_panel.tab_widget.currentWidget()
    if hasattr(current, '_search'):
        current._search.setFocus()
        current._search.selectAll()
```

---

## Step 3.6: F-001 Agent 运行/停止功能

**实现**: `_on_run_agent()` 和 `_on_stop_agent()`

**功能**:
- 显示输入对话框获取玩家指令
- 在后台线程中运行 Agent
- 显示运行结果
- 支持停止运行中的 Agent

---

## Step 3.7: F-003 撤销/重做功能

**状态**: ✅ 已实现（见 Step 3.1）

---

## Step 3.8: F-004 标签页快捷键

**View 菜单**:
```python
next_tab_action = QAction("下一个标签页", self)
next_tab_action.setShortcut("Ctrl+Tab")
next_tab_action.triggered.connect(lambda: self._switch_tab(1))

prev_tab_action = QAction("上一个标签页", self)
prev_tab_action.setShortcut("Ctrl+Shift+Tab")
prev_tab_action.triggered.connect(lambda: self._switch_tab(-1))

close_tab_action = QAction("关闭标签页", self)
close_tab_action.setShortcut("Ctrl+W")
close_tab_action.triggered.connect(self._on_close_current_tab)
```

---

## 完整快捷键列表

```
Ctrl+N      新建项目
Ctrl+O      打开项目
Ctrl+S      保存项目
Ctrl+W      关闭标签页
Ctrl+Tab    下一个标签页
Ctrl+Shift+Tab  上一个标签页
Ctrl+B      切换侧边栏
Ctrl+,      打开设置
Ctrl+Shift+P    命令面板
Ctrl+Z      撤销
Ctrl+Y      重做
Ctrl+X      剪切
Ctrl+C      复制
Ctrl+V      粘贴
Ctrl+A      全选
Ctrl+F      查找
F5          运行 Agent
Shift+F5    停止 Agent
F11         全屏切换
Ctrl+Q      退出
Ctrl+Shift+/    显示快捷键列表
```

---

## 相关文件

- `presentation/main_window.py`
