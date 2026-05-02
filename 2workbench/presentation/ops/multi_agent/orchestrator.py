# 2workbench/presentation/ops/multi_agent/orchestrator.py
"""多 Agent 编排器 — Agent 链配置和消息路由

功能:
1. Agent 实例管理（创建/配置/删除）
2. 链式编排（串行/并行/条件分支）
3. 消息路由规则
4. 可视化拓扑
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QListWidget, QListWidgetItem, QTabWidget,
    QFormLayout, QLineEdit, QComboBox, QTextEdit,
    QGroupBox,
)
from PyQt6.QtCore import Qt

from foundation.logger import get_logger
from presentation.widgets.base import BaseWidget
from presentation.widgets.styled_button import StyledButton

logger = get_logger(__name__)


@dataclass
class AgentInstance:
    """Agent 实例定义"""
    id: str = ""
    name: str = ""
    role: str = "general"  # gm / narrator / combat / dialogue / custom
    model: str = "deepseek-chat"
    system_prompt: str = ""
    enabled: bool = True


@dataclass
class ChainStep:
    """链式步骤"""
    agent_id: str = ""
    step_type: str = "sequential"  # sequential / parallel / conditional
    condition: str = ""  # 条件表达式（conditional 时使用）
    next_agent_id: str = ""


class MultiAgentOrchestrator(BaseWidget):
    """多 Agent 编排器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._agents: list[AgentInstance] = []
        self._chain: list[ChainStep] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        self._btn_add_agent = StyledButton("+ 添加 Agent", style_type="primary")
        self._btn_add_agent.clicked.connect(self._add_agent)
        toolbar.addWidget(self._btn_add_agent)

        self._btn_add_link = StyledButton("🔗 添加连接", style_type="secondary")
        self._btn_add_link.clicked.connect(self._add_link)
        toolbar.addWidget(self._btn_add_link)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 主内容
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: Agent 列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        agent_label = QLabel("🤖 Agent 实例")
        agent_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(agent_label)

        self._agent_list = QListWidget()
        self._agent_list.currentRowChanged.connect(self._on_agent_selected)
        left_layout.addWidget(self._agent_list)

        splitter.addWidget(left)

        # 中央: Agent 配置
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(8, 8, 8, 8)

        config_group = QGroupBox("Agent 配置")
        config_layout = QFormLayout(config_group)

        self._name_edit = QLineEdit()
        config_layout.addRow("名称:", self._name_edit)

        self._role_combo = QComboBox()
        self._role_combo.addItems(["gm", "narrator", "combat", "dialogue", "custom"])
        config_layout.addRow("角色:", self._role_combo)

        self._model_combo = QComboBox()
        self._model_combo.addItems(["deepseek-chat", "deepseek-reasoner", "gpt-4o", "claude-sonnet"])
        config_layout.addRow("模型:", self._model_combo)

        self._prompt_edit = QTextEdit()
        self._prompt_edit.setMaximumHeight(120)
        self._prompt_edit.setPlaceholderText("System Prompt...")
        config_layout.addRow("System Prompt:", self._prompt_edit)

        self._btn_save_agent = StyledButton("💾 保存", style_type="primary")
        self._btn_save_agent.clicked.connect(self._save_agent)
        config_layout.addRow(self._btn_save_agent)

        center_layout.addWidget(config_group)
        splitter.addWidget(center)

        # 右侧: 链式拓扑
        right = QWidget()
        right.setMaximumWidth(250)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        chain_label = QLabel("🔗 编排链")
        chain_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(chain_label)

        self._chain_list = QListWidget()
        right_layout.addWidget(self._chain_list)

        splitter.addWidget(right)
        splitter.setSizes([200, 400, 200])
        layout.addWidget(splitter)

    def _add_agent(self) -> None:
        agent = AgentInstance(
            id=f"agent_{len(self._agents)+1}",
            name=f"Agent_{len(self._agents)+1}",
        )
        self._agents.append(agent)
        self._refresh_agent_list()
        self._agent_list.setCurrentRow(len(self._agents) - 1)

    def _on_agent_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._agents):
            return
        agent = self._agents[row]
        self._name_edit.setText(agent.name)
        idx = self._role_combo.findText(agent.role)
        if idx >= 0:
            self._role_combo.setCurrentIndex(idx)
        idx = self._model_combo.findText(agent.model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        self._prompt_edit.setPlainText(agent.system_prompt)

    def _save_agent(self) -> None:
        row = self._agent_list.currentRow()
        if row < 0:
            return
        agent = self._agents[row]
        agent.name = self._name_edit.text()
        agent.role = self._role_combo.currentText()
        agent.model = self._model_combo.currentText()
        agent.system_prompt = self._prompt_edit.toPlainText()
        self._refresh_agent_list()
        self._agent_list.setCurrentRow(row)

    def _add_link(self) -> None:
        if len(self._agents) < 2:
            logger.warning("至少需要 2 个 Agent 才能创建连接")
            return
        step = ChainStep(
            agent_id=self._agents[-2].id,
            next_agent_id=self._agents[-1].id,
        )
        self._chain.append(step)
        self._refresh_chain_list()

    def _refresh_agent_list(self) -> None:
        self._agent_list.clear()
        for agent in self._agents:
            status = "✅" if agent.enabled else "❌"
            self._agent_list.addItem(f"{status} {agent.name} ({agent.role})")

    def _refresh_chain_list(self) -> None:
        self._chain_list.clear()
        for step in self._chain:
            self._chain_list.addItem(f"{step.agent_id} → {step.next_agent_id} [{step.step_type}]")

    def get_config(self) -> dict:
        """导出编排配置"""
        return {
            "agents": [
                {"id": a.id, "name": a.name, "role": a.role, "model": a.model, "system_prompt": a.system_prompt}
                for a in self._agents
            ],
            "chain": [
                {"agent_id": s.agent_id, "next_agent_id": s.next_agent_id, "type": s.step_type}
                for s in self._chain
            ],
        }
