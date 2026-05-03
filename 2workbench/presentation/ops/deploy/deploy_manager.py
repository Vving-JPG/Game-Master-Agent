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
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QLineEdit, QTextEdit,
    QGroupBox, QProgressBar, QTabWidget, QMessageBox,
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
        self._server_process = None
        self._server_thread = None
        self._http_server = None
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
        self._host_edit.setText("127.0.0.1")
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
        """打包项目为 ZIP"""
        import zipfile
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from presentation.project.manager import project_manager

        if not project_manager.is_open:
            self._pack_log.append("❌ 没有打开的项目")
            QMessageBox.warning(self, "提示", "请先打开一个项目")
            return

        path = project_manager.project_path
        name = project_manager.current_project.name if project_manager.current_project else "project"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存打包文件", f"{name}.zip", "ZIP (*.zip)")
        if not save_path:
            return

        self._deploy_status = "packaging"
        self._status_label.setText("📦 打包中...")
        self._progress.setVisible(True)
        self._progress.setValue(0)

        try:
            self._pack_log.append(f"📦 开始打包: {name}")
            self._pack_log.append(f"   项目路径: {path}")

            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                files = list(path.rglob("*"))
                total = len([f for f in files if f.is_file()])
                processed = 0

                for file in files:
                    if file.is_file() and not file.name.endswith('.pyc'):
                        arcname = file.relative_to(path.parent)
                        zf.write(file, arcname)
                        processed += 1
                        progress = int((processed / total) * 100) if total > 0 else 100
                        self._progress.setValue(progress)

            self._progress.setValue(100)
            self._deploy_status = "idle"
            self._status_label.setText("✅ 打包完成")
            self._pack_log.append(f"✅ 打包完成: {save_path}")
            logger.info(f"项目已打包到: {save_path}")
            QMessageBox.information(self, "打包成功", f"项目已打包到:\n{save_path}")
        except Exception as e:
            self._deploy_status = "error"
            self._status_label.setText("❌ 打包失败")
            self._pack_log.append(f"❌ 打包失败: {e}")
            logger.error(f"打包失败: {e}")
            QMessageBox.critical(self, "打包失败", str(e))

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
                    self._http_server = ThreadedHTTPServer((host, port), RequestHandler)
                    logger.info(f"HTTP 服务启动: http://{host}:{port}")
                    self._http_server.serve_forever()

                self._server_thread = threading.Thread(target=run_server, daemon=True)
                self._server_thread.start()
            else:
                self._server_process = subprocess.Popen(
                    [sys.executable, str(script_path), "--host", host, "--port", str(port)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # 启动进程监控线程，防止进程挂起导致UI冻结
                def monitor_process():
                    try:
                        self._server_process.wait(timeout=10)
                        # 如果进程正常结束，记录日志
                        if self._server_process.returncode != 0:
                            stderr = self._server_process.stderr.read().decode('utf-8', errors='ignore')
                            logger.error(f"服务进程异常退出，返回码: {self._server_process.returncode}, 错误: {stderr}")
                    except subprocess.TimeoutExpired:
                        # 进程正常运行超过10秒，视为启动成功
                        logger.info("服务进程已稳定运行")
                    except Exception as e:
                        logger.error(f"进程监控异常: {e}")

                threading.Thread(target=monitor_process, daemon=True).start()

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
        # 停止子进程
        if self._server_process:
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
            self._server_process = None

        # 停止内嵌服务器
        if hasattr(self, '_http_server') and self._http_server:
            self._http_server.shutdown()
            self._http_server = None

        self._deploy_status = "idle"
        self._status_label.setText("⏹ 已停止")
        self._status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self._run_status.setText("已停止")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        logger.info("服务已停止")
