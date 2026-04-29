"""玩家路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.models import player_repo, world_repo, item_repo

router = APIRouter(prefix="/api/worlds/{world_id}", tags=["玩家"])


class PlayerUpdate(BaseModel):
    hp: int | None = None
    mp: int | None = None
    gold: int | None = None
    level: int | None = None


class EquipRequest(BaseModel):
    item_id: int
    slot: str


def _get_player_id(world_id: int) -> int:
    """获取世界中第一个玩家的ID"""
    from src.services.database import get_db
    with get_db() as conn:
        row = conn.execute("SELECT id FROM players WHERE world_id = ? LIMIT 1", (world_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"世界{world_id}中没有玩家")
    return row["id"]


@router.get("/player")
def get_player(world_id: int):
    """获取玩家信息"""
    pid = _get_player_id(world_id)
    player = player_repo.get_player(pid)
    if not player:
        raise HTTPException(status_code=404, detail="玩家不存在")
    return player


@router.patch("/player")
def update_player(world_id: int, body: PlayerUpdate):
    """更新玩家属性"""
    pid = _get_player_id(world_id)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="没有指定要更新的属性")
    player_repo.update_player(pid, **updates)
    return {"message": "玩家属性已更新", "updates": updates}


@router.get("/inventory")
def get_inventory(world_id: int):
    """获取背包"""
    pid = _get_player_id(world_id)
    items = player_repo.get_inventory(pid)
    return items


@router.post("/player/equip")
def equip_item(world_id: int, body: EquipRequest):
    """装备物品"""
    pid = _get_player_id(world_id)
    from src.models import equipment_repo
    equipment_repo.equip_item(pid, body.item_id, body.slot)
    return {"message": f"已装备到{body.slot}槽位"}
