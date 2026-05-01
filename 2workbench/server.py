# workbench/server.py
"""内嵌 HTTP 服务器 — 在 GUI 进程的后台线程运行

Trae 通过 curl 操控 GUI:
    curl http://localhost:18080/api/status
    curl -X POST http://localhost:18080/api/run -d '{"event": "攻击哥布林"}'
"""
import json
import threading
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

# 默认端口
DEFAULT_PORT = 18080


class GuiHTTPHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器 — 处理所有 API 端点"""

    # GUI 实例引用 (由 MainWindow 设置)
    gui_instance = None  # type: MainWindow | None
    project_root = ""

    def log_message(self, format, *args):
        """静默日志 (不打印到控制台)"""
        pass

    def _send_json(self, data: Any, status: int = 200):
        """发送 JSON 响应"""
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        """读取请求体 JSON"""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8"))

    def _resolve_path(self, path: str) -> Path:
        """解析文件路径，防止目录遍历"""
        root = Path(self.project_root)
        full = (root / path).resolve()
        if not str(full).startswith(str(root.resolve())):
            raise ValueError(f"禁止访问: {path}")
        return full

    # ---- OPTIONS (CORS 预检) ----

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---- GET ----

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        try:
            if path == "/health":
                self._send_json({"status": "ok", "version": "2.0"})

            elif path == "/api/status":
                self._handle_get_status()

            elif path == "/api/turns":
                last = int(params.get("last", [5])[0])
                self._handle_get_turns(last)

            elif path == "/api/file":
                file_path = params.get("path", [""])[0]
                self._handle_get_file(file_path)

            elif path == "/api/tree":
                dir_path = params.get("path", [""])[0]
                self._handle_get_tree(dir_path)

            elif path == "/api/screenshot":
                self._handle_get_screenshot()

            elif path == "/api/state":
                widget = params.get("widget", [""])[0]
                self._handle_get_state(widget)

            elif path.startswith("/api/click/"):
                widget = path[len("/api/click/"):]
                self._handle_click_widget(widget)

            else:
                self._send_json({"error": "未知端点"}, 404)

        except Exception as e:
            self._send_json({"error": str(e), "type": type(e).__name__}, 500)

    # ---- POST ----

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/run":
                body = self._read_body()
                self._handle_run(body)

            elif path == "/api/control":
                body = self._read_body()
                self._handle_control(body)

            elif path == "/api/inject":
                body = self._read_body()
                self._handle_inject(body)

            elif path == "/api/force-tool":
                body = self._read_body()
                self._handle_force_tool(body)

            elif path == "/api/file":
                body = self._read_body()
                params = parse_qs(parsed.query)
                file_path = params.get("path", [""])[0]
                self._handle_create_file(file_path, body)

            elif path == "/api/open":
                body = self._read_body()
                self._handle_open_file(body)

            elif path == "/api/save":
                self._handle_save_file()

            elif path == "/api/refresh":
                self._handle_refresh()

            else:
                self._send_json({"error": "未知端点"}, 404)

        except Exception as e:
            self._send_json({"error": str(e), "type": type(e).__name__}, 500)

    # ---- PUT ----

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/file":
                body = self._read_body()
                params = parse_qs(parsed.query)
                file_path = params.get("path", [""])[0]
                self._handle_put_file(file_path, body)
            else:
                self._send_json({"error": "未知端点"}, 404)

        except Exception as e:
            self._send_json({"error": str(e), "type": type(e).__name__}, 500)

    # ---- DELETE ----

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/file":
                params = parse_qs(parsed.query)
                file_path = params.get("path", [""])[0]
                self._handle_delete_file(file_path)
            else:
                self._send_json({"error": "未知端点"}, 404)

        except Exception as e:
            self._send_json({"error": str(e), "type": type(e).__name__}, 500)

    # ---- 处理函数 ----

    def _handle_get_status(self):
        """获取 Agent 状态"""
        gui = self.gui_instance
        if gui and hasattr(gui, "bridge") and gui.bridge:
            status = gui.bridge.get_status()
            turn_count = gui.bridge.get_turn_count()
            self._send_json({"status": status, "turn": turn_count})
        else:
            self._send_json({"status": "uninitialized", "error": "Agent 桥接层未初始化"})

    def _handle_get_turns(self, last: int):
        """获取轮次历史"""
        gui = self.gui_instance
        if gui and hasattr(gui, "bridge") and gui.bridge:
            turn_count = gui.bridge.get_turn_count()
            self._send_json({"turns": [], "total": turn_count})
        else:
            self._send_json({"turns": [], "total": 0})

    def _handle_run(self, body: dict):
        """运行 Agent"""
        gui = self.gui_instance
        event = body.get("event", "")
        if not event:
            self._send_json({"error": "缺少 event 参数"}, 400)
            return

        if gui and hasattr(gui, "bridge") and gui.bridge:
            # 使用信号槽在主线程执行
            from PyQt6.QtCore import QTimer
            
            def run_in_main():
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(gui.bridge.run_agent())
                    else:
                        loop.run_until_complete(gui.bridge.run_agent())
                except RuntimeError:
                    # 没有事件循环，创建新的
                    asyncio.run(gui.bridge.run_agent())
            
            # 使用 QTimer.singleShot 在主线程执行
            QTimer.singleShot(0, run_in_main)
            
            self._send_json({"status": "started", "turn": gui.bridge.get_turn_count()})
        else:
            self._send_json({"status": "error", "error": "Agent 桥接层未初始化"})

    def _handle_control(self, body: dict):
        """控制 Agent"""
        gui = self.gui_instance
        action = body.get("action", "")
        if gui and hasattr(gui, "bridge") and gui.bridge:
            if action == "pause":
                gui.bridge.pause()
                self._send_json({"status": "paused"})
            elif action == "resume":
                gui.bridge.pause()  # pause 是切换状态
                self._send_json({"status": "running"})
            elif action == "step":
                gui.bridge.step()
                self._send_json({"status": "step_waiting"})
            elif action == "reset":
                gui.bridge.reset()
                self._send_json({"status": "idle", "turn": 0})
            else:
                self._send_json({"error": f"未知操作: {action}"}, 400)
        else:
            self._send_json({"error": "Agent 桥接层未初始化"}, 500)

    def _handle_inject(self, body: dict):
        """注入指令"""
        gui = self.gui_instance
        if gui and hasattr(gui, "bridge") and gui.bridge:
            gui.bridge.inject_command(body.get("level", "user"), body.get("content", ""))
            self._send_json({"message": "指令已注入"})
        else:
            self._send_json({"error": "Agent 桥接层未初始化"}, 500)

    def _handle_force_tool(self, body: dict):
        """强制工具"""
        gui = self.gui_instance
        if gui and hasattr(gui, "bridge") and gui.bridge:
            result = gui.bridge.force_tool(body.get("tool", ""), body.get("params", ""))
            self._send_json({"result": result})
        else:
            self._send_json({"error": "Agent 桥接层未初始化"}, 500)

    def _handle_get_file(self, file_path: str):
        """读取文件"""
        try:
            full = self._resolve_path(file_path)
            if not full.exists():
                self._send_json({"error": f"文件不存在: {file_path}"}, 404)
                return
            content = full.read_text(encoding="utf-8")
            self._send_json({"path": file_path, "content": content, "size": len(content)})
        except ValueError as e:
            self._send_json({"error": str(e)}, 403)

    def _handle_put_file(self, file_path: str, body: dict):
        """写入文件"""
        try:
            full = self._resolve_path(file_path)
            content = body.get("content", "")
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            self._send_json({"path": file_path, "status": "saved", "size": len(content)})
        except ValueError as e:
            self._send_json({"error": str(e)}, 403)

    def _handle_create_file(self, file_path: str, body: dict):
        """创建文件"""
        try:
            full = self._resolve_path(file_path)
            if full.exists():
                self._send_json({"error": f"文件已存在: {file_path}"}, 409)
                return
            content = body.get("content", "")
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            self._send_json({"path": file_path, "status": "created"})
        except ValueError as e:
            self._send_json({"error": str(e)}, 403)

    def _handle_delete_file(self, file_path: str):
        """删除文件"""
        try:
            full = self._resolve_path(file_path)
            if not full.exists():
                self._send_json({"error": f"文件不存在: {file_path}"}, 404)
                return
            full.unlink()
            self._send_json({"path": file_path, "status": "deleted"})
        except ValueError as e:
            self._send_json({"error": str(e)}, 403)

    def _handle_get_tree(self, dir_path: str):
        """获取目录树"""
        try:
            full = self._resolve_path(dir_path) if dir_path else Path(self.project_root)
            if not full.exists():
                self._send_json({"items": []})
                return
            items = []
            for item in sorted(full.iterdir()):
                if item.name.startswith("__") or item.name.startswith(".") or item.suffix == ".pyc":
                    continue
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "path": str(item.relative_to(self.project_root)),
                })
            self._send_json({"items": items})
        except ValueError as e:
            self._send_json({"error": str(e)}, 403)

    def _handle_open_file(self, body: dict):
        """在 GUI 中打开文件"""
        gui = self.gui_instance
        file_path = body.get("path", "")
        if gui and hasattr(gui, "editor_stack"):
            gui.editor_stack.open_file(file_path, "unknown")
            self._send_json({"status": "opened", "path": file_path})
        else:
            self._send_json({"error": "GUI 实例不可用"}, 500)

    def _handle_save_file(self):
        """保存当前文件"""
        gui = self.gui_instance
        if gui and hasattr(gui, "editor_stack"):
            gui.editor_stack.save_current()
            self._send_json({"status": "saved"})
        else:
            self._send_json({"error": "GUI 实例不可用"}, 500)

    def _handle_refresh(self):
        """刷新资源树"""
        gui = self.gui_instance
        if gui and hasattr(gui, "resource_tree"):
            gui.resource_tree.refresh()
            self._send_json({"status": "refreshed"})
        else:
            self._send_json({"error": "GUI 实例不可用"}, 500)

    def _handle_get_screenshot(self):
        """截图 GUI 界面"""
        gui = self.gui_instance
        if not gui:
            self._send_json({"error": "GUI 实例不可用"}, 500)
            return
        
        try:
            from PyQt6.QtCore import QBuffer, QByteArray
            from PyQt6.QtGui import QPixmap
            import base64
            
            # 截取整个窗口
            pixmap = gui.grab()
            
            # 转换为 PNG 字节
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            pixmap.save(buffer, "PNG")
            buffer.close()
            
            # Base64 编码
            img_base64 = base64.b64encode(byte_array.data()).decode('utf-8')
            
            self._send_json({
                "status": "ok",
                "format": "png",
                "base64": img_base64,
                "width": pixmap.width(),
                "height": pixmap.height()
            })
        except Exception as e:
            self._send_json({"error": f"截图失败: {str(e)}"}, 500)

    def _handle_get_state(self, widget: str):
        """获取控件状态"""
        gui = self.gui_instance
        if not gui:
            self._send_json({"error": "GUI 实例不可用"}, 500)
            return
        
        try:
            state = {}
            
            if widget == "all" or widget == "":
                # 获取所有主要控件状态
                state["window"] = {
                    "title": gui.windowTitle(),
                    "width": gui.width(),
                    "height": gui.height(),
                    "visible": gui.isVisible()
                }
                
                if hasattr(gui, "bridge") and gui.bridge:
                    state["agent"] = {
                        "status": gui.bridge.get_status(),
                        "turn_count": gui.bridge.get_turn_count()
                    }
                
                if hasattr(gui, "statusbar"):
                    state["statusbar_message"] = gui.statusbar.currentMessage()
                    
            elif widget == "agent":
                if hasattr(gui, "bridge") and gui.bridge:
                    state = {
                        "status": gui.bridge.get_status(),
                        "turn_count": gui.bridge.get_turn_count()
                    }
                else:
                    state = {"error": "Agent 桥接层未初始化"}
                    
            elif widget == "window":
                state = {
                    "title": gui.windowTitle(),
                    "width": gui.width(),
                    "height": gui.height(),
                    "visible": gui.isVisible()
                }
                
            elif widget == "editor":
                if hasattr(gui, "editor_stack"):
                    state = {
                        "current_file": getattr(gui.editor_stack, "current_file", None),
                        "tab_count": gui.editor_stack.count() if hasattr(gui.editor_stack, "count") else 0
                    }
                else:
                    state = {"error": "编辑器不可用"}
                    
            elif widget == "resource_tree":
                if hasattr(gui, "resource_tree"):
                    state = {
                        "project_root": str(gui.resource_tree.project_root) if hasattr(gui.resource_tree, "project_root") else ""
                    }
                else:
                    state = {"error": "资源树不可用"}
            else:
                state = {"error": f"未知控件: {widget}"}
            
            self._send_json({"widget": widget, "state": state})
            
        except Exception as e:
            self._send_json({"error": f"获取状态失败: {str(e)}"}, 500)

    def _handle_click_widget(self, widget: str):
        """模拟点击界面元素"""
        gui = self.gui_instance
        if not gui:
            self._send_json({"error": "GUI 实例不可用"}, 500)
            return
        
        try:
            from PyQt6.QtCore import QTimer, Qt
            
            clicked = False
            target = None
            
            # 根据名称查找并点击控件
            if widget == "run" or widget == "act_run":
                if hasattr(gui, "act_run"):
                    target = gui.act_run
                    QTimer.singleShot(0, gui.act_run.trigger)
                    clicked = True
                    
            elif widget == "pause":
                if hasattr(gui, "act_pause"):
                    target = gui.act_pause
                    QTimer.singleShot(0, gui.act_pause.trigger)
                    clicked = True
                    
            elif widget == "step":
                if hasattr(gui, "act_step"):
                    target = gui.act_step
                    QTimer.singleShot(0, gui.act_step.trigger)
                    clicked = True
                    
            elif widget == "reset":
                if hasattr(gui, "act_reset"):
                    target = gui.act_reset
                    QTimer.singleShot(0, gui.act_reset.trigger)
                    clicked = True
                    
            elif widget == "refresh":
                if hasattr(gui, "resource_tree"):
                    QTimer.singleShot(0, gui.resource_tree.refresh)
                    clicked = True
                    
            elif widget == "save":
                if hasattr(gui, "editor_stack"):
                    QTimer.singleShot(0, gui.editor_stack.save_current)
                    clicked = True
                    
            elif widget.startswith("menu_"):
                # 菜单项点击，如 menu_file_open
                menu_name = widget[5:]
                # 简化处理，实际应该遍历 menubar
                clicked = False

            else:
                # 尝试通过 objectName 查找
                target_widget = gui.findChild(object, widget)
                if target_widget and hasattr(target_widget, "click"):
                    QTimer.singleShot(0, target_widget.click)
                    clicked = True
            
            if clicked:
                self._send_json({
                    "status": "clicked",
                    "widget": widget,
                    "target": str(target) if target else None
                })
            else:
                self._send_json({
                    "status": "not_found",
                    "widget": widget,
                    "available": ["run", "pause", "step", "reset", "refresh", "save"]
                }, 404)
                
        except Exception as e:
            self._send_json({"error": f"点击失败: {str(e)}"}, 500)


def start_server(gui_instance, port: int = DEFAULT_PORT):
    """在后台线程启动 HTTP 服务器"""
    GuiHTTPHandler.gui_instance = gui_instance
    GuiHTTPHandler.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    server = HTTPServer(("127.0.0.1", port), GuiHTTPHandler)
    server.daemon_threads = True

    def _run():
        try:
            server.serve_forever()
        except Exception:
            pass

    thread = threading.Thread(target=_run, daemon=True, name="http-server")
    thread.start()

    return server, thread
