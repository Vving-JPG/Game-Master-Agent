"""游戏行动路由 - 核心交互"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.agent.game_master import GameMaster
from src.services.llm_client import LLMClient
from src.models import world_repo
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/worlds/{world_id}", tags=["游戏行动"])

# 缓存 GameMaster 实例
_gm_cache: dict[int, GameMaster] = {}


class ActionRequest(BaseModel):
    content: str
    stream: bool = False


def _get_gm(world_id: int) -> GameMaster:
    """获取或创建 GameMaster 实例"""
    if world_id not in _gm_cache:
        world = world_repo.get_world(world_id)
        if not world:
            raise HTTPException(status_code=404, detail=f"世界{world_id}不存在")
        from src.services.database import get_db
        with get_db() as conn:
            row = conn.execute("SELECT id FROM players WHERE world_id = ? LIMIT 1", (world_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="世界中没有玩家")
        _gm_cache[world_id] = GameMaster(world_id, row["id"], LLMClient())
    return _gm_cache[world_id]


@router.post("/action")
def game_action(world_id: int, body: ActionRequest):
    """玩家行动 → GM回复"""
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="输入不能为空")

    gm = _get_gm(world_id)
    try:
        reply = gm.process(body.content)
        return {"reply": reply}
    except Exception as e:
        logger.error(f"处理行动失败: {e}")
        raise HTTPException(status_code=500, detail=f"GM处理失败: {e}")
