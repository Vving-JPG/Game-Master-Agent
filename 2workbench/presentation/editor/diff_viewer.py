"""
AI 助手 — 变更预览（Diff Viewer）
显示文件变更的统一 diff 格式，支持确认/拒绝
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QSizePolicy,
    QScrollBar,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

from foundation.logger import get_logger

logger = get_logger(__name__)


class DiffHighlighter:
    """Diff 语法高亮器（用于 QTextEdit）"""

    # 颜色定义
    COLORS = {
        "added_bg": QColor("#e8f5e9"),
        "added_fg": QColor("#2e7d32"),
        "removed_bg": QColor("#ffebee"),
        "removed_fg": QColor("#c62828"),
        "header_bg": QColor("#f5f5f5"),
        "header_fg": QColor("#666"),
        "hunk_bg": QColor("#e3f2fd"),
        "hunk_fg": QColor("#1565c0"),
    }

    @classmethod
    def apply_to_text_edit(cls, text_edit: QTextEdit, diff_text: str):
        """将 diff 文本应用到 QTextEdit 并高亮"""
        text_edit.setPlainText(diff_text)

        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        for line in diff_text.split("\n"):
            # 选中当前行
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(
                QTextCursor.MoveOperation.EndOfLine,
                QTextCursor.MoveMode.KeepAnchor,
            )

            fmt = QTextCharFormat()

            if line.startswith("+") and not line.startswith("+++"):
                fmt.setBackground(cls.COLORS["added_bg"])
                fmt.setForeground(cls.COLORS["added_fg"])
            elif line.startswith("-") and not line.startswith("---"):
                fmt.setBackground(cls.COLORS["removed_bg"])
                fmt.setForeground(cls.COLORS["removed_fg"])
            elif line.startswith("@@"):
                fmt.setBackground(cls.COLORS["hunk_bg"])
                fmt.setForeground(cls.COLORS["hunk_fg"])
                fmt.setFontWeight(QFont.Weight.Bold)
            elif line.startswith("---") or line.startswith("+++"):
                fmt.setBackground(cls.COLORS["header_bg"])
                fmt.setForeground(cls.COLORS["header_fg"])
                fmt.setFontWeight(QFont.Weight.Bold)

            if fmt.background().color() != QColor():
                cursor.mergeCharFormat(fmt)

            # 移动到下一行
            cursor.movePosition(QTextCursor.MoveOperation.Down)


class DiffViewer(QFrame):
    """变更预览组件"""

    diff_action = pyqtSignal(str, int)  # action ("confirm" / "reject"), step_id

    def __init__(self, diff_text: str, file_path: str, step_id: int, parent=None):
        super().__init__(parent)
        self._diff_text = diff_text
        self._file_path = file_path
        self._step_id = step_id
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 容器
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(16, 12, 16, 12)
        container_layout.setSpacing(8)

        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        title = QLabel("📝 变更预览")
        title.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
        title.setStyleSheet("border: none;")
        title_layout.addWidget(title)

        title_layout.addStretch()

        # 文件路径标签
        file_label = QLabel(f"📄 {self._file_path}")
        file_label.setStyleSheet(
            "color: #666; font-size: 11px; "
            "font-family: 'Consolas', 'Courier New', monospace; "
            "border: none;"
        )
        title_layout.addWidget(file_label)

        container_layout.addLayout(title_layout)

        # 步骤信息
        step_info = QLabel(f"步骤 {self._step_id} 的文件变更")
        step_info.setStyleSheet("color: #888; font-size: 11px; border: none;")
        container_layout.addWidget(step_info)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #eee;")
        container_layout.addWidget(line)

        # Diff 显示区域
        self._diff_display = QTextEdit()
        self._diff_display.setReadOnly(True)
        self._diff_display.setMaximumHeight(300)
        self._diff_display.setFont(
            QFont("Consolas", 11)
        )
        self._diff_display.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                background: #fafafa;
            }
        """)

        # 应用 diff 文本和高亮
        DiffHighlighter.apply_to_text_edit(
            self._diff_display, self._diff_text
        )

        container_layout.addWidget(self._diff_display)

        # 统计信息
        stats = self._compute_stats()
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        added_label = QLabel(f"🟢 +{stats['added']} 行新增")
        added_label.setStyleSheet("color: #2e7d32; font-size: 11px; border: none;")
        stats_layout.addWidget(added_label)

        removed_label = QLabel(f"🔴 -{stats['removed']} 行删除")
        removed_label.setStyleSheet("color: #c62828; font-size: 11px; border: none;")
        stats_layout.addWidget(removed_label)

        stats_layout.addStretch()
        container_layout.addLayout(stats_layout)

        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #eee;")
        container_layout.addWidget(line2)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        # 确认按钮
        confirm_btn = QPushButton("✅ 确认变更")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #43a047; }
            QPushButton:pressed { background-color: #388e3c; }
        """)
        confirm_btn.clicked.connect(
            lambda: self.diff_action.emit("confirm", self._step_id)
        )
        btn_layout.addWidget(confirm_btn)

        btn_layout.addStretch()

        # 拒绝按钮
        reject_btn = QPushButton("❌ 拒绝变更（恢复原文件）")
        reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #c62828;
                border: 1px solid #ffcdd2;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #ffebee; }
        """)
        reject_btn.clicked.connect(
            lambda: self.diff_action.emit("reject", self._step_id)
        )
        btn_layout.addWidget(reject_btn)

        container_layout.addLayout(btn_layout)

        layout.addWidget(container)

    def _compute_stats(self) -> dict:
        """计算 diff 统计信息"""
        added = 0
        removed = 0

        for line in self._diff_text.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1

        return {"added": added, "removed": removed}

    def update_diff(self, diff_text: str):
        """更新 diff 内容"""
        self._diff_text = diff_text
        DiffHighlighter.apply_to_text_edit(
            self._diff_display, diff_text
        )
