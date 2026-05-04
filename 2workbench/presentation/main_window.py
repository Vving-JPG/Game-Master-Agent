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
from PyQt6.QtCore import QFileSystemWatcher
from PyQt6.QtWidgets import QSizePolicy
from PyQt6.QtGui import QAction

from foundation.event_bus import event_bus, Event
from foundation.config import settings
from foundation.logger import get_logger
from presentation.theme.manager import theme_manager
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton
from presentation.agent_thread import AgentThread

logger = get_logger(__name__)


class LeftPanel(BaseWidget):
    """左侧面板 — 资源树 + Agent 项目浏览器"""

    # 信号：文件被双击打开
    file_open_requested = pyqtSignal(str)  # 文件路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_path: str | None = None
        self._setup_ui()
        self._setup_file_watcher()

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
        
        # 样式由全局 QSS 控制，不再设置硬编码样式
        
        layout.addWidget(self.project_tree)
        logger.debug("[LeftPanel] UI 初始化完成")

    def _setup_file_watcher(self) -> None:
        """设置文件系统监视器，自动刷新文件树"""
        self._file_watcher = QFileSystemWatcher(self)
        self._file_watcher.directoryChanged.connect(self._on_directory_changed)
        logger.debug("[LeftPanel] 文件监视器已初始化")

    def _on_directory_changed(self, path: str) -> None:
        """目录变化时自动刷新文件树"""
        logger.info(f"[LeftPanel] 检测到目录变化: {path}")
        if self._project_path:
            self.load_project_tree(self._project_path)

    def _on_item_double_clicked(self, item, column):
        """处理双击事件 — 打开文件"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path:
            from pathlib import Path
            path = Path(file_path)
            if path.is_file():
                logger.info(f"[LeftPanel] 双击打开文件: {file_path}")
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
            logger.warning("[LeftPanel] 项目路径为空")
            return

        root = Path(project_path)
        if not root.exists():
            logger.error(f"[LeftPanel] 项目路径不存在: {project_path}")
            return

        # 保存项目路径并添加文件监视
        self._project_path = project_path
        self._file_watcher.addPath(project_path)
        logger.debug(f"[LeftPanel] 添加文件监视: {project_path}")

        project_name = root.name
        logger.info(f"[LeftPanel] 加载项目树: {project_name} ({root})")

        # 创建根节点
        root_item = QTreeWidgetItem(self.project_tree)
        root_item.setText(0, f"📁 {project_name}")
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(root))

        # 添加项目文件和文件夹
        file_count = self._add_tree_items(root_item, root)
        logger.debug(f"[LeftPanel] 添加了 {file_count} 个文件/文件夹")
        
        self.project_tree.expandItem(root_item)
        self.project_tree.update()  # 强制刷新
    
    def _add_tree_items(self, parent_item, path: Path) -> int:
        """递归添加树节点，返回添加的文件/文件夹数量"""
        from pathlib import Path
        from PyQt6.QtWidgets import QTreeWidgetItem
        
        count = 0
        try:
            items = list(path.iterdir())
            logger.debug(f"[LeftPanel] 扫描目录: {path}, 找到 {len(items)} 个条目")
            
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
            logger.error(f"[LeftPanel] 权限错误: {e}")
        except Exception as e:
            logger.error(f"[LeftPanel] 添加树节点错误: {e}")
        
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
        self._welcome_widget = QLabel(
            "🎮 Game Master Agent IDE\n\n"
            "欢迎使用 Agent 集成开发环境\n\n"
            "请通过 File > New Agent Project 创建新项目\n"
            "或 File > Open 打开已有项目"
        )
        self._welcome_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_secondary = theme_manager.get_color("text_secondary")
        self._welcome_widget.setStyleSheet(f"font-size: 16px; color: {text_secondary};")
        self.tab_widget.addTab(self._welcome_widget, "Welcome")

        # 编辑器标签页（默认隐藏，打开项目后显示）
        self._graph_editor = None
        self._prompt_editor = None
        self._tool_manager = None

    def remove_welcome_tab(self) -> None:
        """移除欢迎标签页"""
        if self._welcome_widget and self.tab_widget.indexOf(self._welcome_widget) >= 0:
            self.tab_widget.removeTab(self.tab_widget.indexOf(self._welcome_widget))
            self._welcome_widget = None

    def _on_tab_close(self, index: int) -> None:
        """关闭标签页"""
        # 如果只有一个标签页，不关闭（至少保留一个）
        if self.tab_widget.count() <= 1:
            return
        
        # 获取要关闭的 widget
        widget = self.tab_widget.widget(index)
        
        # 检查 widget 是否有效
        if widget is None or not isinstance(widget, QWidget):
            return
        
        # 检查是否有未保存的更改
        if hasattr(widget, '_is_modified') and widget._is_modified:
            from pathlib import Path
            filename = Path(widget._file_path).name if hasattr(widget, '_file_path') else "文件"
            reply = QMessageBox.question(
                self, "未保存的更改",
                f"'{filename}' 有未保存的更改。是否保存？",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Save:
                # 保存前再次验证 widget 仍然有效且未被销毁
                if not widget or widget.isDestroyed():
                    return  # widget 已被销毁，不执行关闭
                if not self._save_editor_widget(widget):
                    return  # 保存失败，不关闭
            elif reply == QMessageBox.StandardButton.Cancel:
                return  # 取消关闭
        
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
        text_secondary = theme_manager.get_color("text_secondary")
        self.props_hint.setStyleSheet(f"color: {text_secondary}; font-size: 13px; padding: 20px;")
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
        success_color = theme_manager.get_color("success")
        name_value.setStyleSheet(f"font-weight: bold; color: {success_color};")
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
            text_primary = theme_manager.get_color("text_primary")
            desc_value.setStyleSheet(f"color: {text_primary};")
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
        warning_color = theme_manager.get_color("warning")
        name_value.setStyleSheet(f"font-weight: bold; color: {warning_color};")
        self.props_layout.addRow(name_label, name_value)
        
        # 描述
        if "description" in tool_data:
            desc_label = QLabel("描述:")
            desc_value = QLabel(tool_data["description"])
            desc_value.setWordWrap(True)
            text_primary = theme_manager.get_color("text_primary")
            desc_value.setStyleSheet(f"color: {text_primary};")
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
        if status == "运行中":
            color = theme_manager.get_color("success")
        else:
            color = theme_manager.get_color("text_secondary")
        self.agent_status_label.setStyleSheet(f"color: {color};")
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

        # 如果已有打开的项目，自动加载到编辑器
        self._load_current_project_if_exists()

        # 启动 HTTP 控制服务器
        self._start_http_server()

    def _load_project_to_editors(self, project_path: Path) -> None:
        """将当前项目加载到所有编辑器（统一入口）"""
        from presentation.project.manager import project_manager
        
        # 关闭欢迎标签页
        self.center_panel.remove_welcome_tab()

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
        self.left_panel.setVisible(True)
        self.left_panel.load_project_tree(str(project_path))

        # 更新 Feature 状态
        from feature.registry import feature_registry
        features = feature_registry.list_features()
        self.right_panel.update_feature_status(features)

        logger.info("主窗口初始化完成")

    def _load_current_project_if_exists(self) -> None:
        """如果 project_manager 已有打开的项目，自动加载"""
        from presentation.project.manager import project_manager

        if project_manager._current_project and project_manager._project_path:
            logger.info(f"检测到已打开的项目: {project_manager._current_project.name}")
            try:
                self._load_project_to_editors(project_manager._project_path)
                self._show_message(f"项目已加载: {project_manager._current_project.name}", 3000)
                logger.info(f"项目加载完成: {project_manager._current_project.name}")
            except Exception as e:
                logger.error(f"加载项目失败: {e}")
                self._show_message(f"加载项目失败: {e}", 3000)
    
    def _do_create_project(self, name: str, template: str, directory: str, project_root: str):
        """在主线程中创建新项目"""
        logger.info(f"开始创建项目: {name} (模板: {template})")
        from presentation.project.manager import project_manager
        from pathlib import Path

        try:
            # 创建项目
            full_dir = Path(project_root) / directory
            full_dir.mkdir(parents=True, exist_ok=True)
            
            path = project_manager.create_project(name, template=template, directory=str(full_dir))
            logger.info(f"项目已创建: {path}")
            
            # 自动打开项目
            try:
                rel_path = str(path.relative_to(Path(project_root)))
            except ValueError:
                rel_path = str(path)  # fallback 使用绝对路径
            self._do_open_project(rel_path, project_root)
            
            self._show_message(f"项目已创建并打开: {name}", 3000)
            logger.info(f"项目创建完成!")
        except Exception as e:
            import traceback
            self._show_message(f"创建项目失败: {str(e)}", 3000)
            logger.error(f"创建项目失败: {e}")
            logger.error(traceback.format_exc())

    def _do_open_project(self, project_path: str, project_root: str):
        """在主线程中打开项目"""
        logger.info(f"开始打开项目: {project_path}")
        from presentation.project.manager import project_manager
        from pathlib import Path

        full_path = Path(project_root) / project_path
        
        if not full_path.exists():
            logger.warning(f"项目不存在: {full_path}")
            self._show_message(f"项目不存在: {project_path}", 3000)
            return

        try:
            # 打开项目
            config = project_manager.open_project(full_path)
            logger.info(f"项目已打开: {config.name}")
            
            # 加载编辑器（使用统一入口）
            self._load_project_to_editors(full_path)

            self._show_message(f"项目已打开: {config.name}", 3000)
            logger.info(f"项目打开完成!")
        except Exception as e:
            import traceback
            self._show_message(f"打开项目失败: {str(e)}", 3000)
            logger.error(f"打开项目失败: {e}")
            logger.error(traceback.format_exc())

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

        restart_action = QAction("重启(&R)", self)
        restart_action.setShortcut("Ctrl+Shift+R")
        restart_action.triggered.connect(self._on_restart)
        file_menu.addAction(restart_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit 菜单
        edit_menu = menubar.addMenu("编辑(&E)")

        # 撤销/重做 - 仅对文本编辑器有效
        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        # 剪切/复制/粘贴 - 仅对文本编辑器有效
        cut_action = QAction("剪切(&T)", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self._on_cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction("复制(&C)", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self._on_copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction("粘贴(&P)", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self._on_paste)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        # 选择全部
        select_all_action = QAction("全选(&A)", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self._on_select_all)
        edit_menu.addAction(select_all_action)

        # 查找
        find_action = QAction("查找(&F)", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self._on_find)
        edit_menu.addAction(find_action)

        # View 菜单
        view_menu = menubar.addMenu("视图(&V)")

        toggle_left = QAction("左侧面板", self, checkable=True, checked=True)
        toggle_left.setShortcut("Ctrl+B")
        toggle_left.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(toggle_left)

        toggle_right = QAction("右侧面板", self, checkable=True, checked=True)
        toggle_right.triggered.connect(
            lambda checked: self.right_panel.setVisible(checked)
        )
        view_menu.addAction(toggle_right)

        view_menu.addSeparator()

        # 标签页快捷键
        next_tab_action = QAction("下一个标签页", self)
        next_tab_action.setShortcut("Ctrl+Tab")
        next_tab_action.triggered.connect(lambda: self._switch_tab(1))
        view_menu.addAction(next_tab_action)

        prev_tab_action = QAction("上一个标签页", self)
        prev_tab_action.setShortcut("Ctrl+Shift+Tab")
        prev_tab_action.triggered.connect(lambda: self._switch_tab(-1))
        view_menu.addAction(prev_tab_action)

        close_tab_action = QAction("关闭标签页", self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(self._on_close_current_tab)
        view_menu.addAction(close_tab_action)

        view_menu.addSeparator()

        # 全屏切换
        fullscreen_action = QAction("全屏(&F)", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

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

        shortcut_action = QAction("快捷键列表(&K)", self)
        shortcut_action.setShortcut("Ctrl+Shift+/")
        shortcut_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcut_action)

        help_menu.addSeparator()

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

        # 命令面板（不显示在菜单中，只绑定快捷键）
        command_palette_action = QAction("命令面板", self)
        command_palette_action.setShortcut("Ctrl+Shift+P")
        command_palette_action.triggered.connect(self._show_command_palette)
        self.addAction(command_palette_action)

    def _setup_toolbar(self) -> None:
        """设置工具栏"""
        from PyQt6.QtWidgets import QWidget, QHBoxLayout
        
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)

        # 使用系统标准图标替代 Emoji
        from PyQt6.QtWidgets import QStyle

        self._run_action = QAction("运行", self)
        self._run_action.triggered.connect(self._on_run_agent)
        toolbar.addAction(self._run_action)

        self._stop_action = QAction("停止", self)
        self._stop_action.triggered.connect(self._on_stop_agent)
        self._stop_action.setEnabled(False)
        toolbar.addAction(self._stop_action)

        toolbar.addSeparator()

        dark_action = QAction("暗", self)
        dark_action.triggered.connect(lambda: theme_manager.apply("dark"))
        toolbar.addAction(dark_action)

        light_action = QAction("亮", self)
        light_action.triggered.connect(lambda: theme_manager.apply("light"))
        toolbar.addAction(light_action)
        
        # 添加弹性空间，将状态信息推到右侧
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        
        # 状态信息显示在工具栏右侧
        text_secondary = theme_manager.get_color("text_secondary")
        self._toolbar_status_agent = QLabel("🤖 未加载")
        self._toolbar_status_agent.setStyleSheet(f"color: {text_secondary}; padding: 0 10px;")
        toolbar.addWidget(self._toolbar_status_agent)

        self._toolbar_status_model = QLabel("🧠 --")
        self._toolbar_status_model.setStyleSheet(f"color: {text_secondary}; padding: 0 10px;")
        toolbar.addWidget(self._toolbar_status_model)

        self._toolbar_status_theme = QLabel("🎨 Dark")
        self._toolbar_status_theme.setStyleSheet(f"color: {text_secondary}; padding: 0 10px;")
        toolbar.addWidget(self._toolbar_status_theme)

    def _setup_statusbar(self) -> None:
        """设置状态栏 — 最小化，只保留消息提示"""
        statusbar = self.statusBar()
        # 隐藏状态栏，使用顶部工具栏显示状态
        statusbar.setMaximumHeight(0)
        statusbar.hide()

    def _show_message(self, msg: str, duration: int = 3000) -> None:
        """统一消息显示 — 使用工具栏状态标签"""
        self._toolbar_status_agent.setText(f"💬 {msg}")
        if duration > 0:
            QTimer.singleShot(duration, lambda: self._toolbar_status_agent.setText("🤖 未加载"))

    def _setup_eventbus(self) -> None:
        """设置 EventBus 订阅"""
        event_bus.subscribe("feature.ai.turn_start", self._on_turn_start)
        event_bus.subscribe("feature.ai.turn_end", self._on_turn_end)
        event_bus.subscribe("feature.ai.agent_error", self._on_agent_error_event)
        event_bus.subscribe("feature.ai.llm_stream_token", self._on_stream_token)
        # Agent 运行准备完成事件
        event_bus.subscribe("feature.agent.prepared", self._on_agent_prepared)
        event_bus.subscribe("feature.agent.run_failed", self._on_agent_run_failed)
        # 调试面板事件
        self._setup_debugger_connections()

    # --- EventBus 回调 ---

    def _on_turn_start(self, event: Event) -> None:
        turn = event.get("turn", 0)
        self._toolbar_status_agent.setText(f"🤖 运行中 (Turn {turn})")
        success_color = theme_manager.get_color("success")
        self._toolbar_status_agent.setStyleSheet(f"color: {success_color}; padding: 0 10px;")

    def _on_turn_end(self, event: Event) -> None:
        self._toolbar_status_agent.setText("🤖 空闲")
        text_secondary = theme_manager.get_color("text_secondary")
        self._toolbar_status_agent.setStyleSheet(f"color: {text_secondary}; padding: 0 10px;")

    def _on_agent_error_event(self, event: Event) -> None:
        """EventBus 的 agent_error 事件处理"""
        error = event.get("error", "未知错误")
        self._toolbar_status_agent.setText(f"🤖 错误")
        error_color = theme_manager.get_color("error")
        self._toolbar_status_agent.setStyleSheet(f"color: {error_color}; padding: 0 10px;")

    def _on_stream_token(self, event: Event) -> None:
        token = event.get("token", "")
        # 流式 token 更新（后续 Step 在控制台面板显示）
        pass

    def _on_agent_prepared(self, event: Event) -> None:
        """Agent 准备完成，启动运行线程"""
        from feature.ai.agent_runner import agent_runner

        user_input = event.data.get("user_input", "")
        agent = agent_runner.get_current_agent()

        if not agent:
            logger.error("Agent 准备完成但未获取到实例")
            self._run_action.setEnabled(True)
            self._stop_action.setEnabled(False)
            return

        # 在后台线程中运行 Agent
        self._agent_thread = AgentThread(agent, user_input)
        self._agent_thread.finished.connect(self._on_agent_finished)
        self._agent_thread.error.connect(self._on_agent_error)
        self._agent_thread.stopped.connect(self._on_agent_stopped)
        self._agent_thread.start()

    def _on_agent_run_failed(self, event: Event) -> None:
        """Agent 运行准备失败"""
        error = event.data.get("error", "未知错误")
        logger.error(f"Agent 运行准备失败: {error}")

        # 恢复按钮状态
        self._run_action.setEnabled(True)
        self._stop_action.setEnabled(False)

        QMessageBox.critical(self, "Agent 错误", f"运行准备失败: {error}")

    def _setup_debugger_connections(self) -> None:
        """连接调试面板到 Agent"""
        event_bus.subscribe("ui.debugger.run", self._on_debugger_run)
        event_bus.subscribe("ui.debugger.stop", self._on_debugger_stop)
        event_bus.subscribe("ui.debugger.input", self._on_debugger_input)
        event_bus.subscribe("ui.debugger.request_state", self._on_request_state)

    def _on_debugger_run(self, event: Event) -> None:
        """调试面板触发运行"""
        self._on_run_agent()

    def _on_debugger_stop(self, event: Event) -> None:
        """调试面板触发停止"""
        self._on_stop_agent()

    def _on_debugger_input(self, event: Event) -> None:
        """调试面板发送用户输入"""
        text = event.get("text", "")
        if not text:
            return
        # 如果有正在运行的 Agent，发送输入
        if hasattr(self, '_current_agent') and self._current_agent:
            # 通过 EventBus 发送输入事件
            event_bus.emit("feature.ai.user_input", {"text": text})

    def _on_request_state(self, event: Event) -> None:
        """响应调试面板的状态请求"""
        if not hasattr(self, '_current_agent') or not self._current_agent:
            return
        try:
            if hasattr(self._current_agent, 'get_state_snapshot'):
                snapshot = self._current_agent.get_state_snapshot()
                event_bus.emit("ui.debugger.state_update", {"state": snapshot})
            else:
                logger.warning("当前 Agent 不支持 get_state_snapshot 方法")
        except Exception as e:
            logger.error(f"获取 Agent 状态失败: {e}")

    def _on_undo(self) -> None:
        """撤销操作"""
        current = self.center_panel.tab_widget.currentWidget()
        if hasattr(current, 'undo'):
            current.undo()
        elif hasattr(current, 'textCursor'):
            # QTextEdit 默认撤销
            current.undo()

    def _on_redo(self) -> None:
        """重做操作"""
        current = self.center_panel.tab_widget.currentWidget()
        if hasattr(current, 'redo'):
            current.redo()
        elif hasattr(current, 'textCursor'):
            # QTextEdit 默认重做
            current.redo()

    def _on_cut(self) -> None:
        """剪切"""
        current = self.center_panel.tab_widget.currentWidget()
        if hasattr(current, 'cut'):
            current.cut()

    def _on_copy(self) -> None:
        """复制"""
        current = self.center_panel.tab_widget.currentWidget()
        if hasattr(current, 'copy'):
            current.copy()

    def _on_paste(self) -> None:
        """粘贴"""
        current = self.center_panel.tab_widget.currentWidget()
        if hasattr(current, 'paste'):
            current.paste()

    def _on_select_all(self) -> None:
        """全选"""
        current = self.center_panel.tab_widget.currentWidget()
        if hasattr(current, 'selectAll'):
            current.selectAll()

    def _on_find(self) -> None:
        """查找"""
        # 聚焦到当前编辑器的搜索功能
        current = self.center_panel.tab_widget.currentWidget()
        if hasattr(current, '_search'):
            current._search.setFocus()
            current._search.selectAll()

    # --- 菜单动作 ---

    def _on_new_project(self) -> None:
        """新建 Agent 项目"""
        from presentation.project.new_dialog import NewProjectDialog
        dialog = NewProjectDialog(self)
        if dialog.exec():
            data = dialog.get_project_data()
            if not data["name"]:
                self._show_message("项目名称不能为空", 3000)
                return
            # 通过信号触发统一处理
            # 参数: name, template, directory, project_root
            project_dir = data.get("directory", "")
            self.create_project_requested.emit(
                data["name"], data["template"], project_dir, ""
            )

    def _on_open_project(self) -> None:
        """打开项目"""
        from PyQt6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(self, "打开 Agent 项目", "")
        if path:
            # 通过信号触发统一处理
            self.open_project_requested.emit(path, "")

    def _on_restart(self) -> None:
        """重启应用"""
        from PyQt6.QtWidgets import QMessageBox
        import sys
        import os

        reply = QMessageBox.question(
            self, "重启确认", "确定要重启应用吗？\n未保存的更改将会丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            logger.info("用户请求重启应用")
            # 保存当前命令行参数
            args = sys.argv[:]
            # 关闭当前应用
            self.close()
            # 重新启动
            os.execl(sys.executable, sys.executable, *args)

    def _on_save(self) -> None:
        """保存当前项目"""
        from presentation.project.manager import project_manager

        # 首先尝试保存当前文本编辑器
        current = self.center_panel.tab_widget.currentWidget()
        if hasattr(current, '_file_path') and hasattr(current, '_is_modified'):
            if current._is_modified:
                self._save_current_editor()
            return

        if not project_manager.is_open:
            self._show_message("没有打开的项目")
            return

        try:
            # 保存图编辑器
            if self.center_panel._graph_editor:
                graph_data = self.center_panel._graph_editor.get_graph()
                project_manager.save_graph(graph_data)

            # 保存 Prompt 编辑器
            if self.center_panel._prompt_editor:
                prompts = self.center_panel._prompt_editor.get_prompts()
                for name, content in prompts.items():
                    project_manager.save_prompt(name, content)

            # 保存项目元数据
            project_manager.save_project()

            self._show_message(f"项目已保存: {project_manager.current_project.name}")
            logger.info(f"项目已保存: {project_manager.current_project.name}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存项目时出错: {e}")
            logger.error(f"保存项目失败: {e}")

    def _on_file_open(self, file_path: str) -> None:
        """打开项目浏览器中的文件"""
        from pathlib import Path
        path = Path(file_path)
        
        if not path.exists():
            self._show_message(f"文件不存在: {file_path}", 3000)
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
                
            self._show_message(f"已打开: {path.name}", 2000)
            
        except Exception as e:
            self._show_message(f"打开文件失败: {e}", 3000)
    
    def _open_text_editor(self, file_path: str) -> None:
        """在文本编辑器中打开文件"""
        from pathlib import Path
        from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QWidget
        from PyQt6.QtCore import pyqtSignal
        
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
        editor._original_content = ""  # 保存原始内容用于比较
        editor._is_modified = False
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            editor.setPlainText(content)
            editor._original_content = content
        except Exception as e:
            editor.setPlainText(f"读取文件失败: {e}")
        
        # 可编辑
        editor.setReadOnly(False)
        
        # 监听文本变化
        def on_text_changed():
            current = editor.toPlainText()
            was_modified = editor._is_modified
            editor._is_modified = (current != editor._original_content)
            if editor._is_modified != was_modified:
                self._update_tab_title(editor, path.name, editor._is_modified)

        editor.textChanged.connect(on_text_changed)

        # 绑定 Ctrl+S 保存快捷键
        from PyQt6.QtGui import QShortcut, QKeySequence
        save_shortcut = QShortcut(QKeySequence.StandardKey.Save, editor)
        save_shortcut.activated.connect(lambda: self._save_editor_widget(editor))

        # 只保留字体设置，颜色由全局 QSS 控制
        p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
        mono_font = p.get("mono_font", "'Cascadia Code', 'Consolas', 'Monaco', 'Courier New', monospace")
        editor.setStyleSheet(f"font-family: {mono_font};")

        # 添加到标签页
        tab_name = f"📄 {path.name}"
        index = self.center_panel.tab_widget.addTab(editor, tab_name)
        self.center_panel.tab_widget.setCurrentIndex(index)
    
    def _update_tab_title(self, editor: QTextEdit, filename: str, modified: bool) -> None:
        """更新标签页标题（显示修改标记）"""
        for i in range(self.center_panel.tab_widget.count()):
            if self.center_panel.tab_widget.widget(i) == editor:
                title = f"📄 {filename}{'*' if modified else ''}"
                self.center_panel.tab_widget.setTabText(i, title)
                break
    
    def _save_current_editor(self) -> bool:
        """保存当前编辑器的内容"""
        current = self.center_panel.tab_widget.currentWidget()
        if not current or not hasattr(current, '_file_path'):
            return False
        return self._save_editor_widget(current)
    
    def _save_editor_widget(self, widget: QWidget) -> bool:
        """保存指定编辑器 widget 的内容
        
        Args:
            widget: 要保存的编辑器 widget
            
        Returns:
            保存是否成功
        """
        # 验证 widget 有效
        if not widget or not isinstance(widget, QWidget):
            return False
        
        if not hasattr(widget, '_file_path'):
            return False
        
        file_path = widget._file_path
        content = widget.toPlainText()
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            widget._original_content = content
            widget._is_modified = False
            
            # 更新标签标题
            from pathlib import Path
            self._update_tab_title(widget, Path(file_path).name, False)
            
            self._show_message(f"已保存: {Path(file_path).name}", 2000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存文件时出错: {e}")
            return False

    def _on_close_current_tab(self) -> None:
        """关闭当前标签页"""
        index = self.center_panel.tab_widget.currentIndex()
        if index >= 0:
            self.center_panel._on_tab_close(index)

    def _switch_tab(self, direction: int) -> None:
        """切换标签页（direction: 1=下一个, -1=上一个）"""
        count = self.center_panel.tab_widget.count()
        if count <= 1:
            return
        current = self.center_panel.tab_widget.currentIndex()
        next_index = (current + direction) % count
        self.center_panel.tab_widget.setCurrentIndex(next_index)

    def _toggle_sidebar(self) -> None:
        """切换左侧面板可见性"""
        self.left_panel.setVisible(not self.left_panel.isVisible())

    def _toggle_fullscreen(self) -> None:
        """切换全屏"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _on_run_agent(self) -> None:
        """运行 Agent — 通过 EventBus 请求，不解耦直接创建"""
        from presentation.project.manager import project_manager
        from foundation.config import settings

        if not project_manager.is_open:
            self._show_message("请先打开一个项目")
            return

        # 检查图是否有效
        try:
            graph = project_manager.load_graph()
            nodes = graph.get("nodes", [])
            if not nodes:
                QMessageBox.warning(self, "无法运行", "当前项目没有定义任何节点，请先在图编辑器中添加节点。")
                return
        except Exception as e:
            logger.warning(f"加载图检查失败: {e}")

        if not settings.deepseek_api_key:
            QMessageBox.warning(self, "配置缺失",
                "请先在 设置 > API设置 中配置 API Key")
            self._on_settings()
            return

        # 显示输入对话框获取玩家输入
        from PyQt6.QtWidgets import QInputDialog
        user_input, ok = QInputDialog.getText(
            self, "运行 Agent", "请输入玩家指令:",
            text="我要探索幽暗森林"
        )
        if not ok or not user_input:
            return

        # 禁用运行按钮，启用停止按钮
        self._run_action.setEnabled(False)
        self._stop_action.setEnabled(True)
        self._show_message("Agent 运行中...")

        # 保存用户输入供后续使用
        self._pending_user_input = user_input

        # 通过 EventBus 请求 Agent 准备
        event_bus.emit(Event(
            type="ui.agent.run_requested",
            data={
                "world_id": 1,
                "user_input": user_input,
                "db_path": settings.database_path,
            }
        ))

    def _on_agent_finished(self, result: dict) -> None:
        """Agent 运行完成回调"""
        # 恢复按钮状态
        self._run_action.setEnabled(True)
        self._stop_action.setEnabled(False)

        status = result.get("status", "unknown")
        if status == "success":
            narrative = result.get("narrative", "")
            turn = result.get("turn_count", 0)
            self._show_message(f"Agent 回合 {turn} 完成", 3000)

            # 显示叙事结果（简单弹窗）
            QMessageBox.information(
                self, "Agent 运行结果",
                f"<h3>回合 {turn}</h3>"
                f"<p>{narrative[:500]}{'...' if len(narrative) > 500 else ''}</p>"
            )
        else:
            error = result.get("error", "未知错误")
            self._show_message(f"Agent 运行失败: {error}", 5000)
            QMessageBox.critical(self, "Agent 错误", f"运行失败: {error}")

    def _on_agent_error(self, error: str) -> None:
        """Agent 运行错误回调"""
        # 恢复按钮状态
        self._run_action.setEnabled(True)
        self._stop_action.setEnabled(False)

        self._show_message(f"Agent 运行错误: {error}", 5000)
        QMessageBox.critical(self, "Agent 错误", f"运行失败: {error}")

    def _on_stop_agent(self) -> None:
        """停止 Agent"""
        if hasattr(self, '_agent_thread') and self._agent_thread.isRunning():
            # 使用协作式取消而非 terminate()
            self._agent_thread.stop()
            # 等待线程结束（带超时）
            if not self._agent_thread.wait(5000):  # 等待最多5秒
                # 超时后作为最后手段使用 terminate
                self._agent_thread.terminate()
                self._agent_thread.wait()
            # 按钮状态在 stopped 信号中恢复
        else:
            self._show_message("Agent 未在运行")

    def _on_agent_stopped(self) -> None:
        """Agent 被停止回调"""
        # 恢复按钮状态
        self._run_action.setEnabled(True)
        self._stop_action.setEnabled(False)
        self._show_message("Agent 已停止")

    def _show_ops_panel(self, panel_type: str) -> None:
        """显示运营工具面板"""
        from presentation.ops.debugger import RuntimePanel, EventMonitor
        from presentation.ops.eval_workbench import EvalWorkbench
        from presentation.ops.knowledge_editor import KnowledgeEditor
        from presentation.ops.safety_panel import SafetyPanel
        from presentation.ops.multi_agent_orchestrator import MultiAgentOrchestrator
        from presentation.ops.log_viewer import LogViewer
        from presentation.ops.deploy_manager import DeployManager

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
            self._show_message("设置已保存，重启后生效", 3000)

    def _show_command_palette(self) -> None:
        """显示命令面板（VS Code 风格）"""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QLineEdit, QListWidget,
            QListWidgetItem, QLabel, QHBoxLayout
        )
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QKeyEvent
        
        class CommandPaletteDialog(QDialog):
            def __init__(self, parent=None, main_window=None):
                super().__init__(parent)
                self.main_window = main_window
                self.setWindowTitle("命令面板")
                self.setMinimumWidth(600)
                self.setMaximumHeight(500)
                
                # 无边框、置顶
                self.setWindowFlags(
                    Qt.WindowType.Dialog |
                    Qt.WindowType.FramelessWindowHint |
                    Qt.WindowType.WindowStaysOnTopHint
                )
                
                self._setup_ui()
                self._setup_commands()
                
                # 居中显示
                if parent:
                    self.move(
                        parent.x() + (parent.width() - self.width()) // 2,
                        parent.y() + 100
                    )
            
            def _setup_ui(self):
                layout = QVBoxLayout(self)
                layout.setContentsMargins(12, 12, 12, 12)
                layout.setSpacing(8)
                
                # 搜索框
                self.search_box = QLineEdit()
                self.search_box.setPlaceholderText("> 输入命令...")
                self.search_box.textChanged.connect(self._filter_commands)
                layout.addWidget(self.search_box)
                
                # 命令列表
                self.command_list = QListWidget()
                self.command_list.itemActivated.connect(self._execute_command)
                self.command_list.itemClicked.connect(self._execute_command)
                layout.addWidget(self.command_list)
                
                # 提示
                hint = QLabel("↑↓ 选择 · Enter 执行 · Esc 关闭")
                text_secondary = theme_manager.get_color("text_secondary")
                hint.setStyleSheet(f"color: {text_secondary}; font-size: 11px;")
                hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(hint)
                
                # 聚焦搜索框
                QTimer.singleShot(0, self.search_box.setFocus)
            
            def _setup_commands(self):
                """设置可用命令列表"""
                self.commands = [
                    ("📁 新建项目", "new_project", "Ctrl+N"),
                    ("📂 打开项目", "open_project", "Ctrl+O"),
                    ("💾 保存", "save", "Ctrl+S"),
                    ("🔧 图编辑器", "show_graph", ""),
                    ("📝 Prompt 管理器", "show_prompt", ""),
                    ("🔨 工具管理器", "show_tools", ""),
                    ("▶️ 运行 Agent", "run_agent", "F5"),
                    ("⏹️ 停止 Agent", "stop_agent", "Shift+F5"),
                    ("🔍 运行时调试器", "debugger", ""),
                    ("📊 评估工作台", "evaluator", ""),
                    ("📖 知识库编辑器", "knowledge", ""),
                    ("🔒 安全护栏", "safety", ""),
                    ("🤖 多 Agent 编排", "multi_agent", ""),
                    ("📋 日志追踪", "logger", ""),
                    ("🚀 部署管理", "deploy", ""),
                    ("⚙️ 设置", "settings", "Ctrl+,"),
                    ("🎨 Dark 主题", "theme_dark", ""),
                    ("🎨 Light 主题", "theme_light", ""),
                    ("🖥️ 全屏切换", "fullscreen", "F11"),
                    ("❓ 快捷键列表", "shortcuts", "Ctrl+Shift+/"),
                    ("ℹ️ 关于", "about", ""),
                ]
                
                for name, cmd, shortcut in self.commands:
                    display = f"{name}"
                    if shortcut:
                        display += f"  [{shortcut}]"
                    item = QListWidgetItem(display)
                    item.setData(Qt.ItemDataRole.UserRole, cmd)
                    self.command_list.addItem(item)
                
                if self.command_list.count() > 0:
                    self.command_list.setCurrentRow(0)
            
            def _filter_commands(self, text: str):
                """过滤命令列表"""
                text = text.lower()
                for i in range(self.command_list.count()):
                    item = self.command_list.item(i)
                    cmd_name = self.commands[i][0].lower()
                    cmd_id = self.commands[i][1].lower()
                    match = text == "" or text in cmd_name or text in cmd_id
                    item.setHidden(not match)
                
                # 选中第一个可见项
                for i in range(self.command_list.count()):
                    if not self.command_list.item(i).isHidden():
                        self.command_list.setCurrentRow(i)
                        break
            
            def _execute_command(self, item=None):
                """执行选中的命令"""
                if item is None:
                    item = self.command_list.currentItem()
                if not item:
                    return
                
                cmd = item.data(Qt.ItemDataRole.UserRole)
                self.close()
                
                if self.main_window:
                    self.main_window._execute_palette_command(cmd)
            
            def keyPressEvent(self, event: QKeyEvent):
                """处理键盘事件"""
                if event.key() == Qt.Key.Key_Escape:
                    self.close()
                elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                    self._execute_command()
                elif event.key() == Qt.Key.Key_Down:
                    self._move_selection(1)
                elif event.key() == Qt.Key.Key_Up:
                    self._move_selection(-1)
                else:
                    super().keyPressEvent(event)
            
            def _move_selection(self, direction: int):
                """移动选择"""
                current = self.command_list.currentRow()
                count = self.command_list.count()
                
                # 找到下一个可见项
                for i in range(1, count + 1):
                    new_idx = (current + direction * i) % count
                    if not self.command_list.item(new_idx).isHidden():
                        self.command_list.setCurrentRow(new_idx)
                        break
        
        # 显示命令面板
        palette = CommandPaletteDialog(self, self)
        palette.exec()
    
    def _execute_palette_command(self, cmd: str):
        """执行命令面板的命令"""
        handlers = {
            "new_project": self._on_new_project,
            "open_project": self._on_open_project,
            "save": self._on_save,
            "show_graph": lambda: self.center_panel.show_graph_editor(),
            "show_prompt": lambda: self.center_panel.show_prompt_editor(),
            "show_tools": lambda: self.center_panel.show_tool_manager(self.right_panel),
            "run_agent": self._on_run_agent,
            "stop_agent": self._on_stop_agent,
            "debugger": lambda: self._show_ops_panel("debugger"),
            "evaluator": lambda: self._show_ops_panel("evaluator"),
            "knowledge": lambda: self._show_ops_panel("knowledge"),
            "safety": lambda: self._show_ops_panel("safety"),
            "multi_agent": lambda: self._show_ops_panel("multi_agent"),
            "logger": lambda: self._show_ops_panel("logger"),
            "deploy": lambda: self._show_ops_panel("deploy"),
            "settings": self._on_settings,
            "theme_dark": lambda: theme_manager.apply("dark"),
            "theme_light": lambda: theme_manager.apply("light"),
            "fullscreen": self._toggle_fullscreen,
            "shortcuts": self._show_shortcuts,
            "about": self._on_about,
        }
        
        handler = handlers.get(cmd)
        if handler:
            handler()

    def _show_shortcuts(self) -> None:
        """显示快捷键列表"""
        shortcuts = """
        <h3>快捷键列表</h3>
        <table cellpadding="5">
        <tr><td><b>Ctrl+N</b></td><td>新建项目</td></tr>
        <tr><td><b>Ctrl+O</b></td><td>打开项目</td></tr>
        <tr><td><b>Ctrl+S</b></td><td>保存项目</td></tr>
        <tr><td><b>Ctrl+W</b></td><td>关闭标签页</td></tr>
        <tr><td><b>Ctrl+Tab</b></td><td>下一个标签页</td></tr>
        <tr><td><b>Ctrl+Shift+Tab</b></td><td>上一个标签页</td></tr>
        <tr><td><b>Ctrl+B</b></td><td>切换侧边栏</td></tr>
        <tr><td><b>Ctrl+,</b></td><td>打开设置</td></tr>
        <tr><td><b>Ctrl+Shift+P</b></td><td>命令面板</td></tr>
        <tr><td><b>Ctrl+Z</b></td><td>撤销</td></tr>
        <tr><td><b>Ctrl+Y</b></td><td>重做</td></tr>
        <tr><td><b>Ctrl+X</b></td><td>剪切</td></tr>
        <tr><td><b>Ctrl+C</b></td><td>复制</td></tr>
        <tr><td><b>Ctrl+V</b></td><td>粘贴</td></tr>
        <tr><td><b>Ctrl+A</b></td><td>全选</td></tr>
        <tr><td><b>Ctrl+F</b></td><td>查找</td></tr>
        <tr><td><b>F5</b></td><td>运行 Agent</td></tr>
        <tr><td><b>Shift+F5</b></td><td>停止 Agent</td></tr>
        <tr><td><b>F11</b></td><td>全屏切换</td></tr>
        <tr><td><b>Ctrl+Q</b></td><td>退出</td></tr>
        <tr><td><b>Ctrl+Shift+/</b></td><td>显示快捷键列表</td></tr>
        </table>
        """
        QMessageBox.information(self, "快捷键列表", shortcuts)

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
