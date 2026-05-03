"""主题管理器 — 支持多主题切换和自定义 QSS

使用方式:
    from presentation.theme.manager import theme_manager

    # 切换主题
    theme_manager.apply("dark")
    theme_manager.apply("light")

    # 获取当前主题色
    color = theme_manager.get_color("primary")
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor

THEME_DIR = Path(__file__).parent


class ThemeManager:
    """主题管理器"""

    # 默认调色板
    PALETTES = {
        "dark": {
            "bg_primary": "#1e1e1e",
            "bg_secondary": "#252526",
            "bg_tertiary": "#2d2d30",
            "bg_hover": "#3e3e42",
            "bg_active": "#094771",
            "text_primary": "#cccccc",
            "text_secondary": "#858585",
            "text_bright": "#ffffff",
            "border": "#3e3e42",
            "accent": "#007acc",
            "accent_hover": "#1c97ea",
            "success": "#4ec9b0",
            "warning": "#dcdcaa",
            "error": "#f44747",
            "info": "#569cd6",
            "scrollbar": "#424242",
            "scrollbar_hover": "#4f4f4f",
        },
        "light": {
            "bg_primary": "#ffffff",
            "bg_secondary": "#f3f3f3",
            "bg_tertiary": "#e8e8e8",
            "bg_hover": "#e8e8e8",
            "bg_active": "#0060c0",
            "text_primary": "#333333",
            "text_secondary": "#6e6e6e",
            "text_bright": "#000000",
            "border": "#d4d4d4",
            "accent": "#0066bf",
            "accent_hover": "#005ba4",
            "success": "#388a34",
            "warning": "#bf8803",
            "error": "#d32f2f",
            "info": "#1976d2",
            "scrollbar": "#c1c1c1",
            "scrollbar_hover": "#a8a8a8",
        },
    }

    def __init__(self):
        self._current_theme = "dark"
        self._custom_overrides: dict[str, str] = {}

    @property
    def current_theme(self) -> str:
        return self._current_theme

    def apply(self, theme_name: str) -> None:
        """应用主题

        Args:
            theme_name: "dark" 或 "light"
        """
        if theme_name not in self.PALETTES:
            return

        self._current_theme = theme_name
        app = QApplication.instance()
        if not app:
            return

        # 加载 QSS 文件
        qss_path = THEME_DIR / f"{theme_name}.qss"
        if qss_path.exists():
            qss = qss_path.read_text(encoding="utf-8")
            # 替换颜色变量
            palette = self.PALETTES[theme_name]
            for key, value in palette.items():
                qss = qss.replace(f"${{{key}}}", value)
            # 应用自定义覆盖
            for key, value in self._custom_overrides.items():
                qss = qss.replace(f"${{{key}}}", value)
            app.setStyleSheet(qss)

        # 通知所有 StyledButton 刷新样式
        self._refresh_styled_buttons()

    def _refresh_styled_buttons(self) -> None:
        """刷新所有 StyledButton 的样式"""
        app = QApplication.instance()
        if not app:
            return
        # 查找所有 StyledButton 并刷新
        from presentation.widgets.styled_button import StyledButton
        for widget in app.findChildren(StyledButton):
            widget._apply_style()

    def get_color(self, name: str) -> str:
        """获取当前主题的颜色值"""
        palette = self.PALETTES.get(self._current_theme, {})
        return palette.get(name, self._custom_overrides.get(name, "#000000"))

    def get_qcolor(self, name: str) -> QColor:
        """获取 QColor 对象"""
        return QColor(self.get_color(name))

    def set_custom_color(self, name: str, value: str) -> None:
        """设置自定义颜色覆盖"""
        self._custom_overrides[name] = value


# 全局单例
theme_manager = ThemeManager()
