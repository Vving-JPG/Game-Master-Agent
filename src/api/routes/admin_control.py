"""管理端 - GM 参数控制路由"""
from fastapi import APIRouter
from pydantic import BaseModel
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/admin/control", tags=["管理端-控制"])

# 运行时参数（全局可修改）
runtime_config = {
    "temperature": 0.7,
    "max_tool_rounds": 10,
    "max_context_messages": 100,
    "paused": False,
}


class ConfigUpdate(BaseModel):
    temperature: float | None = None
    max_tool_rounds: int | None = None
    max_context_messages: int | None = None
    paused: bool | None = None


@router.get("/config")
def get_config():
    """获取当前运行时配置"""
    return runtime_config


@router.post("/config")
def update_config(body: ConfigUpdate):
    """更新运行时配置（立即生效）"""
    updates = body.model_dump(exclude_none=True)
    runtime_config.update(updates)
    logger.info(f"GM 配置已更新: {updates}")
    return {"message": "配置已更新", "config": runtime_config}


@router.post("/pause")
def pause_gm():
    """暂停 GM（拒绝新请求）"""
    runtime_config["paused"] = True
    return {"message": "GM 已暂停"}


@router.post("/resume")
def resume_gm():
    """恢复 GM"""
    runtime_config["paused"] = False
    return {"message": "GM 已恢复"}
