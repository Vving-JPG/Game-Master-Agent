"""资源树组件"""
from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog,
    QMessageBox, QLineEdit
)
from PyQt6.QtCore import pyqtSignal


class ResourceTree(QTreeWidget):
    """资源树（Workspace + Skills）"""
    
    file_selected = pyqtSignal(str, str)  # path, file_type
    
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setHeaderLabel("资源")
        self.setColumnCount(1)
        
        # 根节点
        self.workspace_root = QTreeWidgetItem(self, ["📁 Workspace"])
        self.skills_root = QTreeWidgetItem(self, ["⚡ Skills"])
        
        self.workspace_root.setExpanded(True)
        self.skills_root.setExpanded(True)
        
        # 信号连接
        self.itemClicked.connect(self.on_item_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def refresh(self):
        """刷新树"""
        self.clear()
        self.workspace_root = QTreeWidgetItem(self, ["📁 Workspace"])
        self.skills_root = QTreeWidgetItem(self, ["⚡ Skills"])
        self.workspace_root.setExpanded(True)
        self.skills_root.setExpanded(True)
        
        # 加载 Workspace
        try:
            self.load_workspace("", self.workspace_root)
        except Exception as e:
            self.workspace_root.addChild(QTreeWidgetItem([f"错误: {e}"]))
            
        # 加载 Skills
        try:
            skills = self.api.list_skills()
            for skill in skills:
                item = QTreeWidgetItem(self.skills_root, [f"⚡ {skill['name']}"])
                item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "skill",
                    "name": skill["name"],
                    "source": skill.get("source", "builtin")
                })
        except Exception as e:
            self.skills_root.addChild(QTreeWidgetItem([f"错误: {e}"]))
            
    def load_workspace(self, path: str, parent: QTreeWidgetItem):
        """加载 Workspace 目录"""
        try:
            data = self.api.get_workspace_tree(path)
            for child in data.get("children", []):
                name = child["name"]
                child_path = child["path"]
                
                if child["type"] == "directory":
                    item = QTreeWidgetItem(parent, [f"📁 {name}"])
                    item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "directory",
                        "path": child_path
                    })
                    # 递归加载子目录
                    self.load_workspace(child_path, item)
                else:
                    icon = "📄"
                    if name.endswith(".md"):
                        icon = "📝"
                    elif name.endswith(".yaml") or name.endswith(".yml"):
                        icon = "⚙️"
                    elif name.endswith(".py"):
                        icon = "🐍"
                        
                    item = QTreeWidgetItem(parent, [f"{icon} {name}"])
                    item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "file",
                        "path": child_path
                    })
        except Exception as e:
            parent.addChild(QTreeWidgetItem([f"错误: {e}"]))
            
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """点击事件"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        if data.get("type") == "file":
            self.file_selected.emit(data["path"], "workspace")
        elif data.get("type") == "skill":
            self.file_selected.emit(data["name"], "skill")
            
    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.itemAt(position)
        menu = QMenu()
        
        if not item:
            # 根菜单
            new_file_action = menu.addAction("📄 新建文件")
            new_file_action.triggered.connect(self.create_file)
            refresh_action = menu.addAction("🔄 刷新")
            refresh_action.triggered.connect(self.refresh)
        else:
            data = item.data(0, Qt.ItemDataRole.UserRole) or {}
            
            if data.get("type") == "directory":
                new_file_action = menu.addAction("📄 新建文件")
                new_file_action.triggered.connect(lambda: self.create_file(data["path"]))
                new_dir_action = menu.addAction("📁 新建文件夹")
                new_dir_action.triggered.connect(lambda: self.create_directory(data["path"]))
                menu.addSeparator()
                delete_action = menu.addAction("🗑️ 删除")
                delete_action.triggered.connect(lambda: self.delete_item(data["path"], "directory"))
                
            elif data.get("type") == "file":
                delete_action = menu.addAction("🗑️ 删除")
                delete_action.triggered.connect(lambda: self.delete_item(data["path"], "file"))
                
            elif data.get("type") == "skill":
                if data.get("source") == "agent_created":
                    delete_action = menu.addAction("🗑️ 删除")
                    delete_action.triggered.connect(lambda: self.delete_skill(data["name"]))
                    
        menu.exec(self.viewport().mapToGlobal(position))
        
    def create_file(self, directory: str = ""):
        """创建文件"""
        name, ok = QInputDialog.getText(
            self, "新建文件", "文件名:",
            QLineEdit.EchoMode.Normal, "new_file.md"
        )
        if ok and name:
            try:
                path = f"{directory}/{name}" if directory else name
                self.api.create_file(path, "")
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建失败: {e}")
                
    def create_directory(self, parent: str = ""):
        """创建目录"""
        name, ok = QInputDialog.getText(
            self, "新建文件夹", "文件夹名:",
            QLineEdit.EchoMode.Normal, "new_folder"
        )
        if ok and name:
            try:
                path = f"{parent}/{name}/.gitkeep" if parent else f"{name}/.gitkeep"
                self.api.create_file(path, "")
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建失败: {e}")
                
    def delete_item(self, path: str, item_type: str):
        """删除文件/目录"""
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除 {path} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api.delete_file(path)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {e}")
                
    def delete_skill(self, name: str):
        """删除 Skill"""
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除 Skill '{name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api.delete_skill(name)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {e}")


from PyQt6.QtCore import Qt
