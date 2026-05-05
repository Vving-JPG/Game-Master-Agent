# settings_dialog.py 修复指导文档

> 将 `2workbench/presentation/dialogs/settings_dialog.py` 整体替换为下方代码即可修复全部 5 个问题。

## 修复的问题

| # | 问题 | 修复方式 |
|---|------|----------|
| 1 | 设置窗口显示空白 | `refresh()` 改为完全重建 UI，不再用 `deleteLater()` 局部刷新 |
| 2 | config.json 未更新 | `_sync_to_config()` 适配 `{"providers": {...}}` 格式 |
| 3 | 配置格式混乱 | 同 provider 多模型不再互相覆盖，自定义数据独立存 `custom_models.json` |
| 4 | 界面布局空白 | 紧凑布局，标题+按钮同行，行高 36px |
| 5 | 编辑数据未填充 | 移除无用参数，`_on_edit` 直接通过 `model_id` 查找并传递 `edit_data` |

## 完整替换代码

将 `settings_dialog.py` 全部内容替换为：

```python
"""设置对话框 — Trae 风格模型管理

主界面为模型列表，点击"+ 添加模型"弹出添加表单。
自定义模型支持编辑、删除。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel,
    QWidget, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from foundation.logger import get_logger
from presentation.theme.manager import theme_manager

logger = get_logger(__name__)

CUSTOM_MODELS_FILE = Path("./data/custom_models.json")


class AddModelDialog(QDialog):
    """添加/编辑模型对话框"""

    def __init__(self, parent=None, edit_data: Dict[str, Any] | None = None):
        super().__init__(parent)
        self._edit_data = edit_data
        self._result: Dict[str, Any] | None = None

        self.setWindowTitle("编辑模型" if edit_data else "添加模型")
        self.setFixedSize(380, 300)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self._setup_ui()
        self._apply_theme()
        if edit_data:
            self._fill_data(edit_data)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("编辑模型" if self._edit_data else "添加模型")
        title.setObjectName("dialogTitle")
        root.addWidget(title)

        root.addWidget(self._label("* 模型"))
        self._model_input = self._input("例如 deepseek-chat")
        root.addWidget(self._model_input)

        root.addWidget(self._label("* API 密钥"))
        self._key_input = self._input("输入 API 密钥", password=True)
        root.addWidget(self._key_input)

        root.addWidget(self._label("自定义请求地址（可选）"))
        self._url_input = self._input("留空使用默认地址")
        root.addWidget(self._url_input)

        root.addStretch(1)

        btn_row = QHBoxLayout()
        cancel = QPushButton("取消")
        cancel.setObjectName("cancelBtn")
        cancel.setFixedHeight(32)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        btn_row.addStretch(1)

        submit = QPushButton("保存" if self._edit_data else "添加")
        submit.setObjectName("submitBtn")
        submit.setFixedHeight(32)
        submit.clicked.connect(self._on_submit)
        btn_row.addWidget(submit)
        root.addLayout(btn_row)

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("formLabel")
        return lbl

    @staticmethod
    def _input(placeholder: str, password: bool = False) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setObjectName("formInput")
        edit.setMinimumHeight(30)
        if password:
            edit.setEchoMode(QLineEdit.EchoMode.Password)
        return edit

    def _fill_data(self, data: Dict[str, Any]) -> None:
        self._model_input.setText(data.get("model", ""))
        self._key_input.setText(data.get("api_key", ""))
        self._url_input.setText(data.get("base_url", ""))

    def _on_submit(self) -> None:
        model = self._model_input.text().strip()
        api_key = self._key_input.text().strip()
        if not model or not api_key:
            QMessageBox.warning(self, "提示", "请填写模型名称和 API 密钥")
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
        return self._result

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        super().keyPressEvent(event)

    def _apply_theme(self) -> None:
        p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
        bg_card = p.get("bg_secondary", "#252526")
        bg_input = p.get("bg_tertiary", "#2d2d30")
        border = p.get("border", "#3e3e42")
        accent = p.get("accent", "#007acc")
        text = p.get("text_primary", "#cccccc")
        text_b = p.get("text_bright", "#ffffff")
        text_s = p.get("text_secondary", "#858585")
        bg_hover = p.get("bg_hover", "#3e3e42")
        font = p.get("font_family", "sans-serif")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLabel#dialogTitle {{
                color: {text_b}; font-size: 16px; font-weight: 600;
                font-family: {font}; background: transparent;
            }}
            QLabel#formLabel {{
                color: {text}; font-size: 13px;
                font-family: {font}; background: transparent;
            }}
            QLineEdit#formInput {{
                background-color: {bg_input}; color: {text_b};
                border: 1px solid {border}; border-radius: 4px;
                padding: 6px 10px; font-size: 13px; font-family: {font};
            }}
            QLineEdit#formInput:focus {{ border-color: {accent}; }}
            QPushButton#submitBtn {{
                background-color: {accent}; color: {text_b};
                border: none; border-radius: 4px;
                font-size: 13px; font-weight: 500; font-family: {font};
                padding: 0 16px;
            }}
            QPushButton#submitBtn:hover {{
                background-color: {p.get("accent_hover", "#1c97ea")};
            }}
            QPushButton#cancelBtn {{
                background-color: transparent; color: {text_s};
                border: 1px solid {border}; border-radius: 4px;
                font-size: 13px; font-family: {font}; padding: 0 16px;
            }}
            QPushButton#cancelBtn:hover {{
                background-color: {bg_hover}; color: {text_b};
            }}
        """)


class ModelListWidget(QWidget):
    """模型列表组件"""

    model_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._custom_models: List[Dict[str, Any]] = []
        self._load_custom_models()
        self._build_ui()
        self._apply_theme()

    # ============================================================ UI
    def _build_ui(self) -> None:
        """完整构建 UI（初始化和 refresh 都调用此方法）"""
        old_layout = self.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())
            QWidget().setLayout(old_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题 + 添加按钮 同一行
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 8)
        title = QLabel("模型管理")
        title.setObjectName("pageTitle")
        top.addWidget(title)
        top.addStretch(1)

        add_btn = QPushButton("+ 添加模型")
        add_btn.setObjectName("addModelBtn")
        add_btn.setFixedHeight(28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._on_add_model)
        top.addWidget(add_btn)
        layout.addLayout(top)

        # 列表
        list_frame = QFrame()
        list_frame.setObjectName("listFrame")
        self._list_layout = QVBoxLayout(list_frame)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)

        self._list_layout.addWidget(self._make_header())

        if self._custom_models:
            for m in self._custom_models:
                self._list_layout.addWidget(self._make_row(m))
        else:
            self._list_layout.addWidget(self._make_empty())

        layout.addWidget(list_frame)

    @staticmethod
    def _clear_layout(ly) -> None:
        while ly.count():
            item = ly.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
            elif item.layout():
                ModelListWidget._clear_layout(item.layout())

    def _make_header(self) -> QFrame:
        h = QFrame()
        h.setObjectName("listHeader")
        h.setFixedHeight(30)
        hl = QHBoxLayout(h)
        hl.setContentsMargins(12, 0, 12, 0)
        for text, stretch in [("模型", 5), ("服务商", 2), ("操作", 3)]:
            lbl = QLabel(text)
            lbl.setObjectName("headerLabel")
            if stretch != 5:
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hl.addWidget(lbl, stretch=stretch)
        return h

    @staticmethod
    def _make_empty() -> QLabel:
        lbl = QLabel("暂无自定义模型")
        lbl.setObjectName("emptyLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedHeight(48)
        return lbl

    def _make_row(self, data: Dict) -> QFrame:
        row = QFrame()
        row.setObjectName("modelRow")
        row.setFixedHeight(36)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 0, 12, 0)
        rl.setSpacing(0)

        name = QLabel(data.get("model", ""))
        name.setObjectName("modelName")
        rl.addWidget(name, stretch=5)

        prov = QLabel(data.get("provider", "自定义"))
        prov.setObjectName("modelProvider")
        prov.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(prov, stretch=2)

        al = QHBoxLayout()
        al.setSpacing(6)
        al.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignRight)
        mid = data.get("id", "")

        edit_btn = QPushButton("配置")
        edit_btn.setObjectName("rowActionBtn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda _, m=mid: self._on_edit(m))
        al.addWidget(edit_btn)

        del_btn = QPushButton("删除")
        del_btn.setObjectName("rowActionBtnDelete")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda _, m=mid: self._on_delete(m))
        al.addWidget(del_btn)

        rl.addLayout(al, stretch=3)
        return row

    # ============================================================ 操作
    def _on_add_model(self) -> None:
        dialog = AddModelDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if not result:
                return
            import uuid
            result["id"] = str(uuid.uuid4())[:8]
            result["provider"] = self._guess_provider(result["model"])
            self._custom_models.append(result)
            self._save()
            self._sync_to_config()
            self.refresh()
            self.model_changed.emit()

    def _on_edit(self, model_id: str) -> None:
        data = next((m for m in self._custom_models if m.get("id") == model_id), None)
        if not data:
            logger.warning(f"编辑失败: 找不到模型 {model_id}")
            return
        dialog = AddModelDialog(self, edit_data=data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if not result:
                return
            result["provider"] = self._guess_provider(result["model"])
            for i, m in enumerate(self._custom_models):
                if m.get("id") == model_id:
                    self._custom_models[i] = result
                    break
            self._save()
            self._sync_to_config()
            self.refresh()
            self.model_changed.emit()

    def _on_delete(self, model_id: str) -> None:
        reply = QMessageBox.question(
            self, "删除模型", "确定要删除这个模型配置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._custom_models = [
                m for m in self._custom_models if m.get("id") != model_id
            ]
            self._save()
            self._sync_to_config()
            self.refresh()
            self.model_changed.emit()

    # ============================================================ 刷新
    def refresh(self) -> None:
        self._build_ui()
        self._apply_theme()
        self.update()
        self.updateGeometry()

    # ============================================================ 持久化
    def _load_custom_models(self) -> None:
        if CUSTOM_MODELS_FILE.exists():
            try:
                self._custom_models = json.loads(
                    CUSTOM_MODELS_FILE.read_text(encoding="utf-8")
                )
            except Exception as e:
                logger.warning(f"加载自定义模型失败: {e}")
                self._custom_models = []

    def _save(self) -> None:
        CUSTOM_MODELS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            CUSTOM_MODELS_FILE.write_text(
                json.dumps(self._custom_models, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"保存自定义模型失败: {e}")

    def _sync_to_config(self) -> None:
        """同步到 config/config.json，格式: {"providers": {"deepseek": {...}}}"""
        try:
            config_file = Path("./config/config.json")

            config: Dict[str, Any] = {}
            if config_file.exists():
                try:
                    config = json.loads(config_file.read_text(encoding="utf-8"))
                except Exception:
                    config = {}

            if "providers" not in config:
                config["providers"] = {}

            for m in self._custom_models:
                if not m.get("enabled", True):
                    continue
                model_name = m.get("model", "")
                provider_key = self._provider_key(model_name)
                config["providers"][provider_key] = {
                    "api_key": m.get("api_key", ""),
                    "base_url": m.get("base_url", ""),
                    "model": model_name,
                }

            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(
                json.dumps(config, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"配置已同步到 {config_file}")
        except Exception as e:
            logger.error(f"同步配置失败: {e}")

    # ============================================================ 工具
    @staticmethod
    def _guess_provider(model_name: str) -> str:
        n = model_name.lower()
        if "deepseek" in n:   return "DeepSeek"
        if "gpt" in n or "openai" in n: return "OpenAI"
        if "claude" in n or "anthropic" in n: return "Anthropic"
        if "qwen" in n:       return "Qwen"
        if "glm" in n:        return "GLM"
        return "自定义"

    @staticmethod
    def _provider_key(model_name: str) -> str:
        n = model_name.lower()
        if "deepseek" in n:   return "deepseek"
        if "gpt" in n or "openai" in n: return "openai"
        if "claude" in n or "anthropic" in n: return "anthropic"
        if "qwen" in n:       return "qwen"
        if "glm" in n:        return "glm"
        return "custom"

    def get_enabled_custom_models(self) -> List[Dict[str, Any]]:
        return [m for m in self._custom_models if m.get("enabled", True)]

    # ============================================================ 主题
    def _apply_theme(self) -> None:
        p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
        bg = p.get("bg_primary", "#1e1e1e")
        bg_sec = p.get("bg_secondary", "#252526")
        bg_ter = p.get("bg_tertiary", "#2d2d30")
        bg_hover = p.get("bg_hover", "#3e3e42")
        border = p.get("border", "#3e3e42")
        accent = p.get("accent", "#007acc")
        text = p.get("text_primary", "#cccccc")
        text_b = p.get("text_bright", "#ffffff")
        text_s = p.get("text_secondary", "#858585")
        error = p.get("error", "#f44747")
        font = p.get("font_family", "sans-serif")

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg}; font-family: {font};
            }}
            QLabel#pageTitle {{
                color: {text_b}; font-size: 16px; font-weight: 600;
                background: transparent;
            }}
            QPushButton#addModelBtn {{
                color: {text_b}; background-color: {bg_ter};
                border: 1px solid {border}; border-radius: 4px;
                font-size: 12px; font-family: {font}; padding: 0 12px;
            }}
            QPushButton#addModelBtn:hover {{
                background-color: {bg_hover}; border-color: {accent};
            }}
            QFrame#listFrame {{
                background-color: {bg_sec};
                border: 1px solid {border}; border-radius: 4px;
            }}
            QFrame#listHeader {{
                background-color: {bg_ter};
                border-bottom: 1px solid {border};
                border-radius: 4px 4px 0 0;
            }}
            QLabel#headerLabel {{
                color: {text_s}; font-size: 11px; font-weight: 500;
                background: transparent;
            }}
            QFrame#modelRow {{
                border-bottom: 1px solid {border};
            }}
            QFrame#modelRow:hover {{
                background-color: {bg_hover};
            }}
            QLabel#modelName {{
                color: {text_b}; font-size: 13px; background: transparent;
            }}
            QLabel#modelProvider {{
                color: {text_s}; font-size: 12px; background: transparent;
            }}
            QLabel#emptyLabel {{
                color: {text_s}; font-size: 12px; background: transparent;
            }}
            QPushButton#rowActionBtn {{
                color: {text_s}; background-color: {bg_ter};
                border: 1px solid {border}; font-size: 11px;
                border-radius: 3px; padding: 2px 8px;
            }}
            QPushButton#rowActionBtn:hover {{
                color: {text_b}; background-color: {bg_hover};
                border-color: {accent};
            }}
            QPushButton#rowActionBtnDelete {{
                color: {error}; background-color: transparent;
                border: 1px solid {border}; font-size: 11px;
                border-radius: 3px; padding: 2px 8px;
            }}
            QPushButton#rowActionBtnDelete:hover {{
                color: {text_b}; background-color: {error};
                border-color: {error};
            }}
        """)


class SettingsDialog(QDialog):
    """设置对话框 — 模型管理"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(460, 340)
        self.resize(460, 340)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
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

## 验收标准

- [ ] 打开设置窗口，内容正常显示（不空白）
- [ ] 点击"+ 添加模型"弹出对话框，填写模型名和 API Key 后点"添加"
- [ ] 添加后模型立即出现在列表中
- [ ] 点击"配置"弹出编辑对话框，数据已正确填充
- [ ] 编辑保存后列表更新
- [ ] 点击"删除"有确认弹窗，确认后从列表移除
- [ ] `config/config.json` 格式为 `{"providers": {"deepseek": {...}}}`
- [ ] `data/custom_models.json` 保存了完整的自定义模型数据
