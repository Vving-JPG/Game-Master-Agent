"""管理端 - 游戏数据管理路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.models import npc_repo, quest_repo, item_repo, world_repo, player_repo

router = APIRouter(prefix="/api/admin/data", tags=["管理端-数据"])


# ===== NPC 管理 =====
@router.get("/npcs")
def list_npcs(world_id: int):
    from src.models import location_repo
    npcs = []
    for loc in location_repo.get_locations_by_world(world_id):
        npcs.extend(npc_repo.get_npcs_by_location(loc["id"]))
    return npcs

@router.delete("/npcs/{npc_id}")
def delete_npc(npc_id: int):
    npc_repo.delete_npc(npc_id)
    return {"message": f"NPC {npc_id} 已删除"}

# ===== 任务管理 =====
@router.get("/quests")
def list_quests(world_id: int):
    return quest_repo.get_quests_by_world(world_id)

@router.patch("/quests/{quest_id}")
def update_quest(quest_id: int, status: str | None = None):
    if status:
        quest_repo.update_quest(quest_id, status=status)
    return {"message": "任务已更新"}

@router.delete("/quests/{quest_id}")
def delete_quest(quest_id: int):
    quest_repo.delete_quest(quest_id)
    return {"message": f"任务 {quest_id} 已删除"}

# ===== 道具管理 =====
@router.get("/items")
def list_items(world_id: int):
    return item_repo.get_items_by_world(world_id)

@router.delete("/items/{item_id}")
def delete_item(item_id: int):
    item_repo.delete_item(item_id)
    return {"message": f"道具 {item_id} 已删除"}

# ===== 玩家管理 =====
@router.get("/players")
def list_players(world_id: int):
    from src.services.database import get_db
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM players WHERE world_id = ?", (world_id,)).fetchall()
    return [dict(r) for r in rows]

@router.patch("/players/{player_id}")
def update_player(player_id: int, hp: int | None = None, gold: int | None = None,
                  level: int | None = None, exp: int | None = None):
    updates = {}
    if hp is not None: updates["hp"] = hp
    if gold is not None: updates["gold"] = gold
    if level is not None: updates["level"] = level
    if exp is not None: updates["exp"] = exp
    if updates:
        player_repo.update_player(player_id, **updates)
    return {"message": "玩家已更新", "updates": updates}
