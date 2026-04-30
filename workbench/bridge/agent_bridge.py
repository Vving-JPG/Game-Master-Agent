# workbench/bridge/agent_bridge.py
"""WorkBench ↔ 后端桥接层"""
import asyncio
import sys
import os
from pathlib import Path
from typing import Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import qasync


class AgentBridge(QObject):
    """后端桥接层 — 直接 import 后端模块"""

    # 信号
    log_signal = pyqtSignal(str, str)       # (event_type, message)
    status_changed = pyqtSignal(str)        # status string
    turn_completed = pyqtSignal(int, str)   # (turn_id, summary)
    node_highlight = pyqtSignal(str)        # node_id
    error_occurred = pyqtSignal(str)        # error message

    def __init__(self, project_root: str):
        super().__init__()
        self.project_root = Path(project_root)
        self._event_handler = None
        self._memory_manager = None
        self._skill_loader = None
        self._game_master = None
        self._turn_count = 0
        self._status = "IDLE"
        self._current_node = None

    def init_backend(self) -> bool:
        """初始化后端模块"""
        try:
            # 添加项目根目录到 Python 路径
            if str(self.project_root) not in sys.path:
                sys.path.insert(0, str(self.project_root))

            from src.memory.manager import MemoryManager
            from src.skills.loader import SkillLoader

            self._memory_manager = MemoryManager(str(self.project_root / "workspace"))
            self._skill_loader = SkillLoader(str(self.project_root / "skills"))

            self.log_signal.emit("info", "后端模块初始化成功")
            self.log_signal.emit("info", f"Workspace: {self.project_root / 'workspace'}")
            self.log_signal.emit("info", f"Skills: {self.project_root / 'skills'}")
            return True
        except ImportError as e:
            self.log_signal.emit("error", f"后端模块导入失败: {e}")
            return False
        except Exception as e:
            self.log_signal.emit("error", f"后端初始化失败: {e}")
            return False

    async def run_agent(self):
        """运行 Agent"""
        if self._status == "RUNNING":
            self.log_signal.emit("warning", "Agent 已经在运行中")
            return

        self._set_status("RUNNING")
        self.log_signal.emit("info", "Agent 开始运行...")

        try:
            # 模拟 Agent 执行流程
            await self._execute_workflow()
        except Exception as e:
            self.log_signal.emit("error", f"Agent 运行失败: {e}")
            self.error_occurred.emit(str(e))
            self._set_status("ERROR")
            await asyncio.sleep(1)
            self._set_status("IDLE")

    async def _execute_workflow(self):
        """执行工作流"""
        workflow_nodes = [
            ("receive_event", "接收事件"),
            ("build_prompt", "构建 Prompt"),
            ("llm_reasoning", "LLM 推理"),
            ("parse_command", "解析命令"),
            ("update_memory", "更新记忆"),
            ("send_command", "发送命令"),
        ]

        for node_id, node_desc in workflow_nodes:
            if self._status == "PAUSED":
                self.log_signal.emit("info", "Agent 已暂停，等待继续...")
                while self._status == "PAUSED":
                    await asyncio.sleep(0.1)

            if self._status == "IDLE":
                self.log_signal.emit("info", "Agent 已停止")
                return

            self._current_node = node_id
            self.node_highlight.emit(node_id)
            self.log_signal.emit("info", f"执行节点: {node_desc} ({node_id})")

            # 模拟节点执行时间
            await asyncio.sleep(0.5)

            # 模拟 LLM 推理输出
            if node_id == "llm_reasoning":
                self.log_signal.emit("narrative", "玩家探索了铁匠铺，发现了一把锋利的剑。")
                self.log_signal.emit("command", '{"tool": "narration.describe", "params": {"scene": "铁匠铺"}}')

        self._turn_count += 1
        self.turn_completed.emit(self._turn_count, "完成")
        self.log_signal.emit("info", f"回合 {self._turn_count} 完成")
        self._set_status("IDLE")

    def pause(self):
        """暂停 Agent"""
        if self._status == "RUNNING":
            self._set_status("PAUSED")
            self.log_signal.emit("info", "Agent 已暂停")
        elif self._status == "PAUSED":
            self._set_status("RUNNING")
            self.log_signal.emit("info", "Agent 继续运行")

    def step(self):
        """单步执行"""
        self._set_status("STEP_WAITING")
        self.log_signal.emit("info", "单步执行模式 (待实现)")
        # TODO: 实现单步执行逻辑

    def reset(self):
        """重置 Agent"""
        self._turn_count = 0
        self._current_node = None
        self._set_status("IDLE")
        self.log_signal.emit("info", "Agent 已重置")
        self.turn_completed.emit(0, "重置")

    def _set_status(self, status: str):
        """设置状态"""
        self._status = status
        self.status_changed.emit(status)

    def get_status(self) -> str:
        """获取当前状态"""
        return self._status

    def get_turn_count(self) -> int:
        """获取回合数"""
        return self._turn_count

    def inject_command(self, level: str, content: str):
        """注入指令"""
        self.log_signal.emit("info", f"注入指令 [{level}]: {content[:50]}...")
        # TODO: 实现指令注入逻辑

    def force_tool(self, tool_name: str, params: str):
        """强制工具执行"""
        self.log_signal.emit("info", f"强制工具: {tool_name}")
        self.log_signal.emit("command", f"参数: {params}")
        # TODO: 实现工具强制调用
        return {"status": "success", "result": "工具执行结果示例"}
