"""
Agent 交互 API。
提供事件发送、状态查询、上下文查看、中断、重置端点。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Agent 实例引用，由 app.py 启动时注入
_event_handler = None
_game_master = None
_engine_adapter = None


def set_agent_refs(event_handler, game_master, engine_adapter):
    """注入 Agent 实例引用"""
    global _event_handler, _game_master, _engine_adapter
    _event_handler = event_handler
    _game_master = game_master
    _engine_adapter = engine_adapter


class EventRequest(BaseModel):
    """引擎事件请求"""
    event_id: str
    timestamp: str
    type: str
    data: dict
    context_hints: list[str] = []
    game_state: dict = {}


@router.post("/event")
async def send_event(body: EventRequest) -> dict:
    """
    手动发送引擎事件（调试用）。
    调用 EventHandler 处理事件，返回完整响应。
    """
    if _event_handler is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if _event_handler.is_processing:
        raise HTTPException(status_code=429, detail="Agent is processing another event")

    from src.adapters.base import EngineEvent

    event = EngineEvent(
        event_id=body.event_id,
        timestamp=body.timestamp,
        type=body.type,
        data=body.data,
        context_hints=body.context_hints,
        game_state=body.game_state,
    )

    response = await _event_handler.handle_event(event)
    return response


@router.get("/status")
async def get_status() -> dict:
    """获取 Agent 当前状态"""
    if _game_master is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return {
        "state": "processing" if _event_handler and _event_handler.is_processing else "idle",
        "turn_count": _game_master.turn_count,
        "total_tokens": _game_master.total_tokens,
        "history_length": len(_game_master.history) // 2,  # 每 2 条消息 = 1 轮
        "current_event": (
            _event_handler.current_event.type
            if _event_handler and _event_handler.current_event
            else None
        ),
    }


@router.get("/context")
async def get_context() -> dict:
    """
    获取当前上下文（调试用）。
    返回 system prompt、加载的记忆文件、激活的 Skill。
    """
    if _game_master is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    builder = _game_master.prompt_builder

    return {
        "system_prompt": builder.load_system_prompt(),
        "system_prompt_length": len(builder.load_system_prompt()),
        "history_length": len(_game_master.history),
        "active_skills": [],  # 需要从最近一次 build 调用中获取
    }


@router.post("/interrupt")
async def interrupt_agent() -> dict:
    """中断当前回合"""
    if _event_handler is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if not _event_handler.is_processing:
        return {"status": "ok", "message": "Agent is not processing"}

    # TODO: 实现真正的中断机制（需要 asyncio.CancelledError 或 threading.Event）
    return {"status": "ok", "message": "Interrupt signal sent"}


@router.post("/reset")
async def reset_session() -> dict:
    """重置 Agent 会话"""
    if _game_master is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    _game_master.reset()
    return {"status": "ok", "message": "Session reset"}


@router.post("/control")
async def control_agent(action: str):
    """
    控制 Agent 执行: pause / resume / step
    """
    if _game_master is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if action == "pause":
        _game_master.pause()
    elif action == "resume":
        _game_master.resume()
    elif action == "step":
        _game_master.step_once()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    return {"state": _game_master.execution_state.value}


@router.get("/workflow")
async def get_workflow():
    """获取当前工作流定义"""
    if _game_master is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    workflow = _game_master.workflow
    return {
        "state": workflow.state.value,
        "current_step": workflow.current_step_id,
        "steps": [
            {
                "id": s.id,
                "type": s.type.value,
                "next": s.next,
                "conditions": s.conditions,
            }
            for s in workflow.steps.values()
        ],
    }


class InjectRequest(BaseModel):
    """指令注入请求"""
    level: str = "user"  # system / user / override
    content: str


@router.post("/inject")
async def inject_instruction(body: InjectRequest) -> dict:
    """
    注入指令到 Agent。
    level: system / user / override
    """
    if _game_master is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content is required")

    # 构造注入事件
    from src.adapters.base import EngineEvent
    from datetime import datetime

    event = EngineEvent(
        event_id=f"inject_{_game_master.turn_count + 1}",
        timestamp=datetime.now().isoformat(),
        type="player_action",
        data={"raw_text": body.content, "player_id": "debug", "inject_level": body.level},
        context_hints=[],
        game_state={},
    )

    # 异步处理
    response = await _event_handler.handle_event(event)

    return {
        "status": "injected",
        "level": body.level,
        "response_id": response.get("response_id"),
    }
