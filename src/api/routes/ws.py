"""WebSocket 路由 - 实时双向通信"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.agent.game_master import GameMaster
from src.services.llm_client import LLMClient
from src.models import world_repo
from src.utils.logger import get_logger
from src.api.connection_manager import manager

logger = get_logger(__name__)
router = APIRouter()


@router.websocket("/ws/worlds/{world_id}")
async def game_websocket(websocket: WebSocket, world_id: int):
    """游戏 WebSocket 连接

    消息格式:
    客户端→服务端: {"type": "action", "content": "玩家输入"}
    服务端→客户端: {"type": "narrative", "content": "文本片段"}
    服务端→客户端: {"type": "system", "content": "系统消息"}
    """
    await manager.connect(world_id, websocket)
    logger.info(f"WebSocket 连接: world_id={world_id}")

    # 初始化 GameMaster
    world = world_repo.get_world(world_id)
    if not world:
        await websocket.send_json({"type": "system", "content": f"世界{world_id}不存在"})
        await websocket.close()
        manager.disconnect(world_id, websocket)
        return

    from src.services.database import get_db
    with get_db() as conn:
        row = conn.execute("SELECT id FROM players WHERE world_id = ? LIMIT 1", (world_id,)).fetchone()
    if not row:
        await websocket.send_json({"type": "system", "content": "世界中没有玩家"})
        await websocket.close()
        manager.disconnect(world_id, websocket)
        return

    gm = GameMaster(world_id, row["id"], LLMClient())

    try:
        await websocket.send_json({"type": "system", "content": f"已连接到世界: {world['name']}"})

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "system", "content": "无效的JSON格式"})
                continue

            msg_type = msg.get("type", "action")
            content = msg.get("content", "")

            if msg_type == "action" and content.strip():
                try:
                    # 处理并流式发送
                    for chunk in gm.process_stream(content):
                        await websocket.send_json({
                            "type": "narrative",
                            "content": chunk,
                        })
                except Exception as e:
                    logger.error(f"处理消息失败: {e}")
                    await websocket.send_json({"type": "system", "content": f"处理失败: {e}"})
            else:
                await websocket.send_json({"type": "system", "content": "未知消息类型"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: world_id={world_id}")
        manager.disconnect(world_id, websocket)
