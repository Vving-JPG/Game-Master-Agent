# 2workbench/feature/ai/events.py
"""Agent 事件定义 — 通过 EventBus 通知上层

事件命名规范: feature.ai.{category}.{action}

替代原有的 EventHandler SSE 推送机制。
上层（Presentation）通过订阅这些事件来更新 UI。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from foundation.event_bus import Event


# ===== 事件类型常量 =====

# 生命周期
TURN_START = "feature.ai.lifecycle.turn_start"
TURN_END = "feature.ai.lifecycle.turn_end"
AGENT_ERROR = "feature.ai.lifecycle.error"
AGENT_PAUSED = "feature.ai.lifecycle.paused"
AGENT_RESUMED = "feature.ai.lifecycle.resumed"

# 节点执行
NODE_STARTED = "feature.ai.node.started"
NODE_COMPLETED = "feature.ai.node.completed"

# LLM
LLM_REQUEST = "feature.ai.llm.request"
LLM_RESPONSE = "feature.ai.llm.response"
LLM_STREAM_TOKEN = "feature.ai.llm.stream_token"
LLM_STREAM_REASONING = "feature.ai.llm.stream_reasoning"
LLM_TOOL_CALL = "feature.ai.llm.tool_call"

# 命令
COMMAND_PARSED = "feature.ai.command.parsed"
COMMAND_EXECUTED = "feature.ai.command.executed"
COMMAND_REJECTED = "feature.ai.command.rejected"

# 记忆
MEMORY_STORED = "feature.ai.memory.stored"
MEMORY_UPDATED = "feature.ai.memory.updated"

# 状态
STATE_CHANGED = "feature.ai.state.changed"
STATE_SNAPSHOT = "feature.ai.state.snapshot"


# ===== 事件创建辅助函数 =====

def create_turn_start_event(world_id: str, turn_count: int) -> Event:
    """创建回合开始事件"""
    return Event(
        type=TURN_START,
        data={"world_id": world_id, "turn_count": turn_count},
        source="feature.ai",
    )


def create_turn_end_event(
    world_id: str,
    turn_count: int,
    narrative: str = "",
    commands_count: int = 0,
    tokens_used: int = 0,
    latency_ms: int = 0,
) -> Event:
    """创建回合结束事件"""
    return Event(
        type=TURN_END,
        data={
            "world_id": world_id,
            "turn_count": turn_count,
            "narrative": narrative[:200],  # 截断避免事件过大
            "commands_count": commands_count,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
        },
        source="feature.ai",
    )


def create_node_event(node_name: str, status: str, data: dict | None = None) -> Event:
    """创建节点执行事件"""
    return Event(
        type=f"feature.ai.node.{status}",
        data={"node": node_name, **(data or {})},
        source="feature.ai",
    )


def create_stream_token_event(content: str) -> Event:
    """创建流式 token 事件"""
    return Event(
        type=LLM_STREAM_TOKEN,
        data={"content": content},
        source="feature.ai",
    )


def create_error_event(error: str, node: str = "") -> Event:
    """创建错误事件"""
    return Event(
        type=AGENT_ERROR,
        data={"error": error, "node": node},
        source="feature.ai",
    )
