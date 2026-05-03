"""项目选择器 — 仿 Godot 4.6 项目管理器界面

启动时显示项目列表，让用户选择或创建新项目。
完全重写版本，采用 Godot 4.6 项目管理器的布局风格。
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QFrame, QMessageBox, QFileDialog,
    QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QStyledItemDelegate, QStyle, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect
from PyQt6.QtGui import QFont, QColor, QPen, QBrush, QPainter

from foundation.logger import get_logger
from presentation.theme.manager import theme_manager

logger = get_logger(__name__)


class ProjectItemDelegate(QStyledItemDelegate):
    """自定义项目列表项绘制 — 仿 Godot 风格"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        """绘制项目项"""
        painter.save()
        info = index.data(Qt.ItemDataRole.UserRole)
        if not info:
            painter.restore()
            return

        # 获取主题颜色
        p = theme_manager.PALETTES.get(theme_manager.current_theme, {})

        bg_primary = p.get("bg_primary", "#1e1e1e")
        bg_hover = p.get("bg_hover", "#3e3e42")
        bg_selected = p.get("accent", "#007acc")
        text_bright = p.get("text_bright", "#ffffff")
        text_secondary = p.get("text_secondary", "#858585")
        text_disabled = p.get("text_secondary", "#858585")
        border = p.get("border", "#3e3e42")

        rect = option.rect

        # 背景
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, QColor(bg_selected))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, QColor(bg_hover))
        else:
            painter.fillRect(rect, QColor(bg_primary))

        # 底部分割线
        painter.setPen(QPen(QColor(border), 1))
        painter.drawLine(rect.left() + 12, rect.bottom(), rect.right() - 12, rect.bottom())

        # 图标区域（48x48，左侧）
        icon_rect = QRect(rect.left() + 44, rect.top() + 12, 48, 48)
        template = info.get("template", "blank")
        icon_colors = {"blank": "#569cd6", "trpg": "#4ec9b0", "chatbot": "#c586c0"}
        icon_color = QColor(icon_colors.get(template, "#569cd6"))
        painter.setBrush(QBrush(icon_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(icon_rect, 6, 6)

        # 图标上的 emoji
        icons = {"blank": "📄", "trpg": "🎲", "chatbot": "🤖"}
        painter.setFont(QFont("", 20))
        painter.setPen(QColor(text_bright))
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, icons.get(template, "📄"))

        # 项目名称（图标右侧）
        name_rect = QRect(rect.left() + 104, rect.top() + 14, rect.width() - 280, 24)
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Medium))
        painter.setPen(QColor(text_bright))
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        info.get("name", ""))

        # 路径（名称下方）
        path_text = f"📁 {info.get('path', '')}"
        path_rect = QRect(rect.left() + 104, rect.top() + 40, rect.width() - 280, 20)
        painter.setFont(QFont("Microsoft YaHei", 10))
        painter.setPen(QColor(text_secondary))
        painter.drawText(path_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        path_text)

        # 右侧：修改时间
        time_rect = QRect(rect.right() - 170, rect.top() + 20, 160, 20)
        painter.setFont(QFont("Microsoft YaHei", 10))
        painter.setPen(QColor(text_disabled))
        painter.drawText(time_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        info.get("modified", ""))

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(0, 72)  # 每行 72px 高


class ProjectSelector(QDialog):
    """项目选择器对话框 — 仿 Godot 4.6 项目管理器"""

    project_selected = pyqtSignal(str)  # 发射选中的项目路径
    new_project_requested = pyqtSignal()  # 请求创建新项目

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Game Master Agent IDE - 项目管理器")
        self.setMinimumSize(960, 640)
        self.resize(960, 640)

        self._projects: List[Dict[str, Any]] = []
        self._filtered_projects: List[Dict[str, Any]] = []
        self._selected_project: Dict[str, Any] | None = None

        self._setup_ui()
        self._load_projects()
        self._apply_theme()

    def _setup_ui(self) -> None:
        """设置 UI — 仿 Godot 4.6 布局"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.get_color("bg_primary")};
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ========== Header (64px) ==========
        self._header = QFrame()
        self._header.setFixedHeight(64)
        self._header.setObjectName("header")

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(8)

        # Logo
        logo_label = QLabel("🎲")
        logo_label.setFont(QFont("", 24))
        header_layout.addWidget(logo_label)

        # 标题
        title_label = QLabel("Game Master Agent")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title_label.setObjectName("titleLabel")
        header_layout.addWidget(title_label)

        header_layout.addStretch(1)

        # 导航标签
        self._projects_tab = QPushButton("📋 项目")
        self._projects_tab.setObjectName("navTabActive")
        self._projects_tab.setFlat(True)
        self._projects_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(self._projects_tab)

        self._assets_tab = QPushButton("📦 资产库")
        self._assets_tab.setObjectName("navTabInactive")
        self._assets_tab.setFlat(True)
        self._assets_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self._assets_tab.setEnabled(False)  # 暂未实现
        header_layout.addWidget(self._assets_tab)

        header_layout.addStretch(1)

        main_layout.addWidget(self._header)

        # ========== Toolbar (40px) ==========
        self._toolbar = QFrame()
        self._toolbar.setFixedHeight(40)
        self._toolbar.setObjectName("toolbar")

        toolbar_layout = QHBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(12, 4, 12, 4)
        toolbar_layout.setSpacing(8)

        # 新建按钮
        self._new_btn = self._create_toolbar_button("➕", "新建")
        self._new_btn.setObjectName("newBtn")
        self._new_btn.clicked.connect(self._on_new_project)
        toolbar_layout.addWidget(self._new_btn)

        # 导入按钮
        self._import_btn = self._create_toolbar_button("📂", "导入")
        self._import_btn.setObjectName("importBtn")
        self._import_btn.clicked.connect(self._on_import_project)
        toolbar_layout.addWidget(self._import_btn)

        # 扫描按钮
        self._scan_btn = self._create_toolbar_button("🔍", "扫描")
        self._scan_btn.setObjectName("scanBtn")
        self._scan_btn.clicked.connect(self._load_projects)
        toolbar_layout.addWidget(self._scan_btn)

        toolbar_layout.addSpacing(16)

        # 筛选输入框
        self._filter_edit = QLineEdit()
        self._filter_edit.setObjectName("filterEdit")
        self._filter_edit.setPlaceholderText("🔍 筛选项目...")
        self._filter_edit.setFixedWidth(200)
        self._filter_edit.textChanged.connect(self._on_filter_changed)
        toolbar_layout.addWidget(self._filter_edit)

        toolbar_layout.addStretch(1)

        # 排序标签
        sort_label = QLabel("排序:")
        sort_label.setObjectName("sortLabel")
        toolbar_layout.addWidget(sort_label)

        # 排序下拉框
        self._sort_combo = QComboBox()
        self._sort_combo.setObjectName("sortCombo")
        self._sort_combo.addItems(["最近编辑", "项目名称", "创建时间"])
        self._sort_combo.setFixedWidth(120)
        self._sort_combo.currentTextChanged.connect(self._on_sort_changed)
        toolbar_layout.addWidget(self._sort_combo)

        main_layout.addWidget(self._toolbar)

        # ========== Body (主内容区) ==========
        body_layout = QHBoxLayout()
        body_layout.setSpacing(0)
        body_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧项目列表 (~78%)
        self._project_list_panel = QWidget()
        self._project_list_panel.setObjectName("projectListPanel")
        list_layout = QVBoxLayout(self._project_list_panel)
        list_layout.setContentsMargins(8, 8, 8, 8)
        list_layout.setSpacing(0)

        self._project_list = QListWidget()
        self._project_list.setObjectName("projectList")
        self._project_list.setFrameShape(QFrame.Shape.NoFrame)
        self._project_list.setSpacing(0)
        self._project_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._project_list.setItemDelegate(ProjectItemDelegate(self._project_list))
        self._project_list.currentItemChanged.connect(self._on_selection_changed)
        self._project_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        list_layout.addWidget(self._project_list)

        body_layout.addWidget(self._project_list_panel, stretch=78)

        # 右侧操作栏 (~22%, 固定宽度 180px)
        self._action_panel = QFrame()
        self._action_panel.setFixedWidth(180)
        self._action_panel.setObjectName("actionPanel")

        action_layout = QVBoxLayout(self._action_panel)
        action_layout.setContentsMargins(8, 8, 8, 8)
        action_layout.setSpacing(1)

        # 操作按钮
        self._edit_btn = self._create_action_button("✏️", "编辑", "editBtn")
        self._edit_btn.clicked.connect(self._on_edit_project)
        action_layout.addWidget(self._edit_btn)

        self._run_btn = self._create_action_button("▶", "运行", "runBtn", primary=True)
        self._run_btn.clicked.connect(self._on_run_project)
        action_layout.addWidget(self._run_btn)

        self._rename_btn = self._create_action_button("📝", "重命名", "renameBtn")
        self._rename_btn.clicked.connect(self._on_rename_project)
        action_layout.addWidget(self._rename_btn)

        self._duplicate_btn = self._create_action_button("📄", "创建副本", "duplicateBtn")
        self._duplicate_btn.clicked.connect(self._on_duplicate_project)
        action_layout.addWidget(self._duplicate_btn)

        self._tag_btn = self._create_action_button("🏷️", "管理标签", "tagBtn")
        self._tag_btn.clicked.connect(self._on_manage_tags)
        action_layout.addWidget(self._tag_btn)

        # 分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        action_layout.addWidget(separator)

        self._remove_btn = self._create_action_button("🗑️", "移除", "removeBtn", danger=True)
        self._remove_btn.clicked.connect(self._on_remove_project)
        action_layout.addWidget(self._remove_btn)

        self._missing_btn = self._create_action_button("🔗", "移除缺失项", "missingBtn")
        self._missing_btn.setEnabled(False)
        action_layout.addWidget(self._missing_btn)

        action_layout.addStretch(1)

        # 关于按钮
        self._about_btn = self._create_action_button("ℹ️", "关于", "aboutBtn")
        self._about_btn.clicked.connect(self._on_about)
        action_layout.addWidget(self._about_btn)

        body_layout.addWidget(self._action_panel, stretch=22)

        main_layout.addLayout(body_layout, stretch=1)

        # ========== Footer (28px) ==========
        self._footer = QFrame()
        self._footer.setFixedHeight(28)
        self._footer.setObjectName("footer")

        footer_layout = QHBoxLayout(self._footer)
        footer_layout.setContentsMargins(12, 0, 12, 0)
        footer_layout.addStretch(1)

        version_label = QLabel("v2.0.0")
        version_label.setObjectName("versionLabel")
        footer_layout.addWidget(version_label)

        main_layout.addWidget(self._footer)

        # 初始化按钮状态
        self._update_action_buttons()

    def _create_toolbar_button(self, icon: str, text: str) -> QPushButton:
        """创建工具栏按钮"""
        btn = QPushButton(f"{icon} {text}")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(28)
        btn.setObjectName("toolbarBtn")
        return btn

    def _create_action_button(self, icon: str, text: str, object_name: str = "",
                              primary: bool = False, danger: bool = False) -> QPushButton:
        """创建操作栏按钮"""
        btn = QPushButton(f"  {icon}  {text}")
        btn.setObjectName(object_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(36)
        btn.setFlat(True)
        return btn

    def _apply_theme(self) -> None:
        """应用主题样式"""
        p = theme_manager.PALETTES.get(theme_manager.current_theme, {})

        bg_primary = p.get("bg_primary", "#1e1e1e")
        bg_secondary = p.get("bg_secondary", "#252526")
        bg_tertiary = p.get("bg_tertiary", "#2d2d30")
        bg_hover = p.get("bg_hover", "#3e3e42")
        accent = p.get("accent", "#007acc")
        accent_hover = p.get("accent_hover", "#1c97ea")
        text_primary = p.get("text_primary", "#cccccc")
        text_bright = p.get("text_bright", "#ffffff")
        text_secondary = p.get("text_secondary", "#858585")
        border = p.get("border", "#3e3e42")
        error = p.get("error", "#f44747")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_primary};
            }}

            /* Header */
            QFrame#header {{
                background-color: #151515;
                border-bottom: 1px solid {border};
            }}
            QLabel#titleLabel {{
                color: {text_bright};
            }}
            QPushButton#navTabActive {{
                background-color: transparent;
                color: {accent};
                border: none;
                border-bottom: 2px solid {accent};
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton#navTabInactive {{
                background-color: transparent;
                color: {text_secondary};
                border: none;
                padding: 8px 16px;
                font-size: 13px;
            }}
            QPushButton#navTabInactive:hover {{
                color: {text_primary};
            }}

            /* Toolbar */
            QFrame#toolbar {{
                background-color: {bg_secondary};
                border-bottom: 1px solid {border};
            }}
            QPushButton#toolbarBtn {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton#toolbarBtn:hover {{
                background-color: {bg_hover};
                color: {text_bright};
            }}
            QLineEdit#filterEdit {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QLineEdit#filterEdit:focus {{
                border-color: {accent};
            }}
            QLabel#sortLabel {{
                color: {text_secondary};
                font-size: 12px;
            }}
            QComboBox#sortCombo {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QComboBox#sortCombo::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox#sortCombo QAbstractItemView {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border};
                selection-background-color: {accent};
            }}

            /* Project List Panel */
            QWidget#projectListPanel {{
                background-color: {bg_primary};
            }}
            QListWidget#projectList {{
                background-color: {bg_primary};
                border: none;
                outline: none;
            }}
            QListWidget#projectList::item {{
                padding: 0px;
                margin: 0px;
            }}

            /* Action Panel */
            QFrame#actionPanel {{
                background-color: {bg_secondary};
                border-left: 1px solid {border};
            }}
            QPushButton#editBtn, QPushButton#renameBtn, QPushButton#duplicateBtn,
            QPushButton#tagBtn, QPushButton#aboutBtn {{
                background-color: transparent;
                color: {text_primary};
                border: none;
                padding: 8px 12px;
                text-align: left;
                font-size: 12px;
                border-radius: 4px;
            }}
            QPushButton#editBtn:hover, QPushButton#renameBtn:hover,
            QPushButton#duplicateBtn:hover, QPushButton#tagBtn:hover,
            QPushButton#aboutBtn:hover {{
                background-color: {bg_hover};
                color: {text_bright};
            }}
            QPushButton#runBtn {{
                background-color: transparent;
                color: {accent};
                border: none;
                padding: 8px 12px;
                text-align: left;
                font-size: 12px;
                font-weight: 500;
                border-radius: 4px;
            }}
            QPushButton#runBtn:hover {{
                background-color: {bg_hover};
            }}
            QPushButton#removeBtn {{
                background-color: transparent;
                color: {error};
                border: none;
                padding: 8px 12px;
                text-align: left;
                font-size: 12px;
                border-radius: 4px;
            }}
            QPushButton#removeBtn:hover {{
                background-color: {bg_hover};
            }}
            QPushButton#missingBtn {{
                background-color: transparent;
                color: {text_secondary};
                border: none;
                padding: 8px 12px;
                text-align: left;
                font-size: 12px;
                border-radius: 4px;
            }}
            QFrame#separator {{
                background-color: {border};
                margin: 4px 0;
            }}

            /* Footer */
            QFrame#footer {{
                background-color: #181818;
                border-top: 1px solid {border};
            }}
            QLabel#versionLabel {{
                color: {text_secondary};
                font-size: 10px;
            }}
        """)

    def _load_projects(self) -> None:
        """加载项目列表"""
        self._projects = self._scan_projects()
        self._apply_filter_and_sort()

    def _scan_projects(self) -> List[Dict[str, Any]]:
        """扫描项目目录"""
        projects = []
        try:
            from presentation.project.manager import project_manager
            workspace = project_manager.workspace_dir / "data" if project_manager.workspace_dir else Path("./data")
        except Exception:
            workspace = Path("./data")

        if not workspace.exists():
            return projects

        for project_dir in workspace.iterdir():
            if project_dir.is_dir() and project_dir.suffix == ".agent":
                project_file = project_dir / "project.json"
                if project_file.exists():
                    try:
                        with open(project_file, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        # 获取最后修改时间
                        mtime = project_dir.stat().st_mtime
                        modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

                        projects.append({
                            "name": data.get("name", project_dir.name),
                            "path": str(project_dir),
                            "template": data.get("template", "blank"),
                            "modified": modified,
                            "created": data.get("created", modified),
                        })
                    except Exception as e:
                        logger.warning(f"读取项目失败 {project_dir}: {e}")

        return projects

    def _apply_filter_and_sort(self) -> None:
        """应用筛选和排序"""
        # 筛选
        filter_text = self._filter_edit.text().lower()
        if filter_text:
            self._filtered_projects = [
                p for p in self._projects
                if filter_text in p.get("name", "").lower()
                or filter_text in p.get("path", "").lower()
            ]
        else:
            self._filtered_projects = self._projects.copy()

        # 排序
        sort_type = self._sort_combo.currentText()
        if sort_type == "项目名称":
            self._filtered_projects.sort(key=lambda x: x.get("name", ""))
        elif sort_type == "创建时间":
            self._filtered_projects.sort(key=lambda x: x.get("created", ""))
        else:  # 最近编辑（默认）
            self._filtered_projects.sort(key=lambda x: x.get("modified", ""), reverse=True)

        self._refresh_list()

    def _refresh_list(self) -> None:
        """刷新列表显示"""
        self._project_list.clear()

        for project in self._filtered_projects:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, project)
            item.setSizeHint(QSize(0, 72))
            self._project_list.addItem(item)

        if not self._filtered_projects:
            # 显示空状态
            item = QListWidgetItem("暂无项目，点击「新建」创建")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
            text_secondary = p.get("text_secondary", "#858585")
            # 空状态样式通过 delegate 处理较复杂，这里简单处理
            self._project_list.addItem(item)

        self._selected_project = None
        self._update_action_buttons()

    def _on_filter_changed(self, text: str) -> None:
        """筛选文本改变"""
        self._apply_filter_and_sort()

    def _on_sort_changed(self, text: str) -> None:
        """排序方式改变"""
        self._apply_filter_and_sort()

    def _on_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """选择改变"""
        if current:
            self._selected_project = current.data(Qt.ItemDataRole.UserRole)
        else:
            self._selected_project = None
        self._update_action_buttons()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """双击项目"""
        project = item.data(Qt.ItemDataRole.UserRole)
        if project:
            self._selected_project = project
            self._on_run_project()

    def _update_action_buttons(self) -> None:
        """更新操作按钮状态"""
        has_selection = self._selected_project is not None
        self._edit_btn.setEnabled(has_selection)
        self._run_btn.setEnabled(has_selection)
        self._rename_btn.setEnabled(has_selection)
        self._duplicate_btn.setEnabled(has_selection)
        self._tag_btn.setEnabled(has_selection)
        self._remove_btn.setEnabled(has_selection)

    def _on_new_project(self) -> None:
        """新建项目"""
        self.new_project_requested.emit()
        self.accept()

    def _on_import_project(self) -> None:
        """导入项目"""
        path = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if path:
            self.project_selected.emit(path)
            self.accept()

    def _on_edit_project(self) -> None:
        """编辑项目"""
        if self._selected_project:
            self.project_selected.emit(self._selected_project["path"])
            self.accept()

    def _on_run_project(self) -> None:
        """运行项目"""
        if self._selected_project:
            self.project_selected.emit(self._selected_project["path"])
            self.accept()

    def _on_rename_project(self) -> None:
        """重命名项目"""
        if not self._selected_project:
            return

        from PyQt6.QtWidgets import QInputDialog

        old_name = self._selected_project["name"]
        new_name, ok = QInputDialog.getText(
            self, "重命名项目", "新项目名称:", text=old_name
        )

        if ok and new_name and new_name != old_name:
            try:
                project_path = Path(self._selected_project["path"])
                project_file = project_path / "project.json"

                if project_file.exists():
                    with open(project_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    data["name"] = new_name

                    with open(project_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    logger.info(f"项目重命名: {old_name} -> {new_name}")
                    self._load_projects()
            except Exception as e:
                logger.error(f"重命名项目失败: {e}")
                QMessageBox.critical(self, "错误", f"重命名失败: {e}")

    def _on_duplicate_project(self) -> None:
        """创建项目副本"""
        if not self._selected_project:
            return

        from PyQt6.QtWidgets import QInputDialog

        old_name = self._selected_project["name"]
        new_name, ok = QInputDialog.getText(
            self, "创建副本", "新项目名称:", text=f"{old_name}_副本"
        )

        if ok and new_name:
            try:
                src_path = Path(self._selected_project["path"])

                # 生成新的项目目录名
                new_dir_name = new_name.replace(" ", "_") + ".agent"
                dst_path = src_path.parent / new_dir_name

                if dst_path.exists():
                    QMessageBox.warning(self, "警告", "目标项目已存在")
                    return

                # 复制项目
                shutil.copytree(src_path, dst_path)

                # 更新 project.json
                project_file = dst_path / "project.json"
                if project_file.exists():
                    with open(project_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    data["name"] = new_name
                    data["created"] = datetime.now().strftime("%Y-%m-%d")

                    with open(project_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                logger.info(f"项目副本已创建: {new_name}")
                self._load_projects()
            except Exception as e:
                logger.error(f"创建副本失败: {e}")
                QMessageBox.critical(self, "错误", f"创建副本失败: {e}")

    def _on_manage_tags(self) -> None:
        """管理标签"""
        QMessageBox.information(self, "管理标签", "标签管理功能开发中...")

    def _on_remove_project(self) -> None:
        """移除项目"""
        if not self._selected_project:
            return

        project_name = self._selected_project["name"]
        project_path = self._selected_project["path"]

        reply = QMessageBox.question(
            self,
            "确认移除",
            f"确定要移除项目 '{project_name}' 吗？\n\n项目文件将被删除，此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(project_path)
                logger.info(f"项目已移除: {project_path}")
                self._load_projects()
            except Exception as e:
                logger.error(f"移除项目失败: {e}")
                QMessageBox.critical(self, "错误", f"移除项目失败: {e}")

    def _on_about(self) -> None:
        """关于"""
        QMessageBox.about(
            self,
            "关于 Game Master Agent IDE",
            "<h2>Game Master Agent IDE</h2>"
            "<p>版本: v2.0.0</p>"
            "<p>基于 PyQt6 的 AI 游戏主控代理开发环境</p>"
        )

    def refresh(self) -> None:
        """刷新项目列表"""
        self._load_projects()

    def refresh_theme(self) -> None:
        """刷新主题（外部调用）"""
        self._apply_theme()
