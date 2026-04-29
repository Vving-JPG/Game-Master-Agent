"""管理端 - Prompt 管理路由"""
from fastapi import APIRouter
from pydantic import BaseModel
from src.models import prompt_repo

router = APIRouter(prefix="/api/admin/prompts", tags=["管理端-Prompt"])


class PromptUpdate(BaseModel):
    prompt_key: str
    content: str


class PromptRollback(BaseModel):
    prompt_key: str
    version: int


@router.get("/{prompt_key}")
def get_prompt(prompt_key: str):
    """获取当前活跃 Prompt"""
    content = prompt_repo.get_active_prompt(prompt_key)
    if not content:
        return {"prompt_key": prompt_key, "content": "", "version": 0, "message": "无活跃版本，使用默认"}
    return {"prompt_key": prompt_key, "content": content}


@router.post("")
def update_prompt(body: PromptUpdate):
    """更新 Prompt（立即生效）"""
    version_id = prompt_repo.save_prompt(body.prompt_key, body.content)
    return {"message": f"Prompt 已更新", "version_id": version_id}


@router.get("/{prompt_key}/history")
def get_history(prompt_key: str):
    """获取版本历史"""
    return prompt_repo.get_prompt_history(prompt_key)


@router.post("/rollback")
def rollback(body: PromptRollback):
    """回滚到指定版本"""
    prompt_repo.rollback_prompt(body.prompt_key, body.version)
    return {"message": f"已回滚到版本 {body.version}"}
