"""
Prompt 组装器。
将 system prompt、Skill、记忆、历史对话、当前事件组装为完整的 messages 列表。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.memory.manager import MemoryManager
from src.skills.loader import SkillLoader, SkillMetadata

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Prompt 组装器"""

    def __init__(
        self,
        system_prompt_path: str,
        memory_manager: MemoryManager,
        skill_loader: SkillLoader,
    ):
        self.system_prompt_path = Path(system_prompt_path)
        self.memory_manager = memory_manager
        self.skill_loader = skill_loader
        self._system_prompt_cache: Optional[str] = None

    def load_system_prompt(self) -> str:
        """加载 system prompt（带缓存）"""
        if self._system_prompt_cache is None:
            if self.system_prompt_path.exists():
                self._system_prompt_cache = self.system_prompt_path.read_text(
                    encoding="utf-8"
                )
            else:
                logger.warning(f"system prompt 文件不存在: {self.system_prompt_path}")
                self._system_prompt_cache = "你是一个游戏 GM Agent。"
        return self._system_prompt_cache

    def invalidate_system_prompt_cache(self):
        """清除 system prompt 缓存"""
        self._system_prompt_cache = None

    def build(
        self,
        event: dict,
        history: list[dict],
        memory_depth: str = "activation",
    ) -> list[dict]:
        """
        组装完整的 messages 列表。

        :param event: 引擎事件 (EngineEvent 的 data 字段)
        :param history: 历史对话消息列表 (OpenAI 格式)
        :param memory_depth: 记忆加载深度 ("index" / "activation" / "execution")
        :return: OpenAI 格式的 messages 列表
        """
        messages = []

        # 1. System prompt
        system_content = self._build_system_content(event, memory_depth)
        messages.append({"role": "system", "content": system_content})

        # 2. 历史对话
        messages.extend(history)

        # 3. 当前事件（作为 user 消息）
        user_content = self._format_event_as_user_message(event)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_system_content(self, event: dict, memory_depth: str) -> str:
        """构建 system 消息内容"""
        parts = []

        # 1. 基础 system prompt
        parts.append(self.load_system_prompt())

        # 2. 相关 Skill
        event_type = event.get("type", "")
        user_input = event.get("data", {}).get("raw_text", "")
        context_hints = event.get("context_hints", [])

        relevant_skills = self.skill_loader.get_relevant_skills(
            event_type=event_type,
            user_input=user_input,
            context_hints=context_hints,
        )

        if relevant_skills:
            skill_sections = ["\n\n## 可用能力 (Skills)\n"]
            for skill in relevant_skills:
                content = self.skill_loader.load_skill_activation(skill.name)
                if content:
                    skill_sections.append(content)
                    skill_sections.append("")
            parts.append("\n".join(skill_sections))

        # 3. 记忆上下文
        if context_hints:
            memory_text = self.memory_manager.load_context(
                context_hints, depth=memory_depth
            )
            if memory_text.strip():
                parts.append(f"\n\n## 相关记忆\n\n{memory_text}")

        # 4. 游戏状态快照
        game_state = event.get("game_state", {})
        if game_state:
            state_lines = ["\n\n## 当前游戏状态\n"]
            for key, value in game_state.items():
                state_lines.append(f"- {key}: {value}")
            parts.append("\n".join(state_lines))

        return "".join(parts)

    def _format_event_as_user_message(self, event: dict) -> str:
        """将引擎事件格式化为 user 消息"""
        event_type = event.get("type", "unknown")
        data = event.get("data", {})
        raw_text = data.get("raw_text", "")

        if raw_text:
            return f"[{event_type}] 玩家: {raw_text}"

        # 非 player_action 类型的事件
        descriptions = {
            "player_move": f"玩家移动到 {data.get('to', '未知位置')}",
            "combat_start": f"战斗开始: 对手 {data.get('enemy_id', '未知')}",
            "combat_action": f"战斗动作: {data.get('action', '未知')}",
            "combat_end": f"战斗结束: {data.get('result', '未知')}",
            "quest_update": f"任务更新: {data.get('quest_id', '未知')} - {data.get('status', '')}",
            "item_acquire": f"获得物品: {data.get('item_id', '未知')}",
            "npc_interact": f"NPC {data.get('npc_id', '')} 主动交互",
            "time_pass": f"时间流逝: {data.get('new_time', '')}",
            "system_event": f"系统事件: {data.get('message', '')}",
        }
        return f"[{event_type}] {descriptions.get(event_type, str(data))}"
