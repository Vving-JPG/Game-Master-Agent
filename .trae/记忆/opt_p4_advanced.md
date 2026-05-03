# P4: 进阶功能补全

> 优化阶段: P4 | 优先级: 🟢 低 | 状态: ✅ 已完成 | 预估工作量: 4-6 小时
> 相关文档: [优化大纲](../优化大纲.md) | [优化步骤P4](../优化步骤P4.md)

---

## 问题概述

实现进阶功能：文件编辑保存、撤销重做、HTTP认证、跨平台截图、命令行参数。

---

## Step 4.1: 实现文件编辑和保存

### 问题描述
F-002 — 文件编辑器缺少保存功能。

### 实现方案
在 `main_window.py` 中实现保存逻辑：

```python
def _on_save(self) -> None:
    """保存当前文件"""
    current = self.center_panel.tab_widget.currentWidget()
    if current and hasattr(current, '_file_path'):
        self._save_current_editor()

def _save_current_editor(self) -> bool:
    """保存当前编辑器"""
    current = self.center_panel.tab_widget.currentWidget()
    if not current or not hasattr(current, '_file_path'):
        return False
    
    file_path = current._file_path
    if isinstance(current, QTextEdit):
        content = current.toPlainText()
        try:
            Path(file_path).write_text(content, encoding='utf-8')
            self.show_message(f"已保存: {Path(file_path).name}", 2000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return False
    return False
```

### 快捷键绑定
```python
save_action = QAction("保存", self)
save_action.setShortcut("Ctrl+S")
save_action.triggered.connect(self._on_save)
```

### 代码位置
[main_window.py L648-649, L984-1020, L1119-1137](../../2workbench/presentation/main_window.py)

### 验证结果
✅ Ctrl+S 保存功能已实现

---

## Step 4.2: 实现撤销/重做

### 问题描述
F-003 — 编辑器缺少撤销/重做功能。

### 实现方案
QTextEdit 自带撤销/重做功能，只需绑定快捷键：

```python
def _on_undo(self) -> None:
    """撤销"""
    current = self.center_panel.tab_widget.currentWidget()
    if isinstance(current, QTextEdit):
        current.undo()

def _on_redo(self) -> None:
    """重做"""
    current = self.center_panel.tab_widget.currentWidget()
    if isinstance(current, QTextEdit):
        current.redo()
```

### 快捷键绑定
```python
undo_action = QAction("撤销", self)
undo_action.setShortcut("Ctrl+Z")
undo_action.triggered.connect(self._on_undo)

redo_action = QAction("重做", self)
redo_action.setShortcut("Ctrl+Y")
redo_action.triggered.connect(self._on_redo)
```

### 代码位置
[main_window.py L664-670, L910-928](../../2workbench/presentation/main_window.py)

### 验证结果
✅ Ctrl+Z/Y 撤销重做功能已实现

---

## Step 4.3: HTTP 服务器添加基础认证

### 问题描述
F-018 — HTTP 服务器缺少认证授权。

### 实现方案
生成随机 Token 并验证：

```python
import secrets

# 启动时生成随机 token
_AUTH_TOKEN = secrets.token_hex(32)

def get_auth_token() -> str:
    """获取认证 Token"""
    return _AUTH_TOKEN

class GuiHTTPHandler(BaseHTTPRequestHandler):
    def _check_auth(self) -> bool:
        """检查请求中的认证 token"""
        auth = self.headers.get("X-Auth-Token", "")
        return auth == _AUTH_TOKEN
    
    def do_GET(self):
        # 健康检查端点不需要认证
        if self.path == "/health":
            self._send_json({"status": "ok", "version": "2.0"})
            return
        
        # 其他端点需要认证
        if not self._check_auth():
            self._send_json({"error": "Unauthorized"}, 401)
            return
        # ... 原有逻辑
    
    def do_POST(self):
        if not self._check_auth():
            self._send_json({"error": "Unauthorized"}, 401)
            return
        # ... 原有逻辑
```

### 启动时打印 Token
```python
def start_server(gui_instance, port: int = DEFAULT_PORT):
    # ...
    logger.info(f"HTTP Server started on http://127.0.0.1:{port}")
    logger.info(f"Auth Token: {_AUTH_TOKEN}")
    return server, thread
```

### 使用示例
```bash
# 无 token 的请求返回 401
curl http://localhost:18080/api/status
# {"error": "Unauthorized"}

# 带 token 的请求正常处理
curl -H "X-Auth-Token: <token>" http://localhost:18080/api/status
```

### 代码位置
[server.py L39-44, L71-78, L125-130, L165-170, L666](../../2workbench/presentation/server.py)

### 验证结果
✅ X-Auth-Token 认证已实现

---

## Step 4.4: 跨平台截图支持

### 问题描述
F-019 — 截图功能仅支持 Windows。

### 实现方案
根据平台选择截图方法：

```python
import sys

def _handle_get_screenshot(self):
    # ...
    # 根据平台选择截图方法
    if sys.platform == "win32":
        screenshot_bytes = self._capture_window_winapi(gui)
    else:
        screenshot_bytes = self._capture_with_qt_bytes(gui)
    # ...

def _capture_with_qt_bytes(self, gui) -> bytes | None:
    """使用 Qt 方法截图（跨平台方案）"""
    try:
        from PyQt6.QtCore import QBuffer, QByteArray
        from PyQt6.QtGui import QPixmap
        
        pixmap = gui.grab()
        
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        buffer.close()
        
        return bytes(byte_array.data())
    except Exception as e:
        logger.error(f"[Screenshot] Qt 截图失败: {e}")
        return None
```

### 代码位置
[server.py L334-337, L581-601](../../2workbench/presentation/server.py)

### 验证结果
✅ 跨平台截图已实现（Windows: WinAPI, Linux/macOS: Qt）

---

## Step 4.5: app.py 命令行参数

### 问题描述
F-020 — 缺少命令行参数支持。

### 实现方案
使用 `argparse` 添加参数：

```python
import argparse

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Game Master Agent IDE")
    parser.add_argument("--project", "-p", help="直接打开指定项目路径")
    parser.add_argument("--version", "-v", action="version", version="2.0.0")
    parser.add_argument("--no-gui", action="store_true", help="无头模式（仅测试）")
    parser.add_argument("--theme", "-t", choices=["dark", "light"], default="dark", help="主题模式")
    parser.add_argument("--port", type=int, default=18080, help="HTTP 服务器端口")
    parser.add_argument("--debug", "-d", action="store_true", help="调试模式")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    parser.add_argument("--skip-selector", action="store_true", help="跳过项目选择器")
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    
    # 如果通过命令行指定了项目路径，直接打开
    if args.project:
        project_path = Path(args.project)
        if project_path.exists():
            selected_project = project_path
        else:
            logger.error(f"项目路径不存在: {args.project}")
            return
```

### 使用示例
```bash
# 显示帮助
python app.py --help

# 直接打开项目
python app.py --project /path/to/project

# 指定主题和端口
python app.py --theme light --port 8080

# 调试模式
python app.py --debug

# 跳过项目选择器
python app.py --skip-selector
```

### 代码位置
[app.py L15-40, L73-80](../../2workbench/app.py)

### 验证结果
✅ 命令行参数已实现

---

## 相关文件

| 文件 | 修改内容 |
|------|---------|
| [main_window.py](../../2workbench/presentation/main_window.py) | 文件保存、撤销重做 |
| [server.py](../../2workbench/presentation/server.py) | HTTP认证、跨平台截图 |
| [app.py](../../2workbench/app.py) | 命令行参数 |

---

## 验收标准

- [x] 双击文件可编辑
- [x] Ctrl+S 保存文件内容
- [x] 保存成功有提示
- [x] Ctrl+Z 撤销
- [x] Ctrl+Y 重做
- [x] 无 token 的请求返回 401
- [x] 带 token 的请求正常处理
- [x] Windows 上截图正常
- [x] Linux/macOS 上截图正常（Qt 方式）
- [x] --help 显示帮助
- [x] --project /path 直接打开项目
- [x] --version 显示版本号

---

*创建时间: 2026-05-03*
*更新记录: 初始创建*
