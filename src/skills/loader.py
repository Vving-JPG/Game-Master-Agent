"""
Skill 发现与加载器。
扫描 skills/ 目录，发现和匹配 SKILL.md 文件。
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import frontmatter


@dataclass
class SkillMetadata:
    """Skill 元数据"""
    name: str
    description: str
    version: str
    tags: list[str] = field(default_factory=list)
    triggers: list[dict] = field(default_factory=list)
    file_path: str = ""
    source: str = ""


class SkillLoader:
    """Skill 发现与加载器"""

    def __init__(self, skills_path: str):
        self.skills_path = Path(skills_path)
        self._cache: dict[str, SkillMetadata] = {}

    def discover_all(self) -> list[SkillMetadata]:
        """发现所有 Skill（带缓存）"""
        if self._cache:
            return list(self._cache.values())
        skills = []
        for skill_dir in self._skills_dirs():
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            post = frontmatter.load(str(skill_md))
            metadata = SkillMetadata(
                name=post.get("name", skill_dir.name),
                description=post.get("description", ""),
                version=post.get("version", "0.0.0"),
                tags=post.get("tags", []),
                triggers=post.get("triggers", []),
                file_path=str(skill_md),
                source="builtin" if "builtin" in str(skill_dir) else "agent_created"
            )
            self._cache[metadata.name] = metadata
            skills.append(metadata)
        return skills

    def get_relevant_skills(
        self,
        event_type: str = None,
        user_input: str = None,
        context_hints: list[str] = None
    ) -> list[SkillMetadata]:
        """根据事件匹配相关 Skill，按相关度排序"""
        all_skills = self.discover_all()
        relevant = []
        for skill in all_skills:
            score = 0
            for trigger in skill.triggers:
                if event_type and trigger.get("event_type") == event_type:
                    score += 10
                if user_input and "keyword" in trigger:
                    keywords = trigger["keyword"]
                    if isinstance(keywords, str):
                        keywords = [keywords]
                    for kw in keywords:
                        if kw in user_input:
                            score += 5
                if context_hints and "memory_hint" in trigger:
                    hints = trigger["memory_hint"]
                    if isinstance(hints, str):
                        hints = [hints]
                    for hint in hints:
                        if any(hint in ch for ch in context_hints):
                            score += 3
            if score > 0:
                relevant.append((skill, score))
        relevant.sort(key=lambda x: x[1], reverse=True)
        return [skill for skill, score in relevant]

    def load_skill_content(self, skill_name: str) -> Optional[str]:
        """加载 Skill 的完整 Markdown Body"""
        if skill_name not in self._cache:
            return None
        post = frontmatter.load(self._cache[skill_name].file_path)
        return post.content

    def load_skill_activation(self, skill_name: str) -> Optional[str]:
        """加载 Skill 的激活层（YAML 关键字段 + 前 2000 字符）"""
        if skill_name not in self._cache:
            return None
        skill = self._cache[skill_name]
        post = frontmatter.load(skill.file_path)
        info_lines = [
            f"## Skill: {skill.name} (v{skill.version})",
            f"**描述**: {skill.description}",
        ]
        if skill.tags:
            info_lines.append(f"**标签**: {', '.join(skill.tags)}")
        allowed_tools = post.get("allowed-tools", [])
        if allowed_tools:
            info_lines.append(f"**可用指令**: {', '.join(allowed_tools)}")
        body_preview = post.content[:2000]
        if len(post.content) > 2000:
            body_preview += "\n\n... (内容已截断)"
        return "\n".join(info_lines) + "\n\n" + body_preview

    def invalidate_cache(self):
        """清除缓存"""
        self._cache.clear()

    def _skills_dirs(self) -> list[Path]:
        """获取所有 Skill 目录"""
        dirs = []
        for root_dir in ["builtin", "agent_created"]:
            base = self.skills_path / root_dir
            if base.exists():
                for d in base.iterdir():
                    if d.is_dir():
                        dirs.append(d)
        return dirs
