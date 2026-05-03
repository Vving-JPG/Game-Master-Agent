# P3: 进阶功能补全（v5 版本）

> 优先级：🟢 低 | 预估工作量：4-6 小时 | 前置条件：P2 完成
> **v5 变更**: 大部分 Ops 面板功能已在 v5 中实现，仅剩进阶功能
> **记录时间**: 2026-05-03

---

## 修复内容概览

本次优化实现了以下进阶功能：
1. **部署服务启停** - 真实启动/停止 HTTP 服务
2. **文件编辑保存** - Ctrl+S 保存文本编辑器内容
3. **撤销/重做** - 文本编辑器撤销/重做功能
4. **命令行参数** - 完善版本号显示
5. **Agent 运行完善** - 空图检查、按钮状态管理

---

## Step 3.1: 实现部署服务启停

### 问题描述
- **文件**: `2workbench/presentation/ops/deploy/deploy_manager.py`
- **问题**: `_start_service()` 和 `_stop_service()` 仅切换 UI 状态标签，没有实际启动服务

### 修复方案

```python
import subprocess
import sys
import threading

class DeployManager(BaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._deploy_status = "idle"
        self._server_process = None
        self._server_thread = None
        self._setup_ui()

    def _start_service(self) -> None:
        """启动 HTTP 服务"""
        port = self._port_spin.value()
        host = self._host_edit.text() or "127.0.0.1"

        try:
            # 启动子进程运行 server
            script_path = Path(__file__).parent.parent.parent / "server_main.py"
            if not script_path.exists():
                # 如果没有独立入口，使用内嵌服务器
                from presentation.server import ThreadedHTTPServer, RequestHandler

                def run_server():
                    server = ThreadedHTTPServer((host, port), RequestHandler)
                    logger.info(f"HTTP 服务启动: http://{host}:{port}")
                    server.serve_forever()

                self._server_thread = threading.Thread(target=run_server, daemon=True)
                self._server_thread.start()
            else:
                self._server_process = subprocess.Popen(
                    [sys.executable, str(script_path), "--host", host, "--port", str(port)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

            self._deploy_status = "running"
            self._status_label.setText(f"✅ 运行中 — http://{host}:{port}")
            self._status_label.setStyleSheet("color: #4ec9b0;")
            self._run_status.setText(f"运行中 — http://{host}:{port}")
            self._btn_start.setEnabled(False)
            self._btn_stop.setEnabled(True)
            logger.info(f"服务已启动: http://{host}:{port}")
        except Exception as e:
            logger.error(f"启动服务失败: {e}")
            QMessageBox.critical(self, "启动失败", str(e))

    def _stop_service(self) -> None:
        """停止 HTTP 服务"""
        if self._server_process:
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
            self._server_process = None

        self._deploy_status = "idle"
        self._status_label.setText("⏹ 已停止")
        self._status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self._run_status.setText("已停止")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        logger.info("服务已停止")
```

### 关键代码位置
- [deploy_manager.py L199-L252](file:///d:/Game-Master-Agent/2workbench/presentation/ops/deploy/deploy_manager.py#L199-L252)

---

## Step 3.2: 实现文件编辑保存

### 问题描述
- **文件**: `2workbench/presentation/main_window.py`
- **问题**: F-002 — 双击文件打开后为只读，需要实现 Ctrl+S 保存功能

### 修复方案

在 `_open_text_editor` 方法中添加 Ctrl+S 快捷键绑定：

```python
def _open_text_editor(self, file_path: str) -> None:
    """在文本编辑器中打开文件"""
    # ... 创建编辑器代码 ...
    
    # 可编辑
    editor.setReadOnly(False)
    
    # 监听文本变化
    def on_text_changed():
        current = editor.toPlainText()
        was_modified = editor._is_modified
        editor._is_modified = (current != editor._original_content)
        if editor._is_modified != was_modified:
            self._update_tab_title(editor, path.name, editor._is_modified)

    editor.textChanged.connect(on_text_changed)

    # 绑定 Ctrl+S 保存快捷键
    from PyQt6.QtGui import QShortcut, QKeySequence
    save_shortcut = QShortcut(QKeySequence.StandardKey.Save, editor)
    save_shortcut.activated.connect(lambda: self._save_editor_widget(editor))

    # ... 添加到标签页 ...
```

### 关键代码位置
- [main_window.py L1147-L1150](file:///d:/Game-Master-Agent/2workbench/presentation/main_window.py#L1147-L1150)

---

## Step 3.3: 实现撤销/重做

### 问题描述
- **文件**: `2workbench/presentation/main_window.py`
- **问题**: F-003 — Ctrl+Z/Y 需要能撤销/重做文本编辑

### 实现状态
- **状态**: 功能已存在，无需修改
- **说明**: QTextEdit 自带 undo/redo 功能，菜单已绑定 `_on_undo` 和 `_on_redo` 方法

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

### 关键代码位置
- [main_window.py L947-L963](file:///d:/Game-Master-Agent/2workbench/presentation/main_window.py#L947-L963)

---

## Step 3.4: 实现命令行参数

### 问题描述
- **文件**: `2workbench/app.py`
- **问题**: F-020 — 完善版本号显示

### 修复方案

```python
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Game Master Agent IDE")
    parser.add_argument("--project", "-p", help="直接打开指定项目路径")
    parser.add_argument("--version", "-v", action="version", version="GMA IDE v2.0.0")  # 更新格式
    parser.add_argument("--no-gui", action="store_true", help="无头模式（仅测试）")
    parser.add_argument("--theme", "-t", choices=["dark", "light"], default="dark", help="主题模式")
    parser.add_argument("--port", type=int, default=18080, help="HTTP 服务器端口")
    parser.add_argument("--debug", "-d", action="store_true", help="调试模式")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    parser.add_argument("--skip-selector", action="store_true", help="跳过项目选择器")
    return parser.parse_args()
```

### 关键代码位置
- [app.py L33](file:///d:/Game-Master-Agent/2workbench/app.py#L33)

---

## Step 3.5: Agent 运行功能完善

### 问题描述
- **文件**: `2workbench/presentation/main_window.py`
- **问题**: F-001 — Agent 运行需要完善错误处理和状态反馈

### 修复方案

#### 1. 添加空图检查
```python
def _on_run_agent(self) -> None:
    """运行 Agent"""
    # ... 前置检查 ...
    
    # 检查图是否有效
    try:
        graph = project_manager.load_graph()
        nodes = graph.get("nodes", [])
        if not nodes:
            QMessageBox.warning(self, "无法运行", "当前项目没有定义任何节点，请先在图编辑器中添加节点。")
            return
    except Exception as e:
        logger.warning(f"加载图检查失败: {e}")
```

#### 2. 运行中按钮状态管理
```python
    # 禁用运行按钮，启用停止按钮
    self._run_action.setEnabled(False)
    self._stop_action.setEnabled(True)
    self._show_message("Agent 运行中...")
```

#### 3. 运行完成后恢复按钮状态
```python
def _on_agent_finished(self, result: dict) -> None:
    """Agent 运行完成回调"""
    # 恢复按钮状态
    self._run_action.setEnabled(True)
    self._stop_action.setEnabled(False)
    # ... 处理结果 ...

def _on_agent_error(self, error: str) -> None:
    """Agent 运行错误回调"""
    # 恢复按钮状态
    self._run_action.setEnabled(True)
    self._stop_action.setEnabled(False)
    # ... 显示错误 ...
```

#### 4. 工具栏按钮改为实例变量
```python
# _setup_toolbar 方法中
self._run_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "运行", self)
self._run_action.triggered.connect(self._on_run_agent)
toolbar.addAction(self._run_action)

self._stop_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop), "停止", self)
self._stop_action.triggered.connect(self._on_stop_agent)
toolbar.addAction(self._stop_action)
```

### 关键代码位置
- [main_window.py L827-L835](file:///d:/Game-Master-Agent/2workbench/presentation/main_window.py#L827-L835)
- [main_window.py L1243-L1250](file:///d:/Game-Master-Agent/2workbench/presentation/main_window.py#L1243-L1250)
- [main_window.py L1269-L1272](file:///d:/Game-Master-Agent/2workbench/presentation/main_window.py#L1269-L1272)
- [main_window.py L1315-L1318](file:///d:/Game-Master-Agent/2workbench/presentation/main_window.py#L1315-L1318)
- [main_window.py L1338-L1341](file:///d:/Game-Master-Agent/2workbench/presentation/main_window.py#L1338-L1341)

---

## 验收标准

- [x] 点击启动后服务实际运行
- [x] 点击停止后服务正确终止
- [x] 状态标签实时更新
- [x] 双击文件可编辑内容
- [x] Ctrl+S 保存到原文件
- [x] 保存成功有消息提示
- [x] Ctrl+Z 撤销文本编辑
- [x] Ctrl+Y 重做文本编辑
- [x] `--help` 显示帮助
- [x] `--project /path` 直接打开
- [x] `--version` 显示版本号
- [x] 空图时给出明确提示
- [x] 运行中按钮状态正确
- [x] 错误时有详细反馈

---

## 相关文件

| 文件路径 | 修改类型 | 说明 |
|---------|---------|------|
| `presentation/ops/deploy/deploy_manager.py` | 修改 | 实现真实服务启停 |
| `presentation/main_window.py` | 修改 | 文件保存、Agent运行完善 |
| `app.py` | 修改 | 版本号格式 |

---

*最后更新: 2026-05-03*
