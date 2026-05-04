"""多 Agent 编排服务 — Feature 层

负责 Agent 实例管理和链式编排逻辑，通过 EventBus 与 Presentation 层通信。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any
from enum import Enum

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger

logger = get_logger(__name__)


class AgentRole(str, Enum):
    """Agent 角色类型"""
    GM = "gm"
    NARRATOR = "narrator"
    COMBAT = "combat"
    DIALOGUE = "dialogue"
    CUSTOM = "custom"


class StepType(str, Enum):
    """链式步骤类型"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


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
    id: str = ""
    agent_id: str = ""
    step_type: str = "sequential"  # sequential / parallel / conditional
    condition: str = ""  # 条件表达式（conditional 时使用）
    next_step_id: str = ""


class MultiAgentService:
    """多 Agent 编排服务

    管理 Agent 实例和链式编排逻辑。
    """

    def __init__(self):
        self._agents: list[AgentInstance] = []
        self._chain: list[ChainStep] = []
        self._setup_listeners()

    def _setup_listeners(self):
        """设置 EventBus 监听器"""
        event_bus.subscribe("ui.multi_agent.load_requested", self._on_load_agents)
        event_bus.subscribe("ui.multi_agent.save_requested", self._on_save_agents)
        event_bus.subscribe("ui.multi_agent.add_requested", self._on_add_agent)
        event_bus.subscribe("ui.multi_agent.update_requested", self._on_update_agent)
        event_bus.subscribe("ui.multi_agent.delete_requested", self._on_delete_agent)
        event_bus.subscribe("ui.multi_agent.chain.load_requested", self._on_load_chain)
        event_bus.subscribe("ui.multi_agent.chain.save_requested", self._on_save_chain)
        event_bus.subscribe("ui.multi_agent.chain.validate_requested", self._on_validate_chain)

    def _on_load_agents(self, event: Event):
        """加载 Agent 列表"""
        try:
            event_bus.emit(Event(
                type="feature.multi_agent.loaded",
                data={"agents": [asdict(agent) for agent in self._agents], "success": True}
            ))
        except Exception as e:
            logger.error(f"加载 Agent 失败: {e}")
            event_bus.emit(Event(
                type="feature.multi_agent.load_failed",
                data={"error": str(e)}
            ))

    def _on_save_agents(self, event: Event):
        """保存 Agent 列表"""
        try:
            agents_data = event.data.get("agents", [])
            self._agents = [AgentInstance(**agent) for agent in agents_data]
            event_bus.emit(Event(
                type="feature.multi_agent.saved",
                data={"success": True, "count": len(self._agents)}
            ))
        except Exception as e:
            logger.error(f"保存 Agent 失败: {e}")
            event_bus.emit(Event(
                type="feature.multi_agent.save_failed",
                data={"error": str(e)}
            ))

    def _on_add_agent(self, event: Event):
        """添加 Agent"""
        try:
            agent_data = event.data.get("agent", {})
            agent = AgentInstance(**agent_data)
            self._agents.append(agent)
            event_bus.emit(Event(
                type="feature.multi_agent.added",
                data={"agent": asdict(agent), "success": True}
            ))
        except Exception as e:
            logger.error(f"添加 Agent 失败: {e}")
            event_bus.emit(Event(
                type="feature.multi_agent.add_failed",
                data={"error": str(e)}
            ))

    def _on_update_agent(self, event: Event):
        """更新 Agent"""
        try:
            agent_id = event.data.get("id", "")
            agent_data = event.data.get("agent", {})
            for i, agent in enumerate(self._agents):
                if agent.id == agent_id:
                    self._agents[i] = AgentInstance(**agent_data)
                    event_bus.emit(Event(
                        type="feature.multi_agent.updated",
                        data={"agent": agent_data, "success": True}
                    ))
                    return
            event_bus.emit(Event(
                type="feature.multi_agent.update_failed",
                data={"error": f"Agent {agent_id} 不存在"}
            ))
        except Exception as e:
            logger.error(f"更新 Agent 失败: {e}")
            event_bus.emit(Event(
                type="feature.multi_agent.update_failed",
                data={"error": str(e)}
            ))

    def _on_delete_agent(self, event: Event):
        """删除 Agent"""
        try:
            agent_id = event.data.get("id", "")
            self._agents = [agent for agent in self._agents if agent.id != agent_id]
            # 同时删除相关的链式步骤
            self._chain = [step for step in self._chain if step.agent_id != agent_id]
            event_bus.emit(Event(
                type="feature.multi_agent.deleted",
                data={"id": agent_id, "success": True}
            ))
        except Exception as e:
            logger.error(f"删除 Agent 失败: {e}")
            event_bus.emit(Event(
                type="feature.multi_agent.delete_failed",
                data={"error": str(e)}
            ))

    def _on_load_chain(self, event: Event):
        """加载链式配置"""
        try:
            event_bus.emit(Event(
                type="feature.multi_agent.chain.loaded",
                data={"chain": [asdict(step) for step in self._chain], "success": True}
            ))
        except Exception as e:
            logger.error(f"加载链式配置失败: {e}")
            event_bus.emit(Event(
                type="feature.multi_agent.chain.load_failed",
                data={"error": str(e)}
            ))

    def _on_save_chain(self, event: Event):
        """保存链式配置"""
        try:
            chain_data = event.data.get("chain", [])
            self._chain = [ChainStep(**step) for step in chain_data]
            event_bus.emit(Event(
                type="feature.multi_agent.chain.saved",
                data={"success": True, "count": len(self._chain)}
            ))
        except Exception as e:
            logger.error(f"保存链式配置失败: {e}")
            event_bus.emit(Event(
                type="feature.multi_agent.chain.save_failed",
                data={"error": str(e)}
            ))

    def _on_validate_chain(self, event: Event):
        """验证链式配置"""
        try:
            errors = []
            warnings = []

            # 检查是否有孤立的步骤
            agent_ids = {agent.id for agent in self._agents}
            for step in self._chain:
                if step.agent_id not in agent_ids:
                    errors.append(f"步骤 {step.id} 引用了不存在的 Agent: {step.agent_id}")

            # 检查循环依赖
            visited = set()
            recursion_stack = set()

            def has_cycle(step_id: str) -> bool:
                if step_id in recursion_stack:
                    return True
                if step_id in visited:
                    return False
                visited.add(step_id)
                recursion_stack.add(step_id)

                # 找到下一步
                next_steps = [s for s in self._chain if s.id == step_id]
                for step in next_steps:
                    if step.next_step_id and has_cycle(step.next_step_id):
                        return True

                recursion_stack.remove(step_id)
                return False

            for step in self._chain:
                if has_cycle(step.id):
                    errors.append(f"检测到循环依赖: {step.id}")
                    break

            # 检查是否有起始步骤
            if not self._chain:
                warnings.append("链式配置为空")

            is_valid = len(errors) == 0
            event_bus.emit(Event(
                type="feature.multi_agent.chain.validated",
                data={
                    "valid": is_valid,
                    "errors": errors,
                    "warnings": warnings,
                }
            ))
        except Exception as e:
            logger.error(f"验证链式配置失败: {e}")
            event_bus.emit(Event(
                type="feature.multi_agent.chain.validate_failed",
                data={"error": str(e)}
            ))


# 全局单例
multi_agent_service = MultiAgentService()
