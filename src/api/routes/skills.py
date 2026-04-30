"""
Skill 管理 API。
提供 Skill 的列表、读取、创建、更新、删除端点。
"""
from __future__ import annotations

import frontmatter
from fastapi import APIRouter, HTTPException
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from src.memory.file_io import atomic_write

router = APIRouter(prefix="/api/skills", tags=["skills"])

# Skills 根路径，由 app.py 启动时注入
SKILLS_PATH: Path = Path("./skills")


def set_skills_path(path: str):
    """设置 skills 根路径"""
    global SKILLS_PATH
    SKILLS_PATH = Path(path)


class SkillUpdateRequest(BaseModel):
    """Skill 更新请求"""
    content: str


class SkillCreateRequest(BaseModel):
    """Skill 创建请求"""
    name: str
    content: str
    source: str = "agent_created"


@router.get("")
async def list_skills() -> list[dict]:
    """
    列出所有 Skill。
    返回每个 Skill 的元数据（YAML Front Matter）。
    """
    skills = []

    if not SKILLS_PATH.exists():
        return skills

    # 扫描 builtin 和 agent_created 目录
    for source_dir in ["builtin", "agent_created"]:
        source_path = SKILLS_PATH / source_dir
        if not source_path.exists():
            continue

        for skill_dir in sorted(source_path.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                post = frontmatter.load(str(skill_file))
                skills.append({
                    "name": post.get("name", skill_dir.name),
                    "description": post.get("description", ""),
                    "version": post.get("version", "0.0.0"),
                    "tags": post.get("tags", []),
                    "source": source_dir,
                    "file_path": str(skill_file.relative_to(SKILLS_PATH)).replace("\\", "/"),
                })
            except Exception:
                continue

    return skills


@router.get("/{skill_name}")
async def get_skill(skill_name: str) -> dict:
    """读取 Skill 内容"""
    skill_file = _find_skill_file(skill_name)

    if not skill_file:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")

    try:
        post = frontmatter.load(str(skill_file))
        return {
            "frontmatter": dict(post.metadata),
            "content": post.content,
            "raw": frontmatter.dumps(post),
            "file_path": str(skill_file.relative_to(SKILLS_PATH)).replace("\\", "/"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse skill: {e}")


@router.put("/{skill_name}")
async def update_skill(skill_name: str, body: SkillUpdateRequest) -> dict:
    """更新 Skill 内容"""
    skill_file = _find_skill_file(skill_name)

    if not skill_file:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")

    try:
        atomic_write(str(skill_file), body.content)
        return {"status": "ok", "name": skill_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update skill: {e}")


@router.post("")
async def create_skill(body: SkillCreateRequest) -> dict:
    """
    创建新 Skill。
    仅允许在 agent_created 目录下创建。
    """
    if body.source != "agent_created":
        raise HTTPException(
            status_code=403,
            detail="Can only create skills in agent_created directory"
        )

    skill_dir = SKILLS_PATH / "agent_created" / body.name
    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists():
        raise HTTPException(status_code=409, detail=f"Skill already exists: {body.name}")

    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(str(skill_file), body.content)
        return {"status": "ok", "name": body.name, "path": str(skill_file)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create skill: {e}")


@router.delete("/{skill_name}")
async def delete_skill(skill_name: str) -> dict:
    """
    删除 Skill。
    仅允许删除 agent_created 目录下的 Skill。
    """
    skill_file = _find_skill_file(skill_name)

    if not skill_file:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")

    # 检查是否为 builtin（不允许删除）
    rel_path = skill_file.relative_to(SKILLS_PATH)
    parts = rel_path.parts
    if parts[0] == "builtin":
        raise HTTPException(
            status_code=403,
            detail="Cannot delete builtin skills"
        )

    try:
        # 删除整个 skill 目录
        skill_dir = skill_file.parent
        import shutil
        shutil.rmtree(str(skill_dir))
        return {"status": "ok", "name": skill_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete skill: {e}")


def _find_skill_file(skill_name: str) -> Path | None:
    """在 builtin 和 agent_created 目录中查找 Skill 文件"""
    for source_dir in ["builtin", "agent_created"]:
        skill_file = SKILLS_PATH / source_dir / skill_name / "SKILL.md"
        if skill_file.exists():
            return skill_file
    return None
