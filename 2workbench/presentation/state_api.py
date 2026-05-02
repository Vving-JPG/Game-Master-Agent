"""结构化状态 API — 让 GUI "告诉" AI 它的状态

三层方案组合:
1. Widget Tree API (/api/dom) — 递归遍历 Qt Widget 树，输出结构化 JSON
2. 应用状态 API (/api/state) — 直接暴露业务状态
3. Windows UI Automation — 使用 Windows 内置 UIA API

用法:
    GET /api/state          → 获取完整应用状态
    GET /api/dom            → 获取 Widget 树 JSON
    GET /api/dom?selector=console → 获取特定区域
    GET /api/dom?diff=true  → 只返回变化部分
    GET /api/uia            → 获取 Windows UIA 树
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable
from dataclasses import dataclass, field
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QTextEdit, QTableWidget,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QCheckBox, QSlider, QProgressBar, QGroupBox,
    QSplitter, QMainWindow, QMenuBar, QToolBar,
    QStatusBar, QTreeWidget, QListWidget
)
from PyQt6.QtCore import QObject, Qt

from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WidgetState:
    """控件状态快照"""
    class_name: str
    object_name: str
    text: str = ""
    visible: bool = True
    enabled: bool = True
    geometry: dict = field(default_factory=dict)
    properties: dict = field(default_factory=dict)
    children: list = field(default_factory=list)


class WidgetTreeSerializer:
    """Widget 树序列化器 — 将 Qt Widget 树转换为结构化 JSON"""

    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
        self._last_tree: dict | None = None
        self._tree_timestamp: float = 0

    def serialize(
        self,
        widget: QWidget,
        depth: int = 0,
        selector: str | None = None,
        diff: bool = False
    ) -> dict | None:
        """将 Qt Widget 树序列化为结构化 JSON

        Args:
            widget: 根 Widget
            depth: 当前深度
            selector: CSS-like 选择器，用于过滤特定区域
            diff: 是否只返回变化的部分

        Returns:
            Widget 树 JSON，如果超过最大深度返回 None
        """
        if depth > self.max_depth:
            return None

        # 应用选择器过滤
        if selector and depth == 0:
            widget = self._find_by_selector(widget, selector)
            if not widget:
                return {"error": f"选择器未找到: {selector}"}

        info = self._serialize_widget(widget, depth)

        if diff and self._last_tree:
            info = self._compute_diff(self._last_tree, info)

        self._last_tree = info
        self._tree_timestamp = time.time()
        return info

    def _serialize_widget(self, widget: QWidget, depth: int) -> dict:
        """序列化单个 Widget"""
        info = {
            "class": widget.__class__.__name__,
            "id": widget.objectName() or "",
            "visible": widget.isVisible(),
            "enabled": widget.isEnabled(),
            "geometry": {
                "x": widget.x(),
                "y": widget.y(),
                "width": widget.width(),
                "height": widget.height(),
            },
            "children": [],
        }

        # 文本属性
        info["text"] = self._get_text(widget)

        # 类型特定属性
        info["properties"] = self._get_type_specific_properties(widget)

        # 递归子组件
        for child in widget.children():
            if isinstance(child, QWidget) and not child.isWindow():
                child_info = self.serialize(child, depth + 1)
                if child_info:
                    info["children"].append(child_info)

        return info

    def _get_text(self, widget: QWidget) -> str:
        """获取 Widget 文本"""
        # 尝试各种文本获取方法
        if hasattr(widget, 'text') and callable(getattr(widget, 'text')):
            try:
                return str(widget.text())
            except:
                pass

        if hasattr(widget, 'toPlainText') and callable(getattr(widget, 'toPlainText')):
            try:
                text = widget.toPlainText()
                return text[:200] + "..." if len(text) > 200 else text
            except:
                pass

        if hasattr(widget, 'currentText') and callable(getattr(widget, 'currentText')):
            try:
                return str(widget.currentText())
            except:
                pass

        if hasattr(widget, 'windowTitle') and callable(getattr(widget, 'windowTitle')):
            try:
                return str(widget.windowTitle())
            except:
                pass

        return ""

    def _get_type_specific_properties(self, widget: QWidget) -> dict:
        """获取类型特定的属性"""
        props = {}

        # QTabWidget
        if isinstance(widget, QTabWidget):
            props["tab_count"] = widget.count()
            props["current_index"] = widget.currentIndex()
            props["tabs"] = [
                {"index": i, "text": widget.tabText(i)}
                for i in range(widget.count())
            ]
            current = widget.currentWidget()
            if current:
                props["current_tab_id"] = current.objectName() or ""

        # QTextEdit / QPlainTextEdit
        elif isinstance(widget, QTextEdit):
            props["line_count"] = widget.document().lineCount()
            props["character_count"] = len(widget.toPlainText())
            props["read_only"] = widget.isReadOnly()
            # 获取最后几行内容
            lines = widget.toPlainText().split('\n')
            props["last_lines"] = lines[-5:] if len(lines) > 5 else lines

        # QTableWidget
        elif isinstance(widget, QTableWidget):
            props["row_count"] = widget.rowCount()
            props["column_count"] = widget.columnCount()
            props["selected_items"] = len(widget.selectedItems())

        # QPushButton
        elif isinstance(widget, QPushButton):
            props["checked"] = widget.isChecked()
            props["checkable"] = widget.isCheckable()
            props["flat"] = widget.isFlat()

        # QComboBox
        elif isinstance(widget, QComboBox):
            props["item_count"] = widget.count()
            props["editable"] = widget.isEditable()
            props["items"] = [widget.itemText(i) for i in range(min(widget.count(), 10))]

        # QCheckBox
        elif isinstance(widget, QCheckBox):
            props["checked"] = widget.isChecked()
            props["tristate"] = widget.isTristate()

        # QSlider
        elif isinstance(widget, QSlider):
            props["minimum"] = widget.minimum()
            props["maximum"] = widget.maximum()
            props["value"] = widget.value()
            props["orientation"] = "horizontal" if widget.orientation() == Qt.Orientation.Horizontal else "vertical"

        # QProgressBar
        elif isinstance(widget, QProgressBar):
            props["minimum"] = widget.minimum()
            props["maximum"] = widget.maximum()
            props["value"] = widget.value()
            props["text_visible"] = widget.isTextVisible()
            props["format"] = widget.format()

        # QTreeWidget
        elif isinstance(widget, QTreeWidget):
            props["top_level_item_count"] = widget.topLevelItemCount()
            props["column_count"] = widget.columnCount()
            props["header_labels"] = [widget.headerItem().text(i) for i in range(widget.columnCount())]

        # QListWidget
        elif isinstance(widget, QListWidget):
            props["count"] = widget.count()
            props["current_row"] = widget.currentRow()

        # QSplitter
        elif isinstance(widget, QSplitter):
            props["orientation"] = "horizontal" if widget.orientation() == Qt.Orientation.Horizontal else "vertical"
            props["handle_count"] = widget.count()
            props["sizes"] = widget.sizes()

        # QGroupBox
        elif isinstance(widget, QGroupBox):
            props["title"] = widget.title()
            props["checkable"] = widget.isCheckable()
            if widget.isCheckable():
                props["checked"] = widget.isChecked()

        # QLineEdit
        elif isinstance(widget, QLineEdit):
            props["placeholder"] = widget.placeholderText()
            props["max_length"] = widget.maxLength()
            props["read_only"] = widget.isReadOnly()
            props["echo_mode"] = self._echo_mode_to_string(widget.echoMode())

        return props

    def _echo_mode_to_string(self, mode) -> str:
        """转换 EchoMode 为字符串"""
        from PyQt6.QtWidgets import QLineEdit
        modes = {
            QLineEdit.EchoMode.Normal: "normal",
            QLineEdit.EchoMode.NoEcho: "no_echo",
            QLineEdit.EchoMode.Password: "password",
            QLineEdit.EchoMode.PasswordEchoOnEdit: "password_echo_on_edit",
        }
        return modes.get(mode, "unknown")

    def _find_by_selector(self, root: QWidget, selector: str) -> QWidget | None:
        """CSS-like 选择器查找 Widget

        支持的选择器:
        - #id — 按 objectName 查找
        - .class — 按类名查找
        - 标签名 — 按类名查找
        - console, editor, sidebar 等预定义区域
        """
        # 预定义区域快捷方式
        predefined = {
            "console": self._find_console,
            "editor": self._find_editor,
            "sidebar": self._find_sidebar,
            "toolbar": self._find_toolbar,
            "statusbar": self._find_statusbar,
            "menubar": self._find_menubar,
        }

        if selector in predefined:
            return predefined[selector](root)

        # #id 选择器
        if selector.startswith('#'):
            name = selector[1:]
            return self._find_by_object_name(root, name)

        # .class 选择器
        if selector.startswith('.'):
            class_name = selector[1:]
            return self._find_by_class_name(root, class_name)

        # 标签名选择器
        return self._find_by_class_name(root, selector)

    def _find_by_object_name(self, root: QWidget, name: str) -> QWidget | None:
        """按 objectName 递归查找"""
        if root.objectName() == name:
            return root
        for child in root.children():
            if isinstance(child, QWidget):
                result = self._find_by_object_name(child, name)
                if result:
                    return result
        return None

    def _find_by_class_name(self, root: QWidget, class_name: str) -> QWidget | None:
        """按类名递归查找"""
        if root.__class__.__name__ == class_name:
            return root
        for child in root.children():
            if isinstance(child, QWidget):
                result = self._find_by_class_name(child, class_name)
                if result:
                    return result
        return None

    def _find_console(self, root: QWidget) -> QWidget | None:
        """查找控制台区域"""
        return self._find_by_object_name(root, "console_tabs") or \
               self._find_by_class_name(root, "ConsoleTabs")

    def _find_editor(self, root: QWidget) -> QWidget | None:
        """查找编辑器区域"""
        return self._find_by_object_name(root, "editor_stack") or \
               self._find_by_class_name(root, "EditorStack")

    def _find_sidebar(self, root: QWidget) -> QWidget | None:
        """查找侧边栏区域"""
        return self._find_by_object_name(root, "left_panel") or \
               self._find_by_class_name(root, "LeftPanel")

    def _find_toolbar(self, root: QWidget) -> QWidget | None:
        """查找工具栏区域"""
        for child in root.children():
            if isinstance(child, QToolBar):
                return child
        return None

    def _find_statusbar(self, root: QWidget) -> QWidget | None:
        """查找状态栏区域"""
        if isinstance(root, QMainWindow):
            return root.statusBar()
        return self._find_by_class_name(root, "QStatusBar")

    def _find_menubar(self, root: QWidget) -> QWidget | None:
        """查找菜单栏区域"""
        if isinstance(root, QMainWindow):
            return root.menuBar()
        return self._find_by_class_name(root, "QMenuBar")

    def _compute_diff(self, old: dict, new: dict) -> dict:
        """计算两个树之间的差异"""
        diff = {"changed": [], "added": [], "removed": []}

        # 简化实现：标记变化的节点
        if old.get("text") != new.get("text"):
            diff["changed"].append({
                "id": new.get("id"),
                "field": "text",
                "old": old.get("text"),
                "new": new.get("text")
            })

        if old.get("visible") != new.get("visible"):
            diff["changed"].append({
                "id": new.get("id"),
                "field": "visible",
                "old": old.get("visible"),
                "new": new.get("visible")
            })

        if old.get("enabled") != new.get("enabled"):
            diff["changed"].append({
                "id": new.get("id"),
                "field": "enabled",
                "old": old.get("enabled"),
                "new": new.get("enabled")
            })

        # 递归比较子节点
        old_children = {c.get("id"): c for c in old.get("children", [])}
        new_children = {c.get("id"): c for c in new.get("children", [])}

        for child_id, child_new in new_children.items():
            if child_id not in old_children:
                diff["added"].append(child_id)
            else:
                child_diff = self._compute_diff(old_children[child_id], child_new)
                diff["changed"].extend(child_diff["changed"])

        for child_id in old_children:
            if child_id not in new_children:
                diff["removed"].append(child_id)

        return diff


class ApplicationStateProvider:
    """应用状态提供者 — 收集各层状态"""

    def __init__(self, gui_instance: QWidget | None = None):
        self.gui = gui_instance
        self._state_cache: dict = {}
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 1.0  # 缓存 1 秒

    def get_state(self, use_cache: bool = True) -> dict:
        """获取完整应用状态"""
        now = time.time()

        if use_cache and self._state_cache and (now - self._cache_timestamp) < self._cache_ttl:
            return self._state_cache

        state = {
            "timestamp": now,
            "project": self._get_project_state(),
            "agent": self._get_agent_state(),
            "features": self._get_features_state(),
            "editor": self._get_editor_state(),
            "console": self._get_console_state(),
            "ui": self._get_ui_state(),
            "metrics": self._get_metrics_state(),
        }

        self._state_cache = state
        self._cache_timestamp = now
        return state

    def _get_project_state(self) -> dict:
        """获取项目状态"""
        if not self.gui:
            return {"open": False}

        try:
            # 尝试从 GUI 获取项目信息
            if hasattr(self.gui, 'current_project'):
                project = self.gui.current_project
                if project:
                    return {
                        "open": True,
                        "name": getattr(project, 'name', 'unknown'),
                        "path": getattr(project, 'path', ''),
                        "template": getattr(project, 'template', 'unknown'),
                    }

            # 尝试从窗口标题推断
            title = self.gui.windowTitle()
            if title and " - " in title:
                parts = title.split(" - ")
                return {
                    "open": True,
                    "name": parts[0],
                    "title": title,
                }

            return {"open": False}
        except Exception as e:
            logger.warning(f"获取项目状态失败: {e}")
            return {"open": False, "error": str(e)}

    def _get_agent_state(self) -> dict:
        """获取 Agent 状态"""
        state = {
            "status": "unknown",
            "turn": 0,
            "model": "unknown",
        }

        if not self.gui:
            return state

        try:
            # 尝试从 GUI 获取 Agent 状态
            if hasattr(self.gui, 'agent_status'):
                state["status"] = self.gui.agent_status

            if hasattr(self.gui, 'current_turn'):
                state["turn"] = self.gui.current_turn

            if hasattr(self.gui, 'current_model'):
                state["model"] = self.gui.current_model

            # 从状态栏推断
            status_bar = self.gui.statusBar() if hasattr(self.gui, 'statusBar') else None
            if status_bar:
                for child in status_bar.children():
                    if isinstance(child, QLabel):
                        text = child.text()
                        if "Agent" in text or "状态" in text:
                            state["status_text"] = text

            return state
        except Exception as e:
            logger.warning(f"获取 Agent 状态失败: {e}")
            return state

    def _get_features_state(self) -> dict:
        """获取 Feature 状态"""
        features = {}

        try:
            from feature.registry import feature_registry
            for name, info in feature_registry.list_features().items():
                features[name] = {
                    "enabled": info.get("enabled", False),
                    "description": info.get("description", ""),
                }
        except Exception as e:
            logger.warning(f"获取 Feature 状态失败: {e}")

        return features

    def _get_editor_state(self) -> dict:
        """获取编辑器状态"""
        state = {
            "active_tab": None,
            "modified": False,
            "open_files": [],
        }

        if not self.gui:
            return state

        try:
            # 查找编辑器栈
            editor_stack = None
            for child in self.gui.children():
                if child.__class__.__name__ == "EditorStack":
                    editor_stack = child
                    break

            if editor_stack and hasattr(editor_stack, 'tabText'):
                state["active_tab"] = editor_stack.tabText(editor_stack.currentIndex())
                state["open_files"] = [
                    editor_stack.tabText(i)
                    for i in range(editor_stack.count())
                ]

            return state
        except Exception as e:
            logger.warning(f"获取编辑器状态失败: {e}")
            return state

    def _get_console_state(self) -> dict:
        """获取控制台状态"""
        state = {
            "last_lines": [],
            "line_count": 0,
        }

        if not self.gui:
            return state

        try:
            # 查找控制台
            console = None
            for child in self.gui.children():
                if child.__class__.__name__ in ["ConsoleTabs", "ConsoleWidget"]:
                    console = child
                    break

            if console:
                # 查找 QTextEdit
                for subchild in console.children():
                    if isinstance(subchild, QTextEdit):
                        text = subchild.toPlainText()
                        lines = text.split('\n')
                        state["line_count"] = len(lines)
                        state["last_lines"] = lines[-10:] if len(lines) > 10 else lines
                        break

            return state
        except Exception as e:
            logger.warning(f"获取控制台状态失败: {e}")
            return state

    def _get_ui_state(self) -> dict:
        """获取 UI 状态"""
        state = {
            "theme": "unknown",
            "window": {
                "title": "",
                "size": {"width": 0, "height": 0},
            }
        }

        if not self.gui:
            return state

        try:
            from presentation.theme.manager import theme_manager
            state["theme"] = theme_manager.current_theme

            state["window"]["title"] = self.gui.windowTitle()
            state["window"]["size"] = {
                "width": self.gui.width(),
                "height": self.gui.height(),
            }

            return state
        except Exception as e:
            logger.warning(f"获取 UI 状态失败: {e}")
            return state

    def _get_metrics_state(self) -> dict:
        """获取指标状态"""
        metrics = {
            "tokens": 0,
            "cost": 0.0,
            "errors": 0,
            "uptime": 0,
        }

        try:
            # 尝试从 foundation 获取指标
            from foundation.event_bus import event_bus
            # 这里可以订阅指标事件
        except Exception as e:
            logger.warning(f"获取指标状态失败: {e}")

        return metrics


class WindowsUIAutomationProvider:
    """Windows UI Automation 提供者 — 使用 Windows UIA API"""

    def __init__(self):
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """检查 UIA 是否可用"""
        try:
            import comtypes.client
            return True
        except ImportError:
            return False

    def is_available(self) -> bool:
        """UIA 是否可用"""
        return self._available

    def get_ui_tree(self, hwnd: int | None = None) -> dict:
        """获取 UI 自动化树

        Args:
            hwnd: 窗口句柄，如果为 None 则使用前台窗口

        Returns:
            UI 树 JSON
        """
        if not self._available:
            return {"error": "Windows UI Automation 不可用 (缺少 comtypes)"}

        try:
            import comtypes.client
            from comtypes.gen.UIAutomationClient import (
                CUIAutomation, IUIAutomation,
                TreeScope_Descendants, UIA_PropertyIds
            )

            # 创建 UIA 实例
            uia = comtypes.client.CreateObject(
                "{ff48dba4-60ef-4201-aa87-54103eef5944}",
                interface=IUIAutomation
            )

            # 获取根元素
            if hwnd:
                root = uia.ElementFromHandle(hwnd)
            else:
                root = uia.GetRootElement()

            if not root:
                return {"error": "无法获取 UI 根元素"}

            # 序列化 UI 树
            return self._serialize_element(root, uia, depth=0)

        except Exception as e:
            logger.error(f"获取 UIA 树失败: {e}")
            return {"error": str(e)}

    def _serialize_element(self, element, uia, depth: int = 0, max_depth: int = 5) -> dict | None:
        """序列化 UIA 元素"""
        if depth > max_depth:
            return None

        try:
            info = {
                "control_type": self._get_control_type_name(element.CurrentControlType),
                "name": element.CurrentName or "",
                "class_name": element.CurrentClassName or "",
                "automation_id": element.CurrentAutomationId or "",
                "enabled": element.CurrentIsEnabled,
                "visible": not element.CurrentIsOffscreen,
                "bounding_rectangle": {
                    "left": element.CurrentBoundingRectangle.left,
                    "top": element.CurrentBoundingRectangle.top,
                    "right": element.CurrentBoundingRectangle.right,
                    "bottom": element.CurrentBoundingRectangle.bottom,
                },
                "children": [],
            }

            # 获取子元素
            try:
                children = element.FindAll(TreeScope_Descendants, uia.CreateTrueCondition())
                for i in range(min(children.Length, 50)):  # 限制子元素数量
                    child = children.GetElement(i)
                    child_info = self._serialize_element(child, uia, depth + 1, max_depth)
                    if child_info:
                        info["children"].append(child_info)
            except Exception as e:
                info["children_error"] = str(e)

            return info

        except Exception as e:
            return {"error": str(e)}

    def _get_control_type_name(self, control_type_id: int) -> str:
        """获取控件类型名称"""
        control_types = {
            50000: "Button",
            50001: "Calendar",
            50002: "CheckBox",
            50003: "ComboBox",
            50004: "Edit",
            50005: "Hyperlink",
            50006: "Image",
            50007: "ListItem",
            50008: "List",
            50009: "Menu",
            50010: "MenuBar",
            50011: "MenuItem",
            50012: "ProgressBar",
            50013: "RadioButton",
            50014: "ScrollBar",
            50015: "Slider",
            50016: "Spinner",
            50017: "StatusBar",
            50018: "Tab",
            50019: "TabItem",
            50020: "Text",
            50021: "ToolBar",
            50022: "ToolTip",
            50023: "Tree",
            50024: "TreeItem",
            50025: "Custom",
            50026: "Group",
            50027: "Thumb",
            50028: "DataGrid",
            50029: "DataItem",
            50030: "Document",
            50031: "SplitButton",
            50032: "Window",
            50033: "Pane",
            50034: "Header",
            50035: "HeaderItem",
            50036: "Table",
            50037: "TitleBar",
            50038: "Separator",
            50039: "SemanticZoom",
            50040: "AppBar",
        }
        return control_types.get(control_type_id, f"Unknown({control_type_id})")


class StateAPI:
    """结构化状态 API 门面 — 整合三层方案"""

    def __init__(self, gui_instance: QWidget | None = None):
        self.gui = gui_instance
        self.widget_serializer = WidgetTreeSerializer()
        self.state_provider = ApplicationStateProvider(gui_instance)
        self.uia_provider = WindowsUIAutomationProvider()

    def get_dom(self, selector: str | None = None, diff: bool = False) -> dict:
        """获取 Widget DOM 树

        Args:
            selector: CSS-like 选择器
            diff: 是否只返回变化部分

        Returns:
            Widget 树 JSON
        """
        if not self.gui:
            return {"error": "GUI 实例不可用"}

        try:
            tree = self.widget_serializer.serialize(
                self.gui,
                selector=selector,
                diff=diff
            )
            return {
                "status": "ok",
                "selector": selector,
                "diff_mode": diff,
                "tree": tree,
            }
        except Exception as e:
            logger.error(f"获取 DOM 失败: {e}")
            return {"error": str(e)}

    def get_state(self) -> dict:
        """获取应用状态"""
        return {
            "status": "ok",
            "state": self.state_provider.get_state(),
        }

    def get_uia_tree(self, hwnd: int | None = None) -> dict:
        """获取 Windows UIA 树"""
        if not self.uia_provider.is_available():
            return {
                "status": "unavailable",
                "error": "Windows UI Automation 不可用",
                "hint": "安装 comtypes: pip install comtypes",
            }

        tree = self.uia_provider.get_ui_tree(hwnd)
        return {
            "status": "ok",
            "hwnd": hwnd,
            "tree": tree,
        }

    def find_widget(self, query: dict) -> dict:
        """查找 Widget

        Args:
            query: 查询条件，如 {"id": "run_button"} 或 {"class": "QPushButton", "text": "运行"}

        Returns:
            找到的 Widget 信息
        """
        if not self.gui:
            return {"error": "GUI 实例不可用"}

        results = self._find_widgets_recursive(self.gui, query)
        return {
            "status": "ok",
            "query": query,
            "count": len(results),
            "results": results[:10],  # 最多返回 10 个
        }

    def _find_widgets_recursive(self, widget: QWidget, query: dict) -> list:
        """递归查找 Widget"""
        results = []

        # 检查当前 Widget
        match = True
        if "id" in query and widget.objectName() != query["id"]:
            match = False
        if "class" in query and widget.__class__.__name__ != query["class"]:
            match = False
        if "text" in query:
            text = ""
            if hasattr(widget, 'text') and callable(getattr(widget, 'text')):
                try:
                    text = str(widget.text())
                except:
                    pass
            if text != query["text"]:
                match = False

        if match:
            results.append({
                "class": widget.__class__.__name__,
                "id": widget.objectName() or "",
                "text": self.widget_serializer._get_text(widget),
                "geometry": {
                    "x": widget.x(),
                    "y": widget.y(),
                    "width": widget.width(),
                    "height": widget.height(),
                },
            })

        # 递归子组件
        for child in widget.children():
            if isinstance(child, QWidget):
                results.extend(self._find_widgets_recursive(child, query))

        return results

    def get_widget_by_path(self, path: str) -> dict:
        """通过路径获取 Widget

        Args:
            path: 路径，如 "/main_window/toolbar/run_button"

        Returns:
            Widget 信息
        """
        if not self.gui:
            return {"error": "GUI 实例不可用"}

        parts = path.strip("/").split("/")
        current = self.gui

        for part in parts[1:]:  # 跳过第一个（通常是 main_window）
            found = None
            for child in current.children():
                if isinstance(child, QWidget):
                    if child.objectName() == part or \
                       child.__class__.__name__ == part:
                        found = child
                        break

            if not found:
                return {"error": f"路径未找到: {path} (在 {part} 处失败)"}

            current = found

        return {
            "status": "ok",
            "path": path,
            "widget": self.widget_serializer._serialize_widget(current, 0),
        }


# 全局 API 实例
_state_api: StateAPI | None = None


def init_state_api(gui_instance: QWidget) -> StateAPI:
    """初始化状态 API"""
    global _state_api
    _state_api = StateAPI(gui_instance)
    return _state_api


def get_state_api() -> StateAPI | None:
    """获取状态 API 实例"""
    return _state_api
