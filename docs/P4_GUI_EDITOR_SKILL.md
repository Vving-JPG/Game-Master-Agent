# P4: Presentation 层 — IDE 核心编辑器

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。
> **前置条件**: P0 Foundation + P1 Core + P2 LangGraph Agent + P3 Feature Services 已全部完成。

## 项目概述

你正在帮助用户将 **Game Master Agent V2** 的 `2workbench/` 目录重构为**四层架构**。

- **技术**: Python 3.11+ / PyQt6 / SQLite / LangGraph / uv
- **包管理器**: uv
- **开发 IDE**: Trae
- **本 Phase 目标**: 实现 Presentation 层的 IDE 核心编辑器组件，包括主窗口重构、Agent 项目管理器、LangGraph 可视化图编辑器、Prompt 管理器、工具/插件管理器。将现有 `_legacy/` 中的 UI 代码迁移到新的四层架构中。

### 架构约束

```
入口层 → Presentation (表现层) → Feature (功能层) → Core (核心层) → Foundation (基础层)
```

- ✅ Presentation 层**只依赖** Feature、Core 和 Foundation 层
- ❌ Presentation 层**绝对不能**被下层 import
- ✅ Presentation 层通过 EventBus 订阅 Feature 层事件，实现 UI 更新
- ✅ Presentation 层通过调用 Feature 层 API 触发业务操作
- ❌ Presentation 层**不直接操作数据库**，必须通过 Core 层 Repository
- ❌ Presentation 层**不直接调用 LLM**，必须通过 Feature 层

### 本 Phase (P4) 范围

1. **Presentation 基础设施** — 主题系统、全局样式、通用 Widget 基类
2. **主窗口重构** — 三栏布局、菜单栏、工具栏、状态栏
3. **Agent 项目管理器** — Agent 项目的创建/打开/保存/关闭
4. **LangGraph 可视化图编辑器** — 节点拖拽、连线、属性编辑、运行状态可视化
5. **Prompt 管理器** — Prompt 模板编辑、版本管理、变量注入、预览测试
6. **工具/插件管理器** — LangGraph Tool 注册、配置、测试
7. **集成测试**

### 现有代码参考

| 现有文件（`_legacy/`） | 参考内容 | 改进方向 |
|---------|---------|---------|
| `_legacy/main_window.py` | 三栏布局、工具栏、HTTP 服务 | 重构为模块化主窗口，拆分各面板 |
| `_legacy/app.py` | QApplication 入口、qasync | 保留入口，添加启动引导 |
| `_legacy/server.py` | HTTP API（GET/POST/PUT/DELETE） | 保留为调试工具，不作为核心架构 |
| `_legacy/widgets/resource_tree.py` | 资源树 | 重构为 Agent 项目资源树 |
| `_legacy/widgets/editor_stack.py` | 编辑器标签页 | 重构为多类型编辑器容器 |
| `_legacy/widgets/console_tabs.py` | 控制台 | 重构为运行时调试面板 |
| `_legacy/widgets/workflow_editor.py` | 工作流编辑器 | 重构为 LangGraph 图编辑器 |
| `_legacy/styles/dark_theme.qss` | VS Code Dark+ 主题 | 扩展为可配置主题系统 |

### P0/P1/P2/P3 产出（本 Phase 依赖）

```python
# Foundation
from foundation.event_bus import event_bus, Event
from foundation.config import settings
from foundation.logger import get_logger
from foundation.database import init_db, get_db
from foundation.llm import BaseLLMClient, LLMMessage, LLMResponse, StreamEvent
from foundation.llm.model_router import model_router
from foundation.cache import llm_cache
from foundation.resource_manager import ResourceManager

# Core
from core.state import AgentState, create_initial_state
from core.models import (
    World, Player, NPC, Memory, Quest, Item, Location,
    WorldRepo, PlayerRepo, NPCRepo, MemoryRepo, ItemRepo,
    QuestRepo, LogRepo, MetricsRepo, PromptRepo,
)
from core.calculators import roll_dice, attack, combat_round
from core.constants import NPC_TEMPLATES, STORY_TEMPLATES

# Feature
from feature.base import BaseFeature
from feature.registry import feature_registry
from feature.battle import BattleSystem
from feature.dialogue import DialogueSystem
from feature.quest import QuestSystem
from feature.item import ItemSystem
from feature.exploration import ExplorationSystem
from feature.narration import NarrationSystem
from feature.ai import GMAgent
from feature.ai.events import (
    TURN_START, TURN_END, AGENT_ERROR,
    LLM_STREAM_TOKEN, COMMAND_PARSED, COMMAND_EXECUTED,
)
```

---

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始"后，主动执行
4. **遇到错误先尝试修复**：3 次失败后再询问
5. **代码规范**：UTF-8，中文注释，PEP 8，类型注解
6. **UI 规范**：使用 QSS 样式表，支持主题切换，响应式布局
7. **EventBus 驱动**：UI 更新通过订阅 EventBus 事件触发，不使用定时器轮询
8. **异步安全**：LLM 调用和长时间操作使用 qasync，不阻塞 UI 线程

---

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **工作目录**: `2workbench/`
- **Presentation 层**: `2workbench/presentation/`
- **Legacy 参考**: `2workbench/_legacy/`

---

## 步骤

### Step 1: Presentation 基础设施 — 主题与通用组件

**目的**: 建立 Presentation 层的基础设施，包括主题系统、QSS 样式、通用 Widget 基类。

**参考**: `_legacy/styles/dark_theme.qss`

**方案**:

1.1 创建目录结构：

```
2workbench/presentation/
├── __init__.py
├── theme/
│   ├── __init__.py
│   ├── manager.py          # 主题管理器
│   ├── dark.qss            # Dark 主题
│   └── light.qss           # Light 主题
├── widgets/
│   ├── __init__.py
│   ├── base.py             # 通用 Widget 基类
│   ├── styled_button.py    # 样式按钮
│   ├── styled_label.py     # 样式标签
│   ├── search_bar.py       # 搜索栏
│   ├── icon_button.py      # 图标按钮
│   └── splitter.py         # 可拖拽分割器
└── resources/
    └── icons/              # 图标资源（占位）
```

1.2 创建 `2workbench/presentation/theme/manager.py`：

```python
# 2workbench/presentation/theme/manager.py
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
```

1.3 创建 `2workbench/presentation/theme/dark.qss`：

```css
/* Dark Theme — VS Code Dark+ 风格 */

/* 全局 */
QWidget {
    background-color: ${bg_primary};
    color: ${text_primary};
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    selection-background-color: ${accent};
    selection-color: ${text_bright};
}

/* 滚动条 */
QScrollBar:vertical {
    background: ${bg_primary};
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background: ${scrollbar};
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: ${scrollbar_hover};
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: ${bg_primary};
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: ${scrollbar};
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: ${scrollbar_hover};
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* 主窗口 */
QMainWindow {
    background-color: ${bg_primary};
}

/* 菜单栏 */
QMenuBar {
    background-color: ${bg_tertiary};
    color: ${text_primary};
    border-bottom: 1px solid ${border};
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: ${bg_hover};
}
QMenu {
    background-color: ${bg_secondary};
    color: ${text_primary};
    border: 1px solid ${border};
    padding: 4px;
}
QMenu::item:selected {
    background-color: ${accent};
    color: ${text_bright};
}

/* 工具栏 */
QToolBar {
    background-color: ${bg_tertiary};
    border-bottom: 1px solid ${border};
    spacing: 4px;
    padding: 2px;
}

/* 状态栏 */
QStatusBar {
    background-color: ${accent};
    color: ${text_bright};
    font-size: 12px;
}

/* 分割器 */
QSplitter::handle {
    background-color: ${border};
}
QSplitter::handle:horizontal {
    width: 1px;
}
QSplitter::handle:vertical {
    height: 1px;
}

/* 标签页 */
QTabWidget::pane {
    border: 1px solid ${border};
    background-color: ${bg_primary};
}
QTabBar::tab {
    background-color: ${bg_secondary};
    color: ${text_secondary};
    padding: 6px 16px;
    border: 1px solid ${border};
    border-bottom: none;
    margin-right: 1px;
}
QTabBar::tab:selected {
    background-color: ${bg_primary};
    color: ${text_bright};
    border-bottom: 2px solid ${accent};
}

/* 输入框 */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: ${bg_primary};
    color: ${text_primary};
    border: 1px solid ${border};
    border-radius: 3px;
    padding: 4px 8px;
    selection-background-color: ${accent};
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: ${accent};
}

/* 按钮 */
QPushButton {
    background-color: ${bg_tertiary};
    color: ${text_primary};
    border: 1px solid ${border};
    border-radius: 4px;
    padding: 5px 16px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: ${bg_hover};
    border-color: ${accent};
}
QPushButton:pressed {
    background-color: ${accent};
    color: ${text_bright};
}

/* 列表/树 */
QListView, QTreeView, QTreeWidget {
    background-color: ${bg_primary};
    color: ${text_primary};
    border: 1px solid ${border};
    alternate-background-color: ${bg_secondary};
    show-decoration-selected: 1;
}
QListView::item:selected, QTreeView::item:selected {
    background-color: ${bg_active};
    color: ${text_bright};
}
QListView::item:hover, QTreeView::item:hover {
    background-color: ${bg_hover};
}

/* 下拉框 */
QComboBox {
    background-color: ${bg_tertiary};
    color: ${text_primary};
    border: 1px solid ${border};
    border-radius: 3px;
    padding: 4px 8px;
    min-height: 24px;
}
QComboBox:hover {
    border-color: ${accent};
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: ${bg_secondary};
    color: ${text_primary};
    border: 1px solid ${border};
    selection-background-color: ${accent};
}

/* 对话框 */
QDialog {
    background-color: ${bg_secondary};
}

/* 分组框 */
QGroupBox {
    border: 1px solid ${border};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

/* 工具提示 */
QToolTip {
    background-color: ${bg_tertiary};
    color: ${text_primary};
    border: 1px solid ${border};
    padding: 4px;
}
```

1.4 创建 `2workbench/presentation/theme/light.qss`：

```css
/* Light Theme — 与 Dark 共享结构，仅颜色不同 */

QWidget {
    background-color: ${bg_primary};
    color: ${text_primary};
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    selection-background-color: ${accent};
    selection-color: ${text_bright};
}

/* 滚动条 */
QScrollBar:vertical {
    background: ${bg_primary};
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background: ${scrollbar};
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: ${scrollbar_hover};
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: ${bg_primary};
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: ${scrollbar};
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: ${scrollbar_hover};
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* 主窗口 */
QMainWindow {
    background-color: ${bg_primary};
}

/* 菜单栏 */
QMenuBar {
    background-color: ${bg_tertiary};
    color: ${text_primary};
    border-bottom: 1px solid ${border};
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: ${bg_hover};
}
QMenu {
    background-color: ${bg_secondary};
    color: ${text_primary};
    border: 1px solid ${border};
    padding: 4px;
}
QMenu::item:selected {
    background-color: ${accent};
    color: ${text_bright};
}

/* 工具栏 */
QToolBar {
    background-color: ${bg_tertiary};
    border-bottom: 1px solid ${border};
    spacing: 4px;
    padding: 2px;
}

/* 状态栏 */
QStatusBar {
    background-color: ${accent};
    color: ${text_bright};
    font-size: 12px;
}

/* 分割器 */
QSplitter::handle {
    background-color: ${border};
}
QSplitter::handle:horizontal {
    width: 1px;
}
QSplitter::handle:vertical {
    height: 1px;
}

/* 标签页 */
QTabWidget::pane {
    border: 1px solid ${border};
    background-color: ${bg_primary};
}
QTabBar::tab {
    background-color: ${bg_secondary};
    color: ${text_secondary};
    padding: 6px 16px;
    border: 1px solid ${border};
    border-bottom: none;
    margin-right: 1px;
}
QTabBar::tab:selected {
    background-color: ${bg_primary};
    color: ${text_bright};
    border-bottom: 2px solid ${accent};
}

/* 输入框 */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: ${bg_primary};
    color: ${text_primary};
    border: 1px solid ${border};
    border-radius: 3px;
    padding: 4px 8px;
    selection-background-color: ${accent};
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: ${accent};
}

/* 按钮 */
QPushButton {
    background-color: ${bg_tertiary};
    color: ${text_primary};
    border: 1px solid ${border};
    border-radius: 4px;
    padding: 5px 16px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: ${bg_hover};
    border-color: ${accent};
}
QPushButton:pressed {
    background-color: ${accent};
    color: ${text_bright};
}

/* 列表/树 */
QListView, QTreeView, QTreeWidget {
    background-color: ${bg_primary};
    color: ${text_primary};
    border: 1px solid ${border};
    alternate-background-color: ${bg_secondary};
    show-decoration-selected: 1;
}
QListView::item:selected, QTreeView::item:selected {
    background-color: ${bg_active};
    color: ${text_bright};
}
QListView::item:hover, QTreeView::item:hover {
    background-color: ${bg_hover};
}

/* 下拉框 */
QComboBox {
    background-color: ${bg_tertiary};
    color: ${text_primary};
    border: 1px solid ${border};
    border-radius: 3px;
    padding: 4px 8px;
    min-height: 24px;
}
QComboBox:hover {
    border-color: ${accent};
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: ${bg_secondary};
    color: ${text_primary};
    border: 1px solid ${border};
    selection-background-color: ${accent};
}

/* 对话框 */
QDialog {
    background-color: ${bg_secondary};
}

/* 分组框 */
QGroupBox {
    border: 1px solid ${border};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

/* 工具提示 */
QToolTip {
    background-color: ${bg_tertiary};
    color: ${text_primary};
    border: 1px solid ${border};
    padding: 4px;
}
```

1.5 创建 `2workbench/presentation/widgets/base.py`：

```python
# 2workbench/presentation/widgets/base.py
"""通用 Widget 基类 — 提供主题感知和 EventBus 集成"""
from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QWidget

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger


class BaseWidget(QWidget):
    """通用 Widget 基类

    提供:
    1. 自动日志
    2. EventBus 订阅管理（自动清理）
    3. 主题感知
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._subscriptions: list[tuple[str, Any]] = []
        self._logger = get_logger(f"ui.{self.__class__.__name__}")

    def subscribe(self, event_type: str, handler) -> None:
        """订阅 EventBus 事件"""
        event_bus.subscribe(event_type, handler)
        self._subscriptions.append((event_type, handler))

    def unsubscribe_all(self) -> None:
        """取消所有订阅"""
        for event_type, handler in self._subscriptions:
            event_bus.unsubscribe(event_type, handler)
        self._subscriptions.clear()

    def closeEvent(self, event) -> None:
        """关闭时自动清理订阅"""
        self.unsubscribe_all()
        super().closeEvent(event)

    def emit_event(self, event_type: str, data: dict | None = None) -> list:
        """发出 EventBus 事件"""
        event = Event(
            type=event_type,
            data=data or {},
            source=f"ui.{self.__class__.__name__}",
        )
        return event_bus.emit(event)
```

1.6 创建 `2workbench/presentation/widgets/styled_button.py`：

```python
# 2workbench/presentation/widgets/styled_button.py
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
```

1.7 创建 `2workbench/presentation/widgets/search_bar.py`：

```python
# 2workbench/presentation/widgets/search_bar.py
"""搜索栏 — 带图标和清除按钮的搜索输入框"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QCompleter,
)
from PyQt6.QtCore import pyqtSignal, Qt


class SearchBar(QWidget):
    """搜索栏组件"""

    search_changed = pyqtSignal(str)
    search_submitted = pyqtSignal(str)

    def __init__(self, placeholder: str = "搜索...", parent=None):
        super().__init__(parent)
        self._setup_ui(placeholder)

    def _setup_ui(self, placeholder: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText(placeholder)
        self._line_edit.setClearButtonEnabled(True)
        self._line_edit.textChanged.connect(self.search_changed.emit)
        self._line_edit.returnPressed.connect(
            lambda: self.search_submitted.emit(self._line_edit.text())
        )
        layout.addWidget(self._line_edit)

    def text(self) -> str:
        return self._line_edit.text()

    def set_text(self, text: str) -> None:
        self._line_edit.setText(text)

    def set_completer(self, completer: QCompleter) -> None:
        self._line_edit.setCompleter(completer)

    def set_placeholder(self, text: str) -> None:
        self._line_edit.setPlaceholderText(text)
```

1.8 创建各模块的 `__init__.py`：

```python
# 2workbench/presentation/__init__.py
"""Presentation 层 — UI 表现层"""
# 初始化时按需导入，避免循环依赖

# 2workbench/presentation/theme/__init__.py
"""主题系统"""
from presentation.theme.manager import theme_manager, ThemeManager
__all__ = ["theme_manager", "ThemeManager"]

# 2workbench/presentation/widgets/__init__.py
"""通用 Widget 组件"""
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton
from presentation.widgets.search_bar import SearchBar
__all__ = ["BaseWidget", "StyledButton", "SearchBar"]
```

1.9 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

# 测试主题管理器
from presentation.theme.manager import theme_manager

# 应用 dark 主题
theme_manager.apply('dark')
assert theme_manager.current_theme == 'dark'
color = theme_manager.get_color('accent')
assert color == '#007acc'
print(f'Dark 主题: accent={color}')

# 切换 light 主题
theme_manager.apply('light')
assert theme_manager.current_theme == 'light'
color = theme_manager.get_color('accent')
assert color == '#0066bf'
print(f'Light 主题: accent={color}')

# 测试 StyledButton
from presentation.widgets.styled_button import StyledButton
btn = StyledButton('测试按钮', style_type='primary')
assert btn.text() == '测试按钮'
print(f'按钮文本: {btn.text()}')

# 测试 SearchBar
from presentation.widgets.search_bar import SearchBar
search = SearchBar('搜索 Agent...')
assert search.text() == ''
print(f'搜索栏占位符已设置')

# 测试 BaseWidget
from presentation.widgets.base import BaseWidget
widget = BaseWidget()
print(f'BaseWidget 类名: {widget.__class__.__name__}')

print('✅ Presentation 基础设施测试通过')
"
```

**验收**:
- [ ] 目录结构创建完成
- [ ] ThemeManager 支持 dark/light 切换
- [ ] QSS 样式文件加载正常
- [ ] BaseWidget 带 EventBus 订阅管理
- [ ] StyledButton 支持 5 种预设样式
- [ ] SearchBar 组件可用
- [ ] 测试通过

---

### Step 2: 主窗口重构

**目的**: 重构主窗口为模块化三栏布局，拆分各面板为独立组件。

**参考**: `_legacy/main_window.py`

**方案**:

2.1 创建 `2workbench/presentation/main_window.py`：

```python
# 2workbench/presentation/main_window.py
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

from typing import Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QToolBar, QStatusBar, QTabWidget,
    QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Agent 项目浏览器（占位，Step 3 实现）
        self.project_tree = QLabel("📂 Agent 项目浏览器\n（Step 3 实现）")
        self.project_tree.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.project_tree.setStyleSheet("color: #858585; font-size: 14px;")
        layout.addWidget(self.project_tree)


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

    def add_tab(self, widget: QWidget, title: str) -> int:
        """添加标签页"""
        return self.tab_widget.addTab(widget, title)

    def current_tab(self) -> QWidget | None:
        """获取当前标签页"""
        return self.tab_widget.currentWidget()


class RightPanel(BaseWidget):
    """右侧面板 — 属性编辑器 + 状态监控"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 属性面板（占位）
        self.props_panel = QLabel("📋 属性面板\n（Step 4 实现）")
        self.props_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.props_panel.setStyleSheet("color: #858585; font-size: 14px;")
        self.tab_widget.addTab(self.props_panel, "属性")

        # Agent 状态面板
        self.status_panel = QLabel("📊 Agent 状态\n（Step 5 实现）")
        self.status_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_panel.setStyleSheet("color: #858585; font-size: 14px;")
        self.tab_widget.addTab(self.status_panel, "状态")


class MainWindow(QMainWindow):
    """主窗口"""

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

        # 应用主题
        theme_manager.apply("dark")

        logger.info("主窗口初始化完成")

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
        tools_menu.addAction("Prompt 管理器")
        tools_menu.addAction("工具/插件管理器")
        tools_menu.addAction("知识库编辑器")
        tools_menu.addAction("评估工作台")

        # Help 菜单
        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self) -> None:
        """设置工具栏"""
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

    def _setup_statusbar(self) -> None:
        """设置状态栏"""
        statusbar = self.statusBar()

        self._status_connection = QLabel("🔌 未连接")
        statusbar.addWidget(self._status_connection)

        self._status_agent = QLabel("🤖 Agent: 未加载")
        statusbar.addPermanentWidget(self._status_agent)

        self._status_model = QLabel("🧠 模型: --")
        statusbar.addPermanentWidget(self._status_model)

        self._status_theme = QLabel("🎨 Dark")
        statusbar.addPermanentWidget(self._status_theme)

    def _setup_eventbus(self) -> None:
        """设置 EventBus 订阅"""
        event_bus.subscribe("feature.ai.turn_start", self._on_turn_start)
        event_bus.subscribe("feature.ai.turn_end", self._on_turn_end)
        event_bus.subscribe("feature.ai.agent_error", self._on_agent_error)
        event_bus.subscribe("feature.ai.llm_stream_token", self._on_stream_token)

    # --- EventBus 回调 ---

    def _on_turn_start(self, event: Event) -> None:
        turn = event.get("turn", 0)
        self._status_agent.setText(f"🤖 Agent: 运行中 (Turn {turn})")

    def _on_turn_end(self, event: Event) -> None:
        self._status_agent.setText("🤖 Agent: 空闲")

    def _on_agent_error(self, event: Event) -> None:
        error = event.get("error", "未知错误")
        self._status_agent.setText(f"🤖 Agent: 错误")
        self.statusBar().showMessage(f"Agent 错误: {error}", 5000)

    def _on_stream_token(self, event: Event) -> None:
        token = event.get("token", "")
        # 流式 token 更新（后续 Step 在控制台面板显示）
        pass

    # --- 菜单动作 ---

    def _on_new_project(self) -> None:
        """新建 Agent 项目（Step 3 实现）"""
        self.statusBar().showMessage("新建 Agent 项目... (Step 3 实现)", 3000)

    def _on_open_project(self) -> None:
        """打开项目"""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "打开 Agent 项目", "", "Agent 项目 (*.agent.json);;所有文件 (*)"
        )
        if path:
            self.statusBar().showMessage(f"打开项目: {path}", 3000)

    def _on_save(self) -> None:
        """保存"""
        self.statusBar().showMessage("项目已保存", 2000)

    def _on_run_agent(self) -> None:
        """运行 Agent"""
        self.statusBar().showMessage("启动 Agent... (Step 5 实现)", 3000)

    def _on_stop_agent(self) -> None:
        """停止 Agent"""
        self.statusBar().showMessage("停止 Agent", 2000)

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

    def closeEvent(self, event) -> None:
        """关闭窗口"""
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
```

2.2 更新 `2workbench/presentation/__init__.py`：

```python
# 2workbench/presentation/__init__.py
"""Presentation 层 — UI 表现层"""
from presentation.main_window import MainWindow
from presentation.theme.manager import theme_manager

__all__ = ["MainWindow", "theme_manager"]
```

2.3 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.main_window import MainWindow

window = MainWindow()
assert window.windowTitle() == 'Game Master Agent IDE'
assert window.minimumWidth() == 1200

# 检查面板存在
assert hasattr(window, 'left_panel')
assert hasattr(window, 'center_panel')
assert hasattr(window, 'right_panel')

# 检查菜单栏
menubar = window.menuBar()
assert menubar is not None
actions = menubar.actions()
assert len(actions) >= 5  # File/Edit/View/Agent/Tools/Help
print(f'菜单项: {[a.text() for a in actions]}')

# 检查状态栏
statusbar = window.statusBar()
assert statusbar is not None

# 检查主题
from presentation.theme.manager import theme_manager
assert theme_manager.current_theme == 'dark'

print('✅ 主窗口测试通过')
"
```

**验收**:
- [ ] 三栏布局（左 240px / 中 flex / 右 300px）
- [ ] 菜单栏（File/Edit/View/Agent/Tools/Help）
- [ ] 工具栏（新建/打开/保存/运行/停止/主题切换）
- [ ] 状态栏（连接状态/Agent 状态/模型/主题）
- [ ] EventBus 订阅（turn_start/turn_end/agent_error/stream_token）
- [ ] 主题切换（Dark/Light）
- [ ] 测试通过

---

### Step 3: Agent 项目管理器

**目的**: 实现 Agent 项目的创建/打开/保存/关闭，管理项目文件结构。

**方案**:

3.1 定义 Agent 项目结构：

```
<project_name>.agent/
├── project.json          # 项目元数据
├── graph.json            # LangGraph 图定义
├── prompts/              # Prompt 模板
│   ├── system.md
│   ├── narrative.md
│   └── combat.md
├── tools/                # 自定义工具
│   └── custom_tools.py
├── knowledge/            # 知识库
│   └── world_lore.md
├── config.json           # Agent 运行配置
├── saves/                # 存档
│   └── save_001.db
└── logs/                 # 运行日志
```

3.2 创建 `2workbench/presentation/project/manager.py`：

```python
# 2workbench/presentation/project/manager.py
"""Agent 项目管理器 — 项目的 CRUD 操作

职责:
1. 创建新 Agent 项目（初始化目录结构和默认文件）
2. 打开已有项目（加载 project.json）
3. 保存项目（序列化当前状态）
4. 关闭项目（清理资源）
5. 项目模板选择
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentProjectConfig:
    """Agent 项目配置"""
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    created_at: str = ""
    updated_at: str = ""
    template: str = "blank"  # blank / trpg / chatbot / workflow
    graph_file: str = "graph.json"
    config_file: str = "config.json"

    # 运行配置
    default_model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
    stream_enabled: bool = True

    # 功能开关
    features: dict[str, bool] = field(default_factory=lambda: {
        "battle": True,
        "dialogue": True,
        "quest": True,
        "item": True,
        "exploration": True,
        "narration": True,
    })


# 项目模板
PROJECT_TEMPLATES = {
    "blank": {
        "name": "空白项目",
        "description": "从零开始创建 Agent",
        "graph": {
            "nodes": [
                {"id": "input", "type": "input", "label": "用户输入", "position": {"x": 100, "y": 200}},
                {"id": "reasoning", "type": "llm", "label": "LLM 推理", "position": {"x": 400, "y": 200}},
                {"id": "output", "type": "output", "label": "输出", "position": {"x": 700, "y": 200}},
            ],
            "edges": [
                {"from": "input", "to": "reasoning"},
                {"from": "reasoning", "to": "output"},
            ],
        },
        "prompts": {
            "system": "你是一个 AI 助手。请根据用户输入提供帮助。",
        },
        "config": {
            "default_model": "deepseek-chat",
            "temperature": 0.7,
        },
    },
    "trpg": {
        "name": "TRPG 游戏",
        "description": "桌面角色扮演游戏 Agent",
        "graph": {
            "nodes": [
                {"id": "handle_event", "type": "event", "label": "事件处理", "position": {"x": 100, "y": 200}},
                {"id": "build_prompt", "type": "prompt", "label": "Prompt 组装", "position": {"x": 300, "y": 200}},
                {"id": "llm_reasoning", "type": "llm", "label": "LLM 推理", "position": {"x": 500, "y": 200}},
                {"id": "parse_output", "type": "parser", "label": "命令解析", "position": {"x": 700, "y": 150}},
                {"id": "execute_commands", "type": "executor", "label": "命令执行", "position": {"x": 700, "y": 250}},
                {"id": "update_memory", "type": "memory", "label": "记忆更新", "position": {"x": 900, "y": 200}},
            ],
            "edges": [
                {"from": "handle_event", "to": "build_prompt"},
                {"from": "build_prompt", "to": "llm_reasoning"},
                {"from": "llm_reasoning", "to": "parse_output"},
                {"from": "parse_output", "to": "execute_commands"},
                {"from": "execute_commands", "to": "update_memory"},
            ],
        },
        "prompts": {
            "system": "你是一位经验丰富的游戏主持人（Game Master）。你负责引导玩家在一个奇幻世界中冒险。\n\n## 世界观\n{world_description}\n\n## 玩家信息\n{player_info}\n\n## 当前场景\n{current_scene}\n\n## 规则\n1. 保持沉浸感，用第二人称描述\n2. 每次回复控制在 200 字以内\n3. 遇到战斗时使用 JSON 格式发出战斗指令",
            "narrative": "请根据以下游戏状态生成叙事描述：\n\n{context}",
            "combat": "战斗叙事生成规则：\n1. 描述要生动有力\n2. 突出关键动作\n3. 包含伤害数值",
        },
        "config": {
            "default_model": "deepseek-chat",
            "temperature": 0.8,
            "features": {
                "battle": True,
                "dialogue": True,
                "quest": True,
                "item": True,
                "exploration": True,
                "narration": True,
            },
        },
    },
    "chatbot": {
        "name": "对话机器人",
        "description": "通用对话 Agent",
        "graph": {
            "nodes": [
                {"id": "input", "type": "input", "label": "用户输入", "position": {"x": 100, "y": 200}},
                {"id": "context", "type": "memory", "label": "上下文检索", "position": {"x": 300, "y": 200}},
                {"id": "llm", "type": "llm", "label": "LLM 生成", "position": {"x": 500, "y": 200}},
                {"id": "output", "type": "output", "label": "回复输出", "position": {"x": 700, "y": 200}},
            ],
            "edges": [
                {"from": "input", "to": "context"},
                {"from": "context", "to": "llm"},
                {"from": "llm", "to": "output"},
            ],
        },
        "prompts": {
            "system": "你是一个友好的 AI 助手。请用简洁清晰的方式回答用户问题。",
        },
        "config": {
            "default_model": "deepseek-chat",
            "temperature": 0.7,
        },
    },
}


class ProjectManager:
    """Agent 项目管理器"""

    def __init__(self, workspace_dir: str | Path | None = None):
        self._workspace = Path(workspace_dir) if workspace_dir else Path.cwd()
        self._current_project: AgentProjectConfig | None = None
        self._project_path: Path | None = None

    @property
    def current_project(self) -> AgentProjectConfig | None:
        return self._current_project

    @property
    def project_path(self) -> Path | None:
        return self._project_path

    @property
    def is_open(self) -> bool:
        return self._current_project is not None

    def create_project(
        self,
        name: str,
        template: str = "blank",
        directory: str | Path | None = None,
        **overrides,
    ) -> Path:
        """创建新 Agent 项目

        Args:
            name: 项目名称
            template: 模板名称（blank/trpg/chatbot）
            directory: 创建目录（默认 workspace）

        Returns:
            项目路径
        """
        if template not in PROJECT_TEMPLATES:
            raise ValueError(f"未知模板: {template}，可选: {list(PROJECT_TEMPLATES.keys())}")

        base_dir = Path(directory) if directory else self._workspace
        project_dir = base_dir / f"{name}.agent"

        if project_dir.exists():
            raise FileExistsError(f"项目已存在: {project_dir}")

        # 创建目录结构
        project_dir.mkdir(parents=True)
        (project_dir / "prompts").mkdir()
        (project_dir / "tools").mkdir()
        (project_dir / "knowledge").mkdir()
        (project_dir / "saves").mkdir()
        (project_dir / "logs").mkdir()

        # 获取模板
        tmpl = PROJECT_TEMPLATES[template]
        now = datetime.now().isoformat()

        # 创建 project.json
        config = AgentProjectConfig(
            name=name,
            description=overrides.get("description", tmpl["description"]),
            created_at=now,
            updated_at=now,
            template=template,
            **{k: v for k, v in overrides.items() if k in AgentProjectConfig.__dataclass_fields__},
        )

        # 合并模板配置
        tmpl_config = tmpl.get("config", {})
        if "default_model" in tmpl_config:
            config.default_model = tmpl_config["default_model"]
        if "temperature" in tmpl_config:
            config.temperature = tmpl_config["temperature"]
        if "features" in tmpl_config:
            config.features = tmpl_config["features"]

        self._save_project_json(project_dir, config)

        # 创建 graph.json
        graph_path = project_dir / "graph.json"
        graph_path.write_text(
            json.dumps(tmpl["graph"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 创建 Prompt 文件
        prompts = tmpl.get("prompts", {})
        for prompt_name, content in prompts.items():
            prompt_path = project_dir / "prompts" / f"{prompt_name}.md"
            prompt_path.write_text(content, encoding="utf-8")

        # 创建 config.json
        config_path = project_dir / "config.json"
        config_path.write_text(
            json.dumps({
                "default_model": config.default_model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "stream_enabled": config.stream_enabled,
                "features": config.features,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info(f"项目创建成功: {project_dir}")
        event_bus.emit(Event(type="ui.project.created", data={"path": str(project_dir), "name": name}))

        return project_dir

    def open_project(self, path: str | Path) -> AgentProjectConfig:
        """打开项目

        Args:
            path: project.json 路径或项目目录

        Returns:
            项目配置
        """
        project_dir = Path(path)
        if project_dir.is_file():
            project_dir = project_dir.parent

        project_json = project_dir / "project.json"
        if not project_json.exists():
            raise FileNotFoundError(f"项目文件不存在: {project_json}")

        config = self._load_project_json(project_json)
        self._current_project = config
        self._project_path = project_dir

        logger.info(f"项目已打开: {project_dir} ({config.name})")
        event_bus.emit(Event(type="ui.project.opened", data={
            "path": str(project_dir),
            "name": config.name,
            "template": config.template,
        }))

        return config

    def save_project(self) -> None:
        """保存当前项目"""
        if not self._current_project or not self._project_path:
            raise RuntimeError("没有打开的项目")

        self._current_project.updated_at = datetime.now().isoformat()
        self._save_project_json(self._project_path, self._current_project)

        logger.info(f"项目已保存: {self._project_path}")
        event_bus.emit(Event(type="ui.project.saved", data={
            "path": str(self._project_path),
            "name": self._current_project.name,
        }))

    def close_project(self) -> None:
        """关闭当前项目"""
        if self._current_project:
            name = self._current_project.name
            event_bus.emit(Event(type="ui.project.closing", data={"name": name}))

        self._current_project = None
        self._project_path = None

        logger.info("项目已关闭")
        event_bus.emit(Event(type="ui.project.closed", data={}))

    def load_graph(self) -> dict:
        """加载 LangGraph 图定义"""
        if not self._project_path:
            return {}
        graph_path = self._project_path / "graph.json"
        if not graph_path.exists():
            return {}
        return json.loads(graph_path.read_text(encoding="utf-8"))

    def save_graph(self, graph_data: dict) -> None:
        """保存 LangGraph 图定义"""
        if not self._project_path:
            raise RuntimeError("没有打开的项目")
        graph_path = self._project_path / "graph.json"
        graph_path.write_text(
            json.dumps(graph_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_prompt(self, name: str) -> str:
        """加载 Prompt 模板"""
        if not self._project_path:
            return ""
        prompt_path = self._project_path / "prompts" / f"{name}.md"
        if not prompt_path.exists():
            return ""
        return prompt_path.read_text(encoding="utf-8")

    def save_prompt(self, name: str, content: str) -> None:
        """保存 Prompt 模板"""
        if not self._project_path:
            raise RuntimeError("没有打开的项目")
        prompt_path = self._project_path / "prompts" / f"{name}.md"
        prompt_path.write_text(content, encoding="utf-8")

    def list_prompts(self) -> list[str]:
        """列出所有 Prompt 模板"""
        if not self._project_path:
            return []
        prompts_dir = self._project_path / "prompts"
        if not prompts_dir.exists():
            return []
        return [p.stem for p in prompts_dir.glob("*.md")]

    def _save_project_json(self, project_dir: Path, config: AgentProjectConfig) -> None:
        """保存 project.json"""
        project_json = project_dir / "project.json"
        project_json.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_project_json(self, path: Path) -> AgentProjectConfig:
        """加载 project.json"""
        data = json.loads(path.read_text(encoding="utf-8"))
        return AgentProjectConfig(**data)


# 全局单例
project_manager = ProjectManager()
```

3.3 创建 `2workbench/presentation/project/__init__.py`：

```python
# 2workbench/presentation/project/__init__.py
"""Agent 项目管理"""
from presentation.project.manager import (
    ProjectManager, project_manager, AgentProjectConfig,
    PROJECT_TEMPLATES,
)
__all__ = ["ProjectManager", "project_manager", "AgentProjectConfig", "PROJECT_TEMPLATES"]
```

3.4 创建项目创建对话框 `2workbench/presentation/project/new_dialog.py`：

```python
# 2workbench/presentation/project/new_dialog.py
"""新建项目对话框"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QDialogButtonBox,
    QLabel,
)
from PyQt6.QtCore import Qt

from presentation.project.manager import PROJECT_TEMPLATES


class NewProjectDialog(QDialog):
    """新建 Agent 项目对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建 Agent 项目")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 表单
        form = QFormLayout()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("my_agent")
        form.addRow("项目名称:", self._name_edit)

        self._template_combo = QComboBox()
        for key, tmpl in PROJECT_TEMPLATES.items():
            self._template_combo.addItem(f"{tmpl['name']} — {tmpl['description']}", key)
        form.addRow("项目模板:", self._template_combo)

        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(80)
        self._desc_edit.setPlaceholderText("项目描述（可选）")
        form.addRow("描述:", self._desc_edit)

        layout.addLayout(form)

        # 模板预览
        self._preview_label = QLabel()
        self._preview_label.setStyleSheet("color: #858585; padding: 8px;")
        self._preview_label.setWordWrap(True)
        layout.addWidget(self._preview_label)
        self._update_preview()

        self._template_combo.currentIndexChanged.connect(self._update_preview)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_preview(self) -> None:
        """更新模板预览"""
        key = self._template_combo.currentData()
        if key and key in PROJECT_TEMPLATES:
            tmpl = PROJECT_TEMPLATES[key]
            nodes = tmpl["graph"]["nodes"]
            edges = tmpl["graph"]["edges"]
            self._preview_label.setText(
                f"模板: {tmpl['name']}\n"
                f"节点数: {len(nodes)} | 边数: {len(edges)}\n"
                f"Prompt 模板: {', '.join(tmpl['prompts'].keys())}"
            )

    def get_project_data(self) -> dict:
        """获取用户输入的项目数据"""
        return {
            "name": self._name_edit.text().strip(),
            "template": self._template_combo.currentData() or "blank",
            "description": self._desc_edit.toPlainText().strip(),
        }
```

3.5 测试：

```bash
cd 2workbench ; python -c "
import tempfile, os, json, shutil

from presentation.project.manager import ProjectManager, PROJECT_TEMPLATES

# 创建临时工作目录
tmp_dir = tempfile.mkdtemp()

try:
    pm = ProjectManager(workspace_dir=tmp_dir)

    # 测试创建项目
    path = pm.create_project('test_agent', template='blank', directory=tmp_dir)
    assert path.exists()
    assert (path / 'project.json').exists()
    assert (path / 'graph.json').exists()
    assert (path / 'prompts').exists()
    assert (path / 'tools').exists()
    assert (path / 'knowledge').exists()
    assert (path / 'saves').exists()
    assert (path / 'logs').exists()
    print(f'✅ 项目创建成功: {path}')

    # 测试创建 TRPG 项目
    trpg_path = pm.create_project('my_trpg', template='trpg', directory=tmp_dir)
    assert (trpg_path / 'prompts' / 'system.md').exists()
    assert (trpg_path / 'prompts' / 'narrative.md').exists()
    assert (trpg_path / 'prompts' / 'combat.md').exists()
    print(f'✅ TRPG 项目创建成功: {trpg_path}')

    # 测试打开项目
    config = pm.open_project(trpg_path)
    assert config.name == 'my_trpg'
    assert config.template == 'trpg'
    assert pm.is_open
    print(f'✅ 项目打开成功: {config.name}')

    # 测试加载图定义
    graph = pm.load_graph()
    assert 'nodes' in graph
    assert 'edges' in graph
    assert len(graph['nodes']) == 6
    print(f'✅ 图定义加载成功: {len(graph[\"nodes\"])} 节点')

    # 测试 Prompt 管理
    prompts = pm.list_prompts()
    assert 'system' in prompts
    assert 'narrative' in prompts
    print(f'✅ Prompt 列表: {prompts}')

    system_prompt = pm.load_prompt('system')
    assert '游戏主持人' in system_prompt
    print(f'✅ System Prompt 加载成功 ({len(system_prompt)} 字符)')

    # 测试保存 Prompt
    pm.save_prompt('test', '这是一个测试 Prompt')
    assert pm.load_prompt('test') == '这是一个测试 Prompt'
    print('✅ Prompt 保存/加载成功')

    # 测试保存项目
    pm.save_project()
    print('✅ 项目保存成功')

    # 测试关闭项目
    pm.close_project()
    assert not pm.is_open
    print('✅ 项目关闭成功')

    # 测试模板列表
    assert 'blank' in PROJECT_TEMPLATES
    assert 'trpg' in PROJECT_TEMPLATES
    assert 'chatbot' in PROJECT_TEMPLATES
    print(f'✅ 模板列表: {list(PROJECT_TEMPLATES.keys())}')

    print('✅ Agent 项目管理器测试通过')

finally:
    shutil.rmtree(tmp_dir)
"
```

**验收**:
- [ ] 项目创建（3 种模板：blank/trpg/chatbot）
- [ ] 项目目录结构（prompts/tools/knowledge/saves/logs）
- [ ] 项目打开/保存/关闭
- [ ] 图定义加载/保存
- [ ] Prompt 模板加载/保存/列表
- [ ] EventBus 事件通知（created/opened/saved/closed）
- [ ] 测试通过

---

### Step 4: LangGraph 可视化图编辑器

**目的**: 实现可视化的 LangGraph 图编辑器，支持节点拖拽、连线、属性编辑。

**参考**: `_legacy/widgets/workflow_editor.py`

**方案**:

4.1 创建 `2workbench/presentation/editor/graph_editor.py`：

```python
# 2workbench/presentation/editor/graph_editor.py
"""LangGraph 可视化图编辑器

功能:
1. 节点拖拽布局
2. 节点间连线
3. 节点属性编辑
4. 运行时状态可视化（高亮当前执行节点）
5. 缩放和平移

使用 QGraphicsScene/QGraphicsView 实现。

从 _legacy/widgets/workflow_editor.py 重构。
"""
from __future__ import annotations

import json
from typing import Any

from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsItem,
    QGraphicsPathItem, QGraphicsTextItem, QGraphicsRectItem,
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDialog, QLineEdit, QTextEdit, QComboBox, QDialogButtonBox,
    QMenu,
)
from PyQt6.QtCore import (
    Qt, QPointF, QRectF, QLineF, pyqtSignal,
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont,
    QPainterPath, QPolygonF, QWheelEvent,
)

from foundation.logger import get_logger
from presentation.theme.manager import theme_manager

logger = get_logger(__name__)


# 节点类型 → 颜色映射
NODE_COLORS = {
    "input": ("#4ec9b0", "输入"),       # 青色
    "output": ("#4ec9b0", "输出"),      # 青色
    "llm": ("#569cd6", "LLM"),         # 蓝色
    "prompt": ("#dcdcaa", "Prompt"),    # 黄色
    "parser": ("#ce9178", "解析器"),    # 橙色
    "executor": ("#c586c0", "执行器"),  # 紫色
    "memory": ("#6a9955", "记忆"),      # 绿色
    "event": ("#d4d4d4", "事件"),       # 灰色
    "condition": ("#f44747", "条件"),    # 红色
    "custom": ("#9cdcfe", "自定义"),    # 浅蓝
}


class GraphNodeItem(QGraphicsRectItem):
    """图节点 — 可拖拽的矩形节点"""

    def __init__(
        self,
        node_id: str,
        node_type: str = "custom",
        label: str = "",
        position: dict | None = None,
    ):
        width = 160
        height = 60
        super().__init__(0, 0, width, height)

        self.node_id = node_id
        self.node_type = node_type
        self.label = label or node_id

        # 位置
        x = position.get("x", 0) if position else 0
        y = position.get("y", 0) if position else 0
        self.setPos(x, y)

        # 样式
        color_hex, type_label = NODE_COLORS.get(node_type, ("#9cdcfe", "自定义"))
        self._color = QColor(color_hex)

        self.setBrush(QBrush(self._color))
        self.setPen(QPen(QColor("#3e3e42"), 2))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(1)

        # 标签文本
        self._label_item = QGraphicsTextItem(self.label, self)
        self._label_item.setDefaultTextColor(QColor("#ffffff"))
        font = QFont("Microsoft YaHei", 10, QFont.Weight.Bold)
        self._label_item.setFont(font)
        # 居中
        text_rect = self._label_item.boundingRect()
        self._label_item.setPos(
            (width - text_rect.width()) / 2,
            (height - text_rect.height()) / 2 - 6,
        )

        # 类型标签
        self._type_item = QGraphicsTextItem(type_label, self)
        self._type_item.setDefaultTextColor(QColor("#cccccc"))
        type_font = QFont("Microsoft YaHei", 8)
        self._type_item.setFont(type_font)
        type_rect = self._type_item.boundingRect()
        self._type_item.setPos(
            (width - type_rect.width()) / 2,
            height - type_rect.height() - 4,
        )

        # 运行状态
        self._is_running = False

    def set_running(self, running: bool) -> None:
        """设置运行状态高亮"""
        self._is_running = running
        if running:
            self.setPen(QPen(QColor("#ffffff"), 3))
        else:
            self.setPen(QPen(QColor("#3e3e42"), 2))
        self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        """自定义绘制"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._is_running:
            # 运行中: 发光效果
            glow_pen = QPen(QColor("#ffffff"), 4)
            painter.setPen(glow_pen)
            painter.setBrush(QBrush(self._color))
            painter.drawRoundedRect(self.rect(), 8, 8)
        else:
            super().paint(painter, option, widget)

    def itemChange(self, change, value):
        """位置变化时通知"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # 通知场景更新连线
            scene = self.scene()
            if scene and hasattr(scene, "update_edges"):
                scene.update_edges()
        return super().itemChange(change, value)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "position": {
                "x": int(self.pos().x()),
                "y": int(self.pos().y()),
            },
        }

    def contextMenuEvent(self, event) -> None:
        """右键菜单"""
        menu = QMenu()
        menu.addAction("编辑属性", self._edit_properties)
        menu.addAction("删除节点", self._delete)
        menu.exec(event.screenPos())

    def _edit_properties(self) -> None:
        """编辑节点属性"""
        dialog = NodePropertyDialog(self.node_id, self.node_type, self.label)
        if dialog.exec():
            data = dialog.get_data()
            self.node_type = data["type"]
            self.label = data["label"]
            self._label_item.setPlainText(self.label)
            # 更新颜色
            color_hex, _ = NODE_COLORS.get(self.node_type, ("#9cdcfe", "自定义"))
            self._color = QColor(color_hex)
            self.setBrush(QBrush(self._color))

    def _delete(self) -> None:
        """删除节点"""
        scene = self.scene()
        if scene:
            scene.removeItem(self)


class GraphEdgeItem(QGraphicsPathItem):
    """图边 — 连接两个节点的曲线"""

    def __init__(self, source: GraphNodeItem, target: GraphNodeItem):
        super().__init__()
        self.source = source
        self.target = target
        self.setPen(QPen(QColor("#858585"), 2))
        self.setZValue(0)
        self.update_path()

    def update_path(self) -> None:
        """更新连线路径"""
        source_rect = self.source.rect()
        target_rect = self.target.rect()

        # 计算连接点（右侧中点 → 左侧中点）
        start = self.source.pos() + QPointF(source_rect.width(), source_rect.height() / 2)
        end = self.target.pos() + QPointF(0, target_rect.height() / 2)

        # 贝塞尔曲线
        path = QPainterPath()
        path.moveTo(start)
        ctrl_offset = abs(end.x() - start.x()) * 0.5
        path.cubicTo(
            start + QPointF(ctrl_offset, 0),
            end - QPointF(ctrl_offset, 0),
            end,
        )
        self.setPath(path)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "from": self.source.node_id,
            "to": self.target.node_id,
        }


class GraphScene(QGraphicsScene):
    """图场景 — 管理节点和边"""

    node_selected = pyqtSignal(str)  # 节点 ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nodes: dict[str, GraphNodeItem] = {}
        self._edges: list[GraphEdgeItem] = []
        self.setBackgroundBrush(QBrush(QColor("#1e1e1e")))

    def add_node(self, node_id: str, node_type: str, label: str, position: dict | None = None) -> GraphNodeItem:
        """添加节点"""
        node = GraphNodeItem(node_id, node_type, label, position)
        self.addItem(node)
        self._nodes[node_id] = node
        return node

    def add_edge(self, source_id: str, target_id: str) -> GraphEdgeItem | None:
        """添加边"""
        source = self._nodes.get(source_id)
        target = self._nodes.get(target_id)
        if not source or not target:
            return None
        edge = GraphEdgeItem(source, target)
        self.addItem(edge)
        self._edges.append(edge)
        return edge

    def remove_node(self, node_id: str) -> None:
        """删除节点及其连线"""
        node = self._nodes.pop(node_id, None)
        if node:
            # 删除相关边
            self._edges = [
                e for e in self._edges
                if e.source.node_id != node_id and e.target.node_id != node_id
            ]
            for edge in self._edges[:]:
                if edge.scene():
                    pass  # 保留有效边
            self.removeItem(node)

    def set_running_node(self, node_id: str | None) -> None:
        """高亮运行中的节点"""
        for nid, node in self._nodes.items():
            node.set_running(nid == node_id)

    def update_edges(self) -> None:
        """更新所有连线位置"""
        for edge in self._edges:
            edge.update_path()

    def load_graph(self, graph_data: dict) -> None:
        """从字典加载图"""
        self.clear()
        self._nodes.clear()
        self._edges.clear()

        # 添加节点
        for node_data in graph_data.get("nodes", []):
            self.add_node(
                node_id=node_data["id"],
                node_type=node_data.get("type", "custom"),
                label=node_data.get("label", node_data["id"]),
                position=node_data.get("position"),
            )

        # 添加边
        for edge_data in graph_data.get("edges", []):
            self.add_edge(edge_data["from"], edge_data["to"])

    def to_dict(self) -> dict:
        """导出为字典"""
        return {
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "edges": [edge.to_dict() for edge in self._edges],
        }

    def clear(self) -> None:
        """清空场景"""
        self._nodes.clear()
        self._edges.clear()
        super().clear()


class GraphEditorView(QGraphicsView):
    """图编辑器视图 — 支持缩放和平移"""

    def __init__(self, scene: GraphScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self._zoom = 1.0

    def wheelEvent(self, event: QWheelEvent) -> None:
        """鼠标滚轮缩放"""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom *= factor
        self._zoom = max(0.3, min(3.0, self._zoom))
        self.setTransform(self.transform().scale(factor, factor))

    def fit_to_view(self) -> None:
        """适应视图"""
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = 1.0


class NodePropertyDialog(QDialog):
    """节点属性编辑对话框"""

    def __init__(self, node_id: str, node_type: str, label: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"节点属性 — {node_id}")
        self.setMinimumWidth(350)
        self._setup_ui(node_id, node_type, label)

    def _setup_ui(self, node_id: str, node_type: str, label: str) -> None:
        layout = QFormLayout(self)

        self._id_edit = QLineEdit(node_id)
        self._id_edit.setEnabled(False)
        layout.addRow("节点 ID:", self._id_edit)

        self._type_combo = QComboBox()
        for type_key, (color, type_label) in NODE_COLORS.items():
            self._type_combo.addItem(f"{type_label} ({type_key})", type_key)
        # 选中当前类型
        idx = self._type_combo.findData(node_type)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        layout.addRow("节点类型:", self._type_combo)

        self._label_edit = QLineEdit(label)
        layout.addRow("标签:", self._label_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "id": self._id_edit.text(),
            "type": self._type_combo.currentData() or "custom",
            "label": self._label_edit.text(),
        }


class GraphEditorWidget(QWidget):
    """图编辑器组件 — 场景 + 视图 + 工具栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        from presentation.widgets.styled_button import StyledButton

        self._btn_fit = StyledButton("适应视图", style_type="ghost")
        self._btn_fit.clicked.connect(self.fit_to_view)
        toolbar.addWidget(self._btn_fit)

        self._btn_add_node = StyledButton("+ 添加节点", style_type="ghost")
        self._btn_add_node.clicked.connect(self._add_node_dialog)
        toolbar.addWidget(self._btn_add_node)

        self._btn_clear = StyledButton("清空", style_type="ghost")
        self._btn_clear.clicked.connect(self.clear)
        toolbar.addWidget(self._btn_clear)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 场景和视图
        self._scene = GraphScene()
        self._view = GraphEditorView(self._scene)
        layout.addWidget(self._view)

    def load_graph(self, graph_data: dict) -> None:
        """加载图定义"""
        self._scene.load_graph(graph_data)
        # 延迟适应视图
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.fit_to_view)

    def get_graph(self) -> dict:
        """获取当前图定义"""
        return self._scene.to_dict()

    def set_running_node(self, node_id: str | None) -> None:
        """高亮运行中的节点"""
        self._scene.set_running_node(node_id)

    def fit_to_view(self) -> None:
        """适应视图"""
        self._view.fit_to_view()

    def clear(self) -> None:
        """清空图"""
        self._scene.clear()

    def _add_node_dialog(self) -> None:
        """添加节点对话框"""
        dialog = NodePropertyDialog("new_node", "custom", "新节点")
        if dialog.exec():
            data = dialog.get_data()
            self._scene.add_node(
                node_id=data["id"],
                node_type=data["type"],
                label=data["label"],
                position={"x": 200, "y": 200},
            )
```

4.2 创建 `2workbench/presentation/editor/__init__.py`：

```python
# 2workbench/presentation/editor/__init__.py
"""编辑器组件"""
from presentation.editor.graph_editor import GraphEditorWidget, GraphScene
__all__ = ["GraphEditorWidget", "GraphScene"]
```

4.3 测试：

```bash
cd 2workbench ; python -c "
import sys, json
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.editor.graph_editor import GraphEditorWidget

editor = GraphEditorWidget()

# 测试加载 TRPG 图定义
trpg_graph = {
    'nodes': [
        {'id': 'handle_event', 'type': 'event', 'label': '事件处理', 'position': {'x': 100, 'y': 200}},
        {'id': 'build_prompt', 'type': 'prompt', 'label': 'Prompt 组装', 'position': {'x': 300, 'y': 200}},
        {'id': 'llm_reasoning', 'type': 'llm', 'label': 'LLM 推理', 'position': {'x': 500, 'y': 200}},
        {'id': 'parse_output', 'type': 'parser', 'label': '命令解析', 'position': {'x': 700, 'y': 150}},
        {'id': 'execute_commands', 'type': 'executor', 'label': '命令执行', 'position': {'x': 700, 'y': 250}},
        {'id': 'update_memory', 'type': 'memory', 'label': '记忆更新', 'position': {'x': 900, 'y': 200}},
    ],
    'edges': [
        {'from': 'handle_event', 'to': 'build_prompt'},
        {'from': 'build_prompt', 'to': 'llm_reasoning'},
        {'from': 'llm_reasoning', 'to': 'parse_output'},
        {'from': 'parse_output', 'to': 'execute_commands'},
        {'from': 'execute_commands', 'to': 'update_memory'},
    ],
}

editor.load_graph(trpg_graph)

# 验证导出
exported = editor.get_graph()
assert len(exported['nodes']) == 6
assert len(exported['edges']) == 5
print(f'图编辑器: {len(exported[\"nodes\"])} 节点, {len(exported[\"edges\"])} 边')

# 测试运行状态高亮
editor.set_running_node('llm_reasoning')
print('✅ 运行状态高亮设置成功')

editor.set_running_node(None)
print('✅ 运行状态高亮清除成功')

# 测试清空
editor.clear()
assert len(editor.get_graph()['nodes']) == 0
print('✅ 图清空成功')

print('✅ LangGraph 可视化图编辑器测试通过')
"
```

**验收**:
- [ ] GraphNodeItem 支持拖拽和选择
- [ ] GraphEdgeItem 贝塞尔曲线连线
- [ ] GraphScene 管理节点和边
- [ ] GraphEditorView 支持缩放和平移
- [ ] 节点类型颜色映射（10 种类型）
- [ ] 运行状态高亮
- [ ] 图定义加载/导出
- [ ] 节点属性编辑对话框
- [ ] 测试通过

---

### Step 5: Prompt 管理器

**目的**: 实现 Prompt 模板的编辑、版本管理、变量注入和预览测试。

**方案**:

5.1 创建 `2workbench/presentation/editor/prompt_editor.py`：

```python
# 2workbench/presentation/editor/prompt_editor.py
"""Prompt 管理器 — 模板编辑、版本管理、变量注入、预览测试

功能:
1. Prompt 模板列表（左侧）
2. Prompt 编辑器（中央，Markdown 高亮）
3. 变量面板（右侧，自动提取 {variable}）
4. 版本历史
5. 预览/测试面板
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QLabel, QPushButton, QFormLayout, QDialog,
    QDialogButtonBox, QComboBox, QTextBrowser,
    QMenu,
)
from PyQt6.QtCore import pyqtSignal, Qt

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton
from presentation.widgets.search_bar import SearchBar

logger = get_logger(__name__)


@dataclass
class PromptVersion:
    """Prompt 版本"""
    content: str
    timestamp: str = ""
    note: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class PromptEditorWidget(BaseWidget):
    """Prompt 管理器组件"""

    prompt_changed = pyqtSignal(str, str)  # name, content

    def __init__(self, parent=None):
        super().__init__(parent)
        self._prompts: dict[str, str] = {}  # name -> content
        self._versions: dict[str, list[PromptVersion]] = {}  # name -> versions
        self._current_prompt: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: Prompt 列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self._search = SearchBar("搜索 Prompt...")
        left_layout.addWidget(self._search)

        self._prompt_list = QListWidget()
        self._prompt_list.currentRowChanged.connect(self._on_prompt_selected)
        self._prompt_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._prompt_list.customContextMenuRequested.connect(self._on_list_context_menu)
        left_layout.addWidget(self._prompt_list)

        self._btn_new = StyledButton("+ 新建 Prompt", style_type="primary")
        self._btn_new.clicked.connect(self._new_prompt)
        left_layout.addWidget(self._btn_new)

        splitter.addWidget(left)

        # 中央: 编辑器
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(4, 4, 4, 4)

        # Prompt 名称
        name_layout = QHBoxLayout()
        self._name_label = QLabel("Prompt: ")
        self._name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self._name_edit = QLineEdit()
        self._name_edit.setReadOnly(True)
        name_layout.addWidget(self._name_label)
        name_layout.addWidget(self._name_edit, 1)
        center_layout.addLayout(name_layout)

        # 编辑器
        self._editor = QTextEdit()
        self._editor.setPlaceholderText("在此编辑 Prompt 模板...\n\n使用 {variable} 定义变量")
        self._editor.textChanged.connect(self._on_text_changed)
        center_layout.addWidget(self._editor)

        # 底部工具栏
        toolbar = QHBoxLayout()
        self._btn_save = StyledButton("💾 保存", style_type="primary")
        self._btn_save.clicked.connect(self._save_prompt)
        toolbar.addWidget(self._btn_save)

        self._btn_preview = StyledButton("👁 预览", style_type="secondary")
        self._btn_preview.clicked.connect(self._preview_prompt)
        toolbar.addWidget(self._btn_preview)

        self._btn_history = StyledButton("📜 历史", style_type="secondary")
        self._btn_history.clicked.connect(self._show_history)
        toolbar.addWidget(self._btn_history)

        toolbar.addStretch()

        self._var_count_label = QLabel("变量: 0")
        self._var_count_label.setStyleSheet("color: #858585;")
        toolbar.addWidget(self._var_count_label)

        center_layout.addLayout(toolbar)
        splitter.addWidget(center)

        # 右侧: 变量面板
        right = QWidget()
        right.setMaximumWidth(250)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        var_label = QLabel("📋 变量列表")
        var_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        right_layout.addWidget(var_label)

        self._var_list = QListWidget()
        right_layout.addWidget(self._var_list)

        # 变量值编辑
        self._var_value_edit = QLineEdit()
        self._var_value_edit.setPlaceholderText("变量值（预览用）")
        right_layout.addWidget(self._var_value_edit)

        self._btn_set_var = StyledButton("设置变量值", style_type="ghost")
        self._btn_set_var.clicked.connect(self._set_variable_value)
        right_layout.addWidget(self._btn_set_var)

        # 预览区
        preview_label = QLabel("👁 预览")
        preview_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 8px;")
        right_layout.addWidget(preview_label)

        self._preview_browser = QTextBrowser()
        self._preview_browser.setStyleSheet("font-size: 12px;")
        right_layout.addWidget(self._preview_browser)

        splitter.addWidget(right)

        splitter.setSizes([200, 500, 250])
        layout.addWidget(splitter)

        # 变量值存储
        self._var_values: dict[str, str] = {}

    def load_prompts(self, prompts: dict[str, str]) -> None:
        """加载 Prompt 集合

        Args:
            prompts: {name: content}
        """
        self._prompts = prompts
        self._prompt_list.clear()

        for name in sorted(prompts.keys()):
            self._prompt_list.addItem(name)
            # 初始化版本
            if name not in self._versions:
                self._versions[name] = [
                    PromptVersion(content=prompts[name], note="初始版本")
                ]

        if self._prompt_list.count() > 0:
            self._prompt_list.setCurrentRow(0)

    def get_prompts(self) -> dict[str, str]:
        """获取所有 Prompt"""
        return dict(self._prompts)

    def get_prompt(self, name: str) -> str:
        """获取指定 Prompt"""
        return self._prompts.get(name, "")

    def _on_prompt_selected(self, row: int) -> None:
        """选中 Prompt"""
        if row < 0:
            return
        name = self._prompt_list.item(row).text()
        self._current_prompt = name
        self._name_edit.setText(name)
        self._editor.setPlainText(self._prompts.get(name, ""))
        self._update_variables()

    def _on_text_changed(self) -> None:
        """文本变化时更新变量列表"""
        self._update_variables()

    def _update_variables(self) -> None:
        """提取并显示变量"""
        content = self._editor.toPlainText()
        variables = set(re.findall(r'\{(\w+)\}', content))
        self._var_list.clear()
        for var in sorted(variables):
            self._var_list.addItem(var)
        self._var_count_label.setText(f"变量: {len(variables)}")

    def _save_prompt(self) -> None:
        """保存当前 Prompt"""
        if not self._current_prompt:
            return
        content = self._editor.toPlainText()
        self._prompts[self._current_prompt] = content

        # 保存版本
        if self._current_prompt not in self._versions:
            self._versions[self._current_prompt] = []
        self._versions[self._current_prompt].append(
            PromptVersion(content=content, note="手动保存")
        )

        self.prompt_changed.emit(self._current_prompt, content)
        self._logger.info(f"Prompt 保存: {self._current_prompt} ({len(content)} 字符)")

    def _preview_prompt(self) -> None:
        """预览 Prompt（替换变量）"""
        content = self._editor.toPlainText()
        preview = content
        for var, value in self._var_values.items():
            preview = preview.replace(f"{{{var}}}", value)
        self._preview_browser.setPlainText(preview)

    def _set_variable_value(self) -> None:
        """设置当前选中变量的值"""
        current = self._var_list.currentItem()
        if not current:
            return
        var_name = current.text()
        value = self._var_value_edit.text()
        self._var_values[var_name] = value
        self._var_value_edit.clear()
        self._preview_prompt()

    def _new_prompt(self) -> None:
        """新建 Prompt"""
        name = f"prompt_{len(self._prompts) + 1}"
        self._prompts[name] = f"# {name}\n\n在此编写 Prompt 模板..."
        self._versions[name] = [PromptVersion(content=self._prompts[name], note="新建")]
        self._prompt_list.addItem(name)
        self._prompt_list.setCurrentRow(self._prompt_list.count() - 1)

    def _show_history(self) -> None:
        """显示版本历史"""
        if not self._current_prompt:
            return
        versions = self._versions.get(self._current_prompt, [])
        if not versions:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"版本历史 — {self._current_prompt}")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        for i, v in enumerate(reversed(versions)):
            list_widget.addItem(f"[{v.timestamp}] {v.note} ({len(v.content)} 字符)")
        layout.addWidget(list_widget)

        detail = QTextEdit()
        detail.setReadOnly(True)
        list_widget.currentRowChanged.connect(
            lambda row: detail.setPlainText(versions[len(versions) - 1 - row].content)
            if 0 <= row < len(versions) else None
        )
        layout.addWidget(detail)

        if versions:
            list_widget.setCurrentRow(0)

        dialog.exec()

    def _on_list_context_menu(self, pos) -> None:
        """右键菜单"""
        menu = QMenu()
        menu.addAction("重命名", self._rename_prompt)
        menu.addAction("删除", self._delete_prompt)
        menu.exec(self._prompt_list.mapToGlobal(pos))

    def _rename_prompt(self) -> None:
        """重命名 Prompt"""
        current = self._prompt_list.currentItem()
        if not current:
            return
        old_name = current.text()
        # 简单实现: 使用输入对话框
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=old_name)
        if ok and new_name and new_name != old_name:
            self._prompts[new_name] = self._prompts.pop(old_name)
            self._versions[new_name] = self._versions.pop(old_name, [])
            current.setText(new_name)
            self._current_prompt = new_name
            self._name_edit.setText(new_name)

    def _delete_prompt(self) -> None:
        """删除 Prompt"""
        current = self._prompt_list.currentItem()
        if not current:
            return
        name = current.text()
        self._prompts.pop(name, None)
        self._versions.pop(name, None)
        row = self._prompt_list.row(current)
        self._prompt_list.takeItem(row)
        if self._current_prompt == name:
            self._current_prompt = None
            self._editor.clear()
            self._name_edit.clear()
```

5.2 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.editor.prompt_editor import PromptEditorWidget

editor = PromptEditorWidget()

# 加载测试 Prompts
prompts = {
    'system': '你是一个游戏主持人。\n\n## 世界观\n{world_description}\n\n## 玩家\n{player_info}',
    'narrative': '根据以下状态生成叙事:\n{context}\n\n风格: {style}',
    'combat': '战斗叙事规则:\n1. 生动描述\n2. 包含数值',
}

editor.load_prompts(prompts)

# 验证加载
assert editor.get_prompt('system') != ''
assert len(editor.get_prompts()) == 3
print(f'✅ 加载 {len(prompts)} 个 Prompt')

# 验证变量提取（通过 UI 信号模拟）
editor._name_edit.setText('system')
editor._editor.setPlainText(prompts['system'])
editor._update_variables()
var_count = editor._var_list.count()
assert var_count == 2  # world_description, player_info
print(f'✅ system Prompt 变量数: {var_count}')

# 测试新建
editor._new_prompt()
assert len(editor.get_prompts()) == 4
print('✅ 新建 Prompt 成功')

print('✅ Prompt 管理器测试通过')
"
```

**验收**:
- [ ] Prompt 列表（搜索+新建+右键菜单）
- [ ] Prompt 编辑器（QTextEdit）
- [ ] 变量自动提取（正则 `{variable}`）
- [ ] 变量值设置和预览
- [ ] 版本历史查看
- [ ] 重命名/删除
- [ ] 测试通过

---

### Step 6: 工具/插件管理器

**目的**: 管理 LangGraph Tool 的注册、配置和测试。

**方案**:

6.1 创建 `2workbench/presentation/editor/tool_manager.py`：

```python
# 2workbench/presentation/editor/tool_manager.py
"""工具/插件管理器 — LangGraph Tool 管理

功能:
1. 内置工具列表（骰子、战斗、物品、对话等）
2. 自定义工具注册
3. 工具配置编辑
4. 工具测试面板
5. 工具启用/禁用
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QLabel, QFormLayout, QDialog, QDialogButtonBox,
    QComboBox, QCheckBox, QGroupBox, QTextBrowser,
    QPushButton,
)
from PyQt6.QtCore import pyqtSignal, Qt

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str = ""
    category: str = "custom"  # builtin / custom
    enabled: bool = True
    parameters: dict = field(default_factory=dict)  # JSON Schema
    source_file: str = ""  # 自定义工具的文件路径


# 内置工具定义
BUILTIN_TOOLS = [
    ToolDefinition(
        name="roll_dice",
        description="掷骰子（支持 XdY 格式，如 2d6、1d20）",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "notation": {"type": "string", "description": "骰子表示法，如 2d6"},
            },
            "required": ["notation"],
        },
    ),
    ToolDefinition(
        name="start_combat",
        description="开始战斗",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "enemies": {"type": "array", "description": "敌人列表"},
                "player_id": {"type": "integer", "description": "玩家 ID"},
            },
            "required": ["enemies"],
        },
    ),
    ToolDefinition(
        name="give_item",
        description="给予玩家物品",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "物品名称"},
                "quantity": {"type": "integer", "description": "数量", "default": 1},
                "player_id": {"type": "integer", "description": "玩家 ID"},
            },
            "required": ["item_name"],
        },
    ),
    ToolDefinition(
        name="npc_talk",
        description="与 NPC 对话",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "npc_name": {"type": "string", "description": "NPC 名称"},
                "message": {"type": "string", "description": "对话内容"},
            },
            "required": ["npc_name", "message"],
        },
    ),
    ToolDefinition(
        name="update_quest",
        description="更新任务状态",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "quest_id": {"type": "integer", "description": "任务 ID"},
                "status": {"type": "string", "description": "新状态", "enum": ["active", "completed", "failed"]},
            },
            "required": ["quest_id", "status"],
        },
    ),
    ToolDefinition(
        name="move_to",
        description="移动到指定地点",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "location_name": {"type": "string", "description": "目标地点"},
            },
            "required": ["location_name"],
        },
    ),
    ToolDefinition(
        name="check_skill",
        description="进行技能检定",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "skill": {"type": "string", "description": "技能名称"},
                "difficulty": {"type": "integer", "description": "难度等级", "default": 15},
            },
            "required": ["skill"],
        },
    ),
    ToolDefinition(
        name="search_area",
        description="搜索当前区域",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "搜索目标"},
            },
        },
    ),
    ToolDefinition(
        name="use_item",
        description="使用物品",
        category="builtin",
        parameters={
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "物品名称"},
                "target": {"type": "string", "description": "使用目标"},
            },
            "required": ["item_name"],
        },
    ),
]


class ToolManagerWidget(BaseWidget):
    """工具/插件管理器组件"""

    tools_changed = pyqtSignal(list)  # List[ToolDefinition]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tools: list[ToolDefinition] = list(BUILTIN_TOOLS)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: 工具列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        list_label = QLabel("🔧 工具列表")
        list_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        left_layout.addWidget(list_label)

        self._tool_list = QListWidget()
        self._tool_list.currentRowChanged.connect(self._on_tool_selected)
        left_layout.addWidget(self._tool_list)

        # 筛选
        filter_layout = QHBoxLayout()
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["全部", "内置", "自定义"])
        self._filter_combo.currentTextChanged.connect(self._filter_tools)
        filter_layout.addWidget(QLabel("筛选:"))
        filter_layout.addWidget(self._filter_combo)
        left_layout.addLayout(filter_layout)

        self._btn_add = StyledButton("+ 添加自定义工具", style_type="primary")
        self._btn_add.clicked.connect(self._add_tool_dialog)
        left_layout.addWidget(self._btn_add)

        splitter.addWidget(left)

        # 右侧: 工具详情 + 测试
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        # 工具信息
        info_group = QGroupBox("工具信息")
        info_layout = QFormLayout(info_group)

        self._name_edit = QLineEdit()
        self._name_edit.setReadOnly(True)
        info_layout.addRow("名称:", self._name_edit)

        self._desc_edit = QLineEdit()
        self._desc_edit.setReadOnly(True)
        info_layout.addRow("描述:", self._desc_edit)

        self._category_label = QLabel()
        info_layout.addRow("类别:", self._category_label)

        self._enabled_check = QCheckBox("启用")
        self._enabled_check.stateChanged.connect(self._on_enabled_changed)
        info_layout.addRow("状态:", self._enabled_check)

        right_layout.addWidget(info_group)

        # 参数 Schema
        schema_group = QGroupBox("参数 Schema (JSON)")
        schema_layout = QVBoxLayout(schema_group)

        self._schema_edit = QTextEdit()
        self._schema_edit.setReadOnly(True)
        self._schema_edit.setMaximumHeight(150)
        self._schema_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        schema_layout.addWidget(self._schema_edit)

        right_layout.addWidget(schema_group)

        # 测试面板
        test_group = QGroupBox("测试")
        test_layout = QVBoxLayout(test_group)

        self._test_input = QTextEdit()
        self._test_input.setPlaceholderText('输入测试参数 (JSON):\n{"notation": "2d6"}')
        self._test_input.setMaximumHeight(100)
        self._test_input.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        test_layout.addWidget(self._test_input)

        self._btn_test = StyledButton("▶ 执行测试", style_type="success")
        self._btn_test.clicked.connect(self._run_test)
        test_layout.addWidget(self._btn_test)

        self._test_result = QTextBrowser()
        self._test_result.setMaximumHeight(120)
        self._test_result.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        test_layout.addWidget(self._test_result)

        right_layout.addWidget(test_group)
        right_layout.addStretch()

        splitter.addWidget(right)
        splitter.setSizes([250, 400])
        layout.addWidget(splitter)

        # 初始化列表
        self._refresh_list()

    def _refresh_list(self) -> None:
        """刷新工具列表"""
        self._tool_list.clear()
        for tool in self._tools:
            icon = "🔧" if tool.category == "builtin" else "🔌"
            status = "✅" if tool.enabled else "❌"
            self._tool_list.addItem(f"{status} {icon} {tool.name}")

    def _filter_tools(self, filter_text: str) -> None:
        """筛选工具"""
        self._tool_list.clear()
        for tool in self._tools:
            if filter_text == "全部":
                show = True
            elif filter_text == "内置":
                show = tool.category == "builtin"
            else:
                show = tool.category == "custom"
            if show:
                icon = "🔧" if tool.category == "builtin" else "🔌"
                status = "✅" if tool.enabled else "❌"
                self._tool_list.addItem(f"{status} {icon} {tool.name}")

    def _on_tool_selected(self, row: int) -> None:
        """选中工具"""
        if row < 0 or row >= len(self._tools):
            return
        tool = self._tools[row]
        self._name_edit.setText(tool.name)
        self._desc_edit.setText(tool.description)
        self._category_label.setText(tool.category)
        self._enabled_check.setChecked(tool.enabled)
        self._schema_edit.setPlainText(
            json.dumps(tool.parameters, ensure_ascii=False, indent=2)
        )

    def _on_enabled_changed(self, state) -> None:
        """启用/禁用工具"""
        row = self._tool_list.currentRow()
        if row < 0:
            return
        self._tools[row].enabled = bool(state)
        self._refresh_list()
        self._tool_list.setCurrentRow(row)
        self.tools_changed.emit(self._tools)

    def _add_tool_dialog(self) -> None:
        """添加自定义工具对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加自定义工具")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("tool_name")
        layout.addRow("工具名称:", name_edit)

        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("工具描述")
        layout.addRow("描述:", desc_edit)

        schema_edit = QTextEdit()
        schema_edit.setPlaceholderText('参数 JSON Schema:\n{"type": "object", "properties": {...}}')
        schema_edit.setMaximumHeight(120)
        layout.addRow("参数 Schema:", schema_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec():
            name = name_edit.text().strip()
            if not name:
                return
            try:
                params = json.loads(schema_edit.toPlainText()) if schema_edit.toPlainText() else {}
            except json.JSONDecodeError:
                params = {}
            tool = ToolDefinition(
                name=name,
                description=desc_edit.text().strip(),
                category="custom",
                parameters=params,
            )
            self._tools.append(tool)
            self._refresh_list()
            self.tools_changed.emit(self._tools)
            self._logger.info(f"自定义工具添加: {name}")

    def _run_test(self) -> None:
        """执行工具测试"""
        row = self._tool_list.currentRow()
        if row < 0:
            return
        tool = self._tools[row]

        try:
            params = json.loads(self._test_input.toPlainText())
        except json.JSONDecodeError:
            self._test_result.setPlainText("❌ JSON 格式错误")
            return

        self._test_result.setPlainText(f"⏳ 调用 {tool.name}...\n参数: {json.dumps(params, ensure_ascii=False)}")

        # 模拟测试（实际调用在 P5 运行时调试中实现）
        self._test_result.append(f"\n✅ 模拟调用成功\n工具: {tool.name}\n参数: {json.dumps(params, ensure_ascii=False, indent=2)}")

    def get_enabled_tools(self) -> list[ToolDefinition]:
        """获取已启用的工具"""
        return [t for t in self._tools if t.enabled]

    def get_all_tools(self) -> list[ToolDefinition]:
        """获取所有工具"""
        return list(self._tools)
```

6.2 测试：

```bash
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from presentation.editor.tool_manager import ToolManagerWidget, BUILTIN_TOOLS

manager = ToolManagerWidget()

# 验证内置工具加载
all_tools = manager.get_all_tools()
assert len(all_tools) == 9
print(f'✅ 加载 {len(all_tools)} 个内置工具')

# 验证工具名称
names = [t.name for t in all_tools]
assert 'roll_dice' in names
assert 'start_combat' in names
assert 'give_item' in names
assert 'npc_talk' in names
print(f'✅ 工具列表: {names}')

# 验证默认全部启用
enabled = manager.get_enabled_tools()
assert len(enabled) == 9
print(f'✅ 默认启用 {len(enabled)} 个工具')

# 验证参数 Schema
roll_dice = [t for t in all_tools if t.name == 'roll_dice'][0]
assert 'notation' in roll_dice.parameters.get('properties', {})
print(f'✅ roll_dice 参数: {roll_dice.parameters}')

print('✅ 工具/插件管理器测试通过')
"
```

**验收**:
- [ ] 9 个内置工具（roll_dice/start_combat/give_item/npc_talk/update_quest/move_to/check_skill/search_area/use_item）
- [ ] 工具列表（筛选: 全部/内置/自定义）
- [ ] 工具详情（名称/描述/类别/参数 Schema）
- [ ] 启用/禁用切换
- [ ] 自定义工具添加
- [ ] 测试面板（JSON 参数输入 + 结果显示）
- [ ] 测试通过

---

### Step 7: 集成到主窗口 + 端到端测试

**目的**: 将图编辑器、Prompt 管理器、工具管理器集成到主窗口，并运行端到端测试。

**方案**:

7.1 更新 `2workbench/presentation/main_window.py`，在 CenterPanel 中集成编辑器：

在 `CenterPanel._setup_ui` 方法中添加编辑器标签页：

```python
# 在 CenterPanel._setup_ui 中，替换默认欢迎页逻辑

def _setup_ui(self) -> None:
    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    self.tab_widget = QTabWidget()
    self.tab_widget.setTabsClosable(True)
    self.tab_widget.setMovable(True)
    layout.addWidget(self.tab_widget)

    # 欢迎页
    welcome = QLabel(
        "🎮 Game Master Agent IDE\n\n"
        "欢迎使用 Agent 集成开发环境\n\n"
        "请通过 File > New Agent Project 创建新项目"
    )
    welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
    welcome.setStyleSheet("font-size: 16px; color: #858585;")
    self.tab_widget.addTab(welcome, "Welcome")

    # 图编辑器标签页（默认隐藏，打开项目后显示）
    self._graph_editor = None
    self._prompt_editor = None
    self._tool_manager = None

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

def show_tool_manager(self) -> None:
    """显示工具管理器标签页"""
    from presentation.editor.tool_manager import ToolManagerWidget
    if self._tool_manager is None:
        self._tool_manager = ToolManagerWidget()
        self.tab_widget.addTab(self._tool_manager, "🔧 工具")
    idx = self.tab_widget.indexOf(self._tool_manager)
    self.tab_widget.setCurrentIndex(idx)
```

7.2 更新主窗口的菜单动作，连接到实际功能：

```python
# 在 MainWindow 中更新 _on_new_project 和 _on_open_project

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

            self.center_panel.show_tool_manager()

            self.statusBar().showMessage(f"项目已创建: {data['name']}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建项目失败: {e}")

def _on_open_project(self) -> None:
    """打开项目"""
    from PyQt6.QtWidgets import QFileDialog
    path, _ = QFileDialog.getExistingDirectory(
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

            self.center_panel.show_tool_manager()

            self.statusBar().showMessage(f"项目已打开: {config.name}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开项目失败: {e}")
```

7.3 端到端测试：

```bash
cd 2workbench ; python -c "
import sys, tempfile, shutil
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

# 1. 测试主窗口
from presentation.main_window import MainWindow
window = MainWindow()
assert window.windowTitle() == 'Game Master Agent IDE'
print('✅ 主窗口创建成功')

# 2. 测试项目创建
from presentation.project.manager import project_manager
tmp_dir = tempfile.mkdtemp()

try:
    path = project_manager.create_project('e2e_test', template='trpg', directory=tmp_dir)
    config = project_manager.open_project(path)
    assert config.name == 'e2e_test'
    print('✅ 项目创建并打开成功')

    # 3. 测试图编辑器加载
    graph = project_manager.load_graph()
    assert len(graph['nodes']) == 6
    window.center_panel.show_graph_editor(graph)
    assert window.center_panel._graph_editor is not None
    exported = window.center_panel._graph_editor.get_graph()
    assert len(exported['nodes']) == 6
    print('✅ 图编辑器加载成功')

    # 4. 测试 Prompt 管理器加载
    prompts = {}
    for name in project_manager.list_prompts():
        prompts[name] = project_manager.load_prompt(name)
    assert len(prompts) >= 3
    window.center_panel.show_prompt_editor(prompts)
    assert window.center_panel._prompt_editor is not None
    assert len(window.center_panel._prompt_editor.get_prompts()) >= 3
    print(f'✅ Prompt 管理器加载成功 ({len(prompts)} 个)')

    # 5. 测试工具管理器
    window.center_panel.show_tool_manager()
    assert window.center_panel._tool_manager is not None
    assert len(window.center_panel._tool_manager.get_all_tools()) == 9
    print('✅ 工具管理器加载成功')

    # 6. 测试主题切换
    from presentation.theme.manager import theme_manager
    theme_manager.apply('light')
    assert theme_manager.current_theme == 'light'
    theme_manager.apply('dark')
    assert theme_manager.current_theme == 'dark'
    print('✅ 主题切换成功')

    # 7. 测试 EventBus 集成
    from foundation.event_bus import event_bus, Event
    result = event_bus.emit(Event(type="test.event", data={"key": "value"}))
    assert len(result) == 0  # 无订阅者
    print('✅ EventBus 集成正常')

    # 8. 清理
    project_manager.close_project()
    assert not project_manager.is_open
    print('✅ 项目关闭成功')

    print()
    print('=' * 50)
    print('✅ P4 Presentation 层 IDE 核心编辑器 — 端到端测试通过')
    print('=' * 50)

finally:
    shutil.rmtree(tmp_dir)
"
```

**验收**:
- [ ] 主窗口创建成功
- [ ] 项目创建→打开→编辑器加载 全流程
- [ ] 图编辑器加载 TRPG 模板（6 节点 5 边）
- [ ] Prompt 管理器加载 3+ 模板
- [ ] 工具管理器加载 9 个内置工具
- [ ] 主题切换（Dark/Light）
- [ ] EventBus 集成
- [ ] 项目关闭
- [ ] 端到端测试通过

---

## 注意事项

### UI 线程安全

- LLM 调用和长时间操作**必须**使用 `qasync` 或 `QThread`，不阻塞 UI
- EventBus 回调在主线程执行，不应包含耗时操作
- 数据库操作应使用异步方式或在线程池中执行

### 主题系统

- 所有颜色通过 `theme_manager.get_color()` 获取，不硬编码
- QSS 使用 `${variable}` 占位符，由 ThemeManager 替换
- 新增组件样式应同时更新 dark.qss 和 light.qss

### 项目文件格式

- `project.json`: 项目元数据（JSON）
- `graph.json`: LangGraph 图定义（JSON）
- `prompts/*.md`: Prompt 模板（Markdown）
- `config.json`: 运行配置（JSON）
- 所有文件使用 UTF-8 编码

### EventBus 事件命名

Presentation 层事件遵循 `ui.{component}.{action}` 格式：
```
ui.project.created / ui.project.opened / ui.project.saved / ui.project.closed
ui.graph.node_selected / ui.graph.node_moved
ui.prompt.changed / ui.prompt.saved
ui.tool.enabled / ui.tool.disabled
```

---

## 完成检查清单

- [ ] Step 1: Presentation 基础设施（主题/样式/通用组件）
- [ ] Step 2: 主窗口重构（三栏布局/菜单/工具栏/状态栏）
- [ ] Step 3: Agent 项目管理器（创建/打开/保存/关闭）
- [ ] Step 4: LangGraph 可视化图编辑器（节点拖拽/连线/属性编辑）
- [ ] Step 5: Prompt 管理器（编辑/变量/版本/预览）
- [ ] Step 6: 工具/插件管理器（内置工具/自定义/测试）
- [ ] Step 7: 集成到主窗口 + 端到端测试
