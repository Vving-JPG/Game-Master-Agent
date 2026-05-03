# presentation/server.py
"""内嵌 HTTP 服务器 — 在 GUI 进程的后台线程运行

Trae 通过 curl 操控 GUI:
    curl http://localhost:18080/api/status
    curl -X POST http://localhost:18080/api/run -d '{"event": "攻击哥布林"}'
    curl -X POST http://localhost:18080/api/project/open -d '{"path": "data/my_first_agent.agent"}'

结构化状态 API (新):
    curl http://localhost:18080/api/state           # 应用状态
    curl http://localhost:18080/api/dom             # Widget 树
    curl http://localhost:18080/api/dom?selector=console  # 特定区域
    curl http://localhost:18080/api/dom?diff=true   # 变化部分
    curl http://localhost:18080/api/uia             # Windows UIA 树
    curl http://localhost:18080/api/find?id=run_btn # 查找 Widget
"""
from __future__ import annotations

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel

from presentation.state_api import init_state_api, get_state_api
from foundation.logger import get_logger

logger = get_logger(__name__)

# 默认端口
DEFAULT_PORT = 18080


class GuiHTTPHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器 — 处理所有 API 端点"""

    # GUI 实例引用 (由 MainWindow 设置)
    gui_instance = None
    project_root = ""
    _lock = threading.Lock()

    @classmethod
    def set_gui(cls, gui, root: str) -> None:
        """线程安全地设置 GUI 实例"""
        with cls._lock:
            cls.gui_instance = gui
            cls.project_root = root

    def _get_gui(self):
        """线程安全地获取 GUI 实例"""
        with self._lock:
            return self.gui_instance, self.project_root

    def log_message(self, fmt, *args):
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
        gui, project_root = self._get_gui()
        root = Path(project_root)
        full = (root / path).resolve()
        if not str(full).startswith(str(root.resolve())):
            raise ValueError(f"禁止访问: {path}")
        return full

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            if path == "/health":
                self._send_json({"status": "ok", "version": "2.0"})

            elif path == "/api/status":
                self._handle_get_status()

            elif path == "/api/state":
                self._handle_get_state()

            elif path == "/api/dom":
                selector = query.get("selector", [None])[0]
                diff = query.get("diff", ["false"])[0].lower() == "true"
                self._handle_get_dom(selector, diff)

            elif path == "/api/uia":
                self._handle_get_uia()

            elif path == "/api/find":
                self._handle_find_widget(query)

            elif path == "/api/screenshot":
                self._handle_get_screenshot()

            elif path.startswith("/api/click/"):
                widget = path[len("/api/click/"):]
                self._handle_click_widget(widget)

            else:
                self._send_json({"error": "未知端点"}, 404)

        except Exception as e:
            self._send_json({"error": str(e), "type": type(e).__name__}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/run":
                body = self._read_body()
                self._handle_run(body)
            elif path == "/api/project/create":
                body = self._read_body()
                self._handle_create_project(body)
            elif path == "/api/project/open":
                body = self._read_body()
                self._handle_open_project(body)
            else:
                self._send_json({"error": "未知端点"}, 404)

        except Exception as e:
            self._send_json({"error": str(e), "type": type(e).__name__}, 500)

    def _handle_get_status(self):
        """获取状态"""
        gui, _ = self._get_gui()
        if gui:
            self._send_json({"status": "running", "window": gui.windowTitle()})
        else:
            self._send_json({"status": "uninitialized"})

    def _handle_get_state(self):
        """获取应用状态 — 结构化状态 API"""
        api = get_state_api()
        if not api:
            self._send_json({"error": "状态 API 未初始化"}, 500)
            return

        result = api.get_state()
        self._send_json(result)

    def _handle_get_dom(self, selector: str | None, diff: bool):
        """获取 Widget DOM 树 — 结构化状态 API"""
        api = get_state_api()
        if not api:
            self._send_json({"error": "状态 API 未初始化"}, 500)
            return

        result = api.get_dom(selector=selector, diff=diff)
        self._send_json(result)

    def _handle_get_uia(self):
        """获取 Windows UIA 树 — 结构化状态 API"""
        api = get_state_api()
        if not api:
            self._send_json({"error": "状态 API 未初始化"}, 500)
            return

        gui, _ = self._get_gui()
        hwnd = gui.winId() if gui else None
        result = api.get_uia_tree(hwnd)
        self._send_json(result)

    def _handle_find_widget(self, query: dict):
        """查找 Widget — 结构化状态 API"""
        api = get_state_api()
        if not api:
            self._send_json({"error": "状态 API 未初始化"}, 500)
            return

        # 转换查询参数
        query_dict = {}
        for key, values in query.items():
            if values:
                query_dict[key] = values[0]

        result = api.find_widget(query_dict)
        self._send_json(result)

    def _handle_run(self, body: dict):
        """运行 Agent"""
        event = body.get("event", "")
        self._send_json({"status": "started", "event": event})

    def _handle_create_project(self, body: dict):
        """在 GUI 中创建新项目 — 使用信号槽机制确保在主线程执行"""
        gui, project_root = self._get_gui()
        if not gui:
            self._send_json({"error": "GUI 实例不可用"}, 500)
            return

        try:
            name = body.get("name", "")
            template = body.get("template", "trpg")
            directory = body.get("directory", "data")
            
            if not name:
                self._send_json({"error": "缺少 name 参数"}, 400)
                return

            logger.info(f"[HTTP Server] 请求创建项目: {name} (模板: {template})")
            
            # 使用信号槽机制
            gui.create_project_requested.emit(name, template, directory, project_root)
            
            logger.info(f"[HTTP Server] 创建项目信号已发送")
            self._send_json({"status": "creating", "name": name, "template": template})

        except Exception as e:
            import traceback
            self._send_json({"error": f"创建项目失败: {str(e)}"}, 500)
            logger.error(f"[HTTP Server] Error: {e}")
            logger.error(traceback.format_exc())

    def _handle_open_project(self, body: dict):
        """在 GUI 中打开项目 — 使用信号槽机制确保在主线程执行"""
        gui, project_root = self._get_gui()
        if not gui:
            self._send_json({"error": "GUI 实例不可用"}, 500)
            return

        try:
            project_path = body.get("path", "")
            if not project_path:
                self._send_json({"error": "缺少 path 参数"}, 400)
                return

            logger.info(f"[HTTP Server] 请求打开项目: {project_path}")
            
            # 使用信号槽机制 — 信号会自动在接收者（gui）的线程中执行
            gui.open_project_requested.emit(project_path, project_root)
            
            logger.info(f"[HTTP Server] 信号已发送")
            self._send_json({"status": "opening", "path": project_path})

        except Exception as e:
            import traceback
            self._send_json({"error": f"打开项目失败: {str(e)}"}, 500)
            logger.error(f"[HTTP Server] Error: {e}")
            logger.error(traceback.format_exc())

    def _handle_get_screenshot(self):
        """截图 GUI 界面 — 使用 Windows API 支持后台窗口截图
        
        流程:
        1. 将窗口带到前台
        2. 等待窗口渲染完成
        3. 截图
        4. 最小化窗口
        """
        gui, _ = self._get_gui()
        if not gui:
            self._send_json({"error": "GUI 实例不可用"}, 500)
            return

        try:
            import base64
            import io
            import time
            from PIL import Image
            
            # 1. 将窗口带到前台
            was_minimized = self._bring_window_to_front(gui)
            
            # 2. 等待窗口渲染完成
            time.sleep(0.3)
            
            # 3. 截图
            screenshot_bytes = self._capture_window_winapi(gui)
            
            # 4. 如果窗口之前是最小化的，或者需要自动最小化，则最小化
            self._minimize_window(gui)
            
            if screenshot_bytes:
                # 转换为 base64
                img_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                # 获取图片尺寸
                img = Image.open(io.BytesIO(screenshot_bytes))
                width, height = img.size
                
                self._send_json({
                    "status": "ok",
                    "format": "png",
                    "base64": img_base64,
                    "width": width,
                    "height": height
                })
            else:
                # 如果 Windows API 失败，回退到 Qt 方法
                self._capture_with_qt(gui)
                
        except Exception as e:
            self._send_json({"error": f"截图失败: {str(e)}"}, 500)
    
    def _bring_window_to_front(self, gui) -> bool:
        """将窗口带到前台
        
        Returns:
            窗口之前是否是最小化状态
        """
        try:
            import ctypes
            from ctypes import wintypes
            
            hwnd = gui.winId()
            if not hwnd:
                return False
            
            # 检查窗口是否最小化
            SW_MINIMIZE = 6
            SW_RESTORE = 9
            SW_SHOW = 5
            SW_SHOWNA = 8
            
            # 获取窗口状态
            is_minimized = ctypes.windll.user32.IsIconic(hwnd)
            
            # 如果最小化，先恢复
            if is_minimized:
                ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            
            # 将窗口带到前台
            # 先设置前台窗口权限
            try:
                # 使用 AttachThreadInput 来允许设置前台窗口
                foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
                if foreground_hwnd:
                    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
                    foreground_thread = ctypes.windll.user32.GetWindowThreadProcessId(foreground_hwnd, None)
                    if foreground_thread != current_thread:
                        ctypes.windll.user32.AttachThreadInput(foreground_thread, current_thread, True)
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                        ctypes.windll.user32.AttachThreadInput(foreground_thread, current_thread, False)
                    else:
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                else:
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                # 备选方案：使用 ShowWindow
                ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
            
            # 激活窗口
            ctypes.windll.user32.SetActiveWindow(hwnd)
            
            return bool(is_minimized)
            
        except Exception as e:
            logger.warning(f"[Screenshot] 无法将窗口带到前台: {e}")
            return False
    
    def _minimize_window(self, gui) -> None:
        """最小化窗口"""
        try:
            import ctypes
            
            hwnd = gui.winId()
            if not hwnd:
                return
            
            SW_MINIMIZE = 6
            ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
            
        except Exception as e:
            logger.warning(f"[Screenshot] 无法最小化窗口: {e}")
    
    def _capture_window_winapi(self, gui) -> bytes | None:
        """使用 Windows API 捕获窗口（支持后台窗口）
        
        Returns:
            PNG 格式的图片字节，失败返回 None
        """
        try:
            import ctypes
            from ctypes import wintypes
            import io
            from PIL import Image
            
            # Windows API 常量
            SRCCOPY = 0x00CC0020
            CAPTUREBLT = 0x40000000
            
            # 获取窗口句柄
            hwnd = gui.winId()
            if not hwnd:
                return None
            
            # 设置 DPI 感知（解决 Windows 缩放导致的截图不全问题）
            try:
                # Windows 10 1607+
                ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            except Exception:
                try:
                    # Windows 8.1+
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per Monitor DPI Aware
                except Exception:
                    try:
                        # Windows Vista+
                        ctypes.windll.user32.SetProcessDPIAware()
                    except Exception:
                        pass
            
            # 获取窗口尺寸（包括非客户区：标题栏、边框、菜单栏等）
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            
            # 获取 DPI 缩放比例
            try:
                dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
                scale_factor = dpi / 96.0  # 96 是标准 DPI
            except Exception:
                # 如果 GetDpiForWindow 不可用，尝试其他方法
                try:
                    hdc = ctypes.windll.user32.GetDC(hwnd)
                    dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                    ctypes.windll.user32.ReleaseDC(hwnd, hdc)
                    scale_factor = dpi_x / 96.0
                except Exception:
                    scale_factor = 1.0
            
            # 计算实际像素尺寸（考虑 DPI 缩放）
            width = int((rect.right - rect.left) * scale_factor)
            height = int((rect.bottom - rect.top) * scale_factor)
            window_x = rect.left
            window_y = rect.top
            
            if width <= 0 or height <= 0:
                return None
            
            # 创建内存 DC 和位图
            hdc_screen = ctypes.windll.gdi32.CreateDCW("DISPLAY", None, None, None)
            hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
            hbitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
            h_old = ctypes.windll.gdi32.SelectObject(hdc_mem, hbitmap)
            
            try:
                # 方法1: 尝试从屏幕 DC 复制窗口区域（可以捕获完整窗口，包括非客户区）
                # 这要求窗口至少部分可见
                result = ctypes.windll.gdi32.BitBlt(
                    hdc_mem, 0, 0, width, height,
                    hdc_screen, window_x, window_y, SRCCOPY | CAPTUREBLT
                )
                
                if result == 0:
                    # 方法2: 如果 BitBlt 失败，使用 PrintWindow
                    # PrintWindow 可以捕获被遮挡的窗口，但可能不包括非客户区
                    PW_ENTIREWINDOW = 0  # 0 = 整个窗口，1 = 仅客户区
                    ctypes.windll.user32.PrintWindow(hwnd, hdc_mem, PW_ENTIREWINDOW)
                
                # 创建 BITMAPINFO
                class BITMAPINFOHEADER(ctypes.Structure):
                    _fields_ = [
                        ("biSize", wintypes.DWORD),
                        ("biWidth", wintypes.LONG),
                        ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD),
                        ("biBitCount", wintypes.WORD),
                        ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD),
                        ("biXPelsPerMeter", wintypes.LONG),
                        ("biYPelsPerMeter", wintypes.LONG),
                        ("biClrUsed", wintypes.DWORD),
                        ("biClrImportant", wintypes.DWORD),
                    ]
                
                class BITMAPINFO(ctypes.Structure):
                    _fields_ = [
                        ("bmiHeader", BITMAPINFOHEADER),
                        ("bmiColors", wintypes.DWORD * 3),
                    ]
                
                bi = BITMAPINFO()
                bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bi.bmiHeader.biWidth = width
                bi.bmiHeader.biHeight = -height  # 负值表示自上而下的位图
                bi.bmiHeader.biPlanes = 1
                bi.bmiHeader.biBitCount = 32
                bi.bmiHeader.biCompression = 0  # BI_RGB
                
                # 获取位图数据
                buffer_size = width * height * 4
                buffer = ctypes.create_string_buffer(buffer_size)
                
                ctypes.windll.gdi32.GetDIBits(
                    hdc_mem, hbitmap, 0, height,
                    buffer, ctypes.byref(bi), 0  # DIB_RGB_COLORS
                )
                
                # 转换为 PIL Image
                img = Image.frombuffer(
                    'RGBA', (width, height), buffer, 'raw', 'BGRA', 0, 1
                )
                
                # 转换为 RGB（去除 alpha 通道）
                img = img.convert('RGB')
                
                # 保存到字节流
                output = io.BytesIO()
                img.save(output, format='PNG')
                return output.getvalue()
                
            finally:
                ctypes.windll.gdi32.SelectObject(hdc_mem, h_old)
                ctypes.windll.gdi32.DeleteObject(hbitmap)
                ctypes.windll.gdi32.DeleteDC(hdc_mem)
                ctypes.windll.gdi32.DeleteDC(hdc_screen)
                
        except Exception as e:
            logger.error(f"[Screenshot] Windows API 截图失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _capture_with_qt(self, gui) -> None:
        """使用 Qt 方法截图（回退方案）"""
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

    def _handle_click_widget(self, widget: str):
        """模拟点击界面元素"""
        gui, _ = self._get_gui()
        if not gui:
            self._send_json({"error": "GUI 实例不可用"}, 500)
            return

        try:
            clicked = False

            # 根据名称查找并点击控件
            if widget == "run":
                QTimer.singleShot(0, gui._on_run_agent)
                clicked = True
            elif widget == "pause" or widget == "stop":
                QTimer.singleShot(0, gui._on_stop_agent)
                clicked = True
            elif widget == "reset":
                clicked = True  # 占位
            elif widget == "refresh":
                clicked = True  # 占位
            elif widget == "save":
                QTimer.singleShot(0, gui._on_save)
                clicked = True

            if clicked:
                self._send_json({"status": "clicked", "widget": widget})
            else:
                self._send_json({
                    "status": "not_found",
                    "widget": widget,
                    "available": ["run", "pause", "reset", "refresh", "save"]
                }, 404)

        except Exception as e:
            self._send_json({"error": f"点击失败: {str(e)}"}, 500)


def start_server(gui_instance, port: int = DEFAULT_PORT):
    """在后台线程启动 HTTP 服务器"""
    # 使用线程安全的方法设置 GUI 实例
    GuiHTTPHandler.set_gui(gui_instance, str(Path(__file__).parent.parent))

    # 初始化结构化状态 API
    init_state_api(gui_instance)

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
