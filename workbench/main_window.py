# workbench/main_window.py
"""主窗口 — 三栏布局 + 顶部工具栏 + 底部控制台"""
import asyncio
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QToolBar, QLabel, QComboBox, QDoubleSpinBox,
    QStatusBar, QFileDialog, QMenuBar, QMenu,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction
import qasync

from workbench.widgets.resource_tree import ResourceTree
from workbench.widgets.editor_stack import EditorStack
from workbench.widgets.console_tabs import ConsoleTabs
from workbench.widgets.agent_status import AgentStatusPanel
from workbench.widgets.resource_monitor import ResourceMonitorPanel
from workbench.bridge.agent_bridge import AgentBridge


class MainWindow(QMainWindow):
    """WorkBench 主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Master Agent WorkBench")
        self.setMinimumSize(1200, 800)
        self.resize(1600, 900)

        # 当前项目根目录
        self.project_root = Path(".").resolve()

        # 初始化桥接层
        self.bridge = AgentBridge(project_root=str(self.project_root))

        self._setup_menubar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()
        self._setup_shortcuts()
        self._setup_bridge_connections()

        # 初始化后端
        self._init_backend()

    def _setup_menubar(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        # 打开文件夹
        act_open_folder = QAction("打开文件夹...", self)
        act_open_folder.setShortcut("Ctrl+O")
        act_open_folder.triggered.connect(self._on_open_folder)
        file_menu.addAction(act_open_folder)

        file_menu.addSeparator()

        # 退出
        act_exit = QAction("退出", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

    def _on_open_folder(self):
        """打开文件夹对话框"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择项目文件夹",
            str(self.project_root.parent),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self._switch_project(folder)

    def _setup_toolbar(self):
        """顶部工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # 运行控制按钮
        self.act_run = QAction("▶ 运行", self)
        self.act_run.setShortcut("F5")
        toolbar.addAction(self.act_run)

        self.act_pause = QAction("⏸ 暂停", self)
        self.act_pause.setShortcut("F6")
        toolbar.addAction(self.act_pause)

        self.act_step = QAction("⏯ 单步", self)
        self.act_step.setShortcut("F10")
        toolbar.addAction(self.act_step)

        self.act_reset = QAction("↺ 重置", self)
        toolbar.addAction(self.act_reset)

        toolbar.addSeparator()

        # 模型选择
        toolbar.addWidget(QLabel(" 模型: "))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["deepseek-chat", "deepseek-reasoner"])
        self.model_combo.setMinimumWidth(150)
        toolbar.addWidget(self.model_combo)

        # 温度
        toolbar.addWidget(QLabel(" 温度: "))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(0.7)
        self.temp_spin.setDecimals(1)
        toolbar.addWidget(self.temp_spin)

    def _setup_central_widget(self):
        """中央三栏布局 + 底部控制台"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # 主分割器: 上方三栏 + 下方控制台
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # 上方水平三栏
        h_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: 资源导航 (18%)
        self.resource_tree = ResourceTree()
        h_splitter.addWidget(self.resource_tree)

        # 中间: 编辑器 (52%)
        self.editor_stack = EditorStack()
        h_splitter.addWidget(self.editor_stack)

        # 右侧: 辅助面板 (30%)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.agent_status = AgentStatusPanel()
        self.resource_monitor = ResourceMonitorPanel()
        right_layout.addWidget(self.agent_status, stretch=1)
        right_layout.addWidget(self.resource_monitor, stretch=1)
        h_splitter.addWidget(right_panel)

        # 设置初始比例 18:52:30
        h_splitter.setSizes([290, 830, 480])

        # 下方: 底部控制台
        self.console_tabs = ConsoleTabs()
        self.console_tabs.setMaximumHeight(250)
        self.console_tabs.setMinimumHeight(100)

        main_splitter.addWidget(h_splitter)
        main_splitter.addWidget(self.console_tabs)
        main_splitter.setSizes([650, 250])

        layout.addWidget(main_splitter)

        # 连接信号: 资源树点击 → 编辑器打开文件
        self.resource_tree.file_selected.connect(self.editor_stack.open_file)

    def _setup_statusbar(self):
        """底部状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")

    def _setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+S 保存
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.editor_stack.save_current)
        self.addAction(save_action)

        # F5 刷新资源树
        refresh_action = QAction("刷新", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.resource_tree.refresh)
        self.addAction(refresh_action)

    def _setup_bridge_connections(self):
        """设置桥接层连接"""
        # 工具栏按钮 → 桥接层
        self.act_run.triggered.connect(lambda: asyncio.create_task(self.bridge.run_agent()))
        self.act_pause.triggered.connect(self.bridge.pause)
        self.act_step.triggered.connect(self.bridge.step)
        self.act_reset.triggered.connect(self.bridge.reset)

        # 桥接层信号 → UI 更新
        self.bridge.log_signal.connect(self._on_bridge_log)
        self.bridge.status_changed.connect(self._on_status_changed)
        self.bridge.turn_completed.connect(self._on_turn_completed)
        self.bridge.node_highlight.connect(self._on_node_highlight)
        self.bridge.error_occurred.connect(self._on_error)

        # 底部控制台信号
        self.console_tabs.inject_panel.inject_requested.connect(self.bridge.inject_command)
        self.console_tabs.force_tool.tool_execute_requested.connect(self._on_force_tool)

    def _init_backend(self):
        """初始化后端"""
        success = self.bridge.init_backend()
        if success:
            self.statusbar.showMessage("后端初始化成功")
        else:
            self.statusbar.showMessage("后端初始化失败")

    def _on_bridge_log(self, event_type: str, message: str):
        """处理桥接层日志"""
        colors = {
            "narrative": "#569cd6",
            "command": "#dcdcaa",
            "memory": "#6a9955",
            "error": "#f44747",
            "warning": "#ff9800",
            "info": "#d4d4d4",
        }
        self.console_tabs.exec_ctrl.append_log(f"[{event_type}] {message}", colors.get(event_type, "#d4d4d4"))

    def _on_status_changed(self, status: str):
        """处理状态变化"""
        self.console_tabs.exec_ctrl.set_status(status)
        self.agent_status.status_label.setText(f"状态: {status}")
        self.statusbar.showMessage(f"Agent {status}")

    def _on_turn_completed(self, turn_id: int, summary: str):
        """处理回合完成"""
        self.agent_status.turn_label.setText(f"回合: {turn_id}")
        status = "completed" if summary == "完成" else "current"
        self.console_tabs.turn_timeline.add_turn(turn_id, status, summary)

    def _on_node_highlight(self, node_id: str):
        """处理节点高亮"""
        self.console_tabs.flow_view.highlight_node(node_id)

    def _on_error(self, error: str):
        """处理错误"""
        self.statusbar.showMessage(f"错误: {error}")

    def _on_force_tool(self, tool_name: str, params: str):
        """处理强制工具执行"""
        result = self.bridge.force_tool(tool_name, params)
        self.console_tabs.force_tool.show_result(str(result))

    def _switch_project(self, folder: str):
        """切换到新项目"""
        new_root = Path(folder)

        # 验证项目结构
        if not self._validate_project(new_root):
            self.statusbar.showMessage(f"警告: 所选文件夹可能不是有效的 Game Master Agent 项目")

        self.project_root = new_root

        # 切换工作目录
        os.chdir(str(self.project_root))

        # 重新初始化资源树
        self.resource_tree.set_project_root(str(self.project_root))

        # 重新初始化桥接层
        self.bridge = AgentBridge(project_root=str(self.project_root))
        self._setup_bridge_connections()
        self._init_backend()

        # 更新窗口标题
        self.setWindowTitle(f"Game Master Agent WorkBench - {self.project_root.name}")

        self.statusbar.showMessage(f"已切换到项目: {self.project_root}")

    def _validate_project(self, root: Path) -> bool:
        """验证项目结构"""
        # 检查基本目录结构
        required_dirs = ["workspace", "prompts", "skills"]
        has_structure = all((root / d).exists() for d in required_dirs)

        # 检查是否有 src 目录（后端代码）
        has_src = (root / "src").exists()

        return has_structure or has_src
