"""编辑器标签页组件"""
import frontmatter
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QLabel, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt


class EditorTabs(QTabWidget):
    """多标签编辑器"""
    
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        
    def open_file(self, path: str, file_type: str):
        """打开文件"""
        # 检查是否已打开
        for i in range(self.count()):
            widget = self.widget(i)
            if widget.property("path") == path and widget.property("file_type") == file_type:
                self.setCurrentIndex(i)
                return
                
        # 创建新标签
        try:
            if file_type == "skill":
                data = self.api.get_skill(path)
                editor = SkillEditor(self.api, path, data)
                self.addTab(editor, f"⚡ {path}")
            else:
                data = self.api.get_file(path)
                if path.endswith(".md"):
                    editor = MarkdownEditor(self.api, path, data)
                elif path.endswith(".yaml") or path.endswith(".yml"):
                    editor = YamlEditor(self.api, path, data)
                else:
                    editor = TextEditor(self.api, path, data)
                self.addTab(editor, f"📄 {path.split('/')[-1]}")
                
            editor.setProperty("path", path)
            editor.setProperty("file_type", file_type)
            self.setCurrentIndex(self.count() - 1)
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"无法打开文件: {e}")
            
    def close_tab(self, index: int):
        """关闭标签"""
        widget = self.widget(index)
        if hasattr(widget, 'is_modified') and widget.is_modified():
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "未保存", "文件有未保存的更改，是否保存？",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                widget.save()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
                
        self.removeTab(index)
        widget.deleteLater()


class BaseEditor(QWidget):
    """基础编辑器"""
    
    def __init__(self, api, path: str, data: dict):
        super().__init__()
        self.api = api
        self.path = path
        self.data = data
        self._modified = False
        
    def is_modified(self) -> bool:
        return self._modified
        
    def mark_modified(self):
        """标记为已修改"""
        self._modified = True
        self.update_tab_title()
        
    def update_tab_title(self):
        """更新标签标题"""
        parent = self.parent()
        while parent and not isinstance(parent, QTabWidget):
            parent = parent.parent()
        if parent:
            index = parent.indexOf(self)
            title = parent.tabText(index)
            if not title.startswith("*"):
                parent.setTabText(index, "*" + title)


class MarkdownEditor(BaseEditor):
    """Markdown 编辑器（支持 Front Matter）"""
    
    def __init__(self, api, path: str, data: dict):
        super().__init__(api, path, data)
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Front Matter 表格
        self.fm_widget = QWidget()
        fm_layout = QVBoxLayout(self.fm_widget)
        fm_layout.addWidget(QLabel("Front Matter:"))
        
        self.fm_table = QTableWidget()
        self.fm_table.setColumnCount(2)
        self.fm_table.setHorizontalHeaderLabels(["键", "值"])
        self.fm_table.horizontalHeader().setStretchLastSection(True)
        self.fm_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.fm_table.setColumnWidth(0, 150)
        self.fm_table.itemChanged.connect(self.mark_modified)
        
        fm_layout.addWidget(self.fm_table)
        
        # 加载 Front Matter
        self.load_frontmatter(self.data.get("frontmatter", {}))
        
        # 内容编辑器
        self.content_edit = QTextEdit()
        self.content_edit.setPlainText(self.data.get("content", ""))
        self.content_edit.textChanged.connect(self.mark_modified)
        
        splitter.addWidget(self.fm_widget)
        splitter.addWidget(self.content_edit)
        splitter.setSizes([150, 400])
        
        layout.addWidget(splitter)
        
    def load_frontmatter(self, fm: dict):
        """加载 Front Matter"""
        self.fm_table.setRowCount(len(fm))
        for i, (key, value) in enumerate(fm.items()):
            self.fm_table.setItem(i, 0, QTableWidgetItem(key))
            self.fm_table.setItem(i, 1, QTableWidgetItem(str(value)))
            
    def save(self):
        """保存文件"""
        try:
            # 收集 Front Matter
            frontmatter = {}
            for i in range(self.fm_table.rowCount()):
                key_item = self.fm_table.item(i, 0)
                value_item = self.fm_table.item(i, 1)
                if key_item and value_item:
                    key = key_item.text()
                    value = value_item.text()
                    if key:
                        frontmatter[key] = value
                        
            content = self.content_edit.toPlainText()
            
            self.api.update_file(
                self.path,
                content=content,
                frontmatter=frontmatter if frontmatter else None
            )
            
            self._modified = False
            
            # 更新标签标题
            parent = self.parent()
            while parent and not isinstance(parent, QTabWidget):
                parent = parent.parent()
            if parent:
                index = parent.indexOf(self)
                title = parent.tabText(index)
                if title.startswith("*"):
                    parent.setTabText(index, title[1:])
                    
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"保存失败: {e}")


class YamlEditor(BaseEditor):
    """YAML 编辑器"""
    
    def __init__(self, api, path: str, data: dict):
        super().__init__(api, path, data)
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.editor = QTextEdit()
        self.editor.setPlainText(self.data.get("raw", self.data.get("content", "")))
        self.editor.textChanged.connect(self.mark_modified)
        
        layout.addWidget(self.editor)
        
    def save(self):
        """保存文件"""
        try:
            self.api.update_file(self.path, raw=self.editor.toPlainText())
            self._modified = False
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"保存失败: {e}")


class TextEditor(BaseEditor):
    """纯文本编辑器"""
    
    def __init__(self, api, path: str, data: dict):
        super().__init__(api, path, data)
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.editor = QTextEdit()
        
        # 获取原始内容
        content = self.data.get("raw", self.data.get("content", ""))
        self.editor.setPlainText(content)
        self.editor.textChanged.connect(self.mark_modified)
        
        layout.addWidget(self.editor)
        
    def save(self):
        """保存文件"""
        try:
            self.api.update_file(self.path, raw=self.editor.toPlainText())
            self._modified = False
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"保存失败: {e}")


class SkillEditor(BaseEditor):
    """Skill 编辑器"""
    
    def __init__(self, api, name: str, data: dict):
        super().__init__(api, name, data)
        self.name = name
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 信息栏
        info_layout = QHBoxLayout()
        
        fm = self.data.get("frontmatter", {})
        info_layout.addWidget(QLabel(f"名称: {fm.get('name', self.name)}"))
        info_layout.addWidget(QLabel(f"版本: {fm.get('version', 'N/A')}"))
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # 编辑器
        self.editor = QTextEdit()
        self.editor.setPlainText(self.data.get("raw", ""))
        self.editor.textChanged.connect(self.mark_modified)
        
        layout.addWidget(self.editor)
        
    def save(self):
        """保存 Skill"""
        try:
            self.api.update_skill(self.name, self.editor.toPlainText())
            self._modified = False
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"保存失败: {e}")
