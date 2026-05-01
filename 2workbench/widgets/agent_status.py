# workbench/widgets/agent_status.py
"""Agent 状态面板"""
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel


class AgentStatusPanel(QGroupBox):
    """Agent 状态面板"""

    def __init__(self):
        super().__init__("🤖 Agent 状态")
        layout = QVBoxLayout(self)
        self.status_label = QLabel("状态: IDLE")
        self.model_label = QLabel("模型: deepseek-chat")
        self.token_label = QLabel("Token: 0")
        self.skill_label = QLabel("Skill: 无")
        self.turn_label = QLabel("回合: 0")
        for w in [self.status_label, self.model_label, self.token_label, self.skill_label, self.turn_label]:
            layout.addWidget(w)
