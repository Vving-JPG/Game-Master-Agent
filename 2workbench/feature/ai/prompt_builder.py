# 2workbench/feature/ai/prompt_builder.py
"""Prompt 组装器 — 构建 LLM 的 messages 列表

组装结构:
[system] 基础 system prompt + Skills + 记忆上下文 + 游戏状态
[user]   历史对话 N 轮
[user]   当前事件

从 1agent_core/src/prompt_builder.py 重构而来。
"""
from __future__ import annotations

from typing import Any

from foundation.llm import LLMMessage
from foundation.logger import get_logger
from core.models import MemoryRepo, PromptRepo
from core.state import AgentState

logger = get_logger(__name__)


class PromptBuilder:
    """Prompt 组装器

    用法:
        builder = PromptBuilder()
        messages = builder.build(
            system_prompt="你是游戏主持人...",
            state=agent_state,
            active_skills=["narration", "exploration"],
            event_text="玩家说: 我要探索幽暗森林",
        )
    """

    def __init__(self):
        self._system_prompt_cache: str | None = None
        self._system_prompt_key: str | None = None

    def build(
        self,
        system_prompt: str,
        state: AgentState,
        active_skills: list[str] | None = None,
        event_text: str = "",
        skill_contents: list[str] | None = None,
        memory_context: str = "",
        max_history_turns: int = 10,
        db_path: str | None = None,
    ) -> list[LLMMessage]:
        """组装完整的 messages 列表

        Args:
            system_prompt: 基础 system prompt
            state: 当前 Agent 状态
            active_skills: 激活的 Skill 名称列表
            event_text: 当前事件的文本描述
            skill_contents: Skill 内容列表（已加载）
            memory_context: 记忆上下文文本
            max_history_turns: 最大历史轮数
            db_path: 数据库路径

        Returns:
            LLMMessage 列表
        """
        messages: list[LLMMessage] = []

        # 1. System 消息
        system_content = self._build_system_content(
            system_prompt=system_prompt,
            skill_contents=skill_contents or [],
            memory_context=memory_context,
            state=state,
        )
        messages.append(LLMMessage(role="system", content=system_content))

        # 2. 历史对话（从 state.messages 中取最近 N 轮）
        history = self._extract_history(state, max_history_turns)
        messages.extend(history)

        # 3. 当前事件
        if event_text:
            messages.append(LLMMessage(role="user", content=event_text))

        return messages

    def _build_system_content(
        self,
        system_prompt: str,
        skill_contents: list[str],
        memory_context: str,
        state: AgentState,
    ) -> str:
        """构建 system 消息内容"""
        parts = [system_prompt]

        # Skill 内容
        if skill_contents:
            parts.append("\n\n## 当前激活的技能规则\n")
            for i, content in enumerate(skill_contents):
                parts.append(f"\n### 技能 {i+1}\n{content}")

        # 记忆上下文
        if memory_context:
            parts.append(f"\n\n## 相关记忆\n{memory_context}")

        # 游戏状态快照
        state_text = self._format_game_state(state)
        if state_text:
            parts.append(f"\n\n## 当前游戏状态\n{state_text}")

        return "".join(parts)

    def _format_game_state(self, state: AgentState) -> str:
        """格式化游戏状态为文本"""
        parts = []

        player = state.get("player", {})
        if player:
            parts.append(
                f"- 玩家: {player.get('name', '未知')} "
                f"HP:{player.get('hp', 0)}/{player.get('max_hp', 0)} "
                f"MP:{player.get('mp', 0)}/{player.get('max_mp', 0)} "
                f"Lv.{player.get('level', 1)} "
                f"EXP:{player.get('exp', 0)} "
                f"金币:{player.get('gold', 0)}"
            )

        location = state.get("current_location", {})
        if location:
            parts.append(f"- 当前位置: {location.get('name', '未知')}")

        npcs = state.get("active_npcs", [])
        if npcs:
            npc_names = [n.get("name", "未知") for n in npcs]
            parts.append(f"- 场景 NPC: {', '.join(npc_names)}")

        quests = state.get("active_quests", [])
        if quests:
            for q in quests[:3]:  # 最多显示 3 个
                parts.append(f"- 任务: [{q.get('status', '?')}] {q.get('title', '未知')}")

        parts.append(f"- 回合数: {state.get('turn_count', 0)}")

        # 当前地点详情
        current_loc_id = state.get("current_location", {}).get("id", 0)
        if current_loc_id:
            try:
                from core.models.repository import LocationRepo
                from foundation.config import settings
                db_path = getattr(settings, 'database_path', 'data/game.db')
                loc_repo = LocationRepo()
                location = loc_repo.get_by_id(current_loc_id, db_path=db_path)
                if location:
                    parts.append(f"\n**当前地点详情**: {location.name}")
                    if location.description:
                        parts.append(f"  {location.description}")
                    if location.connections:
                        exits = ", ".join([f"{d}" for d in location.connections.keys()])
                        parts.append(f"  可用出口: {exits}")
            except Exception:
                pass

        # 当前场景 NPC 详情
        active_npcs = state.get("active_npcs", [])
        if active_npcs:
            try:
                from core.models.repository import NPCRepo
                from foundation.config import settings
                db_path = getattr(settings, 'database_path', 'data/game.db')
                npc_repo = NPCRepo()
                for npc_ref in active_npcs[:3]:  # 最多显示 3 个
                    npc_id = npc_ref if isinstance(npc_ref, int) else npc_ref.get('id', 0)
                    if npc_id:
                        npc = npc_repo.get_by_id(npc_id, db_path=db_path)
                        if npc:
                            parts.append(f"\n**NPC {npc.name}**: 心情={npc.mood}, 说话风格={npc.speech_style or '未知'}")
                            if npc.backstory:
                                parts.append(f"  背景: {npc.backstory[:100]}")
            except Exception:
                pass

        return "\n".join(parts)

    def _extract_history(self, state: AgentState, max_turns: int) -> list[LLMMessage]:
        """从 state.messages 提取历史对话"""
        messages = state.get("messages", [])
        if not messages:
            return []

        # LangGraph 的 messages 是 LangChain Message 对象列表
        # 取最近 2*max_turns 条消息（N 轮 = 2N 条）
        recent = messages[-(max_turns * 2):]

        result = []
        for msg in recent:
            if hasattr(msg, "role"):
                role = msg.role
                content = msg.content if hasattr(msg, "content") else str(msg)
            elif hasattr(msg, "type"):
                # LangChain BaseMessage
                role = msg.type
                content = msg.content
            else:
                continue

            # 跳过 system 消息（已在前面添加）
            if role == "system":
                continue

            result.append(LLMMessage(role=role, content=content))

        return result
