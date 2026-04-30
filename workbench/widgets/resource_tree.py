# workbench/widgets/resource_tree.py
"""左侧资源导航树 — 动态扫描磁盘"""
from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from pathlib import Path


# 七层资源定义
RESOURCE_LAYERS = [
    ("🧠 Prompt", "prompts", True),
    ("📁 Memory", "workspace", True),
    ("⚙️ Config", ".", False),   # .env, adapter.yaml
    ("🔧 Tools", "skills", True),
    ("🔄 Workflow", "workflow", True),
    ("📊 Runtime", None, False),  # 运行时，不从磁盘加载
]


class ResourceTree(QTreeWidget):
    """七层资源导航树"""
    file_selected = pyqtSignal(str, str)  # (file_path, resource_type)

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemClicked.connect(self._on_item_clicked)
        self._build_tree()

    def _build_tree(self):
        """构建资源树"""
        self.clear()
        for label, dir_path, scan_disk in RESOURCE_LAYERS:
            node = QTreeWidgetItem(self, [label])
            node.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "label": label, "dir_path": dir_path})

            if scan_disk and dir_path:
                self._scan_dir(node, Path(dir_path))

            if label == "📊 Runtime":
                # 运行时固定节点
                QTreeWidgetItem(node, ["Current Turn"]).setData(0, Qt.ItemDataRole.UserRole, {"type": "runtime", "key": "current_turn"})
                QTreeWidgetItem(node, ["Turn History"]).setData(0, Qt.ItemDataRole.UserRole, {"type": "runtime", "key": "turn_history"})
                QTreeWidgetItem(node, ["Event Log"]).setData(0, Qt.ItemDataRole.UserRole, {"type": "runtime", "key": "event_log"})

            node.setExpanded(True)

    def _scan_dir(self, parent: QTreeWidgetItem, dir_path: Path):
        """递归扫描目录"""
        if not dir_path.exists():
            empty_item = QTreeWidgetItem(parent, ["(空)"])
            empty_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "empty"})
            empty_item.setForeground(0, QColor("#666666"))
            return

        try:
            items = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for item in items:
                if item.name.startswith("__") or item.suffix == ".pyc":
                    continue
                if item.name.startswith(".") and item.name not in [".env"]:
                    continue
                if item.is_dir():
                    child = QTreeWidgetItem(parent, [f"📁 {item.name}"])
                    child.setData(0, Qt.ItemDataRole.UserRole, {"type": "dir", "path": str(item)})
                    self._scan_dir(child, item)
                else:
                    icon = self._get_icon(item.suffix)
                    child = QTreeWidgetItem(parent, [f"{icon} {item.name}"])
                    child.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "path": str(item)})
                    # 设置字体颜色
                    child.setForeground(0, self._get_color(item.suffix))
        except PermissionError:
            error_item = QTreeWidgetItem(parent, ["(无权限访问)"])
            error_item.setForeground(0, QColor("#f44336"))

    def _get_icon(self, suffix: str) -> str:
        """根据文件后缀获取图标"""
        return {
            ".md": "📝",
            ".yaml": "⚙️",
            ".yml": "⚙️",
            ".json": "📋",
            ".py": "🐍",
            ".txt": "📄",
            ".env": "🔐",
        }.get(suffix.lower(), "📄")

    def _get_color(self, suffix: str) -> QColor:
        """根据文件后缀获取颜色"""
        return {
            ".md": QColor("#569cd6"),
            ".yaml": QColor("#ce9178"),
            ".yml": QColor("#ce9178"),
            ".py": QColor("#4ec9b0"),
            ".env": QColor("#dcdcaa"),
            ".json": QColor("#9cdcfe"),
        }.get(suffix.lower(), QColor("#d4d4d4"))

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """点击节点"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data.get("type") == "file":
            path = data["path"]
            self.file_selected.emit(path, self._detect_resource_type(path))
        elif data.get("type") == "runtime":
            key = data.get("key", "")
            self.file_selected.emit(f"runtime://{key}", key)

    def _detect_resource_type(self, path: str) -> str:
        """检测资源类型"""
        path_lower = path.lower()
        if "prompts" in path_lower:
            return "prompt"
        elif "skills" in path_lower:
            return "skill"
        elif "workspace" in path_lower:
            return "memory"
        elif "workflow" in path_lower:
            return "workflow"
        elif ".env" in path_lower:
            return "config"
        return "unknown"

    def _show_context_menu(self, position):
        """右键菜单"""
        item = self.itemAt(position)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") not in ("file", "dir", "category"):
            return

        menu = QMenu(self)
        act_open = menu.addAction("打开")
        act_rename = menu.addAction("重命名")
        act_delete = menu.addAction("删除")
        menu.addSeparator()
        act_new_file = menu.addAction("新建文件")
        act_new_dir = menu.addAction("新建文件夹")
        menu.addSeparator()
        act_refresh = menu.addAction("刷新")

        action = menu.exec(self.viewport().mapToGlobal(position))
        if action == act_open:
            self._on_item_clicked(item, 0)
        elif action == act_new_file:
            self._create_new_file(item)
        elif action == act_new_dir:
            self._create_new_dir(item)
        elif action == act_rename:
            self._rename_item(item)
        elif action == act_delete:
            self._delete_item(item)
        elif action == act_refresh:
            self._build_tree()

    def _create_new_file(self, parent_item: QTreeWidgetItem):
        """在选中目录下新建文件"""
        data = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "dir":
            dir_path = Path(data["path"])
        elif data and data.get("type") == "category":
            dir_path = Path(data.get("dir_path", "."))
        else:
            return

        # 创建新文件
        base_name = "untitled"
        ext = ".md"
        counter = 0
        while True:
            name = f"{base_name}{counter if counter > 0 else ''}{ext}"
            new_file = dir_path / name
            if not new_file.exists():
                break
            counter += 1

        try:
            new_file.write_text("# 新文件\n\n", encoding="utf-8")
            self._build_tree()
            self.file_selected.emit(str(new_file), self._detect_resource_type(str(new_file)))
        except Exception as e:
            print(f"创建文件失败: {e}")

    def _create_new_dir(self, parent_item: QTreeWidgetItem):
        """在选中目录下新建文件夹"""
        data = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "dir":
            dir_path = Path(data["path"])
        elif data and data.get("type") == "category":
            dir_path = Path(data.get("dir_path", "."))
        else:
            return

        base_name = "newfolder"
        counter = 0
        while True:
            name = f"{base_name}{counter if counter > 0 else ''}"
            new_dir = dir_path / name
            if not new_dir.exists():
                break
            counter += 1

        try:
            new_dir.mkdir(parents=True, exist_ok=True)
            self._build_tree()
        except Exception as e:
            print(f"创建文件夹失败: {e}")

    def _rename_item(self, item: QTreeWidgetItem):
        """重命名文件或文件夹"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") not in ("file", "dir"):
            return

        old_path = Path(data["path"])
        # TODO: 实现重命名对话框
        print(f"重命名: {old_path}")

    def _delete_item(self, item: QTreeWidgetItem):
        """删除文件或文件夹"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") not in ("file", "dir"):
            return

        path = Path(data["path"])
        # TODO: 实现确认对话框
        print(f"删除: {path}")

    def refresh(self):
        """刷新资源树"""
        self._build_tree()
