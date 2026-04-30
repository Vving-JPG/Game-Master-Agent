"""GUI 入口"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from .main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Game Master Agent")
    app.setApplicationVersion("2.0.0")
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
