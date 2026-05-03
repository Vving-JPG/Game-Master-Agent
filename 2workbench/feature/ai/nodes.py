# 2workbench/feature/ai/nodes.py
"""LangGraph 节点函数 — StateGraph 的计算单元

每个节点函数:
- 接收 AgentState 作为输入
- 执行特定逻辑
- 返回 State 的部分更新字典

节点列表:
1. handle_event — 接收事件，更新状态
2. build_prompt — 组装 Prompt
3. llm_reasoning — 调用 LLM（流式）
4. parse_output — 解析 LLM 输出
5. execute_commands — 执行解析出的命令
6. update_memory — 更新记忆
"""
from __future__ import annotations

import time
from typing import Any

from foundation.event_bus import event_bus
from foundation.llm import LLMMessage
from foundation.llm.model_router import model_router
from foundation.logger import get_logger
from core.state import AgentState

from .events import (
    create_node_event, create_stream_token_event,
    create_error_event, LLM_STREAM_TOKEN, LLM_STREAM_REASONING,
    COMMAND_PARSED, COMMAND_EXECUTED, MEMORY_STORED,
)
from .prompt_builder import PromptBuilder
from .command_parser import parse_llm_output
from .tools import ALL_TOOLS, get_tools_schema

logger = get_logger(__name__)

# 全局 PromptBuilder 实例
_prompt_builder = PromptBuilder()


async def node_handle_event(state: AgentState) -> dict[str, Any]:
    """节点 1: 接收事件，更新状态

    从 state.current_event 中提取事件信息，
    更新 turn_count、execution_state 等。
    """
    event_bus.emit(create_node_event("handle_event", "started"))

    event = state.get("current_event", {})
    turn = state.get("turn_count", 0) + 1

    # 格式化事件文本
    event_type = event.get("type", "player_action")
    event_data = event.get("data", {})
    raw_text = event_data.get("raw_text", "")

    # 根据事件类型格式化
    event_texts = {
        "player_action": f"玩家行动: {raw_text}",
        "player_move": f"玩家移动: {raw_text}",
        "npc_interact": f"与 NPC 交互: {raw_text}",
        "combat_start": f"战斗开始: {raw_text}",
        "system_event": f"系统事件: {raw_text}",
    }
    event_text = event_texts.get(event_type, f"事件: {raw_text}")

    event_bus.emit(create_node_event("handle_event", "completed"))

    return {
        "turn_count": turn,
        "execution_state": "running",
        "current_event": {**event, "_formatted_text": event_text},
    }


async def node_build_prompt(state: AgentState) -> dict[str, Any]:
    """节点 2: 组装 Prompt

    调用 PromptBuilder 组装完整的 messages 列表。
    """
    event_bus.emit(create_node_event("build_prompt", "started"))

    event = state.get("current_event", {})
    event_text = event.get("_formatted_text", event.get("data", {}).get("raw_text", ""))

    # 获取 Skill 内容（简化版，实际应从 SkillLoader 获取）
    skill_contents = []
    active_skills = state.get("active_skills", [])
    # TODO: P3 阶段接入 SkillLoader

    # 组装 Prompt
    system_prompt = _get_system_prompt()
    messages = _prompt_builder.build(
        system_prompt=system_prompt,
        state=state,
        event_text=event_text,
        skill_contents=skill_contents,
    )

    # 转换为 LangChain Message 格式
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    lc_messages = []
    for msg in messages:
        if msg.role == "system":
            lc_messages.append(SystemMessage(content=msg.content))
        elif msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))

    event_bus.emit(create_node_event("build_prompt", "completed"))

    return {
        "prompt_messages": [{"role": m.type, "content": m.content} for m in lc_messages],
    }


async def node_llm_reasoning(state: AgentState) -> dict[str, Any]:
    """节点 3: 调用 LLM（流式）

    使用 ModelRouter 选择合适的模型，
    流式调用 LLM 并通过 EventBus 推送 token。
    """
    event_bus.emit(create_node_event("llm_reasoning", "started"))

    start_time = time.time()
    prompt_messages = state.get("prompt_messages", [])

    if not prompt_messages:
        return {
            "llm_response": {"content": "", "error": "无 prompt 消息"},
            "error": "无 prompt 消息",
        }

    # 获取 LLM 客户端
    content = prompt_messages[-1].get("content", "") if prompt_messages else ""
    client, config = model_router.route(
        content=content,
        provider=state.get("provider"),
        model=state.get("model_name"),
    )

    # 转换为 LLMMessage
    llm_messages = [LLMMessage(role=m["role"], content=m["content"]) for m in prompt_messages]

    # 流式调用
    full_content = ""
    reasoning_content = ""
    tool_calls = []
    total_tokens = 0

    try:
        async for event in client.stream(
            messages=llm_messages,
            temperature=config.get("temperature", 0.7),
            tools=get_tools_schema() if state.get("active_skills") else None,
        ):
            if event.type == "token":
                full_content += event.content
                event_bus.emit(create_stream_token_event(event.content))
            elif event.type == "reasoning":
                reasoning_content += event.content
            elif event.type == "tool_call":
                tool_calls.extend(event.tool_calls)
            elif event.type == "complete":
                total_tokens = event.total_tokens

    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        event_bus.emit(create_error_event(str(e), "llm_reasoning"))
        return {
            "llm_response": {"content": full_content or f"[LLM 错误: {e}]", "error": str(e)},
            "error": str(e),
        }

    latency_ms = int((time.time() - start_time) * 1000)

    event_bus.emit(create_node_event("llm_reasoning", "completed", {
        "latency_ms": latency_ms, "tokens": total_tokens,
    }))

    return {
        "llm_response": {
            "content": full_content,
            "reasoning": reasoning_content,
            "tool_calls": tool_calls,
            "tokens": total_tokens,
            "latency_ms": latency_ms,
            "model": config.get("model", ""),
            "provider": config.get("provider", ""),
        },
    }


async def node_parse_output(state: AgentState) -> dict[str, Any]:
    """节点 4: 解析 LLM 输出

    调用 CommandParser 将 LLM 文本解析为结构化命令。
    """
    event_bus.emit(create_node_event("parse_output", "started"))

    llm_response = state.get("llm_response", {})
    raw_content = llm_response.get("content", "")

    parsed = parse_llm_output(raw_content)

    # 如果 LLM 返回了 tool_calls，也作为命令处理
    tool_commands = []
    for tc in llm_response.get("tool_calls", []):
        func = tc.get("function", {})
        tool_commands.append({
            "intent": f"tool:{func.get('name', '')}",
            "params": {"arguments": func.get("arguments", "{}")},
        })

    all_commands = parsed.commands + [
        __import__("feature.ai.command_parser", fromlist=["ParsedCommand"]).ParsedCommand(
            intent=c["intent"], params=c.get("params", {})
        ) for c in tool_commands
    ]

    event_bus.emit(create_node_event("parse_output", "completed", {
        "commands_count": len(all_commands),
        "parse_method": parsed.parse_method,
    }))

    return {
        "parsed_commands": [
            {"intent": c.intent, "params": c.params} for c in all_commands
        ],
        "memory_updates": parsed.memory_updates,
    }


async def node_execute_commands(state: AgentState) -> dict[str, Any]:
    """节点 5: 执行解析出的命令

    将命令分发给对应的工具或处理器。
    """
    event_bus.emit(create_node_event("execute_commands", "started"))

    commands = state.get("parsed_commands", [])
    results = []

    for cmd in commands:
        intent = cmd.get("intent", "")
        params = cmd.get("params", {})

        try:
            # 查找匹配的工具
            from .tools import ALL_TOOLS
            for tool in ALL_TOOLS:
                if tool.name == intent or intent == f"tool:{tool.name}":
                    # 执行工具
                    if isinstance(params.get("arguments"), str):
                        import json
                        try:
                            params = json.loads(params["arguments"])
                        except Exception:
                            params = {}
                    result = tool.invoke(params)
                    results.append({"intent": intent, "success": True, "result": result})
                    logger.debug(f"工具执行: {intent} -> {result[:100]}")
                    break
            else:
                # 无匹配工具，记录为 no_op
                results.append({"intent": intent, "success": False, "result": "no matching tool"})
        except Exception as e:
            results.append({"intent": intent, "success": False, "result": f"error: {e}"})
            logger.error(f"命令执行失败 ({intent}): {e}")

    event_bus.emit(create_node_event("execute_commands", "completed", {
        "executed": len(results),
    }))

    return {
        "command_results": results,
    }


async def node_update_memory(state: AgentState) -> dict[str, Any]:
    """节点 6: 更新记忆

    将记忆更新写入数据库。
    """
    event_bus.emit(create_node_event("update_memory", "started"))

    memory_updates = state.get("memory_updates", [])
    stored_count = 0

    world_id = int(state.get("world_id", 0))
    turn = state.get("turn_count", 0)

    if world_id > 0 and memory_updates:
        from core.models import MemoryRepo
        repo = MemoryRepo()
        for mem in memory_updates:
            try:
                repo.store(
                    world_id=world_id,
                    category=mem.get("category", "session"),
                    source=mem.get("source", "agent"),
                    content=mem.get("content", ""),
                    title=mem.get("title", ""),
                    importance=mem.get("importance", 0.5),
                    turn=turn,
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"记忆存储失败: {e}")

    event_bus.emit(create_node_event("update_memory", "completed", {
        "stored": stored_count,
    }))

    return {}


# ===== 条件路由函数 =====

async def route_after_llm(state: AgentState) -> str:
    """LLM 推理后的路由

    如果有 tool_calls -> execute_commands
    否则 -> parse_output
    """
    llm_response = state.get("llm_response", {})
    if llm_response.get("tool_calls"):
        return "execute_commands"
    return "parse_output"


async def route_after_parse(state: AgentState) -> str:
    """解析后的路由

    如果有命令 -> execute_commands
    否则 -> update_memory
    """
    commands = state.get("parsed_commands", [])
    if commands:
        return "execute_commands"
    return "update_memory"


# ===== System Prompt =====

def _get_system_prompt() -> str:
    """获取基础 System Prompt"""
    return """你是一个沉浸式游戏主持人（Game Master）。你的职责是：

1. **叙事** — 生动地描述游戏世界、场景、NPC 行为和事件
2. **裁判** — 公平地判定玩家行动的结果
3. **角色扮演** — 扮演 NPC 与玩家互动
4. **推进剧情** — 根据玩家选择推进故事发展

## 输出格式

每次回复必须包含一个 JSON 结构：
```json
{
    "narrative": "你的叙事描述文本",
    "commands": [
        {"intent": "命令名称", "params": {"参数": "值"}}
    ],
    "memory_updates": [
        {"action": "create", "category": "session", "content": "重要信息摘要"}
    ]
}
```

## 可用命令

- `roll_dice` — 掷骰子判定
- `update_player_stat` — 更新玩家属性
- `give_item` / `remove_item` — 物品管理
- `move_to_location` — 移动玩家
- `update_npc_relationship` — 修改 NPC 关系
- `update_quest_status` — 更新任务状态
- `store_memory` — 存储记忆

## 风格要求

- 使用第二人称描述玩家行动
- 保持叙事的沉浸感和连贯性
- 根据玩家选择产生有意义的后果
- 适当使用对话和描写来丰富场景
"""
