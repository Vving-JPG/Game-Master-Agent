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

import os
import time
from typing import Any

from foundation.event_bus import event_bus
from foundation.llm import LLMMessage
from foundation.llm.model_router import model_router
from foundation.logger import get_logger
from core.state import AgentState

from langgraph.types import RunnableConfig

from .events import (
    create_node_event, create_stream_token_event,
    create_error_event, LLM_STREAM_TOKEN, LLM_STREAM_REASONING,
    COMMAND_PARSED, COMMAND_EXECUTED, MEMORY_STORED,
)
from .prompt_builder import PromptBuilder
from .command_parser import parse_llm_output, ParsedCommand
from .tools import ALL_TOOLS, get_tools_schema

logger = get_logger(__name__)

# 全局 PromptBuilder 实例
_prompt_builder = PromptBuilder()


# 节点函数别名（兼容旧代码）
handle_event = None  # 将在文件末尾设置为 node_handle_event


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


async def node_build_prompt(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """节点 2: 组装 Prompt

    调用 PromptBuilder 组装完整的 messages 列表。
    使用 Store 获取长期记忆（跨会话持久化）。
    """
    event_bus.emit(create_node_event("build_prompt", "started"))

    event = state.get("current_event", {})
    event_text = event.get("_formatted_text", event.get("data", {}).get("raw_text", ""))

    # ===== 从 Store 获取长期记忆 =====
    memory_context = ""
    if config:
        try:
            from langgraph.config import get_store
            store = get_store(config)
            world_id = state.get("world_id", "1")
        except Exception as e:
            logger.warning(f"初始化 Store 失败: {e}")
            store = None

        if store:
            player_prefs = []
            world_state = []
            story_events = []

            # 获取玩家偏好（跨会话）
            try:
                player_prefs = store.search(
                    (world_id, "player_preferences"),
                    query=event_text,
                    limit=3,
                )
            except Exception as e:
                logger.warning(f"加载玩家偏好失败: {e}")

            # 获取世界状态
            try:
                world_state = store.search(
                    (world_id, "world_state"),
                    limit=3,
                )
            except Exception as e:
                logger.warning(f"加载世界状态失败: {e}")

            # 获取相关故事事件（语义检索）
            try:
                story_events = store.search(
                    (world_id, "story_events"),
                    query=event_text,
                    limit=5,
                )
            except Exception as e:
                logger.warning(f"加载故事事件失败: {e}")

            # 构建记忆上下文
            memory_parts = []
            if player_prefs:
                memory_parts.append("## 玩家偏好\n" + "\n".join([
                    f"- {p.value.get('content', '')}" for p in player_prefs
                ]))
            if world_state:
                memory_parts.append("## 世界状态\n" + "\n".join([
                    f"- {w.value.get('content', '')}" for w in world_state
                ]))
            if story_events:
                memory_parts.append("## 相关故事事件\n" + "\n".join([
                    f"- {s.value.get('content', '')}" for s in story_events
                ]))

            if memory_parts:
                memory_context = "\n\n".join(memory_parts)
                logger.debug(f"已加载长期记忆: {len(player_prefs)} 偏好, {len(world_state)} 世界状态, {len(story_events)} 事件")

    # 获取 Skill 内容
    skill_contents = []
    active_skills = state.get("active_skills", [])
    if not active_skills:
        # 自动加载 Skill（优先从项目目录加载）
        try:
            from feature.ai.skill_loader import SkillLoader
            from feature.project import project_manager

            # 优先使用项目中的 skills 目录
            skills_dir = None
            if project_manager.is_open and project_manager.project_path:
                project_skills = project_manager.project_path / "skills"
                if project_skills.exists():
                    skills_dir = str(project_skills)

            # 回退到默认 skills 目录
            if not skills_dir:
                skills_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'skills')

            if skills_dir and os.path.isdir(skills_dir):
                loader = SkillLoader(skills_dir)
                relevant = loader.get_relevant_skills(
                    user_input=state.get("current_event", ""),
                    event_type="player_action",
                    context_hints=["narrative", "world_building"]
                )
                for skill in relevant:
                    content = loader.load_activation(skill)
                    if content:
                        skill_contents.append(content)
        except Exception as e:
            logger.warning(f"Skill 加载失败: {e}")  # Skill 加载失败不影响主流程

    # 组装 Prompt
    system_prompt = _get_system_prompt()

    # 如果有长期记忆，注入到 system prompt
    if memory_context:
        system_prompt = f"{system_prompt}\n\n# 长期记忆（跨会话信息）\n{memory_context}"

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
        ParsedCommand(
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
                        except Exception as e:
                            logger.warning(f"工具参数解析失败: {e}")
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

    # 将工具执行结果格式化为消息，通过返回值更新状态
    new_messages = []
    if results:
        results_text = "\n".join([
            f"[工具结果] {r.get('intent', 'unknown')}: {r.get('result', '无结果')}"
            for r in results
        ])
        if results_text:
            new_messages.append({
                "role": "tool",
                "content": results_text
            })

    event_bus.emit(create_node_event("execute_commands", "completed", {
        "executed": len(results),
    }))

    # 通过返回值更新状态，包含 messages 和 command_results
    return {
        "messages": new_messages,
        "command_results": results,
    }


async def node_update_memory(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """节点 6: 更新记忆

    将记忆更新写入 Store（长期记忆存储）。
    同时保留对旧 MemoryRepo 的兼容（降级方案）。
    """
    event_bus.emit(create_node_event("update_memory", "started"))

    memory_updates = state.get("memory_updates", [])
    stored_count = 0

    world_id = state.get("world_id", "1")
    turn = state.get("turn_count", 0)

    # ===== 使用 Store 存储长期记忆 =====
    if config and memory_updates:
        try:
            from langgraph.config import get_store
            store = get_store(config)

            for mem in memory_updates:
                try:
                    category = mem.get("category", "session")
                    content = mem.get("content", "")

                    # 构建 key
                    import uuid
                    key = f"{category}_{turn}_{uuid.uuid4().hex[:8]}"

                    # 构建 value
                    value = {
                        "content": content,
                        "metadata": {
                            "category": category,
                            "source": mem.get("source", "agent"),
                            "title": mem.get("title", ""),
                            "importance": mem.get("importance", 0.5),
                            "turn_created": turn,
                            "timestamp": time.time(),
                        }
                    }

                    # 存储到 Store
                    store.put(
                        (world_id, category),
                        key,
                        value,
                    )
                    stored_count += 1
                    logger.debug(f"记忆已存储到 Store: {category}/{key}")
                except Exception as e:
                    logger.error(f"Store 记忆存储失败: {e}")
        except Exception as e:
            logger.warning(f"Store 不可用，回退到 MemoryRepo: {e}")

    # ===== 降级方案：使用旧的 MemoryRepo =====
    if stored_count == 0 and memory_updates:
        try:
            from core.models import MemoryRepo
            repo = MemoryRepo()
            for mem in memory_updates:
                try:
                    repo.store(
                        world_id=int(world_id),
                        category=mem.get("category", "session"),
                        source=mem.get("source", "agent"),
                        content=mem.get("content", ""),
                        title=mem.get("title", ""),
                        importance=mem.get("importance", 0.5),
                        turn=turn,
                    )
                    stored_count += 1
                except Exception as e:
                    logger.error(f"MemoryRepo 存储失败: {e}")
        except Exception as e:
            logger.error(f"MemoryRepo 不可用: {e}")

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
    """获取基础 System Prompt

    优先从当前项目的 prompts/system.md 加载，
    如果失败则返回默认的硬编码 prompt。
    """
    # 尝试从项目加载
    try:
        from feature.project import project_manager
        if project_manager.is_open:
            project_prompt = project_manager.load_prompt("system")
            if project_prompt:
                return project_prompt
    except Exception as e:
        logger.debug(f"项目提示词加载失败: {e}")  # 加载失败时使用默认 prompt

    # 默认硬编码 prompt
    return _DEFAULT_SYSTEM_PROMPT


# 默认系统提示词（当项目没有 system.md 时使用）
_DEFAULT_SYSTEM_PROMPT = """你是一个沉浸式游戏主持人（Game Master）。你的职责是：

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

## 世界构建命令（可随时使用）
- create_npc: 创建新的 NPC 角色（需提供名称，可选地点/性格/背景/说话风格/目标/心情）
- search_npcs: 搜索/查询 NPC（可按地点或名称过滤）
- create_location: 创建新的地点（需提供名称，可选描述和出口连接）
- create_item: 创建新的物品/道具（需提供名称，可选类型/稀有度/描述）
- create_quest: 创建新的任务/剧情（需提供标题，可选描述/类型/奖励/前置条件）
- get_world_state: 获取完整世界状态概览（所有地点/NPC/物品/任务）
- update_npc_state: 更新 NPC 状态（心情/位置/目标）

## 世界构建指导原则
1. 在故事推进过程中，根据需要动态创建 NPC、地点和物品
2. 创建前先用 get_world_state 或 search_npcs 检查是否已存在同名实体
3. 创建的实体应与当前故事情境一致，符合世界观设定
4. 每个新地点应有独特的描述和氛围（包含视觉/听觉/嗅觉细节）
5. NPC 应有鲜明的个性和说话风格，心情应反映当前情境
6. 物品应有合理的属性和背景故事，稀有度要适当
7. 任务应有明确的目标和合理的奖励
8. 创建后通过叙事自然地介绍给玩家，不要生硬地列出属性

## 风格要求

- 使用第二人称描述玩家行动
- 保持叙事的沉浸感和连贯性
- 根据玩家选择产生有意义的后果
- 适当使用对话和描写来丰富场景
"""


# 设置别名（在模块加载完成后）
handle_event = node_handle_event
