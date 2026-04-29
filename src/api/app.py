"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path

app = FastAPI(
    title="游戏大师 Agent API",
    description="AI驱动的RPG游戏Master API，提供游戏世界管理、玩家交互、NPC对话、任务系统等功能",
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "世界管理", "description": "游戏世界的创建、查询、删除"},
        {"name": "玩家", "description": "玩家信息查询和更新"},
        {"name": "游戏行动", "description": "核心游戏交互接口"},
        {"name": "WebSocket", "description": "实时通信接口"},
        {"name": "管理端", "description": "GM管理后台接口"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册异常处理器
from src.api.exceptions import GameError, game_error_handler
app.add_exception_handler(GameError, game_error_handler)

# 注册路由
from src.api.routes.worlds import router as worlds_router
from src.api.routes.player import router as player_router
from src.api.routes.action import router as action_router
from src.api.routes.ws import router as ws_router

app.include_router(worlds_router)
app.include_router(player_router)
app.include_router(action_router)
app.include_router(ws_router)

# 管理端路由
from src.api.routes.admin_prompts import router as admin_prompts_router
from src.api.routes.admin_monitor import router as admin_monitor_router
from src.api.routes.admin_data import router as admin_data_router
from src.api.routes.admin_logs import router as admin_logs_router
from src.api.routes.admin_control import router as admin_control_router

app.include_router(admin_prompts_router)
app.include_router(admin_monitor_router)
app.include_router(admin_data_router)
app.include_router(admin_logs_router)
app.include_router(admin_control_router)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


# 静态文件服务（放在所有路由之后）
web_dir = Path(__file__).parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

# 管理端静态文件（如果存在）
admin_dist = Path(__file__).parent.parent / "admin" / "dist"
if admin_dist.exists():
    app.mount("/admin", StaticFiles(directory=str(admin_dist), html=True), name="admin")


def run_server():
    """启动服务器"""
    import uvicorn
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)
