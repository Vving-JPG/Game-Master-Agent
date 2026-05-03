# P3: Ops 面板功能补全

> 优化阶段: P3 | 优先级: 🟡 中 | 状态: ✅ 已完成 | 预估工作量: 10-15 小时
> 相关文档: [优化大纲](../优化大纲.md) | [优化步骤P3](../优化步骤P3.md)

---

## 问题概述

Ops 面板多个功能为占位符或未实现，需要补全功能。

---

## Step 3.1: 实现物品编辑器

### 问题描述
UX-016 / F-010 — 物品编辑器为 QLabel 占位符。

### 实现方案
创建 `ItemEditor` 类：

```python
class ItemEditor(QWidget):
    """物品编辑器"""
    data_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict] = []
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        # 左侧列表 (QTableWidget)
        # 右侧编辑面板 (名称、类型、描述、效果)
        # 按钮 (添加、保存、删除)
```

### 功能特性
- 表格展示：ID、名称、类型、描述
- 编辑字段：名称、类型下拉框、描述、效果
- 操作按钮：添加、保存修改、删除
- 删除确认对话框

### 代码位置
[ItemEditor @ knowledge_editor.py L387](../../2workbench/presentation/ops/knowledge/knowledge_editor.py#L387)

### 验证结果
✅ ItemEditor 类已实现

---

## Step 3.2: 实现任务编辑器

### 问题描述
UX-016 — 任务编辑器为 QLabel 占位符。

### 实现方案
创建 `QuestEditor` 类：

```python
class QuestEditor(QWidget):
    """任务编辑器"""
    data_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._quests: list[dict] = []
        self._setup_ui()
```

### 功能特性
- 表格展示：ID、名称、状态、奖励、描述
- 编辑字段：名称、状态下拉框(未开始/进行中/已完成/已失败)、奖励、前置条件、描述
- 操作按钮：添加、保存、删除
- 删除确认对话框

### 代码位置
[QuestEditor @ knowledge_editor.py L535](../../2workbench/presentation/ops/knowledge/knowledge_editor.py#L535)

### 验证结果
✅ QuestEditor 类已实现

---

## Step 3.3: 日志查看器添加搜索功能

### 问题描述
F-012 — 日志查看器缺少搜索功能。

### 实现方案
在工具栏添加搜索栏：

```python
# 搜索框
self._search_edit = QLineEdit()
self._search_edit.setPlaceholderText("🔍 搜索日志...")
self._search_edit.returnPressed.connect(self._search_in_log)
toolbar.addWidget(self._search_edit)

self._btn_search = StyledButton("查找", style_type="ghost")
self._btn_search.clicked.connect(self._search_in_log)
```

### 搜索逻辑
```python
def _search_in_log(self) -> None:
    keyword = self._search_edit.text().strip()
    if not keyword:
        return
    cursor = self._output.textCursor()
    document = self._output.document()
    found = document.find(keyword, cursor)
    if not found.isNull():
        self._output.setTextCursor(found)
    else:
        # 循环搜索：从头开始
        cursor.movePosition(cursor.MoveOperation.Start)
        found = document.find(keyword, cursor)
```

### 代码位置
[log_viewer.py L53-60, L96](../../2workbench/presentation/ops/logger_panel/log_viewer.py)

### 验证结果
✅ 搜索框和查找功能已实现

---

## Step 3.4: 日志文件变化监控

### 问题描述
F-013 — 日志文件变化时不能自动更新。

### 实现方案
使用 `QFileSystemWatcher`：

```python
from PyQt6.QtCore import QFileSystemWatcher

# 初始化
self._watcher = QFileSystemWatcher()
self._watcher.fileChanged.connect(self._on_file_changed)

# 加载日志时添加监控
def _load_log(self) -> None:
    if str(self._log_path) not in self._watcher.files():
        self._watcher.addPath(str(self._log_path))

# 文件变化回调
def _on_file_changed(self, path: str) -> None:
    if self._auto_scroll and self._log_path and str(self._log_path) == path:
        content = self._log_path.read_text(encoding="utf-8")
        self._output.setPlainText(content)
        scrollbar = self._output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # 重新添加监控（某些编辑器会创建新文件）
        if str(self._log_path) not in self._watcher.files():
            self._watcher.addPath(str(self._log_path))
```

### 代码位置
[log_viewer.py L14, L37, L85-102](../../2workbench/presentation/ops/logger_panel/log_viewer.py)

### 验证结果
✅ QFileSystemWatcher 已实现

---

## Step 3.5: 编排器添加删除功能

### 问题描述
F-015 — 编排器缺少删除 Agent 和连接的功能。

### 实现方案
添加删除按钮和方法：

```python
# 删除 Agent 按钮
self._btn_delete_agent = StyledButton("🗑️ 删除 Agent", style_type="danger")
self._btn_delete_agent.clicked.connect(self._delete_agent)

# 删除连接按钮
self._btn_delete_link = StyledButton("🗑️ 删除连接", style_type="danger")
self._btn_delete_link.clicked.connect(self._delete_link)

def _delete_agent(self) -> None:
    current = self._agent_list.currentRow()
    if current < 0:
        return
    agent = self._agents.pop(current)
    # 删除相关连接
    self._links = [l for l in self._links if l.agent_id != agent.id and l.next_agent_id != agent.id]
    self._refresh_agent_list()
    self._refresh_chain_list()

def _delete_link(self) -> None:
    current = self._chain_list.currentRow()
    if current < 0:
        return
    self._links.pop(current)
    self._refresh_chain_list()
```

### 代码位置
[orchestrator.py L74-80, L211-240](../../2workbench/presentation/ops/multi_agent/orchestrator.py)

### 验证结果
✅ 删除 Agent 和连接功能已实现

---

## Step 3.6: 编排器链有效性验证

### 问题描述
F-016 — 编排器缺少链结构验证。

### 实现方案
添加验证按钮和方法：

```python
# 验证按钮
self._btn_validate = StyledButton("✓ 验证链", style_type="secondary")
self._btn_validate.clicked.connect(self._on_validate)

def _validate_chain(self) -> list[str]:
    """验证链的完整性，返回错误列表"""
    errors = []
    agent_ids = {a.id for a in self._agents}
    
    # 检查孤立 Agent
    connected_ids = set()
    for link in self._links:
        connected_ids.add(link.agent_id)
        connected_ids.add(link.next_agent_id)
    for agent in self._agents:
        if agent.id not in connected_ids and len(self._agents) > 1:
            errors.append(f"Agent '{agent.name}' 没有任何连接")
    
    # 检查悬空连接
    for link in self._links:
        if link.agent_id not in agent_ids:
            errors.append(f"连接引用了不存在的 Agent: {link.agent_id}")
        if link.next_agent_id not in agent_ids:
            errors.append(f"连接引用了不存在的 Agent: {link.next_agent_id}")
    
    # 检查循环依赖（DFS）
    graph = {a.id: [] for a in self._agents}
    for link in self._links:
        if link.agent_id in graph:
            graph[link.agent_id].append(link.next_agent_id)
    
    visited = set()
    def dfs(node, path):
        if node in path:
            cycle = path[path.index(node):] + [node]
            errors.append(f"检测到循环: {' → '.join(cycle)}")
            return
        if node in visited:
            return
        path.append(node)
        for next_id in graph.get(node, []):
            dfs(next_id, path)
        path.pop()
        visited.add(node)
    
    for agent_id in graph:
        dfs(agent_id, [])
    
    return errors
```

### 代码位置
[orchestrator.py L82, L241-298](../../2workbench/presentation/ops/multi_agent/orchestrator.py)

### 验证结果
✅ 链验证功能已实现（孤立检测、悬空连接、循环依赖）

---

## Step 3.7: 安全面板正则实时验证

### 问题描述
F-017 — 安全面板缺少正则实时验证。

### 实现方案
添加状态标签和实时验证：

```python
# 状态标签
self._pattern_status = QLabel("✓")
self._pattern_status.setStyleSheet("color: #4caf50; font-weight: bold;")
pattern_layout.addWidget(self._pattern_status)

# 实时验证连接
self._pattern_edit.textChanged.connect(self._validate_pattern_live)

def _validate_pattern_live(self, text: str) -> None:
    if not text:
        self._pattern_status.setText("○")
        self._pattern_status.setStyleSheet(f"color: {text_secondary};")
        return
    try:
        re.compile(text)
        self._pattern_status.setText("✓")
        self._pattern_status.setStyleSheet(f"color: {success_color}; font-weight: bold;")
    except re.error as e:
        self._pattern_status.setText("✗")
        self._pattern_status.setStyleSheet(f"color: {error_color}; font-weight: bold;")
```

### 代码位置
[safety_panel.py L137-143, L254-272](../../2workbench/presentation/ops/safety/safety_panel.py)

### 验证结果
✅ 正则实时验证已实现

---

## Step 3.8: 调试器添加输入历史

### 问题描述
F-007 — 调试器缺少输入历史功能。

### 实现方案
添加历史记录和键盘事件处理：

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self._input_history: list[str] = []
    self._history_index = 0

def _on_send_input(self) -> None:
    text = self._input_edit.text().strip()
    if text:
        self._input_history.append(text)
        self._history_index = len(self._input_history)
    # ...

def keyPressEvent(self, event):
    """拦截上下键浏览历史"""
    if event.key() == Qt.Key.Key_Up and self._input_history:
        self._history_index = max(0, self._history_index - 1)
        self._input_edit.setText(self._input_history[self._history_index])
    elif event.key() == Qt.Key.Key_Down and self._input_history:
        self._history_index = min(len(self._input_history), self._history_index + 1)
        if self._history_index < len(self._input_history):
            self._input_edit.setText(self._input_history[self._history_index])
        else:
            self._input_edit.clear()
    else:
        super().keyPressEvent(event)
```

### 代码位置
[runtime_panel.py L309, L434-452](../../2workbench/presentation/ops/debugger/runtime_panel.py)

### 验证结果
✅ 输入历史功能已实现

---

## Step 3.9: 评估工作台添加报告导出

### 问题描述
F-009 — 评估工作台缺少报告导出功能。

### 实现方案
添加导出按钮和方法：

```python
self._btn_export = StyledButton("📤 导出报告", style_type="secondary")
self._btn_export.clicked.connect(self._export_report)

def _export_report(self) -> None:
    path, _ = QFileDialog.getSaveFileName(self, "导出报告", "eval_report.json", "JSON (*.json)")
    if not path:
        return
    
    import json
    from datetime import datetime
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_cases": len(cases),
        "results": [...],
        "cases": [...]
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    QMessageBox.information(self, "导出成功", f"报告已保存到:\n{path}")
```

### 代码位置
[eval_workbench.py L177-179, L383-420](../../2workbench/presentation/ops/evaluator/eval_workbench.py)

### 验证结果
✅ 报告导出功能已实现

---

## Step 3.10: 部署管理器实现基础打包

### 问题描述
F-014 — 部署管理器缺少实际打包功能。

### 实现方案
实现 ZIP 打包：

```python
def _package_project(self) -> None:
    import zipfile
    from presentation.project.manager import project_manager
    
    if not project_manager.is_open:
        QMessageBox.warning(self, "提示", "请先打开一个项目")
        return
    
    path = project_manager.project_path
    name = project_manager.current_project.name
    
    save_path, _ = QFileDialog.getSaveFileName(
        self, "保存打包文件", f"{name}.zip", "ZIP (*.zip)")
    if not save_path:
        return
    
    try:
        with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in path.rglob("*"):
                if file.is_file() and not file.name.endswith('.pyc'):
                    zf.write(file, file.relative_to(path.parent))
        QMessageBox.information(self, "打包成功", f"项目已打包到:\n{save_path}")
    except Exception as e:
        QMessageBox.critical(self, "打包失败", str(e))
```

### 代码位置
[deploy_manager.py L177-220](../../2workbench/presentation/ops/deploy/deploy_manager.py)

### 验证结果
✅ ZIP 打包功能已实现

---

## 相关文件

| 文件 | 修改内容 |
|------|---------|
| [knowledge_editor.py](../../2workbench/presentation/ops/knowledge/knowledge_editor.py) | ItemEditor, QuestEditor |
| [log_viewer.py](../../2workbench/presentation/ops/logger_panel/log_viewer.py) | 搜索、文件监控 |
| [orchestrator.py](../../2workbench/presentation/ops/multi_agent/orchestrator.py) | 删除、链验证 |
| [safety_panel.py](../../2workbench/presentation/ops/safety/safety_panel.py) | 正则验证 |
| [runtime_panel.py](../../2workbench/presentation/ops/debugger/runtime_panel.py) | 输入历史 |
| [eval_workbench.py](../../2workbench/presentation/ops/evaluator/eval_workbench.py) | 报告导出 |
| [deploy_manager.py](../../2workbench/presentation/ops/deploy/deploy_manager.py) | ZIP 打包 |

---

## 验收标准

- [x] 可以添加、编辑、删除物品
- [x] 删除前有确认对话框
- [x] 数据正确保存和加载
- [x] 可以添加、编辑、删除任务
- [x] 状态切换正确
- [x] 输入关键词后跳转到匹配位置
- [x] 多次搜索循环匹配
- [x] 日志文件变化时自动更新
- [x] 自动滚动模式下跟随最新内容
- [x] 可以删除 Agent 和连接
- [x] 删除 Agent 时自动清理相关连接
- [x] 检测孤立 Agent
- [x] 检测悬空连接
- [x] 检测循环依赖
- [x] 输入合法正则时显示绿色提示
- [x] 输入非法正则时显示红色错误
- [x] 上键回溯历史输入
- [x] 下键前进历史输入
- [x] 可以导出 JSON 格式报告
- [x] 报告包含所有用例和结果
- [x] 能将项目打包为 ZIP
- [x] 排除 .pyc 等无关文件

---

*创建时间: 2026-05-03*
*更新记录: 初始创建*
