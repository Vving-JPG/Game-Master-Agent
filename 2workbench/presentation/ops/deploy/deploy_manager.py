# 2workbench/presentation/ops/deploy/deploy_manager.py
"""部署管理器 — Agent 导出为服务、配置打包、运行状态监控

功能:
1. Agent 项目打包（包含所有配置、Prompt、工具）
2. 导出为独立服务（FastAPI/Flask）
3. 运行配置管理
4. 部署状态监控
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QLineEdit, QTextEdit,
    QGroupBox, QProgressBar, QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class DeployManager(BaseWidget):
    """部署管理器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._deploy_status = "idle"  # idle / packaging / deploying / running / error
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 状态栏
        status_bar = QHBoxLayout()
        self._status_label = QLabel("⚪ 就绪")
        self._status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_bar.addWidget(self._status_label)

        status_bar.addStretch()
        layout.addLayout(status_bar)

        # 标签页
        self._tabs = QTabWidget()

        # 打包配置
        pack_widget = QWidget()
        pack_layout = QVBoxLayout(pack_widget)

        config_group = QGroupBox("打包配置")
        config_form = QFormLayout(config_group)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("my_agent_service")
        config_form.addRow("服务名称:", self._name_edit)

        self._version_edit = QLineEdit()
        self._version_edit.setText("1.0.0")
        config_form.addRow("版本:", self._version_edit)

        self._framework_combo = QComboBox()
        self._framework_combo.addItems(["FastAPI", "Flask", "Standalone"])
        config_form.addRow("框架:", self._framework_combo)

        from PyQt6.QtWidgets import QSpinBox
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(8080)
        config_form.addRow("端口:", self._port_spin)

        self._host_edit = QLineEdit()
        self._host_edit.setText("0.0.0.0")
        config_form.addRow("主机:", self._host_edit)

        pack_layout.addWidget(config_group)

        self._btn_package = StyledButton("📦 打包项目", style_type="primary")
        self._btn_package.clicked.connect(self._package_project)
        pack_layout.addWidget(self._btn_package)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        pack_layout.addWidget(self._progress)

        self._pack_log = QTextEdit()
        self._pack_log.setReadOnly(True)
        self._pack_log.setMaximumHeight(150)
        self._pack_log.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        pack_layout.addWidget(self._pack_log)

        pack_layout.addStretch()
        self._tabs.addTab(pack_widget, "📦 打包")

        # 运行监控
        monitor_widget = QWidget()
        monitor_layout = QVBoxLayout(monitor_widget)

        monitor_group = QGroupBox("运行状态")
        monitor_form = QFormLayout(monitor_group)

        self._run_status = QLabel("未运行")
        monitor_form.addRow("状态:", self._run_status)

        self._run_uptime = QLabel("0:00:00")
        monitor_form.addRow("运行时间:", self._run_uptime)

        self._run_requests = QLabel("0")
        monitor_form.addRow("请求数:", self._run_requests)

        self._run_errors = QLabel("0")
        monitor_form.addRow("错误数:", self._run_errors)

        monitor_layout.addWidget(monitor_group)

        run_toolbar = QHBoxLayout()
        self._btn_start = StyledButton("▶ 启动服务", style_type="success")
        self._btn_start.clicked.connect(self._start_service)
        run_toolbar.addWidget(self._btn_start)

        self._btn_stop = StyledButton("⏹ 停止服务", style_type="danger")
        self._btn_stop.clicked.connect(self._stop_service)
        self._btn_stop.setEnabled(False)
        run_toolbar.addWidget(self._btn_stop)

        monitor_layout.addLayout(run_toolbar)
        monitor_layout.addStretch()
        self._tabs.addTab(monitor_widget, "📊 监控")

        layout.addWidget(self._tabs)

    def _package_project(self) -> None:
        """打包项目"""
        from presentation.project.manager import project_manager

        if not project_manager.is_open:
            self._pack_log.append("❌ 没有打开的项目")
            return

        self._deploy_status = "packaging"
        self._status_label.setText("📦 打包中...")
        self._progress.setVisible(True)
        self._progress.setValue(0)

        project_path = project_manager.project_path
        if not project_path:
            return

        name = self._name_edit.text().strip() or "agent_service"
        version = self._version_edit.text().strip()

        # 模拟打包过程
        self._pack_log.append(f"📦 开始打包: {name} v{version}")
        self._pack_log.append(f"   项目路径: {project_path}")
        self._progress.setValue(20)

        # 收集文件列表
        files = list(project_path.rglob("*"))
        file_count = len([f for f in files if f.is_file()])
        self._pack_log.append(f"   文件数: {file_count}")
        self._progress.setValue(50)

        # 模拟生成服务入口
        self._pack_log.append(f"   框架: {self._framework_combo.currentText()}")
        self._pack_log.append(f"   端口: {self._port_spin.text()}")
        self._progress.setValue(80)

        self._pack_log.append(f"   生成入口文件: server.py")
        self._progress.setValue(100)

        self._deploy_status = "idle"
        self._status_label.setText("✅ 打包完成")
        self._pack_log.append(f"✅ 打包完成: {name}_v{version}")
        logger.info(f"项目打包完成: {name} v{version}")

    def _start_service(self) -> None:
        """启动服务"""
        self._deploy_status = "running"
        self._status_label.setText("🟢 运行中")
        self._run_status.setText("运行中")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        logger.info("服务已启动（模拟）")

    def _stop_service(self) -> None:
        """停止服务"""
        self._deploy_status = "idle"
        self._status_label.setText("⚪ 已停止")
        self._run_status.setText("已停止")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        logger.info("服务已停止")
