"""
SSE 流式推送端点。
WorkBench 通过此端点实时订阅 Agent 的输出。
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sse"])

# Agent 实例引用，由 app.py 启动时注入
_event_handler = None


def set_sse_refs(event_handler):
    """注入 EventHandler 引用"""
    global _event_handler
    _event_handler = event_handler


@router.get("/api/agent/stream")
async def agent_stream(
    session_id: str = Query("default", description="会话 ID"),
    last_event_id: Optional[str] = Query(None, description="断线重连的 Last-Event-ID"),
):
    """
    Agent 实时输出流。

    事件类型:
    - turn_start: 回合开始
    - token: 叙事文本 token（逐字推送）
    - reasoning: 思考过程 token
    - command: 单条指令（narrative 完成后发送）
    - memory_update: 单条记忆更新
    - command_rejected: 指令被引擎拒绝
    - turn_end: 回合结束（含统计信息）
    - error: 错误信息
    - heartbeat: 心跳保活

    支持 Last-Event-ID 断线重连。
    """
    if _event_handler is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return StreamingResponse(
        _generate_events(session_id, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


async def _generate_events(
    session_id: str,
    last_event_id: Optional[str] = None,
):
    """
    生成 SSE 事件流。

    通过注册 SSE 回调到 EventHandler，实时接收 Agent 事件。
    使用 asyncio.Queue 实现跨协程的事件传递。
    """
    event_queue: asyncio.Queue[dict | None] = asyncio.Queue()
    event_index = int(last_event_id) + 1 if last_event_id else 0

    # 注册 SSE 回调
    async def on_sse_event(event_name: str, data: dict):
        await event_queue.put({"event": event_name, "data": data})

    # 检查并调用 register_sse_callback
    if hasattr(_event_handler, 'register_sse_callback'):
        _event_handler.register_sse_callback(on_sse_event)
    else:
        # 如果没有该方法，创建一个模拟的回调列表
        if not hasattr(_event_handler, '_sse_callbacks'):
            _event_handler._sse_callbacks = []
        _event_handler._sse_callbacks.append(on_sse_event)

    try:
        while True:
            try:
                # 等待事件，60 秒超时发送心跳
                item = await asyncio.wait_for(event_queue.get(), timeout=60.0)

                if item is None:
                    # None 表示结束信号
                    break

                # SSE 格式: event: <event_name>\ndata: <json>\n\n
                event_line = f"event: {item['event']}\n"
                data_line = f"data: {json.dumps(item['data'], ensure_ascii=False)}\n"
                id_line = f"id: {event_index}\n"
                yield event_line + data_line + id_line + "\n"
                event_index += 1

            except asyncio.TimeoutError:
                # 心跳保活
                heartbeat = f"event: heartbeat\ndata: \"\"\nid: {event_index}\n\n"
                yield heartbeat
                event_index += 1

    except asyncio.CancelledError:
        logger.info(f"SSE stream cancelled for session {session_id}")
    finally:
        # 移除回调
        try:
            if hasattr(_event_handler, '_sse_callbacks'):
                _event_handler._sse_callbacks.remove(on_sse_event)
        except (ValueError, AttributeError):
            pass
