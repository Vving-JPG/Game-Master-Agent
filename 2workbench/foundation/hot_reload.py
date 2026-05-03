"""热重载模块 — 开发模式下自动重启应用

监控 Python 文件变化，自动重启应用。
"""
from __future__ import annotations

import sys
import os
import time
import subprocess
from pathlib import Path
from typing import Callable

from foundation.logger import get_logger

logger = get_logger(__name__)


class HotReloader:
    """文件热重载器"""

    def __init__(self, watch_dirs: list[str | Path], interval: float = 1.0):
        """
        初始化热重载器

        Args:
            watch_dirs: 监控的目录列表
            interval: 检查间隔（秒）
        """
        self.watch_dirs = [Path(d) for d in watch_dirs]
        self.interval = interval
        self._file_mtimes: dict[Path, float] = {}
        self._running = False
        self._on_reload: Callable | None = None

    def set_reload_callback(self, callback: Callable) -> None:
        """设置重载回调函数"""
        self._on_reload = callback

    def start(self) -> None:
        """启动监控（阻塞模式）"""
        self._running = True
        self._scan_files()

        logger.info(f"热重载已启动，监控 {len(self.watch_dirs)} 个目录")

        while self._running:
            time.sleep(self.interval)
            if self._check_changes():
                self._trigger_reload()

    def start_background(self) -> None:
        """在后台线程启动监控"""
        import threading
        self._running = True
        self._scan_files()

        def monitor():
            while self._running:
                time.sleep(self.interval)
                if self._check_changes():
                    self._trigger_reload()

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        logger.info(f"热重载后台监控已启动")

    def stop(self) -> None:
        """停止监控"""
        self._running = False

    def _scan_files(self) -> None:
        """扫描所有文件并记录修改时间"""
        self._file_mtimes.clear()
        for watch_dir in self.watch_dirs:
            if not watch_dir.exists():
                continue
            for py_file in watch_dir.rglob("*.py"):
                # 排除 __pycache__ 和 .venv
                if "__pycache__" in str(py_file) or ".venv" in str(py_file):
                    continue
                try:
                    self._file_mtimes[py_file] = py_file.stat().st_mtime
                except Exception:
                    pass

    def _check_changes(self) -> bool:
        """检查文件是否有变化"""
        for watch_dir in self.watch_dirs:
            if not watch_dir.exists():
                continue
            for py_file in watch_dir.rglob("*.py"):
                if "__pycache__" in str(py_file) or ".venv" in str(py_file):
                    continue
                try:
                    current_mtime = py_file.stat().st_mtime
                    if py_file not in self._file_mtimes:
                        # 新文件
                        self._file_mtimes[py_file] = current_mtime
                        logger.debug(f"新文件: {py_file}")
                        return True
                    if current_mtime != self._file_mtimes[py_file]:
                        # 文件修改
                        self._file_mtimes[py_file] = current_mtime
                        logger.info(f"文件修改: {py_file}")
                        return True
                except Exception:
                    pass
        return False

    def _trigger_reload(self) -> None:
        """触发重载"""
        if self._on_reload:
            self._on_reload()


def restart_application() -> None:
    """重启应用程序"""
    logger.info("正在重启应用...")

    # 获取当前执行的命令
    args = sys.argv.copy()

    # 在 Windows 上使用 start 命令避免控制台窗口闪烁
    if sys.platform == "win32":
        # 使用相同的 Python 解释器重启
        python = sys.executable
        subprocess.Popen([python] + args, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        os.execv(sys.executable, [sys.executable] + args)

    # 退出当前进程
    sys.exit(0)


def create_reloader_for_project(project_root: Path) -> HotReloader:
    """为项目创建热重载器"""
    watch_dirs = [
        project_root / "foundation",
        project_root / "core",
        project_root / "feature",
        project_root / "presentation",
    ]

    reloader = HotReloader(watch_dirs, interval=1.0)
    reloader.set_reload_callback(restart_application)

    return reloader
