# API 设置界面重构指导文档 — Trae 模型管理风格

> 目标：将设置对话框改为 Trae 风格的「模型管理」界面
> 涉及文件：`2workbench/presentation/dialogs/settings_dialog.py`
> 预估工作量：2-3 小时

---

## 一、目标效果

### 截图1：添加模型表单（点击"+ 添加模型"弹出）
```
┌─────────────────────────────────────┐
│  添加模型                        ✕  │
│                                     │
│  * 模型                              │
│  ┌─────────────────────────────┐    │
│  │ 选择模型                  ▼ │    │
│  └─────────────────────────────┘    │
│                                     │
│  * API 密钥                          │
│  ┌─────────────────────────────┐    │
│  │ 输入 API 密钥               │    │
│  └─────────────────────────────┘    │
│                                     │
│    自定义请求地址              ⓘ    │
│  ┌─────────────────────────────┐    │
│  │ 例如 https://api.openai.com │    │
│  │     /v1/chat/completions    │    │
│  └─────────────────────────────┘    │
│                                     │
│  ┌─────────────────────────────┐    │
│  │         添加模型             │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

### 截图2：模型管理列表（设置对话框主界面）
```
┌──────────────────────────────────────────────────────┐
│  模型                                                 │
│                                                      │
│  模型管理                                             │
│  配置 API key 添加更多可用模型，预置模型默认使用稳定版本。  │
│                                                      │
│  [+ 添加模型]                                         │
│                                                      │
│  ┌──────────────────────────────────────────────────┐ │
│  │ 模型                    │ 服务商    │ 操作       │ │
│  ├──────────────────────────┼──────────┼───────────┤ │
│  │ ▼ 内置                                             │ │
│  │   deepseek-v4            │ 预置      │    -      │ │
│  │   gpt-4o                 │ 预置      │    -      │ │
│  │   claude-sonnet-4        │ 预置      │    -      │ │
│  ├──────────────────────────┼──────────┼───────────┤ │
│  │ ▼ 自定义                                           │ │
│  │   deepseek-v4-pro        │ DeepSeek  │ ✎ 🗑 ●   │ │
│  │   my-gpt4                │ OpenAI    │ ✎ 🗑 ○   │ │
│  └──────────────────────────┴──────────┴───────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 二、完整代码

将 `settings_dialog.py` 整体替换为以下代码：

```python
"""设置对话框 — Trae 风格模型管理

主界面为模型列表（内置 + 自定义），点击"+ 添加模型"弹出添加表单。
自定义模型支持编辑、删除、启用/禁用。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QLabel,
    QWidget, QFrame, QScrollArea, QSizePolicy,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPen, QBrush, QPainter

from foundation.config import settings
from foundation.logger import get_logger
from presentation.theme.manager import theme_manager

logger = get_logger(__name__)

# 自定义模型存储路径
CUSTOM_MODELS_FILE = Path("./data/custom_models.json")

# 内置模型列表
BUILTIN_MODELS = [
    {"model": "deepseek-v4", "provider": "预置"},
    {"model": "deepseek-v4-pro", "provider": "预置"},
    {"model": "deepseek-v4-lite", "provider": "预置"},
    {"model": "gpt-4o", "provider": "预置"},
    {"model": "gpt-4o-mini", "provider": "预置"},
    {"model": "claude-sonnet-4-20250514", "provider": "预置"},
    {"model": "claude-haiku-4-20250414", "provider": "预置"},
]


class AddModelDialog(QDialog):
    """添加/编辑模型对话框 — 极简表单"""

    def __init__(self, parent=None, edit_data: Dict[str, Any] | None = None):
        super().__init__(parent)
        self._edit_data = edit_data
        self.setWindowTitle("编辑模型" if edit_data else "添加模型")
        self.setFixedSize(400, 340)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self._setup_ui()
        self._apply_theme()
        if edit_data:
            self._fill_data(edit_data)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 标题栏
        title_bar = QHBoxLayout()
        title_label = QLabel("编辑模型" if self._edit_data else "添加模型")
        title_label.setObjectName("dialogTitle")
        title_bar.addWidget(title_label)
        title_bar.addStretch(1)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("dialogCloseBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.reject)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)

        layout.addSpacing(8)

        # 模型名称
        model_label = QLabel("* 模型")
        model_label.setObjectName("formLabel")
        layout.addWidget(model_label)

        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText("选择模型")
        self._model_input.setObjectName("formInput")
        layout.addWidget(self._model_input)

        # API 密钥
        key_label = QLabel("* API 密钥")
        key_label.setObjectName("formLabel")
        layout.addWidget(key_label)

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("输入 API 密钥")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setObjectName("formInput")
        layout.addWidget(self._key_input)

        # 自定义请求地址（可选）
        url_row = QHBoxLayout()
        url_label = QLabel("自定义请求地址")
        url_label.setObjectName("formLabel")
        url_row.addWidget(url_label)

        info_btn = QPushButton("ⓘ")
        info_btn.setObjectName("infoBtn")
        info_btn.setFixedSize(18, 18)
        info_btn.setToolTip("可选，留空使用默认地址")
        url_row.addWidget(info_btn)
        url_row.addStretch(1)
        layout.addLayout(url_row)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("例如 https://api.openai.com/v1/chat/completions")
        self._url_input.setObjectName("formInput")
        layout.addWidget(self._url_input)

        layout.addStretch(1)

        # 添加按钮
        self._submit_btn = QPushButton("添加模型" if not self._edit_data else "保存")
        self._submit_btn.setObjectName("submitBtn")
        self._submit_btn.setFixedHeight(36)
        self._submit_btn.clicked.connect(self._on_submit)
        layout.addWidget(self._submit_btn)

    def _fill_data(self, data: Dict[str, Any]) -> None:
        """编辑模式填充数据"""
        self._model_input.setText(data.get("model", ""))
        self._key_input.setText(data.get("api_key", ""))
        self._url_input.setText(data.get("base_url", ""))

    def _on_submit(self) -> None:
        model = self._model_input.text().strip()
        api_key = self._key_input.text().strip()
        if not model or not api_key:
            return
        self._result = {
            "model": model,
            "api_key": api_key,
            "base_url": self._url_input.text().strip(),
            "enabled": True,
        }
        if self._edit_data:
            self._result["id"] = self._edit_data.get("id")
        self.accept()

    def get_result(self) -> Dict[str, Any] | None:
        return getattr(self, "_result", None)

    def _apply_theme(self) -> None:
        p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
        bg = p.get("bg_primary", "#1e1e1e")
        bg_card = p.get("bg_secondary", "#252526")
        bg_input = p.get("bg_tertiary", "#2d2d30")
        border = p.get("border", "#3e3e42")
        accent = p.get("accent", "#007acc")
        text = p.get("text_primary", "#cccccc")
        text_bright = p.get("text_bright", "#ffffff")
        text_sec = p.get("text_secondary", "#858585")
        font = p.get("font_family", "sans-serif")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLabel#dialogTitle {{
                color: {text_bright};
                font-size: 16px;
                font-weight: 600;
                font-family: {font};
                background: transparent;
            }}
            QPushButton#dialogCloseBtn {{
                color: {text_sec};
                border: none;
                background: transparent;
                font-size: 14px;
                border-radius: 4px;
            }}
            QPushButton#dialogCloseBtn:hover {{
                color: {text_bright};
                background-color: {p.get("bg_hover", "#3e3e42")};
            }}
            QLabel#formLabel {{
                color: {text};
                font-size: 13px;
                font-family: {font};
                background: transparent;
            }}
            QLineEdit#formInput {{
                background-color: {bg_input};
                color: {text_bright};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: {font};
            }}
            QLineEdit#formInput:focus {{
                border-color: {accent};
            }}
            QPushButton#infoBtn {{
                color: {text_sec};
                border: none;
                background: transparent;
                font-size: 12px;
            }}
            QPushButton#submitBtn {{
                background-color: {p.get("bg_hover", "#3e3e42")};
                color: {text_bright};
                border: 1px solid {border};
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                font-family: {font};
            }}
            QPushButton#submitBtn:hover {{
                background-color: {accent};
                border-color: {accent};
            }}
        """)


class ModelListWidget(QWidget):
    """模型列表 — 内置 + 自定义分组"""

    model_changed = pyqtSignal()  # 模型列表变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._custom_models: List[Dict[str, Any]] = []
        self._load_custom_models()
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 页面标题
        title = QLabel("模型")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        layout.addSpacing(12)

        # 模型管理小节
        section_title = QLabel("模型管理")
        section_title.setObjectName("sectionTitle")
        layout.addWidget(section_title)

        desc = QLabel("配置 API key 添加更多可用模型，预置模型默认使用稳定版本。")
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(12)

        # 添加模型按钮
        self._add_btn = QPushButton("+ 添加模型")
        self._add_btn.setObjectName("addModelBtn")
        self._add_btn.setFixedHeight(34)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add_model)
        layout.addWidget(self._add_btn)

        layout.addSpacing(12)

        # 模型列表容器
        list_frame = QFrame()
        list_frame.setObjectName("listFrame")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        # 表头
        header = QFrame()
        header.setObjectName("listHeader")
        header.setFixedHeight(32)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        col_model = QLabel("模型")
        col_model.setObjectName("headerLabel")
        header_layout.addWidget(col_model, stretch=5)

        col_provider = QLabel("服务商")
        col_provider.setObjectName("headerLabel")
        col_provider.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(col_provider, stretch=2)

        col_action = QLabel("操作")
        col_action.setObjectName("headerLabel")
        col_action.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(col_action, stretch=2)

        list_layout.addWidget(header)

        # 内置模型分组
        self._builtin_section = self._create_section("内置", BUILTIN_MODELS, editable=False)
        list_layout.addWidget(self._builtin_section)

        # 自定义模型分组
        self._custom_section = self._create_section("自定义", self._custom_models, editable=True)
        list_layout.addWidget(self._custom_section)

        layout.addWidget(list_frame)

    def _create_section(self, title: str, models: List[Dict], editable: bool) -> QFrame:
        """创建模型分组"""
        section = QFrame()
        section.setObjectName("modelSection")
        s_layout = QVBoxLayout(section)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(0)

        # 分组标题行
        title_row = QFrame()
        title_row.setObjectName("sectionRow")
        title_row.setFixedHeight(32)
        tr_layout = QHBoxLayout(title_row)
        tr_layout.setContentsMargins(12, 0, 12, 0)

        chevron = QLabel("▼")
        chevron.setObjectName("chevron")
        tr_layout.addWidget(chevron)

        title_label = QLabel(title)
        title_label.setObjectName("sectionLabel")
        tr_layout.addWidget(title_label)

        tr_layout.addStretch(1)
        s_layout.addWidget(title_row)

        # 模型行
        for m in models:
            row = self._create_model_row(m, editable)
            s_layout.addWidget(row)

        return section

    def _create_model_row(self, model_data: Dict, editable: bool) -> QFrame:
        """创建单行模型"""
        row = QFrame()
        row.setObjectName("modelRow")
        row.setFixedHeight(40)
        r_layout = QHBoxLayout(row)
        r_layout.setContentsMargins(12, 0, 12, 0)

        # 模型名
        name_label = QLabel(model_data.get("model", ""))
        name_label.setObjectName("modelName")
        r_layout.addWidget(name_label, stretch=5)

        # 服务商
        provider = model_data.get("provider", "自定义")
        provider_label = QLabel(provider)
        provider_label.setObjectName("modelProvider")
        provider_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r_layout.addWidget(provider_label, stretch=2)

        # 操作列
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if editable:
            model_id = model_data.get("id", "")
            model_name = model_data.get("model", "")

            # 编辑按钮
            edit_btn = QPushButton("✎")
            edit_btn.setObjectName("rowActionBtn")
            edit_btn.setFixedSize(24, 24)
            edit_btn.setToolTip("编辑")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, mid=model_id, mn=model_name: self._on_edit(mid, mn))
            action_layout.addWidget(edit_btn)

            # 删除按钮
            del_btn = QPushButton("🗑")
            del_btn.setObjectName("rowActionBtn danger")
            del_btn.setFixedSize(24, 24)
            del_btn.setToolTip("删除")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, mid=model_id: self._on_delete(mid))
            action_layout.addWidget(del_btn)

            # 启用/禁用开关
            enabled = model_data.get("enabled", True)
            toggle_btn = QPushButton("●" if enabled else "○")
            toggle_btn.setObjectName("toggleBtn" if enabled else "toggleBtn off")
            toggle_btn.setFixedSize(24, 24)
            toggle_btn.setToolTip("启用" if enabled else "禁用")
            toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            toggle_btn.clicked.connect(lambda checked, mid=model_id: self._on_toggle(mid))
            action_layout.addWidget(toggle_btn)
        else:
            dash = QLabel("-")
            dash.setObjectName("dashLabel")
            dash.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_layout.addWidget(dash)

        r_layout.addLayout(action_layout, stretch=2)

        return row

    def _on_add_model(self) -> None:
        """弹出添加模型对话框"""
        dialog = AddModelDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                import uuid
                result["id"] = str(uuid.uuid4())[:8]
                result["provider"] = self._guess_provider(result["model"])
                self._custom_models.append(result)
                self._save_custom_models()
                self.refresh()
                self.model_changed.emit()

    def _on_edit(self, model_id: str, model_name: str) -> None:
        """编辑自定义模型"""
        data = next((m for m in self._custom_models if m.get("id") == model_id), None)
        if not data:
            return
        dialog = AddModelDialog(self, edit_data=data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                result["provider"] = self._guess_provider(result["model"])
                # 更新列表
                for i, m in enumerate(self._custom_models):
                    if m.get("id") == model_id:
                        self._custom_models[i] = result
                        break
                self._save_custom_models()
                self.refresh()
                self.model_changed.emit()

    def _on_delete(self, model_id: str) -> None:
        """删除自定义模型"""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "删除模型", "确定要删除这个模型配置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._custom_models = [m for m in self._custom_models if m.get("id") != model_id]
            self._save_custom_models()
            self.refresh()
            self.model_changed.emit()

    def _on_toggle(self, model_id: str) -> None:
        """启用/禁用模型"""
        for m in self._custom_models:
            if m.get("id") == model_id:
                m["enabled"] = not m.get("enabled", True)
                break
        self._save_custom_models()
        self.refresh()
        self.model_changed.emit()

    def _guess_provider(self, model_name: str) -> str:
        """根据模型名猜测服务商"""
        model_lower = model_name.lower()
        if "deepseek" in model_lower:
            return "DeepSeek"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "OpenAI"
        elif "claude" in model_lower or "anthropic" in model_lower:
            return "Anthropic"
        elif "qwen" in model_lower:
            return "Qwen"
        elif "glm" in model_lower:
            return "GLM"
        else:
            return "自定义"

    def refresh(self) -> None:
        """刷新列表"""
        # 重建整个 widget
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 清理子布局
                sub = item.layout()
                while sub.count():
                    sub_item = sub.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
        self._setup_ui()

    def _load_custom_models(self) -> None:
        """从文件加载自定义模型"""
        if CUSTOM_MODELS_FILE.exists():
            try:
                with open(CUSTOM_MODELS_FILE, "r", encoding="utf-8") as f:
                    self._custom_models = json.load(f)
            except Exception as e:
                logger.warning(f"加载自定义模型失败: {e}")
                self._custom_models = []

    def _save_custom_models(self) -> None:
        """保存自定义模型到文件"""
        CUSTOM_MODELS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(CUSTOM_MODELS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._custom_models, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存自定义模型失败: {e}")

    def get_enabled_custom_models(self) -> List[Dict[str, Any]]:
        """获取所有已启用的自定义模型"""
        return [m for m in self._custom_models if m.get("enabled", True)]

    def _apply_theme(self) -> None:
        p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
        bg = p.get("bg_primary", "#1e1e1e")
        bg_sec = p.get("bg_secondary", "#252526")
        bg_ter = p.get("bg_tertiary", "#2d2d30")
        bg_hover = p.get("bg_hover", "#3e3e42")
        border = p.get("border", "#3e3e42")
        accent = p.get("accent", "#007acc")
        text = p.get("text_primary", "#cccccc")
        text_bright = p.get("text_bright", "#ffffff")
        text_sec = p.get("text_secondary", "#858585")
        success = p.get("success", "#4ec9b0")
        error = p.get("error", "#f44747")
        font = p.get("font_family", "sans-serif")

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                font-family: {font};
            }}
            QLabel#pageTitle {{
                color: {text_bright};
                font-size: 20px;
                font-weight: 600;
                background: transparent;
            }}
            QLabel#sectionTitle {{
                color: {text_bright};
                font-size: 14px;
                font-weight: 600;
                background: transparent;
            }}
            QLabel#sectionDesc {{
                color: {text_sec};
                font-size: 12px;
                background: transparent;
            }}
            QPushButton#addModelBtn {{
                color: {text_bright};
                background-color: {bg_ter};
                border: 1px solid {border};
                border-radius: 6px;
                font-size: 13px;
                font-family: {font};
            }}
            QPushButton#addModelBtn:hover {{
                background-color: {bg_hover};
                border-color: {accent};
            }}

            /* 列表框架 */
            QFrame#listFrame {{
                background-color: {bg_sec};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QFrame#listHeader {{
                background-color: {bg_ter};
                border-bottom: 1px solid {border};
                border-radius: 6px 6px 0 0;
            }}
            QLabel#headerLabel {{
                color: {text_sec};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }}

            /* 分组 */
            QFrame#modelSection {{
                background-color: {bg_sec};
                border: none;
            }}
            QFrame#sectionRow {{
                background-color: {bg_ter};
                border-bottom: 1px solid {border};
            }}
            QLabel#chevron {{
                color: {text_sec};
                font-size: 10px;
                background: transparent;
                padding-right: 6px;
            }}
            QLabel#sectionLabel {{
                color: {text};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }}

            /* 模型行 */
            QFrame#modelRow {{
                border-bottom: 1px solid {border};
            }}
            QFrame#modelRow:hover {{
                background-color: {bg_hover};
            }}
            QLabel#modelName {{
                color: {text_bright};
                font-size: 13px;
                background: transparent;
            }}
            QLabel#modelProvider {{
                color: {text_sec};
                font-size: 12px;
                background: transparent;
            }}
            QLabel#dashLabel {{
                color: {text_sec};
                font-size: 12px;
                background: transparent;
            }}

            /* 行操作按钮 */
            QPushButton#rowActionBtn {{
                color: {text_sec};
                border: none;
                background: transparent;
                font-size: 13px;
                border-radius: 4px;
            }}
            QPushButton#rowActionBtn:hover {{
                color: {text_bright};
                background-color: {bg_hover};
            }}
            QPushButton#rowActionBtn[danger="true"]:hover {{
                color: {error};
            }}

            /* 开关按钮 */
            QPushButton#toggleBtn {{
                color: {success};
                border: none;
                background: transparent;
                font-size: 16px;
            }}
            QPushButton#toggleBtn:hover {{
                color: {success};
            }}
            QPushButton#toggleBtn#off {{
                color: {text_sec};
            }}
            QPushButton#toggleBtn#off:hover {{
                color: {text};
            }}
        """)


class SettingsDialog(QDialog):
    """设置对话框 — 模型管理（Trae 风格）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(560, 600)
        self.resize(560, 600)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(0)

        self._model_list = ModelListWidget(self)
        layout.addWidget(self._model_list)

    def _apply_theme(self) -> None:
        p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
        bg = p.get("bg_primary", "#1e1e1e")
        border = p.get("border", "#3e3e42")
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)
```

---

## 三、关键改动说明

| 改动点 | 旧 | 新 |
|--------|-----|-----|
| **整体布局** | QTabWidget 两页表单 | 模型管理列表 + 弹出式添加表单 |
| **添加模型** | 在表单中填写所有字段 | 点击"+ 添加模型"弹出极简对话框（3个字段） |
| **模型列表** | 无 | 内置模型（只读）+ 自定义模型（可编辑/删除/开关） |
| **数据存储** | 写入 `.env` 文件 | 自定义模型存 `data/custom_models.json`，内置模型硬编码 |
| **服务商识别** | 手动选择 deepseek/openai/anthropic | 根据模型名自动识别（deepseek→DeepSeek, gpt→OpenAI...） |
| **启用/禁用** | 无 | 自定义模型有开关按钮，禁用后不参与 API 调用 |
| **主题** | 无 | 完整接入 theme_manager |

## 四、数据流

```
添加模型 → AddModelDialog → 保存到 custom_models.json → 刷新列表
编辑模型 → AddModelDialog(edit_data) → 更新 custom_models.json → 刷新列表
删除模型 → 确认弹窗 → 从 custom_models.json 移除 → 刷新列表
启用/禁用 → 切换 enabled 字段 → 保存 → 刷新列表
```

## 五、后续集成（可选）

如果需要让自定义模型真正参与 API 调用，需要在 `foundation/config.py` 的 `Settings` 类中添加：

```python
# 在 Settings 类中添加
custom_models_file: str = "./data/custom_models.json"

def get_all_provider_configs(self) -> Dict[str, LLMProviderConfig]:
    """获取所有已配置的供应商（包括自定义）"""
    configs = {}
    # 原有三个预置
    for name in ["deepseek", "openai", "anthropic"]:
        configs[name] = self.get_provider_config(name)
    # 加载自定义
    from pathlib import Path
    import json
    custom_path = Path(self.custom_models_file)
    if custom_path.exists():
        with open(custom_path, "r", encoding="utf-8") as f:
            for m in json.load(f):
                if m.get("enabled", True) and m.get("api_key"):
                    configs[m["model"]] = LLMProviderConfig(
                        api_key=m["api_key"],
                        base_url=m.get("base_url", ""),
                        model=m["model"],
                    )
    return configs
```

## 六、验收标准

- [ ] 主界面显示模型列表，分为"内置"和"自定义"两个分组
- [ ] 内置模型显示模型名 + "预置" + "-"（不可操作）
- [ ] 点击"+ 添加模型"弹出无边框对话框，包含模型/API Key/地址三个字段
- [ ] 填写后点"添加模型"，新模型出现在"自定义"分组中
- [ ] 自定义模型有编辑✎、删除🗑、开关●三个操作
- [ ] 编辑弹出同一对话框，预填数据
- [ ] 删除有确认弹窗
- [ ] 开关切换启用/禁用状态
- [ ] 数据持久化到 `data/custom_models.json`
- [ ] 暗色/亮色主题正确
