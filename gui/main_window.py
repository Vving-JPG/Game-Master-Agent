"""主窗口"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QLabel, QPushButton,
    QToolBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from .api_client import APIClient
from .widgets.resource_tree import ResourceTree
from .widgets.editor_tabs import EditorTabs
from .widgets.agent_panel import AgentPanel
from .widgets.event_log import EventLog
from .widgets.chat_debug import ChatDebug


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.api = APIClient(base_url="http://localhost:8000")
        self.init_ui()
        self.init_timer()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("Game Master Agent")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中心部件
        central = QWidget()
        self.setCentralWidget(central)
        
        # 主布局
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建分割器
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.bottom_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 左侧资源树
        self.resource_tree = ResourceTree(self.api)
        self.resource_tree.file_selected.connect(self.open_file)
        
        # 中间编辑器
        self.editor_tabs = EditorTabs(self.api)
        
        # 右侧 Agent 面板
        self.agent_panel = AgentPanel(self.api)
        
        # 底部区域（事件日志 + 对话调试）
        self.event_log = EventLog()
        self.chat_debug = ChatDebug(self.api)
        
        # 组装底部区域
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)
        
        self.bottom_tabs = self.create_bottom_tabs()
        bottom_layout.addWidget(self.bottom_tabs)
        
        # 组装主分割器
        self.main_splitter.addWidget(self.resource_tree)
        self.main_splitter.addWidget(self.editor_tabs)
        self.main_splitter.addWidget(self.agent_panel)
        
        self.main_splitter.setSizes([250, 800, 300])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 0)
        
        # 垂直分割器（主区域 + 底部）
        self.bottom_splitter.setOrientation(Qt.Orientation.Vertical)
        self.bottom_splitter.addWidget(self.main_splitter)
        self.bottom_splitter.addWidget(bottom_widget)
        self.bottom_splitter.setSizes([600, 250])
        
        layout.addWidget(self.bottom_splitter)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.create_statusbar()
        
        # 连接 SSE 事件
        self.api.event_received.connect(self.event_log.append_event)
        self.api.event_received.connect(self.agent_panel.handle_event)
        
    def create_bottom_tabs(self):
        """创建底部标签页"""
        from PyQt6.QtWidgets import QTabWidget
        
        tabs = QTabWidget()
        tabs.addTab(self.event_log, "事件日志")
        tabs.addTab(self.chat_debug, "对话调试")
        return tabs
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 连接按钮
        self.connect_action = QAction("🔄 连接", self)
        self.connect_action.triggered.connect(self.toggle_connection)
        toolbar.addAction(self.connect_action)
        
        toolbar.addSeparator()
        
        # 刷新按钮
        refresh_action = QAction("🔄 刷新", self)
        refresh_action.triggered.connect(self.refresh_all)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # Agent 控制按钮
        pause_action = QAction("⏸️ 暂停", self)
        pause_action.triggered.connect(self.pause_agent)
        toolbar.addAction(pause_action)
        
        resume_action = QAction("▶️ 继续", self)
        resume_action.triggered.connect(self.resume_agent)
        toolbar.addAction(resume_action)
        
        reset_action = QAction("🔄 重置", self)
        reset_action.triggered.connect(self.reset_agent)
        toolbar.addAction(reset_action)
        
        toolbar.addSeparator()
        
        # Pack 操作
        export_action = QAction("📦 导出", self)
        export_action.triggered.connect(self.export_pack)
        toolbar.addAction(export_action)
        
        import_action = QAction("📥 导入", self)
        import_action.triggered.connect(self.import_pack)
        toolbar.addAction(import_action)
        
    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.status_label = QLabel("未连接")
        self.statusbar.addWidget(self.status_label)
        
        self.agent_state_label = QLabel("Agent: 未知")
        self.statusbar.addPermanentWidget(self.agent_state_label)
        
    def init_timer(self):
        """初始化定时器"""
        # 状态轮询定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.poll_status)
        self.status_timer.start(2000)  # 2秒轮询一次
        
        # 首次连接
        QTimer.singleShot(500, self.connect_to_server)
        
    def connect_to_server(self):
        """连接到服务器"""
        try:
            if self.api.check_health():
                self.status_label.setText("✅ 已连接")
                self.connect_action.setText("断开")
                self.api.start_sse_stream()
                self.refresh_all()
            else:
                self.status_label.setText("❌ 连接失败")
        except Exception as e:
            self.status_label.setText(f"❌ 错误: {e}")
            
    def toggle_connection(self):
        """切换连接状态"""
        if self.api.sse_running:
            self.api.stop_sse_stream()
            self.status_label.setText("未连接")
            self.connect_action.setText("🔄 连接")
        else:
            self.connect_to_server()
            
    def poll_status(self):
        """轮询 Agent 状态"""
        try:
            status = self.api.get_status()
            state = status.get("state", "unknown")
            self.agent_state_label.setText(f"Agent: {state}")
            self.agent_panel.update_status(status)
        except Exception:
            self.agent_state_label.setText("Agent: 离线")
            
    def refresh_all(self):
        """刷新所有数据"""
        self.resource_tree.refresh()
        self.agent_panel.refresh()
        
    def open_file(self, path: str, file_type: str):
        """打开文件"""
        self.editor_tabs.open_file(path, file_type)
        
    def pause_agent(self):
        """暂停 Agent"""
        try:
            self.api.control_agent("pause")
            self.statusbar.showMessage("Agent 已暂停", 3000)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"暂停失败: {e}")
            
    def resume_agent(self):
        """继续 Agent"""
        try:
            self.api.control_agent("resume")
            self.statusbar.showMessage("Agent 已继续", 3000)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"继续失败: {e}")
            
    def reset_agent(self):
        """重置 Agent"""
        reply = QMessageBox.question(
            self, "确认", "确定要重置 Agent 会话吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api.reset_session()
                self.statusbar.showMessage("Agent 已重置", 3000)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重置失败: {e}")
                
    def export_pack(self):
        """导出 Pack"""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 Pack", "agent-pack.zip", "ZIP Files (*.zip)"
        )
        if file_path:
            try:
                self.api.export_pack(file_path)
                self.statusbar.showMessage(f"已导出到: {file_path}", 5000)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导出失败: {e}")
                
    def import_pack(self):
        """导入 Pack"""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入 Pack", "", "ZIP Files (*.zip)"
        )
        if file_path:
            try:
                result = self.api.import_pack(file_path)
                self.statusbar.showMessage(f"导入成功: {len(result.get('files', []))} 个文件", 5000)
                self.refresh_all()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入失败: {e}")
                
    def closeEvent(self, event):
        """关闭事件"""
        self.api.stop_sse_stream()
        event.accept()
