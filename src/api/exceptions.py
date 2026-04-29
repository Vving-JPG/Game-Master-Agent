"""自定义异常和全局错误处理"""
from fastapi import Request
from fastapi.responses import JSONResponse


class GameError(Exception):
    """游戏逻辑错误"""
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code


class WorldNotFound(GameError):
    def __init__(self, world_id: int):
        super().__init__(f"世界{world_id}不存在", 404)


class InvalidAction(GameError):
    def __init__(self, message: str = "无效的行动"):
        super().__init__(message, 400)


class CombatError(GameError):
    def __init__(self, message: str = "战斗出错"):
        super().__init__(message, 409)


async def game_error_handler(request: Request, exc: GameError):
    """全局异常处理器"""
    return JSONResponse(
        status_code=exc.code,
        content={"error": exc.message, "code": exc.code},
    )
