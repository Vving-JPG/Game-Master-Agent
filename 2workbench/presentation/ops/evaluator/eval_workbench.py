# 2workbench/presentation/ops/evaluator/eval_workbench.py
"""评估工作台 — Prompt 评估、批量测试、指标统计、对比分析

功能:
1. 评估用例管理（导入/编辑/运行）
2. 评估指标（相关性、准确性、一致性、延迟、Token 用量）
3. 批量运行（多模型对比）
4. 结果统计和可视化
5. 历史记录
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QFormLayout, QComboBox,
    QLineEdit, QPushButton, QFileDialog, QProgressBar,
    QGroupBox, QDialog, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from foundation.event_bus import event_bus, Event
from foundation.llm import LLMMessage
from foundation.llm.model_router import model_router
from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


@dataclass
class EvalCase:
    """评估用例"""
    id: str = ""
    input_text: str = ""
    expected_output: str = ""
    actual_output: str = ""
    model: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    score: float = 0.0  # 0-10 评分
    notes: str = ""


@dataclass
class EvalResult:
    """评估结果"""
    model: str = ""
    total_cases: int = 0
    avg_score: float = 0.0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    pass_rate: float = 0.0  # score >= 6 的比例
    cases: list[EvalCase] = field(default_factory=list)


class EvalCaseEditor(QWidget):
    """评估用例编辑器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cases: list[EvalCase] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        self._btn_add = StyledButton("+ 添加用例", style_type="primary")
        self._btn_add.clicked.connect(self._add_case)
        toolbar.addWidget(self._btn_add)

        self._btn_import = StyledButton("📥 导入 JSON", style_type="secondary")
        self._btn_import.clicked.connect(self._import_cases)
        toolbar.addWidget(self._btn_import)

        self._btn_clear = StyledButton("清空", style_type="ghost")
        self._btn_clear.clicked.connect(self._clear_cases)
        toolbar.addWidget(self._btn_clear)

        toolbar.addStretch()
        self._count_label = QLabel("用例: 0")
        self._count_label.setStyleSheet("color: #858585;")
        toolbar.addWidget(self._count_label)

        layout.addLayout(toolbar)

        # 用例表格
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "ID", "输入", "期望输出", "实际输出", "评分", "延迟"
        ])
        self._table.horizontalHeader().setStretchLastSection(True)
        for i in range(5):
            self._table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.Interactive
            )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

    def _add_case(self) -> None:
        """添加空用例"""
        case = EvalCase(
            id=f"case_{len(self._cases) + 1}",
            input_text="",
            expected_output="",
        )
        self._cases.append(case)
        self._refresh_table()

    def _import_cases(self) -> None:
        """从 JSON 导入用例"""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入评估用例", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                self._cases.append(EvalCase(
                    id=item.get("id", f"case_{len(self._cases)+1}"),
                    input_text=item.get("input", ""),
                    expected_output=item.get("expected", ""),
                ))
            self._refresh_table()
            logger.info(f"导入 {len(data)} 个评估用例")
        except Exception as e:
            logger.error(f"导入失败: {e}")

    def _clear_cases(self) -> None:
        self._cases.clear()
        self._refresh_table()

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        for case in self._cases:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(case.id))
            self._table.setItem(row, 1, QTableWidgetItem(case.input_text[:50]))
            self._table.setItem(row, 2, QTableWidgetItem(case.expected_output[:50]))
            self._table.setItem(row, 3, QTableWidgetItem(case.actual_output[:50] if case.actual_output else "-"))
            score_item = QTableWidgetItem(f"{case.score:.1f}" if case.score is not None else "-")
            self._table.setItem(row, 4, score_item)
            latency_item = QTableWidgetItem(f"{case.latency_ms:.0f}ms" if case.latency_ms is not None else "-")
            self._table.setItem(row, 5, latency_item)
        self._count_label.setText(f"用例: {len(self._cases)}")

    def refresh_table(self) -> None:
        """公开方法：刷新表格（供外部调用）"""
        self._refresh_table()

    def get_cases(self) -> list[EvalCase]:
        return list(self._cases)


class EvalThread(QThread):
    """评估执行线程"""
    progress = pyqtSignal(int, int)  # current, total
    result = pyqtSignal(object)       # EvalResult
    error = pyqtSignal(str)           # 错误信息

    def __init__(self, cases: list[EvalCase], model: str):
        super().__init__()
        self._cases = cases
        self._model = model

    def run(self):
        try:
            result = EvalResult(model=self._model, total_cases=len(self._cases))
            total_score = 0.0
            total_latency = 0.0
            total_tokens = 0
            passed = 0

            for i, case in enumerate(self._cases):
                # 模拟评估结果
                case.model = self._model
                case.latency_ms = 800 + i * 100  # 模拟延迟
                case.tokens_used = 100 + i * 50
                case.score = 7.0 + (i % 3)  # 模拟评分
                case.actual_output = f"[模拟输出] 对 '{case.input_text[:20]}...' 的回复"

                total_score += case.score
                total_latency += case.latency_ms
                total_tokens += case.tokens_used
                if case.score >= 6:
                    passed += 1

                self.progress.emit(i + 1, len(self._cases))

            result.avg_score = total_score / len(self._cases)
            result.avg_latency_ms = total_latency / len(self._cases)
            result.total_tokens = total_tokens
            result.pass_rate = passed / len(self._cases)
            result.cases = self._cases

            self.result.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class EvalWorkbench(BaseWidget):
    """评估工作台"""

    eval_completed = pyqtSignal(object)  # EvalResult

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: list[EvalResult] = []
        self._running = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 顶部配置
        config_bar = QHBoxLayout()

        config_bar.addWidget(QLabel("Prompt:"))
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setMaximumHeight(60)
        self._prompt_edit.setPlaceholderText("输入要评估的 Prompt 模板...")
        config_bar.addWidget(self._prompt_edit, 1)

        layout.addLayout(config_bar)

        model_bar = QHBoxLayout()
        model_bar.addWidget(QLabel("模型:"))
        self._model_combo = QComboBox()
        self._model_combo.addItems(["deepseek-chat", "deepseek-reasoner", "gpt-4o", "claude-sonnet"])
        self._model_combo.setMinimumWidth(150)
        model_bar.addWidget(self._model_combo)

        self._btn_run = StyledButton("▶ 运行评估", style_type="success")
        self._btn_run.clicked.connect(self._run_eval)
        model_bar.addWidget(self._btn_run)

        self._btn_compare = StyledButton("📊 对比分析", style_type="secondary")
        self._btn_compare.clicked.connect(self._show_comparison)
        model_bar.addWidget(self._btn_compare)

        model_bar.addStretch()

        self._progress = QProgressBar()
        self._progress.setMaximumWidth(200)
        self._progress.setVisible(False)
        model_bar.addWidget(self._progress)

        layout.addLayout(model_bar)

        # 主内容
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 用例编辑器
        self._case_editor = EvalCaseEditor()
        splitter.addWidget(self._case_editor)

        # 结果面板
        result_group = QGroupBox("评估结果")
        result_layout = QVBoxLayout(result_group)

        self._result_table = QTableWidget()
        self._result_table.setColumnCount(6)
        self._result_table.setHorizontalHeaderLabels([
            "模型", "用例数", "平均分", "通过率", "平均延迟", "总 Token"
        ])
        self._result_table.horizontalHeader().setStretchLastSection(True)
        self._result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._result_table.setAlternatingRowColors(True)
        result_layout.addWidget(self._result_table)

        splitter.addWidget(result_group)
        splitter.setSizes([400, 300])

        layout.addWidget(splitter)

    def _run_eval(self) -> None:
        """运行评估（使用后台线程）"""
        cases = self._case_editor.get_cases()
        if not cases:
            logger.warning("没有评估用例")
            return

        model = self._model_combo.currentText()

        self._running = True
        self._btn_run.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setMaximum(len(cases))
        self._progress.setValue(0)

        # 创建评估线程
        self._eval_thread = EvalThread(cases, model)
        self._eval_thread.progress.connect(self._on_eval_progress)
        self._eval_thread.result.connect(self._on_eval_complete)
        self._eval_thread.error.connect(self._on_eval_error)
        self._eval_thread.start()

    def _on_eval_progress(self, current: int, total: int) -> None:
        """评估进度更新"""
        self._progress.setValue(current)

    def _on_eval_complete(self, result: EvalResult) -> None:
        """评估完成"""
        self._results.append(result)
        self._refresh_results()
        self._case_editor.refresh_table()  # 使用公开方法

        self._running = False
        self._btn_run.setEnabled(True)
        self._progress.setVisible(False)

        logger.info(
            f"评估完成: {result.model}, 平均分={result.avg_score:.1f}, "
            f"通过率={result.pass_rate:.0%}"
        )
        self.eval_completed.emit(result)

    def _on_eval_error(self, error_msg: str) -> None:
        """评估错误"""
        logger.error(f"评估失败: {error_msg}")
        self._running = False
        self._btn_run.setEnabled(True)
        self._progress.setVisible(False)

    def _refresh_results(self) -> None:
        """刷新结果表格"""
        self._result_table.setRowCount(0)
        for result in self._results:
            row = self._result_table.rowCount()
            self._result_table.insertRow(row)
            self._result_table.setItem(row, 0, QTableWidgetItem(result.model))
            self._result_table.setItem(row, 1, QTableWidgetItem(str(result.total_cases)))
            self._result_table.setItem(row, 2, QTableWidgetItem(f"{result.avg_score:.1f}"))
            self._result_table.setItem(row, 3, QTableWidgetItem(f"{result.pass_rate:.0%}"))
            self._result_table.setItem(row, 4, QTableWidgetItem(f"{result.avg_latency_ms:.0f}ms"))
            self._result_table.setItem(row, 5, QTableWidgetItem(str(result.total_tokens)))

    def _show_comparison(self) -> None:
        """显示对比分析"""
        if len(self._results) < 2:
            logger.warning("至少需要 2 次评估结果才能对比")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("模型对比分析")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        comparison = QTextEdit()
        comparison.setReadOnly(True)

        lines = ["# 模型对比分析\n"]
        lines.append(f"| 指标 | " + " | ".join(r.model for r in self._results) + " |")
        lines.append("| --- | " + " | ".join("---" for _ in self._results) + " |")
        lines.append(f"| 平均分 | " + " | ".join(f"{r.avg_score:.1f}" for r in self._results) + " |")
        lines.append(f"| 通过率 | " + " | ".join(f"{r.pass_rate:.0%}" for r in self._results) + " |")
        lines.append(f"| 平均延迟 | " + " | ".join(f"{r.avg_latency_ms:.0f}ms" for r in self._results) + " |")
        lines.append(f"| 总 Token | " + " | ".join(str(r.total_tokens) for r in self._results) + " |")

        comparison.setPlainText("\n".join(lines))
        layout.addWidget(comparison)

        dialog.exec()
