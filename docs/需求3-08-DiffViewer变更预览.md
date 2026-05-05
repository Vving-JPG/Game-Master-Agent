# 08 — DiffViewer 变更预览

> 目标执行者：Trae AI
> 依赖：无
> 产出：`presentation/editor/diff_viewer.py`

---

## 1. 设计说明

DiffViewer 显示文件变更的统一 diff 格式预览，让用户可以：

1. **查看变更**：以颜色区分新增（绿色）和删除（红色）的行
2. **确认变更**：接受 AI 的修改
3. **拒绝变更**：撤销 AI 的修改，恢复原始文件
4. **查看文件路径**：显示被修改的文件路径

### 布局结构

```
┌─ 📝 变更预览 ──────────────────────────────┐
│  文件: prompts/dungeon_exploration.md       │
│  步骤: 2                                    │
│  ─────────────────────────────────────────  │
│  --- prompts/dungeon_exploration.md (旧)    │
│  +++ prompts/dungeon_exploration.md (新)    │
│  @@ 新增内容 @@                              │
│  + ## 暗黑地下城探索                         │
│  + 你是一个经验丰富的地下城探索者...          │
│  + 当玩家进入新房间时...                     │
│  ─────────────────────────────────────────  │
│  [✅ 确认变更]  [❌ 拒绝变更]                 │
└────────────────────────────────────────────┘
```

### 颜色方案

| 行类型 | 背景色 | 前景色 | 说明 |
|--------|--------|--------|------|
| `+` 新增 | `#e8f5e9` | `#2e7d32` | 绿色 |
| `-` 删除 | `#ffebee` | `#c62828` | 红色 |
| `@@` 标题 | `#e3f2fd` | `#1565c0` | 蓝色 |
| `---`/`+++` | `#f5f5f5` | `#666` | 灰色 |
| 普通行 | `white` | `#333` | 默认 |

---

## 2. 完整实现

**文件**：`presentation/editor/diff_viewer.py`

```python
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
            QFont("Consolas", "Courier New", 11)
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
```

---

## 3. 验证

```python
from presentation.editor.diff_viewer import DiffViewer

# 测试 diff 文本
diff_text = """--- /dev/null
+++ prompts/dungeon_exploration.md
+---
+category: scene
+created: 2026-05-04
+---
+
+## 暗黑地下城探索
+
+你是一个经验丰富的地下城探索者...
+当玩家进入新房间时，进行陷阱检测...
"""

viewer = DiffViewer(
    diff_text=diff_text,
    file_path="prompts/dungeon_exploration.md",
    step_id=2,
)

# 验证统计
stats = viewer._compute_stats()
assert stats["added"] == 8
assert stats["removed"] == 0
```

---

## 4. 注意事项

1. **DiffHighlighter**：使用 QTextCharFormat 逐行着色，对于大文件可能有性能问题。如果 diff 超过 500 行，考虑只显示前 200 行 + 折叠
2. **字体**：Diff 使用等宽字体（Consolas/Courier New），确保对齐
3. **滚动**：QTextEdit 设置了最大高度 300px，超出部分可滚动
4. **与 ToolExecutor 的交互**：确认/拒绝通过 EventBus 发送到 AIAssistantService，再由 ToolExecutor 处理快照恢复
