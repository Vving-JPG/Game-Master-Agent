# wb_entry.py
"""PyInstaller 打包入口"""
import sys
import os

# 确保项目根目录在 Python 路径中
if hasattr(sys, '_MEIPASS'):
    # PyInstaller 打包后的运行环境
    project_root = sys._MEIPASS
else:
    # 开发环境
    project_root = os.path.dirname(os.path.abspath(__file__))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from workbench.app import main

if __name__ == "__main__":
    main()
