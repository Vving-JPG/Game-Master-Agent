"""设置对话框 — Trae 风格模型管理

主界面为模型列表，点击"+ 添加模型"弹出添加表单。
自定义模型支持编辑、删除、测试。

架构：
- ModelManager: 数据层，负责配置持久化
- ModelListWidget: 表现层，负责 UI 渲染
- ApiTester: 功能层，负责 API 测试
"""
from __future__ import annotations

from typing import Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel,
    QWidget, QFrame, QMessageBox, QLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal

from foundation.logger import get_logger
from presentation.theme.manager import theme_manager
from presentation.dialogs.model_manager import ModelManager, ModelConfig
from feature.services import ApiTester, TestResult

logger = get_logger(__name__)


class AddModelDialog(QDialog):
    """添加/编辑模型对话框"""

    def __init__(self, parent=None, edit_data: Dict[str, Any] | None = None):
        super().__init__(parent)
        self._edit_data = edit_data
        self._result: Dict[str, Any] | None = None

        self.setWindowTitle("编辑模型" if edit_data else "添加模型")
        self.setFixedSize(380, 300)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
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

        if len(api_key) > 200 or "\n" in api_key or "\t" in api_key:
            QMessageBox.warning(self, "提示", "API 密钥格式不正确")
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
    """模型列表组件 — 表现层
    
    依赖 ModelManager 进行数据操作，自身只负责 UI 渲染。
    """

    model_changed = pyqtSignal()

    def __init__(self, parent=None, model_manager: ModelManager | None = None):
        super().__init__(parent)
        # 如果没有传入 model_manager，创建一个并尝试加载项目路径
        if model_manager is None:
            model_manager = ModelManager()
            # 尝试从 project_manager 获取项目路径
            try:
                from presentation.project.manager import project_manager
                if project_manager.project_path:
                    model_manager.set_project_path(project_manager.project_path)
            except Exception:
                pass
        self._manager = model_manager
        self._manager.add_listener(self._on_data_changed)
        self._build_ui()
        self._apply_theme()

    def set_model_manager(self, manager: ModelManager) -> None:
        """设置模型管理器"""
        if self._manager:
            self._manager.remove_listener(self._on_data_changed)
        self._manager = manager
        self._manager.add_listener(self._on_data_changed)
        self.refresh()

    def _on_data_changed(self) -> None:
        """数据变更回调"""
        self.refresh()
        self.model_changed.emit()

    # ============================================================ UI 构建
    def _build_ui(self) -> None:
        """构建 UI"""
        old_layout = self.layout()
        if old_layout:
            self._clear_layout(old_layout)
            old_layout.deleteLater()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题 + 添加按钮
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

        models = self._manager.get_models()
        if models:
            for m in models:
                self._list_layout.addWidget(self._make_row(m))
        else:
            self._list_layout.addWidget(self._make_empty())

        layout.addWidget(list_frame)

    @staticmethod
    def _clear_layout(ly: QLayout) -> None:
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

    def _make_row(self, data: ModelConfig) -> QFrame:
        row = QFrame()
        row.setObjectName("modelRow")
        row.setFixedHeight(36)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 0, 12, 0)
        rl.setSpacing(0)

        name = QLabel(data.model)
        name.setObjectName("modelName")
        rl.addWidget(name, stretch=5)

        prov = QLabel(data.provider)
        prov.setObjectName("modelProvider")
        prov.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(prov, stretch=2)

        al = QHBoxLayout()
        al.setSpacing(6)
        al.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignRight)

        test_btn = QPushButton("测试")
        test_btn.setObjectName("rowActionBtnTest")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.clicked.connect(lambda _, m=data.id: self._on_test(m))
        al.addWidget(test_btn)

        edit_btn = QPushButton("配置")
        edit_btn.setObjectName("rowActionBtn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda _, m=data.id: self._on_edit(m))
        al.addWidget(edit_btn)

        del_btn = QPushButton("删除")
        del_btn.setObjectName("rowActionBtnDelete")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda _, m=data.id: self._on_delete(m))
        al.addWidget(del_btn)

        rl.addLayout(al, stretch=3)
        return row

    # ============================================================ 操作
    def _on_add_model(self) -> None:
        dialog = AddModelDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                self._manager.add_model(
                    model=result["model"],
                    api_key=result["api_key"],
                    base_url=result.get("base_url", ""),
                )
                logger.info(f"添加模型成功: {result['model']}")

    def _on_edit(self, model_id: str) -> None:
        data = self._manager.get_model_by_id(model_id)
        if not data:
            logger.warning(f"编辑失败: 找不到模型 {model_id}")
            return
        
        dialog = AddModelDialog(self, edit_data=data.to_dict())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                self._manager.update_model(
                    model_id=model_id,
                    model=result["model"],
                    api_key=result["api_key"],
                    base_url=result.get("base_url", ""),
                )
                logger.info(f"编辑模型成功: {result['model']}")

    def _on_delete(self, model_id: str) -> None:
        reply = QMessageBox.question(
            self, "删除模型", "确定要删除这个模型配置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            data = self._manager.get_model_by_id(model_id)
            if self._manager.delete_model(model_id):
                logger.info(f"删除模型成功: {data.model if data else 'unknown'}")

    def _on_test(self, model_id: str) -> None:
        """测试 API 连接"""
        # 使用 ApiTester 服务（功能层）
        if not hasattr(self, '_api_tester'):
            self._api_tester = ApiTester()

        # 取消之前的测试
        if self._api_tester.is_testing():
            self._api_tester.cancel_current_test()

        data = self._manager.get_model_by_id(model_id)
        if not data:
            QMessageBox.warning(self, "测试失败", "找不到模型配置")
            return

        if not data.api_key:
            QMessageBox.warning(self, "测试失败", "API 密钥为空")
            return

        self._test_dialog = QMessageBox(self)
        self._test_dialog.setWindowTitle("测试中")
        self._test_dialog.setText("正在测试 API 连接，请稍候...\n(点击取消中止测试)")
        self._test_dialog.setStandardButtons(QMessageBox.StandardButton.Cancel)
        self._test_dialog.setEscapeButton(QMessageBox.StandardButton.Cancel)
        self._test_dialog.rejected.connect(self._on_test_cancelled)

        # 使用 ApiTester 启动异步测试
        self._api_tester.test_async(
            model=data.model,
            api_key=data.api_key,
            base_url=data.base_url,
            callback=self._on_test_result,
        )

        self._test_dialog.open()

    def _on_test_cancelled(self) -> None:
        """用户取消测试"""
        if hasattr(self, '_api_tester') and self._api_tester:
            self._api_tester.cancel_current_test()
        self._test_dialog = None

    def _on_test_result(self, result: TestResult) -> None:
        """测试完成的回调"""
        if not hasattr(self, '_test_dialog') or self._test_dialog is None:
            logger.debug("测试对话框已关闭，忽略结果")
            return

        try:
            self._test_dialog.rejected.disconnect(self._on_test_cancelled)
        except TypeError:
            pass

        self._test_dialog.close()
        self._test_dialog = None

        if result.success:
            QMessageBox.information(
                self, "测试成功",
                f"模型: {result.model_name}\n{result.message}\n\nAPI 连接正常！"
            )
            logger.info(f"API 测试成功: {result.model_name}")
        else:
            QMessageBox.critical(
                self, "测试失败",
                f"模型: {result.model_name}\n错误: {result.message}\n\n请检查密钥和地址"
            )
            logger.error(f"API 测试失败: {result.model_name}, 错误: {result.message}")

    # ============================================================ 刷新
    def refresh(self) -> None:
        self._build_ui()
        self._apply_theme()
        self.update()
        self.updateGeometry()

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
        success = p.get("success", "#4ec9b0")
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
            QPushButton#rowActionBtnTest {{
                color: {success}; background-color: transparent;
                border: 1px solid {border}; font-size: 11px;
                border-radius: 3px; padding: 2px 8px;
            }}
            QPushButton#rowActionBtnTest:hover {{
                color: {text_b}; background-color: {success};
                border-color: {success};
            }}
        """)


class SettingsDialog(QDialog):
    """设置对话框 — 模型管理"""

    def __init__(self, parent=None, model_manager: ModelManager | None = None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(460, 340)
        self.resize(460, 340)
        self._setup_ui(model_manager)
        self._apply_theme()

    def _setup_ui(self, model_manager: ModelManager | None) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(0)
        self._model_list = ModelListWidget(self, model_manager)
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
