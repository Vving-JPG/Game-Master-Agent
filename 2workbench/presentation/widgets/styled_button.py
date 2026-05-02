"""样式按钮 — 预设样式的按钮组件"""
from __future__ import annotations

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QSize


class StyledButton(QPushButton):
    """预设样式的按钮

    样式类型:
    - primary: 主要操作（蓝色）
    - secondary: 次要操作（灰色）
    - danger: 危险操作（红色）
    - success: 成功操作（绿色）
    - ghost: 透明背景
    """

    STYLES = {
        "primary": """
            QPushButton {
                background-color: ${accent};
                color: ${text_bright};
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: ${accent_hover}; }
            QPushButton:pressed { background-color: ${bg_active}; }
            QPushButton:disabled { background-color: ${bg_tertiary}; color: ${text_secondary}; }
        """,
        "secondary": """
            QPushButton {
                background-color: ${bg_tertiary};
                color: ${text_primary};
                border: 1px solid ${border};
                border-radius: 4px;
                padding: 6px 20px;
            }
            QPushButton:hover { background-color: ${bg_hover}; border-color: ${accent}; }
            QPushButton:pressed { background-color: ${accent}; color: ${text_bright}; }
        """,
        "danger": """
            QPushButton {
                background-color: ${error};
                color: ${text_bright};
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-weight: bold;
            }
            QPushButton:hover { opacity: 0.9; }
        """,
        "success": """
            QPushButton {
                background-color: ${success};
                color: ${text_bright};
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-weight: bold;
            }
            QPushButton:hover { opacity: 0.9; }
        """,
        "ghost": """
            QPushButton {
                background-color: transparent;
                color: ${text_primary};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: ${bg_hover}; }
        """,
    }

    def __init__(
        self,
        text: str = "",
        style_type: str = "secondary",
        parent=None,
    ):
        super().__init__(text, parent)
        self._style_type = style_type
        self._apply_style()

    def _apply_style(self) -> None:
        """应用样式"""
        from presentation.theme.manager import theme_manager
        template = self.STYLES.get(self._style_type, self.STYLES["secondary"])
        palette = theme_manager.PALETTES.get(theme_manager.current_theme, {})
        css = template
        for key, value in palette.items():
            css = css.replace(f"${{{key}}}", value)
        self.setStyleSheet(css)

    def set_style_type(self, style_type: str) -> None:
        """切换样式类型"""
        self._style_type = style_type
        self._apply_style()
