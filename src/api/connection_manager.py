"""WebSocket 连接管理器"""
from fastapi import WebSocket
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """管理 WebSocket 连接"""

    def __init__(self):
        # {world_id: set[WebSocket]}
        self.active_connections: dict[int, set[WebSocket]] = {}

    async def connect(self, world_id: int, websocket: WebSocket):
        await websocket.accept()
        if world_id not in self.active_connections:
            self.active_connections[world_id] = set()
        self.active_connections[world_id].add(websocket)
        logger.info(f"客户端连接到世界{world_id}，当前连接数: {len(self.active_connections[world_id])}")

    def disconnect(self, world_id: int, websocket: WebSocket):
        if world_id in self.active_connections:
            self.active_connections[world_id].discard(websocket)
            if not self.active_connections[world_id]:
                del self.active_connections[world_id]
        logger.info(f"客户端断开世界{world_id}")

    async def broadcast(self, world_id: int, message: dict):
        """广播消息给世界中的所有客户端"""
        if world_id not in self.active_connections:
            return
        dead = []
        for ws in self.active_connections[world_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(world_id, ws)

    def get_connection_count(self, world_id: int) -> int:
        return len(self.active_connections.get(world_id, set()))


# 全局连接管理器
manager = ConnectionManager()
