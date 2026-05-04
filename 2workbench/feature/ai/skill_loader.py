# 2workbench/feature/ai/skill_loader.py
"""Skill 加载器 — 评分匹配 + Prompt 注入

Skill 是 Markdown 文件，通过 YAML Front Matter 定义元数据。
Skill 不是可执行代码，而是通过评分匹配后注入 system prompt 的指导文档。

从 1agent_core/src/skills/loader.py 重构而来。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SkillMetadata:
    """Skill 元数据"""
    name: str
    description: str = ""
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    triggers: list[dict[str, Any]] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class Skill:
    """完整的 Skill"""
    metadata: SkillMetadata
    content: str = ""  # Markdown Body（指导 LLM 的规则）


class SkillLoader:
    """Skill 加载器

    用法:
        loader = SkillLoader(skills_dir="./skills")
        loader.discover_all()
        relevant = loader.get_relevant_skills(event_type="player_move", user_input="探索森林")
        contents = [loader.load_activation(s.name) for s in relevant]
    """

    def __init__(self, skills_dir: str | Path | None = None):
        self._skills_dir = Path(skills_dir) if skills_dir else None
        self._skills: dict[str, Skill] = {}
        self._discovered = False

    def discover_all(self) -> list[str]:
        """扫描目录，发现所有 Skill

        目录结构: skills/skill_name/SKILL.md

        Returns:
            发现的 Skill 名称列表
        """
        if not self._skills_dir or not self._skills_dir.exists():
            logger.warning(f"Skill 目录不存在: {self._skills_dir}")
            return []

        self._skills.clear()
        for skill_dir in sorted(self._skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                skill = self._load_skill_file(skill_file)
                self._skills[skill.metadata.name] = skill
                logger.debug(f"发现 Skill: {skill.metadata.name}")
            except Exception as e:
                logger.error(f"加载 Skill 失败 ({skill_file}): {e}")

        self._discovered = True
        logger.info(f"发现 {len(self._skills)} 个 Skill")
        return list(self._skills.keys())

    def get_relevant_skills(
        self,
        event_type: str = "",
        user_input: str = "",
        context_hints: list[str] | None = None,
        max_skills: int = 5,
    ) -> list[Skill]:
        """评分匹配相关 Skill

        评分规则:
        - event_type 匹配: +10 分
        - keyword 匹配: +5 分/关键词
        - context_hint 匹配: +3 分/提示
        - triggers 为空（始终加载）: +100 分

        Args:
            event_type: 事件类型
            user_input: 用户输入
            context_hints: 上下文提示
            max_skills: 最大返回数量

        Returns:
            按评分排序的 Skill 列表
        """
        if not self._discovered:
            self.discover_all()

        scored: list[tuple[int, Skill]] = []
        input_lower = user_input.lower()
        hints = set(context_hints or [])

        for skill in self._skills.values():
            score = 0
            meta = skill.metadata

            # 始终加载的 Skill（如 narration）
            if not meta.triggers and not meta.keywords:
                score += 100

            # event_type 匹配
            for trigger in meta.triggers:
                if trigger.get("event_type") == event_type:
                    score += 10

            # keyword 匹配
            for keyword in meta.keywords:
                if keyword.lower() in input_lower:
                    score += 5

            # context_hint 匹配
            for tag in meta.tags:
                if tag in hints:
                    score += 3

            if score > 0:
                scored.append((score, skill))

        # 按评分降序排序
        scored.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in scored[:max_skills]]

    def load_activation(self, skill_name: str, max_chars: int = 2000) -> str:
        """加载 Skill 的激活层内容

        返回: YAML 关键字段 + Markdown Body 前 N 字符
        """
        skill = self._skills.get(skill_name)
        if not skill:
            return ""

        parts = [f"**{skill.metadata.name}** (v{skill.metadata.version})"]
        parts.append(f"描述: {skill.metadata.description}")
        if skill.metadata.allowed_tools:
            parts.append(f"可用工具: {', '.join(skill.metadata.allowed_tools)}")
        parts.append("")
        parts.append(skill.content[:max_chars])

        return "\n".join(parts)

    def get_all_skill_names(self) -> list[str]:
        """获取所有 Skill 名称"""
        if not self._discovered:
            self.discover_all()
        return list(self._skills.keys())

    def _load_skill_file(self, filepath: Path) -> Skill:
        """从 SKILL.md 文件加载 Skill"""
        content = filepath.read_text(encoding="utf-8")

        # 解析 YAML Front Matter
        metadata = SkillMetadata(name=filepath.parent.name)
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                import yaml
                try:
                    front_matter = yaml.safe_load(content[3:end]) or {}
                    metadata = SkillMetadata(
                        name=front_matter.get("name", filepath.parent.name),
                        description=front_matter.get("description", ""),
                        version=str(front_matter.get("version", "1.0.0")),
                        tags=front_matter.get("tags", []),
                        allowed_tools=front_matter.get("allowed-tools", []),
                        triggers=front_matter.get("triggers", []),
                        keywords=front_matter.get("keywords", []),
                    )
                    content = content[end + 3:].strip()
                except Exception as e:
                    logger.warning(f"解析 YAML Front Matter 失败: {e}")

        return Skill(metadata=metadata, content=content)
