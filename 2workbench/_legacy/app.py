# workbench/app.py
"""Game Master Agent WorkBench — 应用入口"""
import sys
import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import qasync

from .main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Game Master Agent")
    app.setApplicationVersion("2.0")

    # 加载暗色主题
    try:
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        theme_path = os.path.join(script_dir, "styles", "dark_theme.qss")
        with open(theme_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("警告: 暗色主题文件未找到")

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 使用 qasync 运行事件循环
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
