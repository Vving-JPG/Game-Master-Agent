"""世界管理路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.models import world_repo
from src.data.seed_data import seed_world

router = APIRouter(prefix="/api/worlds", tags=["世界管理"])


class WorldCreate(BaseModel):
    name: str = "新世界"
    setting: str = "奇幻世界"


@router.get("")
def list_worlds():
    """列出所有世界"""
    worlds = world_repo.list_worlds()
    return [{"id": w["id"], "name": w["name"], "setting": w["setting"], "created_at": w.get("created_at", "")} for w in worlds]


@router.post("")
def create_world(body: WorldCreate):
    """创建新世界"""
    result = seed_world()
    return {"id": result["world_id"], "name": body.name, "setting": body.setting}


@router.get("/{world_id}")
def get_world(world_id: int):
    """获取世界详情"""
    world = world_repo.get_world(world_id)
    if not world:
        raise HTTPException(status_code=404, detail=f"世界{world_id}不存在")
    return world


@router.delete("/{world_id}")
def delete_world(world_id: int):
    """删除世界"""
    world = world_repo.get_world(world_id)
    if not world:
        raise HTTPException(status_code=404, detail=f"世界{world_id}不存在")
    world_repo.delete_world(world_id)
    return {"message": f"世界{world_id}已删除"}
