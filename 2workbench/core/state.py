"""LangGraph State 定义 — Agent 运行时共享状态

这是 LangGraph StateGraph 的核心数据结构。
所有节点（Node）通过读写此 State 进行通信。

设计原则:
1. 使用 TypedDict 定义（LangGraph 要求）
2. 使用 Annotated + Reducer 控制字段更新策略
3. 只包含运行时数据，不包含持久化配置
4. 与 Pydantic 模型保持一致的字段名和类型
"""
from __future__ import annotations

from typing import Annotated, Any

from typing_extensions import TypedDict

# LangGraph 内置 Reducer
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """Agent 运行时状态

    这是 LangGraph StateGraph 的共享状态。
    每个节点函数接收当前 State，返回部分更新字典。

    Reducer 说明:
    - messages: 使用 add_messages reducer，新消息追加而非覆盖
    - 其他字段: 无 reducer，每次更新覆盖整个字段
    """

    # ===== LangGraph 消息（带 Reducer）=====
    messages: Annotated[list, add_messages]

    # ===== 游戏世界状态 =====
    world_id: str
    player: dict[str, Any]           # Player.model_dump()
    current_location: dict[str, Any] # Location.model_dump()
    active_npcs: list[dict[str, Any]]  # [NPC.model_dump(), ...]
    inventory: list[dict[str, Any]]    # [PlayerItem.model_dump(), ...]
    active_quests: list[dict[str, Any]]  # [Quest.model_dump(), ...]

    # ===== Agent 运行时状态 =====
    turn_count: int
    execution_state: str              # idle / running / paused / step_waiting / completed / error

    # ===== 工作流中间数据 =====
    current_event: dict[str, Any]     # 当前引擎事件
    prompt_messages: list[dict]       # 组装好的 messages（发给 LLM 的）
    llm_response: dict[str, Any]      # LLM 原始响应
    parsed_commands: list[dict]       # 解析后的命令列表
    command_results: list[dict]       # 引擎执行结果
    memory_updates: list[dict]        # 记忆更新列表

    # ===== 配置（运行时可变）=====
    active_skills: list[str]          # 当前激活的 Skill 名称列表
    model_name: str                   # 当前使用的模型
    provider: str                     # 当前供应商
    temperature: float                # 当前温度

    # ===== 错误处理 =====
    error: str                        # 错误信息
    retry_count: int                  # 重试次数


def create_initial_state(
    world_id: str = "1",
    player_name: str = "冒险者",
    model_name: str = "deepseek-chat",
    provider: str = "deepseek",
) -> AgentState:
    """创建初始 Agent 状态

    Args:
        world_id: 世界 ID
        player_name: 玩家名称
        model_name: 模型名称
        provider: 供应商

    Returns:
        初始 AgentState
    """
    return AgentState(
        messages=[],
        world_id=world_id,
        player={
            "id": 0,
            "name": player_name,
            "hp": 100,
            "max_hp": 100,
            "mp": 50,
            "max_mp": 50,
            "level": 1,
            "exp": 0,
            "gold": 0,
            "location_id": 0,
        },
        current_location={},
        active_npcs=[],
        inventory=[],
        active_quests=[],
        turn_count=0,
        execution_state="idle",
        current_event={},
        prompt_messages=[],
        llm_response={},
        parsed_commands=[],
        command_results=[],
        memory_updates=[],
        active_skills=[],
        model_name=model_name,
        provider=provider,
        temperature=0.7,
        error="",
        retry_count=0,
    )