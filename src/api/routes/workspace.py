"""
Workspace 文件操作 API。
提供文件树浏览、文件读取/创建/更新/删除端点。
"""
from __future__ import annotations

import frontmatter
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from src.memory.file_io import atomic_write

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

# Workspace 根路径，由 app.py 启动时注入
WORKSPACE_PATH: Path = Path("./workspace")


def set_workspace_path(path: str):
    """设置 workspace 根路径"""
    global WORKSPACE_PATH
    WORKSPACE_PATH = Path(path)


class FileUpdateRequest(BaseModel):
    """文件更新请求"""
    path: str
    frontmatter: Optional[dict] = None
    content: Optional[str] = None
    raw: Optional[str] = None


class FileCreateRequest(BaseModel):
    """文件创建请求"""
    path: str
    content: str = ""


@router.get("/tree")
async def get_tree(
    path: str = Query("", description="目录路径，空为根目录")
) -> dict:
    """
    获取目录结构。
    返回子项列表，每个子项包含 name, path, type, size。
    跳过隐藏文件和临时文件。
    """
    target = WORKSPACE_PATH / path if path else WORKSPACE_PATH

    if not target.exists() or not target.is_dir():
        return {"children": []}

    children = []
    for item in sorted(target.iterdir()):
        if item.name.startswith(".") or item.name.startswith("~"):
            continue

        rel_path = str(item.relative_to(WORKSPACE_PATH)).replace("\\", "/")
        children.append({
            "name": item.name,
            "path": rel_path,
            "type": "file" if item.is_file() else "directory",
            "size": item.stat().st_size if item.is_file() else None,
        })

    return {"children": children}


@router.get("/file")
async def get_file(
    path: str = Query(..., description="文件相对路径")
) -> dict:
    """
    读取文件内容。
    YAML Front Matter 和 Markdown Body 分离返回。
    """
    file_path = WORKSPACE_PATH / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    try:
        post = frontmatter.load(str(file_path))
        return {
            "frontmatter": dict(post.metadata),
            "content": post.content,
            "raw": frontmatter.dumps(post),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {e}")


@router.put("/file")
async def update_file(body: FileUpdateRequest) -> dict:
    """
    更新文件。
    支持两种模式:
    1. raw 模式: 直接写入原始内容
    2. 分离模式: 分别更新 frontmatter 和 content
    """
    file_path = WORKSPACE_PATH / body.path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {body.path}")

    try:
        if body.raw is not None:
            atomic_write(str(file_path), body.raw)
        else:
            post = frontmatter.load(str(file_path))
            if body.frontmatter:
                for key, value in body.frontmatter.items():
                    post[key] = value
            if body.content is not None:
                post.content = body.content
            atomic_write(str(file_path), frontmatter.dumps(post))

        return {"status": "ok", "path": body.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update file: {e}")


@router.post("/file")
async def create_file(body: FileCreateRequest) -> dict:
    """创建新文件"""
    file_path = WORKSPACE_PATH / body.path

    if file_path.exists():
        raise HTTPException(status_code=409, detail=f"File already exists: {body.path}")

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(str(file_path), body.content)
        return {"status": "ok", "path": body.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create file: {e}")


@router.delete("/file")
async def delete_file(
    path: str = Query(..., description="文件相对路径")
) -> dict:
    """删除文件"""
    file_path = WORKSPACE_PATH / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        file_path.unlink()
        return {"status": "ok", "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")
