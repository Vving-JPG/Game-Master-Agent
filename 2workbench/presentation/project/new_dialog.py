"""新建项目对话框 — 仿 Godot 风格"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame,
    QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from presentation.project.manager import PROJECT_TEMPLATES
from presentation.theme.manager import theme_manager
from foundation.logger import get_logger

logger = get_logger(__name__)


class TemplateCard(QFrame):
    """模板卡片"""

    def __init__(self, icon: str, name: str, template_key: str, color: str, parent=None):
        super().__init__(parent)
        self.template_key = template_key
        self._selected = False
        self._color = color
        self._setup_ui(icon, name, color)

    def _setup_ui(self, icon: str, name: str, color: str) -> None:
        """设置 UI"""
        self.setFixedSize(140, 120)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        # 图标
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 36))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # 名称
        name_label = QLabel(name)
        name_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Medium))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        self._update_style()

    def _update_style(self) -> None:
        """更新样式"""
        p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
        bg_secondary = p.get("bg_secondary", "#252526")
        bg_hover = p.get("bg_hover", "#3e3e42")
        border = p.get("border", "#3e3e42")
        accent = p.get("accent", "#007acc")

        if self._selected:
            self.setStyleSheet(f"""
                TemplateCard {{
                    background-color: {bg_hover};
                    border: 2px solid {self._color};
                    border-radius: 8px;
                }}
                QLabel {{
                    color: #ffffff;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                TemplateCard {{
                    background-color: {bg_secondary};
                    border: 2px solid {border};
                    border-radius: 8px;
                }}
                TemplateCard:hover {{
                    background-color: {bg_hover};
                    border: 2px solid {self._color};
                }}
                QLabel {{
                    color: #cccccc;
                }}
            """)

    def set_selected(self, selected: bool) -> None:
        """设置选中状态"""
        self._selected = selected
        self._update_style()

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_selected(True)
            # 通知父组件
            parent = self.parent()
            if parent:
                parent.on_template_selected(self.template_key)


class NewProjectDialog(QDialog):
    """新建 Agent 项目对话框 — 仿 Godot 风格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建新项目")
        self.setMinimumSize(560, 500)
        self.resize(560, 500)

        # 默认项目目录
        try:
            from presentation.project.manager import project_manager
            self._project_dir = project_manager.workspace_dir / "data" if project_manager.workspace_dir else Path("./data")
        except Exception:
            self._project_dir = Path("./data")

        self._selected_template = "blank"
        self._template_cards: dict[str, TemplateCard] = {}

        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        """设置 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(32, 32, 32, 32)

        # 标题
        title = QLabel("创建新项目")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title.setObjectName("titleLabel")
        main_layout.addWidget(title)

        main_layout.addSpacing(8)

        # 项目名称
        name_label = QLabel("项目名称")
        name_label.setObjectName("fieldLabel")
        main_layout.addWidget(name_label)

        self._name_edit = QLineEdit()
        self._name_edit.setObjectName("nameEdit")
        self._name_edit.setPlaceholderText("my_agent")
        self._name_edit.setFixedHeight(36)
        main_layout.addWidget(self._name_edit)

        main_layout.addSpacing(8)

        # 项目路径
        path_label = QLabel("项目路径")
        path_label.setObjectName("fieldLabel")
        main_layout.addWidget(path_label)

        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)

        self._path_edit = QLineEdit()
        self._path_edit.setObjectName("pathEdit")
        self._path_edit.setText(str(self._project_dir))
        self._path_edit.setReadOnly(True)
        self._path_edit.setFixedHeight(36)
        path_layout.addWidget(self._path_edit, stretch=1)

        self._browse_btn = QPushButton("浏览...")
        self._browse_btn.setObjectName("browseBtn")
        self._browse_btn.setFixedWidth(80)
        self._browse_btn.setFixedHeight(36)
        self._browse_btn.clicked.connect(self._on_browse_path)
        path_layout.addWidget(self._browse_btn)

        main_layout.addLayout(path_layout)

        main_layout.addSpacing(8)

        # 选择模板
        template_label = QLabel("选择模板")
        template_label.setObjectName("fieldLabel")
        main_layout.addWidget(template_label)

        # 模板卡片布局
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        cards_layout.addStretch(1)

        # 空白项目卡片
        self._blank_card = TemplateCard("📄", "空白项目", "blank", "#569cd6")
        self._template_cards["blank"] = self._blank_card
        cards_layout.addWidget(self._blank_card)

        # TRPG 游戏卡片
        self._trpg_card = TemplateCard("🎲", "TRPG 游戏", "trpg", "#4ec9b0")
        self._template_cards["trpg"] = self._trpg_card
        cards_layout.addWidget(self._trpg_card)

        # 对话机器人卡片
        self._chatbot_card = TemplateCard("🤖", "对话机器人", "chatbot", "#c586c0")
        self._template_cards["chatbot"] = self._chatbot_card
        cards_layout.addWidget(self._chatbot_card)

        cards_layout.addStretch(1)
        main_layout.addLayout(cards_layout)

        # 模板描述
        self._desc_label = QLabel("")
        self._desc_label.setObjectName("descLabel")
        self._desc_label.setWordWrap(True)
        self._desc_label.setMinimumHeight(40)
        main_layout.addWidget(self._desc_label)

        # 更新描述
        self._update_template_desc()

        main_layout.addStretch(1)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setObjectName("cancelBtn")
        self._cancel_btn.setFixedHeight(36)
        self._cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self._cancel_btn)

        button_layout.addStretch(1)

        self._create_btn = QPushButton("创建并运行")
        self._create_btn.setObjectName("createBtn")
        self._create_btn.setFixedHeight(36)
        self._create_btn.setDefault(True)
        self._create_btn.clicked.connect(self.accept)
        button_layout.addWidget(self._create_btn)

        main_layout.addLayout(button_layout)

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

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_primary};
            }}
            QLabel#titleLabel {{
                color: {text_bright};
            }}
            QLabel#fieldLabel {{
                color: {text_secondary};
                font-size: 12px;
            }}
            QLabel#descLabel {{
                color: {text_secondary};
                font-size: 12px;
                padding: 8px;
            }}
            QLineEdit#nameEdit, QLineEdit#pathEdit {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 13px;
            }}
            QLineEdit#nameEdit:focus {{
                border-color: {accent};
            }}
            QPushButton#browseBtn {{
                background-color: {bg_secondary};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton#browseBtn:hover {{
                background-color: {bg_hover};
                color: {text_bright};
            }}
            QPushButton#cancelBtn {{
                background-color: transparent;
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 13px;
            }}
            QPushButton#cancelBtn:hover {{
                background-color: {bg_hover};
                color: {text_bright};
            }}
            QPushButton#createBtn {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton#createBtn:hover {{
                background-color: {accent_hover};
            }}
        """)

    def on_template_selected(self, template_key: str) -> None:
        """模板被选中"""
        self._selected_template = template_key

        # 更新所有卡片的选中状态
        for key, card in self._template_cards.items():
            card.set_selected(key == template_key)

        self._update_template_desc()

    def _update_template_desc(self) -> None:
        """更新模板描述"""
        tmpl = PROJECT_TEMPLATES.get(self._selected_template)
        if tmpl:
            nodes = tmpl["graph"]["nodes"]
            edges = tmpl["graph"]["edges"]
            prompts = ", ".join(tmpl["prompts"].keys())
            desc = f"<b>{tmpl['name']}</b> — {tmpl['description']}<br>"
            desc += f"节点数: {len(nodes)} | 边数: {len(edges)} | Prompt模板: {prompts}"
            self._desc_label.setText(desc)
        else:
            self._desc_label.setText("")

    def _on_browse_path(self) -> None:
        """浏览选择项目保存位置"""
        path = QFileDialog.getExistingDirectory(
            self, "选择项目保存位置",
            str(self._project_dir),
        )
        if path:
            self._project_dir = Path(path)
            self._path_edit.setText(path)

    def get_project_data(self) -> dict:
        """获取用户输入的项目数据"""
        return {
            "name": self._name_edit.text().strip(),
            "template": self._selected_template,
            "description": "",
            "directory": str(self._project_dir),
        }
