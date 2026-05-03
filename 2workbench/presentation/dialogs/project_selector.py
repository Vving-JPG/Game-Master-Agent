"""项目选择器 — 像 Godot 一样的启动界面

启动时显示项目列表，让用户选择或创建新项目。
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Dict

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QScrollArea, QFrame,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from foundation.logger import get_logger

logger = get_logger(__name__)


class ProjectCard(QFrame):
    """项目卡片"""
    
    clicked = pyqtSignal(str)  # 发射项目路径
    delete_requested = pyqtSignal(str)  # 发射删除请求
    
    def __init__(self, project_info: Dict[str, str], parent=None):
        super().__init__(parent)
        self.project_path = project_info.get("path", "")
        self._setup_ui(project_info)
        
    def _setup_ui(self, info: Dict[str, str]) -> None:
        """设置 UI"""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            ProjectCard {
                background-color: #2d2d2d;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                padding: 10px;
            }
            ProjectCard:hover {
                background-color: #3d3d3d;
                border: 2px solid #0078d4;
            }
            QPushButton#deleteBtn {
                background-color: transparent;
                color: #ff4444;
                border: 1px solid #ff4444;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
            }
            QPushButton#deleteBtn:hover {
                background-color: #ff4444;
                color: white;
            }
        """)
        self.setFixedSize(280, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # 顶部区域：项目名称和删除按钮
        top_layout = QHBoxLayout()
        
        # 项目名称
        name_label = QLabel(info.get("name", "未知项目"))
        name_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #ffffff;")
        name_label.setWordWrap(True)
        top_layout.addWidget(name_label, stretch=1)
        
        # 删除按钮
        delete_btn = QPushButton("🗑️")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setToolTip("删除项目")
        delete_btn.clicked.connect(self._on_delete)
        top_layout.addWidget(delete_btn)
        
        layout.addLayout(top_layout)
        
        # 模板类型
        template = info.get("template", "blank")
        template_label = QLabel(f"模板: {template}")
        template_label.setStyleSheet("color: #888888;")
        layout.addWidget(template_label)
        
        # 最后修改时间
        modified = info.get("modified", "")
        if modified:
            modified_label = QLabel(f"修改: {modified}")
            modified_label.setStyleSheet("color: #666666; font-size: 11px;")
            layout.addWidget(modified_label)
        
        layout.addStretch()
        
    def _on_delete(self):
        """删除按钮点击"""
        # 阻止事件传播，避免触发卡片的点击事件
        self.delete_requested.emit(self.project_path)
        
    def mousePressEvent(self, event):
        """点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project_path)


class ProjectSelector(QDialog):
    """项目选择器对话框"""
    
    project_selected = pyqtSignal(str)  # 发射选中的项目路径
    new_project_requested = pyqtSignal()  # 请求创建新项目
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Game Master Agent IDE - 选择项目")
        self.setMinimumSize(900, 600)
        self._setup_ui()
        self._load_projects()
        
    def _setup_ui(self) -> None:
        """设置 UI"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton#secondary {
                background-color: #3d3d3d;
            }
            QPushButton#secondary:hover {
                background-color: #4d4d4d;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # 标题
        title = QLabel("🎮 Game Master Agent IDE")
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 副标题
        subtitle = QLabel("选择项目或创建新项目")
        subtitle.setFont(QFont("Microsoft YaHei", 12))
        subtitle.setStyleSheet("color: #888888;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # 项目列表区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.projects_container = QWidget()
        self.projects_layout = QHBoxLayout(self.projects_container)
        self.projects_layout.setSpacing(20)
        self.projects_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.projects_layout.addStretch()
        
        scroll.setWidget(self.projects_container)
        layout.addWidget(scroll)
        
        layout.addSpacing(20)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.open_other_btn = QPushButton("📂 打开其他项目...")
        self.open_other_btn.setObjectName("secondary")
        self.open_other_btn.clicked.connect(self._on_open_other)
        button_layout.addWidget(self.open_other_btn)
        
        button_layout.addStretch()
        
        self.new_project_btn = QPushButton("➕ 新建项目")
        self.new_project_btn.clicked.connect(self._on_new_project)
        button_layout.addWidget(self.new_project_btn)
        
        layout.addLayout(button_layout)
        
    def _load_projects(self) -> None:
        """加载项目列表"""
        projects = self._scan_projects()
        
        # 清除旧的项目卡片（保留 stretch）
        while self.projects_layout.count() > 1:
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加项目卡片
        for project in projects:
            card = ProjectCard(project)
            card.clicked.connect(self._on_project_clicked)
            card.delete_requested.connect(self._on_delete_project)
            self.projects_layout.insertWidget(self.projects_layout.count() - 1, card)
            
        if not projects:
            # 显示提示
            no_project_label = QLabel("暂无项目，点击「新建项目」创建")
            no_project_label.setStyleSheet("color: #666666; font-size: 16px;")
            no_project_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.projects_layout.insertWidget(0, no_project_label)
            
    def _scan_projects(self) -> List[Dict[str, str]]:
        """扫描项目目录"""
        projects = []
        # 使用 project_manager 获取工作区目录，避免依赖当前工作目录
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
                        import json
                        with open(project_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            
                        # 获取最后修改时间
                        mtime = project_dir.stat().st_mtime
                        from datetime import datetime
                        modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                        
                        projects.append({
                            "name": data.get("name", project_dir.name),
                            "path": str(project_dir),
                            "template": data.get("template", "blank"),
                            "modified": modified,
                        })
                    except Exception as e:
                        logger.warning(f"读取项目失败 {project_dir}: {e}")
                        
        # 按修改时间排序
        projects.sort(key=lambda x: x.get("modified", ""), reverse=True)
        return projects
        
    def _on_project_clicked(self, path: str) -> None:
        """项目被点击"""
        self.project_selected.emit(path)
        self.accept()

    def _on_delete_project(self, path: str) -> None:
        """删除项目"""
        from PyQt6.QtWidgets import QMessageBox
        import shutil

        # 获取项目名称
        project_name = Path(path).name

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除项目 '{project_name}' 吗？\n\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 删除项目目录
                shutil.rmtree(path)
                logger.info(f"项目已删除: {path}")
                # 刷新列表
                self._load_projects()
            except Exception as e:
                logger.error(f"删除项目失败: {e}")
                QMessageBox.critical(self, "删除失败", f"删除项目时出错: {e}")

    def _on_new_project(self) -> None:
        """新建项目"""
        self.new_project_requested.emit()
        self.accept()

    def _on_open_other(self) -> None:
        """打开其他项目"""
        path = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if path:
            self.project_selected.emit(path)
            self.accept()

    def refresh(self) -> None:
        """刷新项目列表"""
        self._load_projects()
