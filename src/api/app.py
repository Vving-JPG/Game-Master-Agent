"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

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

app.include_router(worlds_router)
app.include_router(player_router)

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

# === V2 路由注册 ===
from src.api.routes.workspace import router as workspace_router, set_workspace_path
from src.api.routes.skills import router as skills_router, set_skills_path
from src.api.routes.agent import router as agent_router, set_agent_refs
from src.api.sse import router as sse_router, set_sse_refs

# 设置路径
set_workspace_path("./workspace")
set_skills_path("./skills")

# 注册路由
app.include_router(workspace_router)
app.include_router(skills_router)
app.include_router(agent_router)
app.include_router(sse_router)

# Pack 路由（agent-pack 导入/导出）
from src.api.routes.pack import router as pack_router
app.include_router(pack_router)

# === V2 Agent 初始化 ===
def init_v2_agent():
    """初始化 V2 Agent 组件"""
    try:
        from src.agent.game_master import GameMaster
        from src.agent.event_handler import EventHandler
        from src.adapters.base import EngineAdapter, EngineEvent, CommandResult, ConnectionStatus
        from src.services.llm_client import LLMClient
        from src.memory.manager import MemoryManager
        from src.skills.loader import SkillLoader

        # Mock 适配器（用于前端开发测试）
        class MockAdapter(EngineAdapter):
            @property
            def name(self) -> str:
                return "mock"

            @property
            def connection_status(self) -> ConnectionStatus:
                return ConnectionStatus.CONNECTED

            async def connect(self, **kwargs) -> None:
                pass

            async def disconnect(self) -> None:
                pass

            async def send_commands(self, commands: list[dict]) -> list[CommandResult]:
                return [CommandResult(intent=cmd.get("intent", "no_op"), status="success") for cmd in commands]

            async def subscribe_events(self, event_types: list[str], callback) -> None:
                pass

            async def query_state(self, query: dict) -> dict:
                return {"status": "ok"}

        # 初始化适配器
        engine_adapter = MockAdapter()

        # 初始化 LLMClient
        llm_client = LLMClient()

        # 初始化 MemoryManager
        memory_manager = MemoryManager(workspace_path="./workspace")

        # 初始化 SkillLoader
        skill_loader = SkillLoader(skills_path="./skills")

        # 初始化 GameMaster
        game_master = GameMaster(
            llm_client=llm_client,
            memory_manager=memory_manager,
            skill_loader=skill_loader,
            engine_adapter=engine_adapter,
            system_prompt_path="./prompts/system_prompt.md"
        )

        # 初始化 EventHandler
        event_handler = EventHandler(game_master, engine_adapter)

        # 注入引用
        set_agent_refs(event_handler, game_master, engine_adapter)
        set_sse_refs(event_handler)

        print("[OK] V2 Agent initialized successfully")
        return True
    except Exception as e:
        print(f"[WARN] V2 Agent initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# 启动时初始化
init_v2_agent()


@app.get("/")
def root():
    """根路由 - 重定向到 API 文档"""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok"}


def run_server():
    """启动服务器"""
    import uvicorn
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)
