# workbench/widgets/resource_monitor.py
"""资源监控面板"""
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QProgressBar


class ResourceMonitorPanel(QGroupBox):
    """资源监控面板"""

    def __init__(self):
        super().__init__("📊 资源监控")
        layout = QVBoxLayout(self)
        self.memory_label = QLabel("内存: 0 MB")
        self.cpu_label = QLabel("CPU: 0%")
        self.token_bar = QProgressBar()
        self.token_bar.setRange(0, 100)
        self.token_bar.setValue(0)
        self.token_bar.setFormat("Token 用量: %v%")
        for w in [self.memory_label, self.cpu_label, self.token_bar]:
            layout.addWidget(w)
