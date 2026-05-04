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


class AddModelDialog(QDialog):
    """添加/编辑模型对话框 — 极简表单"""

    def __init__(self, parent=None, edit_data: Dict[str, Any] | None = None):
        super().__init__(parent)
        self._edit_data = edit_data
        self.setWindowTitle("编辑模型" if edit_data else "添加模型")
        self.setFixedSize(400, 340)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        # 允许点击外部关闭
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._setup_ui()
        self._apply_theme()
        if edit_data:
            self._fill_data(edit_data)

    def keyPressEvent(self, event) -> None:
        """按 ESC 键关闭对话框"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        """点击对话框外部区域关闭"""
        # 将全局坐标转换为对话框局部坐标
        local_pos = self.mapFromGlobal(event.globalPosition().toPoint())
        if not self.rect().contains(local_pos):
            self.reject()
        else:
            super().mousePressEvent(event)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # 标题栏
        title_bar = QHBoxLayout()
        title_label = QLabel("编辑模型" if self._edit_data else "添加模型")
        title_label.setObjectName("dialogTitle")
        title_bar.addWidget(title_label)
        title_bar.addStretch(1)
        layout.addLayout(title_bar)

        # 模型名称
        model_label = QLabel("* 模型")
        model_label.setObjectName("formLabel")
        layout.addWidget(model_label)

        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText("选择模型")
        self._model_input.setObjectName("formInput")
        self._model_input.setMinimumHeight(32)
        layout.addWidget(self._model_input)

        # API 密钥
        key_label = QLabel("* API 密钥")
        key_label.setObjectName("formLabel")
        layout.addWidget(key_label)

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("输入 API 密钥")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setObjectName("formInput")
        self._key_input.setMinimumHeight(32)
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
        self._url_input.setMinimumHeight(32)
        layout.addWidget(self._url_input)

        layout.addStretch(1)

        # 按钮行
        btn_row = QHBoxLayout()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        
        btn_row.addStretch(1)
        
        # 添加/保存按钮
        self._submit_btn = QPushButton("添加模型" if not self._edit_data else "保存")
        self._submit_btn.setObjectName("submitBtn")
        self._submit_btn.setFixedHeight(36)
        self._submit_btn.clicked.connect(self._on_submit)
        btn_row.addWidget(self._submit_btn)
        
        layout.addLayout(btn_row)

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

        self.setStyleSheet("""
            QDialog {
                background-color: """ + bg_card + """;
                border: 1px solid """ + border + """;
                border-radius: 8px;
            }
            QLabel#dialogTitle {
                color: """ + text_bright + """;
                font-size: 16px;
                font-weight: 600;
                font-family: """ + font + """;
                background: transparent;
            }
            QPushButton#dialogCloseBtn {
                color: """ + text_sec + """;
                border: none;
                background: transparent;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton#dialogCloseBtn:hover {
                color: """ + text_bright + """;
                background-color: """ + p.get("bg_hover", "#3e3e42") + """;
            }
            QLabel#formLabel {
                color: """ + text + """;
                font-size: 13px;
                font-family: """ + font + """;
                background: transparent;
            }
            QLineEdit#formInput {
                background-color: """ + bg_input + """;
                color: """ + text_bright + """;
                border: 1px solid """ + border + """;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: """ + font + """;
            }
            QLineEdit#formInput:focus {
                border-color: """ + accent + """;
            }
            QPushButton#infoBtn {
                color: """ + text_sec + """;
                border: none;
                background: transparent;
                font-size: 12px;
            }
            QPushButton#submitBtn {
                background-color: """ + p.get("bg_hover", "#3e3e42") + """;
                color: """ + text_bright + """;
                border: 1px solid """ + border + """;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                font-family: """ + font + """;
            }
            QPushButton#submitBtn:hover {
                background-color: """ + accent + """;
                border-color: """ + accent + """;
            }
            QPushButton#cancelBtn {
                background-color: transparent;
                color: """ + text_sec + """;
                border: 1px solid """ + border + """;
                border-radius: 6px;
                font-size: 14px;
                font-family: """ + font + """;
            }
            QPushButton#cancelBtn:hover {
                background-color: """ + p.get("bg_hover", "#3e3e42") + """;
                color: """ + text_bright + """;
            }
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
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 页面标题
        title = QLabel("模型")
        title.setObjectName("pageTitle")
        title.setFixedHeight(28)
        layout.addWidget(title)

        # 添加模型按钮
        self._add_btn = QPushButton("+ 添加模型")
        self._add_btn.setObjectName("addModelBtn")
        self._add_btn.setFixedHeight(26)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add_model)
        layout.addWidget(self._add_btn)

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

        # 直接显示模型行，不使用分组标题
        if self._custom_models:
            for m in self._custom_models:
                row = self._create_model_row(m, editable=True)
                list_layout.addWidget(row)
        else:
            # 没有模型时显示提示
            empty_label = QLabel("暂无自定义模型，点击上方按钮添加")
            empty_label.setObjectName("emptyLabel")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setFixedHeight(60)
            list_layout.addWidget(empty_label)

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
        action_layout.setSpacing(6)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if editable:
            model_id = model_data.get("id", "")
            model_name = model_data.get("model", "")

            # 配置按钮
            config_btn = QPushButton("配置")
            config_btn.setObjectName("rowActionBtn")
            config_btn.setToolTip("配置模型")
            config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            config_btn.clicked.connect(lambda checked, mid=model_id, mn=model_name: self._on_edit(mid, mn))
            action_layout.addWidget(config_btn)

            # 测试按钮
            test_btn = QPushButton("测试")
            test_btn.setObjectName("rowActionBtn")
            test_btn.setToolTip("测试连接")
            test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            test_btn.clicked.connect(lambda checked, mid=model_id: self._on_test(mid))
            action_layout.addWidget(test_btn)

            # 删除按钮
            del_btn = QPushButton("删除")
            del_btn.setObjectName("rowActionBtnDelete")
            del_btn.setToolTip("删除模型")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, mid=model_id: self._on_delete(mid))
            action_layout.addWidget(del_btn)
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
                self._sync_to_config()
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
                self._sync_to_config()
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
            self._sync_to_config()
            self.refresh()
            self.model_changed.emit()

    def _on_test(self, model_id: str) -> None:
        """测试模型连接"""
        from PyQt6.QtWidgets import QMessageBox
        
        data = next((m for m in self._custom_models if m.get("id") == model_id), None)
        if not data:
            return
        
        model_name = data.get("model", "")
        QMessageBox.information(
            self, "测试连接", 
            f"正在测试模型: {model_name}\n\n(测试功能待实现)"
        )

    def _on_toggle(self, model_id: str) -> None:
        """启用/禁用模型"""
        for m in self._custom_models:
            if m.get("id") == model_id:
                m["enabled"] = not m.get("enabled", True)
                break
        self._save_custom_models()
        self._sync_to_config()
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
        # 找到 list_frame 并清除其中的内容
        layout = self.layout()
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QFrame) and widget.objectName() == "listFrame":
                    # 清除 list_frame 中的所有内容
                    list_layout = widget.layout()
                    if list_layout:
                        while list_layout.count():
                            child = list_layout.takeAt(0)
                            if child.widget():
                                child.widget().deleteLater()
                        
                        # 重新添加表头
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
                        
                        # 重新添加模型行
                        if self._custom_models:
                            for m in self._custom_models:
                                row = self._create_model_row(m, editable=True)
                                list_layout.addWidget(row)
                        else:
                            empty_label = QLabel("暂无自定义模型，点击上方按钮添加")
                            empty_label.setObjectName("emptyLabel")
                            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            empty_label.setFixedHeight(60)
                            list_layout.addWidget(empty_label)
                    return

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

    def _sync_to_config(self) -> None:
        """同步模型配置到 config.json"""
        try:
            from presentation.project.manager import project_manager
            
            # 获取当前项目路径
            project_path = project_manager.project_path
            if not project_path:
                # 如果没有项目，保存到默认位置
                config_file = Path("./config/config.json")
            else:
                # 保存到项目目录下的 config/config.json
                config_file = Path(project_path) / "config" / "config.json"
            
            # 读取现有配置
            config = {}
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except Exception:
                    config = {}
            
            # 将自定义模型转换为原有格式（deepseek/openai/anthropic）
            for m in self._custom_models:
                if m.get("enabled", True):
                    provider_name = self._guess_provider(m.get("model", "")).lower()
                    # 更新对应 provider 的配置
                    if provider_name not in config:
                        config[provider_name] = {}
                    config[provider_name]["api_key"] = m.get("api_key", "")
                    config[provider_name]["base_url"] = m.get("base_url", "")
                    config[provider_name]["model"] = m.get("model", "")
                    # 设置默认 provider 为第一个启用的模型
                    if "default_provider" not in config or not config["default_provider"]:
                        config["default_provider"] = provider_name
            
            # 保存到 config.json
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"模型配置已同步到 {config_file}")
        except Exception as e:
            logger.error(f"同步配置失败: {e}")

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

        self.setStyleSheet("""
            QWidget {
                background-color: """ + bg + """;
                font-family: """ + font + """;
            }
            QLabel#pageTitle {
                color: """ + text_bright + """;
                font-size: 20px;
                font-weight: 600;
                background: transparent;
            }
            QLabel#sectionTitle {
                color: """ + text_bright + """;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
            }
            QLabel#sectionDesc {
                color: """ + text_sec + """;
                font-size: 12px;
                background: transparent;
            }
            QPushButton#addModelBtn {
                color: """ + text_bright + """;
                background-color: """ + bg_ter + """;
                border: 1px solid """ + border + """;
                border-radius: 6px;
                font-size: 13px;
                font-family: """ + font + """;
            }
            QPushButton#addModelBtn:hover {
                background-color: """ + bg_hover + """;
                border-color: """ + accent + """;
            }

            /* 列表框架 */
            QFrame#listFrame {
                background-color: """ + bg_sec + """;
                border: 1px solid """ + border + """;
                border-radius: 6px;
            }
            QFrame#listHeader {
                background-color: """ + bg_ter + """;
                border-bottom: 1px solid """ + border + """;
                border-radius: 6px 6px 0 0;
            }
            QLabel#headerLabel {
                color: """ + text_sec + """;
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }

            /* 分组 */
            QFrame#modelSection {
                background-color: """ + bg_sec + """;
                border: none;
            }
            QFrame#sectionRow {
                background-color: """ + bg_ter + """;
                border-bottom: 1px solid """ + border + """;
            }
            QLabel#chevron {
                color: """ + text_sec + """;
                font-size: 10px;
                background: transparent;
                padding-right: 6px;
            }
            QLabel#sectionLabel {
                color: """ + text + """;
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }

            /* 模型行 */
            QFrame#modelRow {
                border-bottom: 1px solid """ + border + """;
            }
            QFrame#modelRow:hover {
                background-color: """ + bg_hover + """;
            }
            QLabel#modelName {
                color: """ + text_bright + """;
                font-size: 13px;
                background: transparent;
            }
            QLabel#modelProvider {
                color: """ + text_sec + """;
                font-size: 12px;
                background: transparent;
            }
            QLabel#dashLabel {
                color: """ + text_sec + """;
                font-size: 12px;
                background: transparent;
            }
            QLabel#emptyLabel {
                color: """ + text_sec + """;
                font-size: 13px;
                background: transparent;
                padding: 20px;
            }

            /* 行操作按钮 */
            QPushButton#rowActionBtn {
                color: """ + text_sec + """;
                background-color: """ + bg_ter + """;
                border: 1px solid """ + border + """;
                font-size: 11px;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 40px;
            }
            QPushButton#rowActionBtn:hover {
                color: """ + text_bright + """;
                background-color: """ + bg_hover + """;
                border-color: """ + accent + """;
            }
            QPushButton#rowActionBtnDelete {
                color: """ + error + """;
                background-color: """ + bg_ter + """;
                border: 1px solid """ + border + """;
                font-size: 11px;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 40px;
            }
            QPushButton#rowActionBtnDelete:hover {
                color: """ + text_bright + """;
                background-color: """ + error + """;
                border-color: """ + error + """;
            }
        """)


class SettingsDialog(QDialog):
    """设置对话框 — 模型管理（Trae 风格）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(400, 300)
        self.resize(480, 360)
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
        self.setStyleSheet("""
            QDialog {
                background-color: """ + bg + """;
                border: 1px solid """ + border + """;
                border-radius: 8px;
            }
        """)
