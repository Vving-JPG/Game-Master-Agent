# Game Master Agent V2 - P2: API 扩展

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户将 V1 的 Game Master Agent **重构为 V2 通用游戏驱动 Agent**。
- **技术栈**: Python 3.11+ / DeepSeek API / FastAPI / SQLite / python-frontmatter
- **包管理器**: uv
- **LLM**: DeepSeek（通过 OpenAI 兼容接口调用）
- **开发IDE**: Trae

### 前置条件

**P1 已完成**。以下模块已就绪：
- `src/agent/command_parser.py` — 4 级容错 JSON 解析
- `src/agent/prompt_builder.py` — Prompt 组装（system + skills + memory + history + event）
- `prompts/system_prompt.md` — Agent 主提示词
- `src/services/llm_client.py` — 已改为 AsyncOpenAI，新增 `stream()` 方法
- `src/agent/game_master.py` — 事件驱动主循环（`handle_event()`）
- `src/agent/event_handler.py` — 事件分发与 SSE 推送
- P0 + P1 全部测试通过（基线 **175+** 个）

### P2 阶段目标

1. **新增 workspace API** — 文件树浏览、文件 CRUD（YAML+MD 分离）
2. **新增 skills API** — Skill 列表、读取、创建、更新、删除
3. **新增 agent API** — 事件发送、状态查询、上下文查看、中断、重置
4. **新增 SSE 端点** — 实时推送 Agent 的 token/command/memory 事件
5. **注册路由** — 将所有新端点挂载到 FastAPI app.py
6. **API 测试** — pytest + TestClient 覆盖所有端点

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行，每完成一步都验证通过后再进行下一步
2. **先验证再继续**：每个步骤都有"验收标准"，必须验证通过才能继续
3. **主动执行**：用户说"开始"后，你应该主动执行每一步，不需要用户反复催促
4. **遇到错误先尝试解决**：如果某步出错，先尝试自行排查修复，3次失败后再询问用户
5. **每步完成后汇报**：完成一步后，简要汇报结果和下一步计划
6. **代码规范**：
   - 所有文件使用 UTF-8 编码
   - Python 文件使用中文注释
   - 遵循 PEP 8 风格
   - 每个模块必须有对应的 pytest 测试文件
   - 使用 `from __future__ import annotations` 启用延迟注解
7. **不要跳步**：即使用户让你跳过，也要提醒风险后再决定
8. **不修改已有模块**：P2 只新增文件和修改 `app.py` 的路由注册，不修改 P0/P1 的代码

## 参考设计文档

以下是 V2 架构设计文档，存放在 `docs/` 目录下。

| 文档 | 内容 |
|------|------|
| `docs/architecture_v2.md` | V2 架构总览、目录结构、技术栈 |
| `docs/communication_protocol.md` | JSON 命令流格式、SSE 推送协议、WorkBench API 定义 |
| `docs/workspace_design.md` | WorkBench UI 设计、后端 API 代码参考 |
| `docs/dev_plan_v2.md` | V2 开发计划总览 |

## V1 经验教训（必须遵守）

1. **PowerShell `&&` 语法**: Windows PowerShell 不支持 `&&`，用 `;` 分隔多条命令
2. **测试隔离**: 每个测试模块用 `teardown_module()` 清理全局状态，防止测试间污染
3. **SQLite datetime('now')**: 同一秒内多次调用返回相同时间戳，测试断言用 `>=` 而非 `==`
4. **中文括号**: 测试代码中一律用英文括号 `()`，不要用中文括号 `（）`
5. **原子写入**: 所有 .md 文件写入必须用 `atomic_write()`，不要直接 `open().write()`
6. **YAML Front Matter 格式**: 用 `python-frontmatter` 库解析，不要手写字符串拼接
7. **DeepSeek reasoning_content**: 用 `getattr(delta, 'reasoning_content', None)` 安全获取
8. **reasoning_content 必须回传**: 同一 Turn 内子请求必须包含 reasoning_content
9. **tool_call_id**: tool 消息必须包含 `tool_call_id`，从 tool_calls[i].id 获取
10. **tool_calls 增量拼接**: 流式模式下 arguments 分片返回，用 dict 按 index 累积拼接
11. **FastAPI SSE**: 使用 `EventSourceResponse` + `ServerSentEvent`（来自 `fastapi.sse`）
12. **httpx-sse**: SSE 端点测试使用 `httpx_sse` 库

---

## P2: API 扩展（共 8 步）

### 步骤 2.1 - 新增 src/api/routes/workspace.py

**目的**: Workspace 文件操作 API（文件树、文件 CRUD）

**设计参考**: `docs/workspace_design.md` 第 4.2 节、`docs/communication_protocol.md` 第 6.1 节

**执行**:
1. 先创建 `src/api/routes/` 目录（如果不存在）
2. 创建 `src/api/routes/__init__.py`
3. 创建 `src/api/routes/workspace.py`

**完整代码**:

```python
"""
Workspace 文件操作 API。
提供文件树浏览、文件读取/创建/更新/删除端点。
"""
from __future__ import annotations

import frontmatter
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from src.memory.file_io import atomic_write

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

# Workspace 根路径，由 app.py 启动时注入
WORKSPACE_PATH: Path = Path("./workspace")


def set_workspace_path(path: str):
    """设置 workspace 根路径"""
    global WORKSPACE_PATH
    WORKSPACE_PATH = Path(path)


class FileUpdateRequest(BaseModel):
    """文件更新请求"""
    path: str
    frontmatter: Optional[dict] = None
    content: Optional[str] = None
    raw: Optional[str] = None


class FileCreateRequest(BaseModel):
    """文件创建请求"""
    path: str
    content: str = ""


@router.get("/tree")
async def get_tree(
    path: str = Query("", description="目录路径，空为根目录")
) -> dict:
    """
    获取目录结构。
    返回子项列表，每个子项包含 name, path, type, size。
    跳过隐藏文件和临时文件。
    """
    target = WORKSPACE_PATH / path if path else WORKSPACE_PATH

    if not target.exists() or not target.is_dir():
        return {"children": []}

    children = []
    for item in sorted(target.iterdir()):
        if item.name.startswith(".") or item.name.startswith("~"):
            continue

        rel_path = str(item.relative_to(WORKSPACE_PATH)).replace("\\", "/")
        children.append({
            "name": item.name,
            "path": rel_path,
            "type": "file" if item.is_file() else "directory",
            "size": item.stat().st_size if item.is_file() else None,
        })

    return {"children": children}


@router.get("/file")
async def get_file(
    path: str = Query(..., description="文件相对路径")
) -> dict:
    """
    读取文件内容。
    YAML Front Matter 和 Markdown Body 分离返回。
    """
    file_path = WORKSPACE_PATH / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    try:
        post = frontmatter.load(str(file_path))
        return {
            "frontmatter": dict(post.metadata),
            "content": post.content,
            "raw": frontmatter.dumps(post),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {e}")


@router.put("/file")
async def update_file(body: FileUpdateRequest) -> dict:
    """
    更新文件。
    支持两种模式:
    1. raw 模式: 直接写入原始内容
    2. 分离模式: 分别更新 frontmatter 和 content
    """
    file_path = WORKSPACE_PATH / body.path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {body.path}")

    try:
        if body.raw is not None:
            atomic_write(str(file_path), body.raw)
        else:
            post = frontmatter.load(str(file_path))
            if body.frontmatter:
                for key, value in body.frontmatter.items():
                    post[key] = value
            if body.content is not None:
                post.content = body.content
            atomic_write(str(file_path), frontmatter.dumps(post))

        return {"status": "ok", "path": body.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update file: {e}")


@router.post("/file")
async def create_file(body: FileCreateRequest) -> dict:
    """创建新文件"""
    file_path = WORKSPACE_PATH / body.path

    if file_path.exists():
        raise HTTPException(status_code=409, detail=f"File already exists: {body.path}")

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(str(file_path), body.content)
        return {"status": "ok", "path": body.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create file: {e}")


@router.delete("/file")
async def delete_file(
    path: str = Query(..., description="文件相对路径")
) -> dict:
    """删除文件"""
    file_path = WORKSPACE_PATH / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        file_path.unlink()
        return {"status": "ok", "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")
```

**验收**: `python -c "from src.api.routes.workspace import router"` 成功

---

### 步骤 2.2 - 新增 src/api/routes/skills.py

**目的**: Skill 管理 API（列表、读取、创建、更新、删除）

**设计参考**: `docs/communication_protocol.md` 第 6.3 节

**执行**:
创建 `src/api/routes/skills.py`：

**完整代码**:

```python
"""
Skill 管理 API。
提供 Skill 的列表、读取、创建、更新、删除端点。
"""
from __future__ import annotations

import frontmatter
from fastapi import APIRouter, HTTPException
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from src.memory.file_io import atomic_write

router = APIRouter(prefix="/api/skills", tags=["skills"])

# Skills 根路径，由 app.py 启动时注入
SKILLS_PATH: Path = Path("./skills")


def set_skills_path(path: str):
    """设置 skills 根路径"""
    global SKILLS_PATH
    SKILLS_PATH = Path(path)


class SkillUpdateRequest(BaseModel):
    """Skill 更新请求"""
    content: str


class SkillCreateRequest(BaseModel):
    """Skill 创建请求"""
    name: str
    content: str
    source: str = "agent_created"


@router.get("")
async def list_skills() -> list[dict]:
    """
    列出所有 Skill。
    返回每个 Skill 的元数据（YAML Front Matter）。
    """
    skills = []

    if not SKILLS_PATH.exists():
        return skills

    # 扫描 builtin 和 agent_created 目录
    for source_dir in ["builtin", "agent_created"]:
        source_path = SKILLS_PATH / source_dir
        if not source_path.exists():
            continue

        for skill_dir in sorted(source_path.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                post = frontmatter.load(str(skill_file))
                skills.append({
                    "name": post.get("name", skill_dir.name),
                    "description": post.get("description", ""),
                    "version": post.get("version", "0.0.0"),
                    "tags": post.get("tags", []),
                    "source": source_dir,
                    "file_path": str(skill_file.relative_to(SKILLS_PATH)).replace("\\", "/"),
                })
            except Exception:
                continue

    return skills


@router.get("/{skill_name}")
async def get_skill(skill_name: str) -> dict:
    """读取 Skill 内容"""
    skill_file = _find_skill_file(skill_name)

    if not skill_file:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")

    try:
        post = frontmatter.load(str(skill_file))
        return {
            "frontmatter": dict(post.metadata),
            "content": post.content,
            "raw": frontmatter.dumps(post),
            "file_path": str(skill_file.relative_to(SKILLS_PATH)).replace("\\", "/"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse skill: {e}")


@router.put("/{skill_name}")
async def update_skill(skill_name: str, body: SkillUpdateRequest) -> dict:
    """更新 Skill 内容"""
    skill_file = _find_skill_file(skill_name)

    if not skill_file:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")

    try:
        atomic_write(str(skill_file), body.content)
        return {"status": "ok", "name": skill_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update skill: {e}")


@router.post("")
async def create_skill(body: SkillCreateRequest) -> dict:
    """
    创建新 Skill。
    仅允许在 agent_created 目录下创建。
    """
    if body.source != "agent_created":
        raise HTTPException(
            status_code=403,
            detail="Can only create skills in agent_created directory"
        )

    skill_dir = SKILLS_PATH / "agent_created" / body.name
    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists():
        raise HTTPException(status_code=409, detail=f"Skill already exists: {body.name}")

    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(str(skill_file), body.content)
        return {"status": "ok", "name": body.name, "path": str(skill_file)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create skill: {e}")


@router.delete("/{skill_name}")
async def delete_skill(skill_name: str) -> dict:
    """
    删除 Skill。
    仅允许删除 agent_created 目录下的 Skill。
    """
    skill_file = _find_skill_file(skill_name)

    if not skill_file:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")

    # 检查是否为 builtin（不允许删除）
    rel_path = skill_file.relative_to(SKILLS_PATH)
    parts = rel_path.parts
    if parts[0] == "builtin":
        raise HTTPException(
            status_code=403,
            detail="Cannot delete builtin skills"
        )

    try:
        # 删除整个 skill 目录
        skill_dir = skill_file.parent
        import shutil
        shutil.rmtree(str(skill_dir))
        return {"status": "ok", "name": skill_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete skill: {e}")


def _find_skill_file(skill_name: str) -> Path | None:
    """在 builtin 和 agent_created 目录中查找 Skill 文件"""
    for source_dir in ["builtin", "agent_created"]:
        skill_file = SKILLS_PATH / source_dir / skill_name / "SKILL.md"
        if skill_file.exists():
            return skill_file
    return None
```

**验收**: `python -c "from src.api.routes.skills import router"` 成功

---

### 步骤 2.3 - 新增 src/api/routes/agent.py

**目的**: Agent 交互 API（事件发送、状态查询、上下文查看、中断、重置）

**设计参考**: `docs/communication_protocol.md` 第 6.2 节

**执行**:
创建 `src/api/routes/agent.py`：

**完整代码**:

```python
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
```

**验收**: `python -c "from src.api.routes.agent import router"` 成功

---

### 步骤 2.4 - 新增 src/api/sse.py

**目的**: SSE 流式推送端点，WorkBench 实时订阅 Agent 输出

**设计参考**: `docs/communication_protocol.md` 第 5 节

**执行**:
创建 `src/api/sse.py`：

**完整代码**:

```python
"""
SSE 流式推送端点。
WorkBench 通过此端点实时订阅 Agent 的输出。
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterable
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from fastapi.sse import EventSourceResponse, ServerSentEvent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sse"])

# Agent 实例引用，由 app.py 启动时注入
_event_handler = None


def set_sse_refs(event_handler):
    """注入 EventHandler 引用"""
    global _event_handler
    _event_handler = event_handler


@router.get("/api/agent/stream", response_class=EventSourceResponse)
async def agent_stream(
    session_id: str = Query("default", description="会话 ID"),
    last_event_id: Optional[str] = Query(None, description="断线重连的 Last-Event-ID"),
) -> EventSourceResponse:
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

    支持 Last-Event-ID 断线重连。
    """
    if _event_handler is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return EventSourceResponse(
        _generate_events(session_id, last_event_id),
        sep="\n",
    )


async def _generate_events(
    session_id: str,
    last_event_id: Optional[str] = None,
) -> AsyncIterable[ServerSentEvent]:
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

    _event_handler.register_sse_callback(on_sse_event)

    try:
        while True:
            try:
                # 等待事件，60 秒超时发送心跳
                item = await asyncio.wait_for(event_queue.get(), timeout=60.0)

                if item is None:
                    # None 表示结束信号
                    break

                yield ServerSentEvent(
                    event=item["event"],
                    data=json.dumps(item["data"], ensure_ascii=False),
                    id=str(event_index),
                )
                event_index += 1

            except asyncio.TimeoutError:
                # 心跳保活
                yield ServerSentEvent(
                    event="heartbeat",
                    data="",
                    id=str(event_index),
                )
                event_index += 1

    except asyncio.CancelledError:
        logger.info(f"SSE stream cancelled for session {session_id}")
    finally:
        # 移除回调
        try:
            _event_handler._sse_callbacks.remove(on_sse_event)
        except ValueError:
            pass
```

**验收**: `python -c "from src.api.sse import router"` 成功

---

### 步骤 2.5 - 注册路由到 app.py

**目的**: 将所有新端点挂载到 FastAPI 应用

**说明**: 先阅读 `src/api/app.py`，理解现有代码结构，然后添加路由注册。

**执行**:
1. 先阅读 `src/api/app.py`
2. 在 `app.py` 中添加路由注册代码

**需要添加的代码**（根据实际 app.py 结构调整位置）:

```python
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
```

**重要注意事项**:
- 如果 `app.py` 中已有 `app = FastAPI(...)` 的实例化代码，在它之后添加路由注册
- 如果 `app.py` 中有 `@app.on_event("startup")` 事件，可以在 startup 中初始化 Agent 实例并注入引用
- 如果 V1 的 `app.py` 有 CORS 配置，保留它
- **不要删除 V1 现有的路由**，只做新增

**验收**: `uvicorn src.api.app:app --host 0.0.0.0 --port 8000` 启动成功，访问 `http://localhost:8000/docs` 能看到新端点

---

### 步骤 2.6 - Workspace API 测试

**目的**: 测试文件树、文件 CRUD 端点

**执行**:
创建 `tests/test_api/test_workspace_api.py`：

**完整代码**:

```python
"""Workspace API 测试"""
import pytest
import frontmatter
from fastapi.testclient import TestClient


@pytest.fixture
def workspace(tmp_path):
    """创建临时 workspace 目录"""
    ws = tmp_path / "workspace"
    ws.mkdir()
    # 创建测试文件
    (ws / "npcs").mkdir()
    (ws / "npcs" / "铁匠.md").write_text(
        "---\nname: 铁匠\ntype: npc\nhp: 80\nversion: 1\n---\n## 交互记录\n[第1天] 初始接触。",
        encoding="utf-8"
    )
    (ws / "session").mkdir()
    (ws / "session" / "current.md").write_text(
        "---\ntype: session\nversion: 1\n---\n会话记录。",
        encoding="utf-8"
    )
    return ws


@pytest.fixture
def client(workspace, monkeypatch):
    """创建测试客户端"""
    from src.api.routes.workspace import router, set_workspace_path
    set_workspace_path(str(workspace))

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    return TestClient(app)


class TestWorkspaceTree:
    """文件树 API 测试"""

    def test_root_tree(self, client):
        resp = client.get("/api/workspace/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert "children" in data
        names = [c["name"] for c in data["children"]]
        assert "npcs" in names
        assert "session" in names

    def test_subdirectory_tree(self, client):
        resp = client.get("/api/workspace/tree?path=npcs")
        assert resp.status_code == 200
        data = resp.json()
        names = [c["name"] for c in data["children"]]
        assert "铁匠.md" in names

    def test_nonexistent_directory(self, client):
        resp = client.get("/api/workspace/tree?path=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["children"] == []


class TestWorkspaceFile:
    """文件 CRUD API 测试"""

    def test_get_file(self, client):
        resp = client.get("/api/workspace/file?path=npcs/铁匠.md")
        assert resp.status_code == 200
        data = resp.json()
        assert data["frontmatter"]["name"] == "铁匠"
        assert "交互记录" in data["content"]
        assert "raw" in data

    def test_get_file_not_found(self, client):
        resp = client.get("/api/workspace/file?path=nonexistent.md")
        assert resp.status_code == 404

    def test_update_file_frontmatter(self, client, workspace):
        resp = client.put("/api/workspace/file", json={
            "path": "npcs/铁匠.md",
            "frontmatter": {"hp": 75},
        })
        assert resp.status_code == 200

        # 验证文件更新
        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert post["hp"] == 75
        assert "交互记录" in post.content  # content 不变

    def test_update_file_content(self, client, workspace):
        resp = client.put("/api/workspace/file", json={
            "path": "npcs/铁匠.md",
            "content": "## 新记录\n[第2天] 玩家来了。",
        })
        assert resp.status_code == 200

        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert "新记录" in post.content
        assert post["name"] == "铁匠"  # frontmatter 不变

    def test_update_file_raw(self, client, workspace):
        resp = client.put("/api/workspace/file", json={
            "path": "npcs/铁匠.md",
            "raw": "---\nname: 铁匠\n---\n全新内容。",
        })
        assert resp.status_code == 200

        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert post.content == "全新内容。"

    def test_create_file(self, client, workspace):
        resp = client.post("/api/workspace/file", json={
            "path": "npcs/新NPC.md",
            "content": "---\nname: 新NPC\n---\n## 初始印象\n新角色。",
        })
        assert resp.status_code == 200

        assert (workspace / "npcs" / "新NPC.md").exists()

    def test_create_file_already_exists(self, client):
        resp = client.post("/api/workspace/file", json={
            "path": "npcs/铁匠.md",
            "content": "重复",
        })
        assert resp.status_code == 409

    def test_delete_file(self, client, workspace):
        resp = client.delete("/api/workspace/file?path=npcs/铁匠.md")
        assert resp.status_code == 200
        assert not (workspace / "npcs" / "铁匠.md").exists()

    def test_delete_file_not_found(self, client):
        resp = client.delete("/api/workspace/file?path=nonexistent.md")
        assert resp.status_code == 404
```

**验收**: `pytest tests/test_api/test_workspace_api.py -v` 全部通过

---

### 步骤 2.7 - Agent API + Skills API 测试

**目的**: 测试 Agent 交互端点和 Skill 管理端点

**执行**:
创建 `tests/test_api/test_agent_api.py`：

**完整代码**:

```python
"""Agent API + Skills API 测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def skills_dir(tmp_path):
    """创建临时 skills 目录"""
    sd = tmp_path / "skills"
    builtin = sd / "builtin" / "combat"
    builtin.mkdir(parents=True)
    (builtin / "SKILL.md").write_text(
        "---\nname: combat\ndescription: 战斗系统。\nversion: 1.0.0\n"
        "tags: [combat]\n---\n\n# 战斗系统\n\n伤害公式。",
        encoding="utf-8"
    )
    agent_dir = sd / "builtin" / "dialogue"
    agent_dir.mkdir(parents=True)
    (agent_dir / "SKILL.md").write_text(
        "---\nname: dialogue\ndescription: 对话系统。\nversion: 1.0.0\n---\n\n# 对话",
        encoding="utf-8"
    )
    return sd


@pytest.fixture
def agent_client(tmp_path):
    """创建 Agent API 测试客户端"""
    from src.api.routes.agent import router as agent_router, set_agent_refs

    # 创建 mock 实例
    mock_gm = MagicMock()
    mock_gm.turn_count = 5
    mock_gm.total_tokens = 15000
    mock_gm.history = [{"role": "user", "content": "test"}] * 10
    mock_gm.prompt_builder = MagicMock()
    mock_gm.prompt_builder.load_system_prompt.return_value = "你是 GM Agent。"
    mock_gm.reset = MagicMock()

    mock_handler = MagicMock()
    mock_handler.is_processing = False
    mock_handler.current_event = None

    set_agent_refs(mock_handler, mock_gm, None)

    app = FastAPI()
    app.include_router(agent_router)
    return TestClient(app)


class TestAgentAPI:
    """Agent 交互 API 测试"""

    def test_get_status(self, agent_client):
        resp = agent_client.get("/api/agent/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "idle"
        assert data["turn_count"] == 5
        assert data["total_tokens"] == 15000
        assert data["history_length"] == 5

    def test_get_context(self, agent_client):
        resp = agent_client.get("/api/agent/context")
        assert resp.status_code == 200
        data = resp.json()
        assert "system_prompt" in data
        assert data["system_prompt"] == "你是 GM Agent。"

    def test_reset_session(self, agent_client):
        resp = agent_client.post("/api/agent/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_send_event_not_initialized(self):
        """Agent 未初始化时应返回 503"""
        from src.api.routes.agent import router, set_agent_refs
        set_agent_refs(None, None, None)

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post("/api/agent/event", json={
            "event_id": "test", "timestamp": "t", "type": "player_action",
            "data": {"raw_text": "test"}, "context_hints": [], "game_state": {}
        })
        assert resp.status_code == 503


class TestSkillsAPI:
    """Skill 管理 API 测试"""

    @pytest.fixture
    def skills_client(self, skills_dir):
        from src.api.routes.skills import router, set_skills_path
        set_skills_path(str(skills_dir))

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_list_skills(self, skills_client):
        resp = skills_client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = [s["name"] for s in data]
        assert "combat" in names
        assert "dialogue" in names

    def test_get_skill(self, skills_client):
        resp = skills_client.get("/api/skills/combat")
        assert resp.status_code == 200
        data = resp.json()
        assert data["frontmatter"]["name"] == "combat"
        assert "伤害公式" in data["content"]

    def test_get_skill_not_found(self, skills_client):
        resp = skills_client.get("/api/skills/nonexistent")
        assert resp.status_code == 404

    def test_update_skill(self, skills_client, skills_dir):
        resp = skills_client.put("/api/skills/combat", json={
            "content": "---\nname: combat\ndescription: 更新后的战斗系统。\n---\n\n# 战斗\n新内容。"
        })
        assert resp.status_code == 200

        # 验证文件更新
        import frontmatter
        post = frontmatter.load(str(skills_dir / "builtin" / "combat" / "SKILL.md"))
        assert "新内容" in post.content

    def test_create_skill(self, skills_client, skills_dir):
        resp = skills_client.post("/api/skills", json={
            "name": "custom_skill",
            "content": "---\nname: custom_skill\ndescription: 自定义技能。\n---\n\n# 自定义",
            "source": "agent_created",
        })
        assert resp.status_code == 200

        assert (skills_dir / "agent_created" / "custom_skill" / "SKILL.md").exists()

    def test_create_skill_builtin_forbidden(self, skills_client):
        resp = skills_client.post("/api/skills", json={
            "name": "hacked",
            "content": "---\nname: hacked\n---\n",
            "source": "builtin",
        })
        assert resp.status_code == 403

    def test_delete_skill_builtin_forbidden(self, skills_client):
        resp = skills_client.delete("/api/skills/combat")
        assert resp.status_code == 403

    def test_delete_skill_agent_created(self, skills_client, skills_dir):
        # 先创建
        (skills_dir / "agent_created" / "temp_skill").mkdir(parents=True)
        (skills_dir / "agent_created" / "temp_skill" / "SKILL.md").write_text(
            "---\nname: temp_skill\n---\n", encoding="utf-8"
        )

        resp = skills_client.delete("/api/skills/temp_skill")
        assert resp.status_code == 200
        assert not (skills_dir / "agent_created" / "temp_skill").exists()

    def test_delete_skill_not_found(self, skills_client):
        resp = skills_client.delete("/api/skills/nonexistent")
        assert resp.status_code == 404
```

**验收**: `pytest tests/test_api/test_agent_api.py -v` 全部通过

---

### 步骤 2.8 - SSE 端点测试

**目的**: 测试 SSE 流式推送

**执行**:
1. 安装 httpx-sse: `uv add httpx-sse`
2. 创建 `tests/test_api/test_sse.py`

**完整代码**:

```python
"""SSE 端点测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def sse_client():
    """创建 SSE 测试客户端"""
    from src.api.sse import router, set_sse_refs

    mock_handler = MagicMock()
    mock_handler.is_processing = False
    mock_handler.current_event = None
    mock_handler._sse_callbacks = []

    set_sse_refs(mock_handler)

    app = FastAPI()
    app.include_router(router)
    return TestClient(app), mock_handler


class TestSSEEndpoint:
    """SSE 端点测试"""

    def test_sse_connection(self, sse_client):
        """测试 SSE 连接建立"""
        client, mock_handler = sse_client

        with client.stream("GET", "/api/agent/stream?session_id=test") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_sse_not_initialized(self):
        """Agent 未初始化时应返回 503"""
        from src.api.sse import router, set_sse_refs
        set_sse_refs(None)

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.get("/api/agent/stream?session_id=test")
        assert resp.status_code == 503

    def test_sse_event_format(self, sse_client):
        """测试 SSE 事件格式"""
        client, mock_handler = sse_client

        # 模拟通过回调推送事件
        import asyncio

        async def push_event():
            await asyncio.sleep(0.1)
            for cb in mock_handler._sse_callbacks:
                await cb("turn_start", {"event_id": "evt_001", "type": "player_action"})
                await cb("token", {"text": "测试"})
                await cb("turn_end", {"response_id": "resp_001", "stats": {}})

        # 在后台推送事件
        import threading
        loop = asyncio.new_event_loop()
        t = threading.Thread(target=loop.run_until_complete, args=(push_event(),))
        t.start()

        try:
            with client.stream("GET", "/api/agent/stream?session_id=test") as response:
                events = []
                for line in response.iter_lines():
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data = line.split(":", 1)[1].strip()
                        events.append({"event": event_type, "data": data})
                    if len(events) >= 3:
                        break

            assert len(events) >= 3
            assert events[0]["event"] == "turn_start"
            assert events[1]["event"] == "token"
            assert events[2]["event"] == "turn_end"
        finally:
            t.join(timeout=2)
            loop.close()
```

**验收**: `pytest tests/test_api/test_sse.py -v` 全部通过

---

## P2 完成检查清单

- [ ] Step 2.1: `workspace.py` 路由实现 + 可导入
- [ ] Step 2.2: `skills.py` 路由实现 + 可导入
- [ ] Step 2.3: `agent.py` 路由实现 + 可导入
- [ ] Step 2.4: `sse.py` 路由实现 + 可导入
- [ ] Step 2.5: 路由注册到 `app.py` + 服务启动成功
- [ ] Step 2.6: Workspace API 测试通过 (>=9 个)
- [ ] Step 2.7: Agent API + Skills API 测试通过 (>=12 个)
- [ ] Step 2.8: SSE 端点测试通过 (>=3 个)
- [ ] P0 + P1 全部测试仍然通过（175+ 个）
