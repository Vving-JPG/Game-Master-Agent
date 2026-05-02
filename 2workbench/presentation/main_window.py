"""主窗口 — 三栏布局 IDE 界面

布局:
┌─────────────────────────────────────────────────────┐
│ 菜单栏 (File/Edit/View/Agent/Tools/Help)            │
├─────────────────────────────────────────────────────┤
│ 工具栏 (新建/打开/保存/运行/调试/主题切换)           │
├──────────┬──────────────────────────┬───────────────┤
│ 左侧面板  │     中央编辑区           │  右侧面板     │
│ (资源树)  │  (图编辑器/代码/控制台)  │ (属性/状态)   │
│          │                          │               │
│ 240px    │     flex                 │   300px       │
├──────────┴──────────────────────────┴───────────────┤
│ 状态栏 (连接状态/Agent状态/模型/主题)                │
└─────────────────────────────────────────────────────┘

从 _legacy/main_window.py 重构。
"""
from __future__ import annotations

import json
from typing import Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QToolBar, QStatusBar, QTabWidget,
    QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QSizePolicy
from PyQt6.QtGui import QAction

from foundation.event_bus import event_bus, Event
from foundation.config import settings
from foundation.logger import get_logger
from presentation.theme.manager import theme_manager
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


class LeftPanel(BaseWidget):
    """左侧面板 — 资源树 + Agent 项目浏览器"""

    # 信号：文件被双击打开
    file_open_requested = pyqtSignal(str)  # 文件路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 设置面板最小宽度
        self.setMinimumWidth(200)

        # Agent 项目浏览器 — 使用 QTreeWidget
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabel("📂 Agent 项目浏览器")
        self.project_tree.setColumnCount(1)
        self.project_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # 确保树控件可见
        self.project_tree.setVisible(True)
        
        # 连接双击事件
        self.project_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # 设置样式
        self.project_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #252526;
                color: #cccccc;
                border: none;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px 8px;
            }
            QTreeWidget::item:selected {
                background-color: #094771;
            }
            QTreeWidget::item:hover {
                background-color: #2a2d2e;
            }
            QHeaderView::section {
                background-color: #333333;
                color: #cccccc;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        
        layout.addWidget(self.project_tree)
        print(f"[LeftPanel] UI 初始化完成")
    
    def _on_item_double_clicked(self, item, column):
        """处理双击事件 — 打开文件"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path:
            from pathlib import Path
            path = Path(file_path)
            if path.is_file():
                print(f"[LeftPanel] 双击打开文件: {file_path}")
                self.file_open_requested.emit(file_path)
            else:
                # 文件夹则展开/折叠
                if item.isExpanded():
                    self.project_tree.collapseItem(item)
                else:
                    self.project_tree.expandItem(item)
    
    def load_project_tree(self, project_path: str):
        """加载项目资源树"""
        from pathlib import Path
        from PyQt6.QtWidgets import QTreeWidgetItem
        
        self.project_tree.clear()
        
        if not project_path:
            print(f"[LeftPanel] 项目路径为空")
            return
        
        root = Path(project_path)
        if not root.exists():
            print(f"[LeftPanel] 项目路径不存在: {project_path}")
            return
        
        project_name = root.name
        print(f"[LeftPanel] 加载项目树: {project_name} ({root})")
        
        # 创建根节点
        root_item = QTreeWidgetItem(self.project_tree)
        root_item.setText(0, f"📁 {project_name}")
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(root))
        
        # 添加项目文件和文件夹
        file_count = self._add_tree_items(root_item, root)
        print(f"[LeftPanel] 添加了 {file_count} 个文件/文件夹")
        
        self.project_tree.expandItem(root_item)
        self.project_tree.update()  # 强制刷新
    
    def _add_tree_items(self, parent_item, path: Path) -> int:
        """递归添加树节点，返回添加的文件/文件夹数量"""
        from pathlib import Path
        from PyQt6.QtWidgets import QTreeWidgetItem
        
        count = 0
        try:
            items = list(path.iterdir())
            print(f"[LeftPanel] 扫描目录: {path}, 找到 {len(items)} 个条目")
            
            for item in sorted(items, key=lambda x: (x.is_file(), x.name)):
                tree_item = QTreeWidgetItem(parent_item)
                tree_item.setData(0, Qt.ItemDataRole.UserRole, str(item))
                
                if item.is_dir():
                    tree_item.setText(0, f"📁 {item.name}")
                    # 递归添加子目录
                    count += 1 + self._add_tree_items(tree_item, item)
                else:
                    # 根据文件类型设置图标
                    icon = self._get_file_icon(item.name)
                    tree_item.setText(0, f"{icon} {item.name}")
                    count += 1
        except PermissionError as e:
            print(f"[LeftPanel] 权限错误: {e}")
        except Exception as e:
            print(f"[LeftPanel] 添加树节点错误: {e}")
        
        return count
    
    def _get_file_icon(self, filename: str) -> str:
        """根据文件名返回图标"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        icons = {
            'json': '📋',
            'md': '📝',
            'py': '🐍',
            'txt': '📄',
            'yaml': '⚙️',
            'yml': '⚙️',
            'db': '🗄️',
        }
        
        return icons.get(ext, '📄')


class CenterPanel(BaseWidget):
    """中央编辑区 — 多标签页编辑器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close)
        layout.addWidget(self.tab_widget)

        # 默认欢迎页
        welcome = QLabel(
            "🎮 Game Master Agent IDE\n\n"
            "欢迎使用 Agent 集成开发环境\n\n"
            "请通过 File > New Agent Project 创建新项目\n"
            "或 File > Open 打开已有项目"
        )
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setStyleSheet("font-size: 16px; color: #858585;")
        self.tab_widget.addTab(welcome, "Welcome")

        # 编辑器标签页（默认隐藏，打开项目后显示）
        self._graph_editor = None
        self._prompt_editor = None
        self._tool_manager = None

    def _on_tab_close(self, index: int) -> None:
        """关闭标签页"""
        # 如果只有一个标签页，不关闭（至少保留一个）
        if self.tab_widget.count() <= 1:
            return
        
        # 获取要关闭的 widget
        widget = self.tab_widget.widget(index)
        
        # 从标签页中移除
        self.tab_widget.removeTab(index)
        
        # 如果是编辑器标签页，清理引用
        if widget == self._graph_editor:
            self._graph_editor = None
        elif widget == self._prompt_editor:
            self._prompt_editor = None
        elif widget == self._tool_manager:
            self._tool_manager = None

    def add_tab(self, widget: QWidget, title: str) -> int:
        """添加标签页"""
        return self.tab_widget.addTab(widget, title)

    def current_tab(self) -> QWidget | None:
        """获取当前标签页"""
        return self.tab_widget.currentWidget()

    def show_graph_editor(self, graph_data: dict | None = None) -> None:
        """显示图编辑器标签页"""
        from presentation.editor.graph_editor import GraphEditorWidget
        if self._graph_editor is None:
            self._graph_editor = GraphEditorWidget()
            self.tab_widget.addTab(self._graph_editor, "📊 图编辑器")
        if graph_data:
            self._graph_editor.load_graph(graph_data)
        idx = self.tab_widget.indexOf(self._graph_editor)
        self.tab_widget.setCurrentIndex(idx)

    def show_prompt_editor(self, prompts: dict[str, str] | None = None) -> None:
        """显示 Prompt 管理器标签页"""
        from presentation.editor.prompt_editor import PromptEditorWidget
        if self._prompt_editor is None:
            self._prompt_editor = PromptEditorWidget()
            self.tab_widget.addTab(self._prompt_editor, "📝 Prompt")
        if prompts:
            self._prompt_editor.load_prompts(prompts)
        idx = self.tab_widget.indexOf(self._prompt_editor)
        self.tab_widget.setCurrentIndex(idx)

    def show_tool_manager(self, right_panel=None) -> None:
        """显示工具管理器标签页"""
        from presentation.editor.tool_manager import ToolManagerWidget
        if self._tool_manager is None:
            self._tool_manager = ToolManagerWidget()
            self.tab_widget.addTab(self._tool_manager, "🔧 工具")
            # 连接工具选中信号到右侧面板
            if right_panel:
                self._tool_manager.tool_selected.connect(right_panel.show_tool_properties)
        idx = self.tab_widget.indexOf(self._tool_manager)
        self.tab_widget.setCurrentIndex(idx)


class RightPanel(BaseWidget):
    """右侧面板 — 属性编辑器 + 状态监控"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        from PyQt6.QtWidgets import QFormLayout, QLineEdit, QTextEdit, QComboBox, QCheckBox, QGroupBox, QScrollArea, QWidget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 属性面板
        self.props_scroll = QScrollArea()
        self.props_scroll.setWidgetResizable(True)
        self.props_container = QWidget()
        self.props_layout = QFormLayout(self.props_container)
        self.props_layout.setSpacing(8)
        self.props_layout.setContentsMargins(12, 12, 12, 12)
        
        # 添加默认提示
        self.props_hint = QLabel("选择一个节点或工具查看属性")
        self.props_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.props_hint.setStyleSheet("color: #858585; font-size: 13px; padding: 20px;")
        self.props_layout.addRow(self.props_hint)
        
        self.props_scroll.setWidget(self.props_container)
        self.tab_widget.addTab(self.props_scroll, "属性")

        # Agent 状态面板
        self.status_widget = QWidget()
        self.status_layout = QVBoxLayout(self.status_widget)
        self.status_layout.setSpacing(10)
        self.status_layout.setContentsMargins(12, 12, 12, 12)
        
        # Agent 状态组
        self.agent_status_group = QGroupBox("Agent 状态")
        self.agent_status_layout = QFormLayout(self.agent_status_group)
        self.agent_status_label = QLabel("未加载")
        self.agent_status_layout.addRow("状态:", self.agent_status_label)
        self.status_layout.addWidget(self.agent_status_group)
        
        # 回合信息组
        self.turn_info_group = QGroupBox("回合信息")
        self.turn_info_layout = QFormLayout(self.turn_info_group)
        self.turn_num_label = QLabel("0")
        self.turn_event_label = QLabel("-")
        self.turn_info_layout.addRow("回合数:", self.turn_num_label)
        self.turn_info_layout.addRow("当前事件:", self.turn_event_label)
        self.status_layout.addWidget(self.turn_info_group)
        
        # Feature 状态组
        self.feature_status_group = QGroupBox("Feature 状态")
        self.feature_status_layout = QVBoxLayout(self.feature_status_group)
        self.feature_list = QLabel("未启用任何 Feature")
        self.feature_status_layout.addWidget(self.feature_list)
        self.status_layout.addWidget(self.feature_status_group)
        
        self.status_layout.addStretch()
        self.tab_widget.addTab(self.status_widget, "状态")
    
    def show_node_properties(self, node_data: dict):
        """显示节点属性"""
        # 清除现有内容
        while self.props_layout.count():
            item = self.props_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        from PyQt6.QtWidgets import QLineEdit, QTextEdit, QLabel
        
        # 节点名称
        name_label = QLabel("节点名称:")
        name_value = QLabel(node_data.get("name", "未知"))
        name_value.setStyleSheet("font-weight: bold; color: #4ec9b0;")
        self.props_layout.addRow(name_label, name_value)
        
        # 节点类型
        type_label = QLabel("类型:")
        type_value = QLabel(node_data.get("type", "未知"))
        self.props_layout.addRow(type_label, type_value)
        
        # 描述
        if "description" in node_data:
            desc_label = QLabel("描述:")
            desc_value = QLabel(node_data["description"])
            desc_value.setWordWrap(True)
            desc_value.setStyleSheet("color: #cccccc;")
            self.props_layout.addRow(desc_label, desc_value)
        
        # 配置参数
        if "config" in node_data:
            config_label = QLabel("配置:")
            config_value = QTextEdit(json.dumps(node_data["config"], ensure_ascii=False, indent=2))
            config_value.setReadOnly(True)
            config_value.setMaximumHeight(100)
            self.props_layout.addRow(config_label, config_value)
    
    def show_tool_properties(self, tool_data: dict):
        """显示工具属性"""
        # 清除现有内容
        while self.props_layout.count():
            item = self.props_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        from PyQt6.QtWidgets import QLineEdit, QTextEdit, QLabel, QCheckBox
        
        # 工具名称
        name_label = QLabel("工具名称:")
        name_value = QLabel(tool_data.get("name", "未知"))
        name_value.setStyleSheet("font-weight: bold; color: #dcdcaa;")
        self.props_layout.addRow(name_label, name_value)
        
        # 描述
        if "description" in tool_data:
            desc_label = QLabel("描述:")
            desc_value = QLabel(tool_data["description"])
            desc_value.setWordWrap(True)
            desc_value.setStyleSheet("color: #cccccc;")
            self.props_layout.addRow(desc_label, desc_value)
        
        # 参数 Schema
        if "parameters" in tool_data:
            params_label = QLabel("参数 Schema:")
            params_value = QTextEdit(json.dumps(tool_data["parameters"], ensure_ascii=False, indent=2))
            params_value.setReadOnly(True)
            params_value.setMaximumHeight(150)
            self.props_layout.addRow(params_label, params_value)
        
        # 启用状态
        enabled = tool_data.get("enabled", True)
        enabled_checkbox = QCheckBox("启用")
        enabled_checkbox.setChecked(enabled)
        enabled_checkbox.setEnabled(False)  # 只读显示
        self.props_layout.addRow("状态:", enabled_checkbox)
    
    def update_agent_status(self, status: str, turn: int = 0, event: str = ""):
        """更新 Agent 状态显示"""
        self.agent_status_label.setText(status)
        self.agent_status_label.setStyleSheet(
            "color: #4ec9b0;" if status == "运行中" else "color: #858585;"
        )
        self.turn_num_label.setText(str(turn))
        self.turn_event_label.setText(event if event else "-")
    
    def update_feature_status(self, features: list):
        """更新 Feature 状态显示"""
        if features:
            feature_text = "\n".join([f"✅ {f}" for f in features])
            self.feature_list.setText(feature_text)
        else:
            self.feature_list.setText("未启用任何 Feature")


class MainWindow(QMainWindow):
    """主窗口"""
    
    # 信号定义
    open_project_requested = pyqtSignal(str, str)  # (project_path, project_root)
    create_project_requested = pyqtSignal(str, str, str, str)  # (name, template, directory, project_root)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Master Agent IDE")
        self.setMinimumSize(1200, 800)
        self.resize(1600, 1000)

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_eventbus()
        
        # 连接信号
        self.open_project_requested.connect(self._do_open_project)
        self.create_project_requested.connect(self._do_create_project)

        # 应用主题
        theme_manager.apply("dark")

        # 启动 HTTP 控制服务器
        self._start_http_server()

        # 检查是否有已打开的项目，自动加载
        self._load_current_project_if_exists()

        logger.info("主窗口初始化完成")

    def _load_current_project_if_exists(self) -> None:
        """如果 project_manager 已有打开的项目，自动加载"""
        from presentation.project.manager import project_manager

        if project_manager._current_project and project_manager._project_path:
            logger.info(f"检测到已打开的项目: {project_manager._current_project.name}")
            try:
                # 关闭欢迎标签页
                if self.center_panel.tab_widget.count() > 0:
                    welcome_widget = self.center_panel.tab_widget.widget(0)
                    if isinstance(welcome_widget, QLabel):
                        self.center_panel.tab_widget.removeTab(0)

                # 加载图编辑器
                graph = project_manager.load_graph()
                self.center_panel.show_graph_editor(graph)

                # 加载 Prompt 编辑器
                prompts = {}
                for name in project_manager.list_prompts():
                    prompts[name] = project_manager.load_prompt(name)
                self.center_panel.show_prompt_editor(prompts)

                # 加载工具管理器
                self.center_panel.show_tool_manager(self.right_panel)

                # 加载左侧资源树
                self.left_panel.load_project_tree(str(project_manager._project_path))

                self.statusBar().showMessage(f"项目已加载: {project_manager._current_project.name}", 3000)
                logger.info(f"项目加载完成: {project_manager._current_project.name}")
            except Exception as e:
                logger.error(f"加载项目失败: {e}")
                self.statusBar().showMessage(f"加载项目失败: {e}", 3000)
    
    def _do_create_project(self, name: str, template: str, directory: str, project_root: str):
        """在主线程中创建新项目"""
        print(f"[MainWindow] 开始创建项目: {name} (模板: {template})")
        from presentation.project.manager import project_manager
        from pathlib import Path

        try:
            # 创建项目
            full_dir = Path(project_root) / directory
            full_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"[MainWindow] 调用 project_manager.create_project...")
            path = project_manager.create_project(name, template=template, directory=str(full_dir))
            print(f"[MainWindow] 项目已创建: {path}")
            
            # 自动打开项目
            self._do_open_project(str(path.relative_to(Path(project_root))), project_root)
            
            self.statusBar().showMessage(f"项目已创建并打开: {name}", 3000)
            print(f"[MainWindow] 项目创建完成!")
        except Exception as e:
            import traceback
            self.statusBar().showMessage(f"创建项目失败: {str(e)}", 3000)
            print(f"[MainWindow] Error: {e}")
            print(traceback.format_exc())

    def _do_open_project(self, project_path: str, project_root: str):
        """在主线程中打开项目"""
        print(f"[MainWindow] 开始打开项目: {project_path}")
        from presentation.project.manager import project_manager
        from pathlib import Path

        full_path = Path(project_root) / project_path
        print(f"[MainWindow] 完整路径: {full_path}")
        
        if not full_path.exists():
            print(f"[MainWindow] 项目不存在!")
            self.statusBar().showMessage(f"项目不存在: {project_path}", 3000)
            return

        try:
            # 打开项目
            print(f"[MainWindow] 调用 project_manager.open_project...")
            config = project_manager.open_project(full_path)
            print(f"[MainWindow] 项目已打开: {config.name}")
            
            # 关闭欢迎标签页（第一个标签页）
            print(f"[MainWindow] 关闭欢迎标签页...")
            if self.center_panel.tab_widget.count() > 0:
                welcome_widget = self.center_panel.tab_widget.widget(0)
                if isinstance(welcome_widget, QLabel):
                    self.center_panel.tab_widget.removeTab(0)
                    print(f"[MainWindow] 欢迎标签页已关闭")

            # 加载编辑器
            print(f"[MainWindow] 加载图编辑器...")
            graph = project_manager.load_graph()
            self.center_panel.show_graph_editor(graph)
            print(f"[MainWindow] 图编辑器已加载: {len(graph.get('nodes', []))} 节点")

            print(f"[MainWindow] 加载 Prompt 编辑器...")
            prompts = {}
            for name in project_manager.list_prompts():
                prompts[name] = project_manager.load_prompt(name)
            self.center_panel.show_prompt_editor(prompts)
            print(f"[MainWindow] Prompt 编辑器已加载: {len(prompts)} prompts")

            print(f"[MainWindow] 加载工具管理器...")
            self.center_panel.show_tool_manager(self.right_panel)
            print(f"[MainWindow] 工具管理器已加载")

            # 加载左侧资源树
            print(f"[MainWindow] 加载资源树...")
            print(f"[MainWindow] left_panel 可见: {self.left_panel.isVisible()}")
            print(f"[MainWindow] left_panel 宽度: {self.left_panel.width()}")
            self.left_panel.setVisible(True)  # 确保面板可见
            self.left_panel.load_project_tree(str(full_path))
            print(f"[MainWindow] 资源树已加载")
            
            # 更新右侧面板的 Feature 状态
            print(f"[MainWindow] 更新 Feature 状态...")
            from feature.registry import feature_registry
            features = feature_registry.list_features()
            self.right_panel.update_feature_status(features)
            print(f"[MainWindow] Feature 状态已更新: {len(features)} 个")

            self.statusBar().showMessage(f"项目已打开: {config.name}", 3000)
            print(f"[MainWindow] 项目打开完成!")
        except Exception as e:
            import traceback
            self.statusBar().showMessage(f"打开项目失败: {str(e)}", 3000)
            print(f"[MainWindow] Error: {e}")
            print(traceback.format_exc())

    def _setup_ui(self) -> None:
        """设置三栏布局"""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 三栏分割器
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧面板
        self.left_panel = LeftPanel()
        self.left_panel.file_open_requested.connect(self._on_file_open)
        self._splitter.addWidget(self.left_panel)

        # 中央编辑区
        self.center_panel = CenterPanel()
        self._splitter.addWidget(self.center_panel)

        # 右侧面板
        self.right_panel = RightPanel()
        self._splitter.addWidget(self.right_panel)

        # 设置宽度比例
        self._splitter.setSizes([240, 900, 300])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)

        layout.addWidget(self._splitter)

    def _setup_menu(self) -> None:
        """设置菜单栏"""
        menubar = self.menuBar()

        # File 菜单
        file_menu = menubar.addMenu("文件(&F)")

        new_action = QAction("新建 Agent 项目(&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)

        open_action = QAction("打开项目(&O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_action)

        save_action = QAction("保存(&S)", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit 菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        undo_action = QAction("撤销(&Z)", self)
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&Y)", self)
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)

        # View 菜单
        view_menu = menubar.addMenu("视图(&V)")

        toggle_left = QAction("左侧面板", self, checkable=True, checked=True)
        toggle_left.triggered.connect(
            lambda checked: self.left_panel.setVisible(checked)
        )
        view_menu.addAction(toggle_left)

        toggle_right = QAction("右侧面板", self, checkable=True, checked=True)
        toggle_right.triggered.connect(
            lambda checked: self.right_panel.setVisible(checked)
        )
        view_menu.addAction(toggle_right)

        view_menu.addSeparator()

        dark_action = QAction("Dark 主题", self)
        dark_action.triggered.connect(lambda: theme_manager.apply("dark"))
        view_menu.addAction(dark_action)

        light_action = QAction("Light 主题", self)
        light_action.triggered.connect(lambda: theme_manager.apply("light"))
        view_menu.addAction(light_action)

        # Agent 菜单
        agent_menu = menubar.addMenu("Agent(&A)")
        run_action = QAction("运行 Agent(&R)", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self._on_run_agent)
        agent_menu.addAction(run_action)

        stop_action = QAction("停止(&X)", self)
        stop_action.setShortcut("Shift+F5")
        stop_action.triggered.connect(self._on_stop_agent)
        agent_menu.addAction(stop_action)

        # Tools 菜单
        tools_menu = menubar.addMenu("工具(&T)")

        tools_menu.addAction("🔧 运行时调试器", lambda: self._show_ops_panel("debugger"))
        tools_menu.addAction("📊 评估工作台", lambda: self._show_ops_panel("evaluator"))
        tools_menu.addAction("📖 知识库编辑器", lambda: self._show_ops_panel("knowledge"))
        tools_menu.addAction("🔒 安全护栏", lambda: self._show_ops_panel("safety"))
        tools_menu.addAction("🤖 多 Agent 编排", lambda: self._show_ops_panel("multi_agent"))
        tools_menu.addAction("📋 日志追踪", lambda: self._show_ops_panel("logger"))
        tools_menu.addAction("🚀 部署管理", lambda: self._show_ops_panel("deploy"))

        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")
        api_settings_action = QAction("⚙️ API 设置", self)
        api_settings_action.setShortcut("Ctrl+,")
        api_settings_action.triggered.connect(self._on_settings)
        settings_menu.addAction(api_settings_action)

        # Help 菜单
        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self) -> None:
        """设置工具栏"""
        from PyQt6.QtWidgets import QWidget, QHBoxLayout
        
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)

        toolbar.addAction("📂 新建", self._on_new_project)
        toolbar.addAction("📁 打开", self._on_open_project)
        toolbar.addAction("💾 保存", self._on_save)
        toolbar.addSeparator()
        toolbar.addAction("▶ 运行", self._on_run_agent)
        toolbar.addAction("⏹ 停止", self._on_stop_agent)
        toolbar.addSeparator()
        toolbar.addAction("🌙 Dark", lambda: theme_manager.apply("dark"))
        toolbar.addAction("☀ Light", lambda: theme_manager.apply("light"))
        
        # 添加弹性空间，将状态信息推到右侧
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        
        # 状态信息显示在工具栏右侧
        self._toolbar_status_agent = QLabel("🤖 未加载")
        self._toolbar_status_agent.setStyleSheet("color: #858585; padding: 0 10px;")
        toolbar.addWidget(self._toolbar_status_agent)
        
        self._toolbar_status_model = QLabel("🧠 --")
        self._toolbar_status_model.setStyleSheet("color: #858585; padding: 0 10px;")
        toolbar.addWidget(self._toolbar_status_model)
        
        self._toolbar_status_theme = QLabel("🎨 Dark")
        self._toolbar_status_theme.setStyleSheet("color: #858585; padding: 0 10px;")
        toolbar.addWidget(self._toolbar_status_theme)

    def _setup_statusbar(self) -> None:
        """设置状态栏 — 最小化，只保留消息提示"""
        statusbar = self.statusBar()
        # 隐藏状态栏，使用顶部工具栏显示状态
        statusbar.setMaximumHeight(0)
        statusbar.hide()

    def _setup_eventbus(self) -> None:
        """设置 EventBus 订阅"""
        event_bus.subscribe("feature.ai.turn_start", self._on_turn_start)
        event_bus.subscribe("feature.ai.turn_end", self._on_turn_end)
        event_bus.subscribe("feature.ai.agent_error", self._on_agent_error)
        event_bus.subscribe("feature.ai.llm_stream_token", self._on_stream_token)

    # --- EventBus 回调 ---

    def _on_turn_start(self, event: Event) -> None:
        turn = event.get("turn", 0)
        self._toolbar_status_agent.setText(f"🤖 运行中 (Turn {turn})")
        self._toolbar_status_agent.setStyleSheet("color: #4ec9b0; padding: 0 10px;")

    def _on_turn_end(self, event: Event) -> None:
        self._toolbar_status_agent.setText("🤖 空闲")
        self._toolbar_status_agent.setStyleSheet("color: #858585; padding: 0 10px;")

    def _on_agent_error(self, event: Event) -> None:
        error = event.get("error", "未知错误")
        self._toolbar_status_agent.setText(f"🤖 错误")
        self._toolbar_status_agent.setStyleSheet("color: #f44336; padding: 0 10px;")

    def _on_stream_token(self, event: Event) -> None:
        token = event.get("token", "")
        # 流式 token 更新（后续 Step 在控制台面板显示）
        pass

    # --- 菜单动作 ---

    def _on_new_project(self) -> None:
        """新建 Agent 项目"""
        from presentation.project.new_dialog import NewProjectDialog
        dialog = NewProjectDialog(self)
        if dialog.exec():
            data = dialog.get_project_data()
            if not data["name"]:
                self.statusBar().showMessage("项目名称不能为空", 3000)
                return
            try:
                from presentation.project.manager import project_manager
                path = project_manager.create_project(
                    name=data["name"],
                    template=data["template"],
                    description=data["description"],
                )
                project_manager.open_project(path)

                # 加载到编辑器
                graph = project_manager.load_graph()
                self.center_panel.show_graph_editor(graph)

                prompts = {}
                for name in project_manager.list_prompts():
                    prompts[name] = project_manager.load_prompt(name)
                self.center_panel.show_prompt_editor(prompts)

                self.center_panel.show_tool_manager(self.right_panel)

                # 加载左侧资源树
                self.left_panel.load_project_tree(str(path))

                self.statusBar().showMessage(f"项目已创建: {data['name']}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建项目失败: {e}")

    def _on_open_project(self) -> None:
        """打开项目"""
        from PyQt6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(
            self, "打开 Agent 项目", "",
        )
        if path:
            try:
                from presentation.project.manager import project_manager
                config = project_manager.open_project(path)

                graph = project_manager.load_graph()
                self.center_panel.show_graph_editor(graph)

                prompts = {}
                for name in project_manager.list_prompts():
                    prompts[name] = project_manager.load_prompt(name)
                self.center_panel.show_prompt_editor(prompts)

                self.center_panel.show_tool_manager(self.right_panel)

                # 加载左侧资源树
                self.left_panel.load_project_tree(path)

                self.statusBar().showMessage(f"项目已打开: {config.name}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开项目失败: {e}")

    def _on_save(self) -> None:
        """保存"""
        self.statusBar().showMessage("项目已保存", 2000)

    def _on_file_open(self, file_path: str) -> None:
        """打开项目浏览器中的文件"""
        from pathlib import Path
        path = Path(file_path)
        
        if not path.exists():
            self.statusBar().showMessage(f"文件不存在: {file_path}", 3000)
            return
        
        try:
            # 根据文件类型选择打开方式
            ext = path.suffix.lower()
            
            if ext == '.json':
                # JSON 文件 — 在图编辑器中打开
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if 'nodes' in data:
                    self.center_panel.show_graph_editor(data)
                else:
                    self._open_text_editor(file_path)
                    
            elif ext == '.md':
                # Markdown 文件 — 在文本编辑器中打开
                self._open_text_editor(file_path)
                
            elif ext == '.py':
                # Python 文件 — 在文本编辑器中打开
                self._open_text_editor(file_path)
                
            else:
                # 其他文件 — 在文本编辑器中打开
                self._open_text_editor(file_path)
                
            self.statusBar().showMessage(f"已打开: {path.name}", 2000)
            
        except Exception as e:
            self.statusBar().showMessage(f"打开文件失败: {e}", 3000)
    
    def _open_text_editor(self, file_path: str) -> None:
        """在文本编辑器中打开文件"""
        from pathlib import Path
        from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QWidget
        
        path = Path(file_path)
        
        # 检查是否已打开
        for i in range(self.center_panel.tab_widget.count()):
            widget = self.center_panel.tab_widget.widget(i)
            if hasattr(widget, '_file_path') and widget._file_path == file_path:
                self.center_panel.tab_widget.setCurrentIndex(i)
                return
        
        # 创建新的文本编辑器
        editor = QTextEdit()
        editor._file_path = file_path
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            editor.setPlainText(content)
        except Exception as e:
            editor.setPlainText(f"读取文件失败: {e}")
        
        # 设置只读（临时）
        editor.setReadOnly(True)
        
        # 设置样式
        editor.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
                padding: 10px;
            }
        """)
        
        # 添加到标签页
        tab_name = f"📄 {path.name}"
        index = self.center_panel.tab_widget.addTab(editor, tab_name)
        self.center_panel.tab_widget.setCurrentIndex(index)

    def _on_run_agent(self) -> None:
        """运行 Agent"""
        self.statusBar().showMessage("启动 Agent... (Step 5 实现)", 3000)

    def _on_stop_agent(self) -> None:
        """停止 Agent"""
        self.statusBar().showMessage("停止 Agent", 2000)

    def _show_ops_panel(self, panel_type: str) -> None:
        """显示运营工具面板"""
        from presentation.ops.debugger import RuntimePanel, EventMonitor
        from presentation.ops.evaluator import EvalWorkbench
        from presentation.ops.knowledge import KnowledgeEditor
        from presentation.ops.safety import SafetyPanel
        from presentation.ops.multi_agent import MultiAgentOrchestrator
        from presentation.ops.logger_panel import LogViewer
        from presentation.ops.deploy import DeployManager

        panel_map = {
            "debugger": ("🔧 调试器", RuntimePanel),
            "evaluator": ("📊 评估", EvalWorkbench),
            "knowledge": ("📖 知识库", KnowledgeEditor),
            "safety": ("🔒 安全", SafetyPanel),
            "multi_agent": ("🤖 编排", MultiAgentOrchestrator),
            "logger": ("📋 日志", LogViewer),
            "deploy": ("🚀 部署", DeployManager),
        }

        if panel_type not in panel_map:
            return

        title, panel_class = panel_map[panel_type]

        # 检查是否已打开
        for i in range(self.center_panel.tab_widget.count()):
            if self.center_panel.tab_widget.tabText(i) == title:
                self.center_panel.tab_widget.setCurrentIndex(i)
                return

        # 创建新标签页
        panel = panel_class()
        self.center_panel.tab_widget.addTab(panel, title)
        self.center_panel.tab_widget.setCurrentIndex(
            self.center_panel.tab_widget.count() - 1
        )

    def _on_settings(self) -> None:
        """打开设置对话框"""
        from presentation.dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.statusBar().showMessage("设置已保存，重启后生效", 3000)

    def _on_about(self) -> None:
        """关于"""
        QMessageBox.about(
            self,
            "关于",
            "Game Master Agent IDE\n\n"
            "版本: 2.0\n"
            "架构: 四层 (Foundation/Core/Feature/Presentation)\n"
            "Agent 引擎: LangGraph\n"
            "UI 框架: PyQt6",
        )

    def _start_http_server(self) -> None:
        """启动 HTTP 控制服务器"""
        from presentation.server import start_server
        self._http_server, self._http_thread = start_server(self, port=18080)
        logger.info("HTTP 控制服务器已启动: http://127.0.0.1:18080")

    def closeEvent(self, event) -> None:
        """关闭窗口"""
        # 停止 HTTP 服务器
        if hasattr(self, '_http_server'):
            self._http_server.shutdown()

        reply = QMessageBox.question(
            self, "确认退出",
            "确定要退出吗？未保存的更改将丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
