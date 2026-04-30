# workbench/widgets/kv_editor.py
"""键值对编辑器 — 用于 .env 和配置文件"""
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QHeaderView,
)
from PyQt6.QtCore import Qt
from pathlib import Path


class KeyValueEditor(QWidget):
    """键值对编辑器"""

    modificationChanged = None

    def __init__(self):
        super().__init__()
        self.current_file: str | None = None
        self._modified = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["键", "值"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(200)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        # 添加/删除按钮
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ 添加")
        btn_del = QPushButton("- 删除")
        btn_add.clicked.connect(self._add_row)
        btn_del.clicked.connect(self._del_row)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_del)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_item_changed(self, item):
        """表格项改变时标记修改"""
        self._modified = True

    def load(self, content: str, path: str):
        self.current_file = path
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(key.strip()))
                self.table.setItem(row, 1, QTableWidgetItem(value.strip()))
        self.table.blockSignals(False)
        self._modified = False

    def save(self):
        if not self.current_file:
            return
        lines = []
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            val_item = self.table.item(row, 1)
            if key_item and val_item:
                key = key_item.text().strip()
                val = val_item.text().strip()
                if key:
                    lines.append(f"{key}={val}")
        Path(self.current_file).write_text("\n".join(lines), encoding="utf-8")
        self._modified = False

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self._modified = True

    def _del_row(self):
        rows = set(item.row() for item in self.table.selectedItems())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
        self._modified = True
