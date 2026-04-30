# Game Master Agent V2 - P0: 清理冗余 + 基础设施

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户将 V1 的 Game Master Agent **重构为 V2 通用游戏驱动 Agent**。
- **技术栈**: Python 3.11+ / DeepSeek API / FastAPI / SQLite / python-frontmatter
- **包管理器**: uv
- **LLM**: DeepSeek（通过 OpenAI 兼容接口调用）
- **开发IDE**: Trae

### V2 核心变化

V1 做了一个 MUD 文字游戏，V2 要做一个**通用游戏驱动 Agent 服务**——类似 Trae 驱动代码，我们的 Agent 驱动游戏。Agent 不再是游戏本身，而是通过标准化协议与任意游戏引擎通信的独立服务。

### P0 阶段目标

1. **砍掉 V1 中已被 V2 方案替代的冗余模块**
2. **创建 V2 的新模块**（memory / skills / adapters）
3. **每步跑测试确认不破坏现有功能**

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

## 参考设计文档

以下是 V2 架构设计文档，存放在 `docs/` 目录下。

| 文档 | 内容 |
|------|------|
| `docs/architecture_v2.md` | V2 架构总览、目录结构、技术栈 |
| `docs/memory_system.md` | .md 记忆文件格式、渐进式加载、原子写入 |
| `docs/skill_system.md` | SKILL.md 标准、发现机制、加载流程 |
| `docs/engine_adapter.md` | EngineAdapter 接口、TextAdapter 实现 |
| `docs/communication_protocol.md` | JSON 命令流格式、引擎事件格式 |
| `docs/dev_plan_v2.md` | V2 开发计划总览 |

## V1 经验教训（必须遵守）

1. **PowerShell `&&` 语法**: Windows PowerShell 不支持 `&&`，用 `;` 分隔多条命令
2. **测试隔离**: 每个测试模块用 `teardown_module()` 清理全局状态，防止测试间污染
3. **SQLite datetime('now')**: 同一秒内多次调用返回相同时间戳，测试断言用 `>=` 而非 `==`
4. **中文括号**: 测试代码中一律用英文括号 `()`，不要用中文括号 `（）`
5. **原子写入**: 所有 .md 文件写入必须用 `atomic_write()`，不要直接 `open().write()`
6. **YAML Front Matter 格式**: 用 `python-frontmatter` 库解析，不要手写字符串拼接

---

## P0: 清理冗余 + 基础设施（共 13 步）

### 步骤 0.1 - 删除 V1 冗余模块

**目的**: 砍掉已被 V2 方案替代的 V1 代码，减少干扰

**执行**:
1. 先运行一次 V1 全量测试，确认基线：`pytest tests/ -v`
2. 记录通过的测试数量（应为 179 个）
3. 删除以下 V1 冗余模块：
   ```
   rm -rf src/tools/              # V1 Tool 函数注册系统 → V2 用 Skill (.md 文件)
   rm src/services/context_manager.py  # V1 SQLite 上下文拼接 → V2 用 MemoryManager (.md 文件)
   rm -rf src/plugins/             # V1 插件系统 → V2 用 Skill 系统
   ```
4. 检查是否有其他文件 import 了被删除的模块，如果有则注释掉相关 import（后续步骤会重写）
5. 再次运行测试：`pytest tests/ -v`
6. 如果有测试因为 import 被删模块而失败，删除或注释掉这些测试文件（它们测试的是已废弃的功能）

**删除理由**:
- `src/tools/`: V1 的 Tool 函数（get_npc, create_item 等）全部硬编码在 Python 里。V2 改用 Skill .md 文件定义能力，Agent 通过 LLM 理解 Skill 规则生成 commands，不再需要 Python 函数注册
- `src/services/context_manager.py`: V1 从 SQLite 拼 SQL 查询结果为大段文本塞进 prompt。V2 改用 .md 文件存储记忆，MemoryManager 负责读写
- `src/plugins/`: V1 的插件机制和 V2 的 Skill 系统功能重叠，Skill 更灵活（.md 文件，LLM 可读可写）

**验收**: 没有任何代码 import 被删除的模块；剩余测试全部通过

---

### 步骤 0.2 - 创建 V2 目录结构

**目的**: 建立 V2 新模块的目录骨架

**执行**:
1. 在项目根目录下创建以下目录：
   ```
   src/memory/          # 记忆系统模块
   src/skills/          # Skill 系统模块
   src/adapters/        # 引擎适配层模块
   src/agent/           # Agent 核心模块
   src/api/routes/      # API 路由模块
   workspace/           # Agent Workspace（.md 记忆文件）
   workspace/npcs/
   workspace/locations/
   workspace/story/
   workspace/quests/
   workspace/items/
   workspace/player/
   workspace/session/
   skills/              # Skill 文件目录
   skills/builtin/
   skills/agent_created/
   tests/test_memory/
   tests/test_skills/
   tests/test_adapters/
   ```
2. 在每个 Python 包目录下创建 `__init__.py`（空文件即可）

**验收**: 所有目录存在，所有 `__init__.py` 存在

---

### 步骤 0.3 - 安装 python-frontmatter 依赖

**目的**: 安装 YAML Front Matter + Markdown 解析库

**执行**:
1. 执行 `uv pip install python-frontmatter`
2. 验证：`python -c "import frontmatter; print(frontmatter.__version__)"`
3. 在 `requirements.txt` 中添加 `python-frontmatter>=1.1.0`

**验收**: `import frontmatter` 成功

---

### 步骤 0.4 - 实现 src/memory/file_io.py

**目的**: 提供原子文件写入和 YAML+MD 文件更新能力

**设计参考**: `docs/memory_system.md` 第 6 节

**执行**:
创建 `src/memory/file_io.py`，实现两个函数：

#### `atomic_write(filepath, content, encoding="utf-8")`

原子写入文件：
1. 在目标文件**同目录**创建临时文件（`tempfile.mkstemp`）
2. 写入内容并 `flush()` + `os.fsync()`
3. 用 `os.replace()` 原子替换目标文件
4. 失败时清理临时文件（`except BaseException`）

#### `update_memory_file(filepath, frontmatter_updates=None, append_content=None)`

更新记忆文件：
1. 文件存在则 `frontmatter.load()`，否则创建空 `Post`
2. 更新 YAML 字段 / 追加 Markdown Body
3. 自动递增 `version`，更新 `last_modified`
4. 用 `atomic_write()` 写回

**完整代码**:

```python
"""
记忆文件原子读写模块。
所有 .md 文件的写入操作都必须通过此模块。
"""
import os
import tempfile
from pathlib import Path
from datetime import datetime

import frontmatter


def atomic_write(filepath: str, content: str, encoding: str = "utf-8") -> None:
    """
    原子写入文件。在目标文件同目录创建临时文件，完成后原子替换。
    """
    path = Path(filepath)
    dirpath = path.parent
    dirpath.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(dirpath),
        prefix=f".{path.stem}.tmp_",
        suffix=path.suffix
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def update_memory_file(
    filepath: str,
    frontmatter_updates: dict = None,
    append_content: str = None
) -> None:
    """
    更新记忆文件的统一接口。
    自动递增 version，更新 last_modified。
    """
    path = Path(filepath)

    if path.exists():
        post = frontmatter.load(str(path))
    else:
        post = frontmatter.Post(content="")

    if frontmatter_updates:
        for key, value in frontmatter_updates.items():
            post[key] = value

    if append_content:
        post.content += append_content

    post["version"] = post.get("version", 0) + 1
    post["last_modified"] = datetime.now().isoformat()

    atomic_write(str(path), frontmatter.dumps(post))
```

**验收**: `python -c "from src.memory.file_io import atomic_write, update_memory_file"` 成功

---

### 步骤 0.5 - 实现 src/memory/loader.py

**目的**: 渐进式记忆加载器，3 层加载（Index → Activation → Execution）

**设计参考**: `docs/memory_system.md` 第 3 节

**执行**:
创建 `src/memory/loader.py`：

**完整代码**:

```python
"""
渐进式记忆加载器。
Layer 1 (Index): ~100 tokens/file
Layer 2 (Activation): ~500-2000 tokens/file
Layer 3 (Execution): ~2000-5000 tokens/file
"""
import re
from pathlib import Path

import frontmatter


class MemoryLoader:
    """渐进式记忆加载器"""

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)

    def load_index(self, file_paths: list[str]) -> str:
        """Layer 1: 只读取 name, type, tags, version"""
        lines = ["## 相关实体索引\n"]
        for fp in file_paths:
            full_path = self.workspace / f"{fp}.md"
            if not full_path.exists():
                lines.append(f"- {fp}: [不存在]")
                continue
            post = frontmatter.load(str(full_path))
            name = post.get("name", fp)
            etype = post.get("type", "unknown")
            tags = post.get("tags", [])
            version = post.get("version", 0)
            tag_str = ", ".join(tags) if tags else ""
            lines.append(f"- [{etype}] {name} (v{version}) {tag_str}")
        return "\n".join(lines)

    def load_activation(self, file_paths: list[str]) -> str:
        """Layer 2: 完整 YAML + 章节标题"""
        blocks = []
        for fp in file_paths:
            full_path = self.workspace / f"{fp}.md"
            if not full_path.exists():
                continue
            post = frontmatter.load(str(full_path))
            fm_lines = [f"### {post.get('name', fp)}"]
            for key, value in post.metadata.items():
                if key in ("version", "last_modified", "modified_by", "created_at"):
                    continue
                fm_lines.append(f"- {key}: {value}")
            headings = re.findall(r'^## .+$', post.content, re.MULTILINE)
            if headings:
                fm_lines.append("- 章节: " + " | ".join(h[3:] for h in headings))
            blocks.append("\n".join(fm_lines))
        return "\n\n".join(blocks)

    def load_execution(self, file_paths: list[str]) -> str:
        """Layer 3: 完整文件内容"""
        blocks = []
        for fp in file_paths:
            full_path = self.workspace / f"{fp}.md"
            if not full_path.exists():
                continue
            post = frontmatter.load(str(full_path))
            blocks.append(f"### {post.get('name', fp)}\n{post.content}")
        return "\n\n".join(blocks)
```

**验收**: `python -c "from src.memory.loader import MemoryLoader"` 成功

---

### 步骤 0.6 - 实现 src/memory/manager.py

**目的**: 记忆管理主类，整合 file_io 和 loader

**设计参考**: `docs/memory_system.md` 第 7 节

**执行**:
创建 `src/memory/manager.py`：

**完整代码**:

```python
"""
记忆管理器。整合文件读写和渐进式加载。
"""
from pathlib import Path
from typing import Optional

import frontmatter

from src.memory.file_io import atomic_write, update_memory_file
from src.memory.loader import MemoryLoader


class MemoryManager:
    """Agent 记忆管理器"""

    def __init__(self, workspace_path: str, llm_client=None):
        self.workspace = Path(workspace_path)
        self.loader = MemoryLoader(workspace_path)
        self.llm_client = llm_client

    def load_context(self, context_hints: list[str], depth: str = "auto") -> str:
        """根据 context_hints 加载记忆上下文"""
        if depth == "index":
            return self.loader.load_index(context_hints)
        elif depth == "activation":
            return self.loader.load_activation(context_hints)
        elif depth == "execution":
            return self.loader.load_execution(context_hints)
        else:
            return self.loader.load_index(context_hints)

    def load_full_file(self, file_path: str) -> Optional[dict]:
        """加载完整文件，返回 {frontmatter: dict, content: str}"""
        full_path = self.workspace / file_path
        if not full_path.exists():
            return None
        post = frontmatter.load(str(full_path))
        return {"frontmatter": dict(post.metadata), "content": post.content}

    def apply_state_changes(self, state_changes: list[dict]) -> None:
        """引擎执行 commands 后，更新 YAML Front Matter"""
        for change in state_changes:
            update_memory_file(
                filepath=str(self.workspace / change["file"]),
                frontmatter_updates=change["frontmatter"]
            )

    def apply_memory_updates(self, updates: list[dict]) -> None:
        """Agent 每回合追加记忆到 Markdown Body"""
        for update in updates:
            if update["action"] == "append":
                update_memory_file(
                    filepath=str(self.workspace / update["file"]),
                    append_content=update["content"]
                )
            elif update["action"] == "create":
                atomic_write(
                    str(self.workspace / update["file"]),
                    update["content"]
                )

    def initialize_workspace(self) -> None:
        """初始化 workspace 目录结构和索引文件"""
        dirs = ["npcs", "locations", "story", "quests", "items", "player", "session"]
        for d in dirs:
            dir_path = self.workspace / d
            dir_path.mkdir(parents=True, exist_ok=True)
            index_path = dir_path / "_index.md"
            if not index_path.exists():
                atomic_write(
                    str(index_path),
                    f"---\ntype: index\ncategory: {d}\nentity_count: 0\n---\n\n## {d}\n\n(暂无)"
                )
```

**验收**: `python -c "from src.memory.manager import MemoryManager"` 成功

---

### 步骤 0.7 - 实现 src/skills/loader.py

**目的**: Skill 发现与加载器

**设计参考**: `docs/skill_system.md` 第 3 节

**执行**:
创建 `src/skills/loader.py`：

**完整代码**:

```python
"""
Skill 发现与加载器。
扫描 skills/ 目录，发现和匹配 SKILL.md 文件。
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import frontmatter


@dataclass
class SkillMetadata:
    """Skill 元数据"""
    name: str
    description: str
    version: str
    tags: list[str] = field(default_factory=list)
    triggers: list[dict] = field(default_factory=list)
    file_path: str = ""
    source: str = ""


class SkillLoader:
    """Skill 发现与加载器"""

    def __init__(self, skills_path: str):
        self.skills_path = Path(skills_path)
        self._cache: dict[str, SkillMetadata] = {}

    def discover_all(self) -> list[SkillMetadata]:
        """发现所有 Skill（带缓存）"""
        if self._cache:
            return list(self._cache.values())
        skills = []
        for skill_dir in self._skills_dirs():
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            post = frontmatter.load(str(skill_md))
            metadata = SkillMetadata(
                name=post.get("name", skill_dir.name),
                description=post.get("description", ""),
                version=post.get("version", "0.0.0"),
                tags=post.get("tags", []),
                triggers=post.get("triggers", []),
                file_path=str(skill_md),
                source="builtin" if "builtin" in str(skill_dir) else "agent_created"
            )
            self._cache[metadata.name] = metadata
            skills.append(metadata)
        return skills

    def get_relevant_skills(
        self,
        event_type: str = None,
        user_input: str = None,
        context_hints: list[str] = None
    ) -> list[SkillMetadata]:
        """根据事件匹配相关 Skill，按相关度排序"""
        all_skills = self.discover_all()
        relevant = []
        for skill in all_skills:
            score = 0
            for trigger in skill.triggers:
                if event_type and trigger.get("event_type") == event_type:
                    score += 10
                if user_input and "keyword" in trigger:
                    keywords = trigger["keyword"]
                    if isinstance(keywords, str):
                        keywords = [keywords]
                    for kw in keywords:
                        if kw in user_input:
                            score += 5
                if context_hints and "memory_hint" in trigger:
                    hints = trigger["memory_hint"]
                    if isinstance(hints, str):
                        hints = [hints]
                    for hint in hints:
                        if any(hint in ch for ch in context_hints):
                            score += 3
            if score > 0:
                relevant.append((skill, score))
        relevant.sort(key=lambda x: x[1], reverse=True)
        return [skill for skill, score in relevant]

    def load_skill_content(self, skill_name: str) -> Optional[str]:
        """加载 Skill 的完整 Markdown Body"""
        if skill_name not in self._cache:
            return None
        post = frontmatter.load(self._cache[skill_name].file_path)
        return post.content

    def load_skill_activation(self, skill_name: str) -> Optional[str]:
        """加载 Skill 的激活层（YAML 关键字段 + 前 2000 字符）"""
        if skill_name not in self._cache:
            return None
        skill = self._cache[skill_name]
        post = frontmatter.load(skill.file_path)
        info_lines = [
            f"## Skill: {skill.name} (v{skill.version})",
            f"**描述**: {skill.description}",
        ]
        if skill.tags:
            info_lines.append(f"**标签**: {', '.join(skill.tags)}")
        allowed_tools = post.get("allowed-tools", [])
        if allowed_tools:
            info_lines.append(f"**可用指令**: {', '.join(allowed_tools)}")
        body_preview = post.content[:2000]
        if len(post.content) > 2000:
            body_preview += "\n\n... (内容已截断)"
        return "\n".join(info_lines) + "\n\n" + body_preview

    def invalidate_cache(self):
        """清除缓存"""
        self._cache.clear()

    def _skills_dirs(self) -> list[Path]:
        """获取所有 Skill 目录"""
        dirs = []
        for root_dir in ["builtin", "agent_created"]:
            base = self.skills_path / root_dir
            if base.exists():
                for d in base.iterdir():
                    if d.is_dir():
                        dirs.append(d)
        return dirs
```

**验收**: `python -c "from src.skills.loader import SkillLoader, SkillMetadata"` 成功

---

### 步骤 0.8 - 实现 src/adapters/base.py

**目的**: 定义引擎适配器的抽象接口和数据类

**设计参考**: `docs/engine_adapter.md` 第 2 节

**执行**:
创建 `src/adapters/base.py`：

**完整代码**:

```python
"""
引擎适配器抽象接口。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable, Optional
import time


class ConnectionStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class EngineEvent:
    """标准引擎事件（引擎 → Agent）"""
    event_id: str
    timestamp: str
    type: str
    data: dict = field(default_factory=dict)
    context_hints: list[str] = field(default_factory=list)
    game_state: dict = field(default_factory=dict)


@dataclass
class CommandResult:
    """单条指令执行结果"""
    intent: str
    status: str  # success, rejected, partial, error
    new_value: Optional[any] = None
    state_changes: Optional[dict] = None
    reason: Optional[str] = None
    suggestion: Optional[str] = None


EventCallback = Callable[["EngineEvent"], Awaitable[None]]


class EngineAdapter(ABC):
    """引擎适配器抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def connection_status(self) -> ConnectionStatus: ...

    @abstractmethod
    async def connect(self, **kwargs) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def send_commands(self, commands: list[dict]) -> list[CommandResult]: ...

    @abstractmethod
    async def subscribe_events(self, event_types: list[str], callback: EventCallback) -> None: ...

    @abstractmethod
    async def query_state(self, query: dict) -> dict: ...

    async def health_check(self) -> dict:
        start = time.time()
        try:
            await self.query_state({"type": "ping"})
            latency = int((time.time() - start) * 1000)
            return {"status": "ok", "adapter": self.name, "latency_ms": latency}
        except Exception as e:
            return {"status": "error", "adapter": self.name, "error": str(e)}
```

**验收**: `python -c "from src.adapters.base import EngineAdapter, EngineEvent, CommandResult"` 成功

---

### 步骤 0.9 - 实现 src/adapters/text_adapter.py

**目的**: MUD 文字游戏适配器，复用 V1 的 Service 层

**设计参考**: `docs/engine_adapter.md` 第 3 节

**说明**: TextAdapter 接收 V1 的 Service 实例（world_service, player_service 等），将标准 intent 路由到 V1 的 repo 方法。P0 测试用 Mock 对象。

**执行**:
创建 `src/adapters/text_adapter.py`：

**完整代码**:

```python
"""
MUD 文字游戏适配器。复用 V1 的 SQLite 数据层。
"""
import uuid
from datetime import datetime

from src.adapters.base import (
    EngineAdapter, EngineEvent, CommandResult,
    ConnectionStatus, EventCallback
)


class TextAdapter(EngineAdapter):
    """MUD 文字游戏适配器"""

    def __init__(self, world_service, player_service, npc_service,
                 item_service, quest_service):
        self._world = world_service
        self._player = player_service
        self._npc = npc_service
        self._item = item_service
        self._quest = quest_service
        self._status = ConnectionStatus.DISCONNECTED
        self._event_callback: EventCallback = None
        self._player_id: str = None
        self._world_id: str = None

    @property
    def name(self) -> str:
        return "text"

    @property
    def connection_status(self) -> ConnectionStatus:
        return self._status

    async def connect(self, world_id: str = None, player_id: str = None) -> None:
        self._status = ConnectionStatus.CONNECTING
        try:
            if world_id:
                self._world_id = world_id
            else:
                worlds = self._world.list_worlds()
                if worlds:
                    self._world_id = worlds[0]["id"]
                else:
                    raise ConnectionError("没有可用的游戏世界")
            if player_id:
                self._player_id = player_id
            else:
                players = self._player.list_players(self._world_id)
                if players:
                    self._player_id = players[0]["id"]
                else:
                    raise ConnectionError("没有可用的玩家角色")
            self._status = ConnectionStatus.CONNECTED
        except Exception as e:
            self._status = ConnectionStatus.ERROR
            raise ConnectionError(f"连接失败: {e}")

    async def disconnect(self) -> None:
        self._status = ConnectionStatus.DISCONNECTED
        self._player_id = None
        self._world_id = None

    async def send_commands(self, commands: list[dict]) -> list[CommandResult]:
        results = []
        for cmd in commands:
            intent = cmd.get("intent", "no_op")
            params = cmd.get("params", {})
            try:
                result = await self._execute_intent(intent, params)
                results.append(result)
            except Exception as e:
                results.append(CommandResult(intent=intent, status="error", reason=str(e)))
        return results

    async def _execute_intent(self, intent: str, params: dict) -> CommandResult:
        now = datetime.now().isoformat()

        if intent == "update_npc_relationship":
            npc_id = params["npc_id"]
            change = params.get("change", 0)
            npc = self._npc.get_npc(self._world_id, npc_id)
            if not npc:
                return CommandResult(intent=intent, status="rejected", reason=f"NPC not found: {npc_id}")
            new_rel = max(0, min(100, npc.get("relationship", 0) + change))
            self._npc.update_npc(self._world_id, npc_id, {"relationship": new_rel})
            return CommandResult(
                intent=intent, status="success", new_value=new_rel,
                state_changes={"file": f"npcs/{npc.get('name', npc_id)}.md",
                    "frontmatter": {"relationship_with_player": new_rel,
                        "version": npc.get("version", 0) + 1,
                        "last_modified": now, "modified_by": "engine"}})

        elif intent == "update_npc_state":
            npc_id = params["npc_id"]
            npc = self._npc.get_npc(self._world_id, npc_id)
            if not npc:
                return CommandResult(intent=intent, status="rejected", reason=f"NPC not found: {npc_id}")
            self._npc.update_npc(self._world_id, npc_id, {params["field"]: params["value"]})
            return CommandResult(
                intent=intent, status="success", new_value=params["value"],
                state_changes={"file": f"npcs/{npc.get('name', npc_id)}.md",
                    "frontmatter": {params["field"]: params["value"],
                        "version": npc.get("version", 0) + 1,
                        "last_modified": now, "modified_by": "engine"}})

        elif intent == "offer_quest":
            quest_id = self._quest.create_quest(self._world_id, {
                "title": params["title"], "description": params.get("description", ""),
                "objective": params.get("objective", ""), "reward": params.get("reward", ""),
                "status": "active"})
            return CommandResult(intent=intent, status="success", new_value=quest_id,
                state_changes={"file": f"quests/{params.get('quest_id', quest_id)}.md",
                    "frontmatter": {"status": "active", "version": 1,
                        "last_modified": now, "modified_by": "engine"}})

        elif intent == "update_quest":
            self._quest.update_quest(self._world_id, params["quest_id"],
                {"status": params.get("status"), "progress": params.get("progress")})
            return CommandResult(intent=intent, status="success",
                state_changes={"file": f"quests/{params['quest_id']}.md",
                    "frontmatter": {"status": params.get("status"), "version": 0,
                        "last_modified": now, "modified_by": "engine"}})

        elif intent == "give_item":
            self._item.create_item(self._world_id, {
                "name": params.get("name", params.get("item_id", "")),
                "type": params.get("type", "misc"), "player_id": self._player_id})
            return CommandResult(intent=intent, status="success")

        elif intent == "remove_item":
            self._item.delete_item(self._world_id, params["item_id"])
            return CommandResult(intent=intent, status="success")

        elif intent == "modify_stat":
            player = self._player.get_player(self._world_id, self._player_id)
            stat = params["stat"]
            new_val = player.get(stat, 0) + params.get("change", 0)
            self._player.update_player(self._world_id, self._player_id, {stat: new_val})
            return CommandResult(intent=intent, status="success", new_value=new_val,
                state_changes={"file": "player/profile.md",
                    "frontmatter": {stat: new_val,
                        "version": player.get("version", 0) + 1,
                        "last_modified": now, "modified_by": "engine"}})

        elif intent == "teleport_player":
            self._player.update_player(self._world_id, self._player_id,
                {"location": params["location_id"]})
            return CommandResult(intent=intent, status="success")

        elif intent == "show_notification":
            print(f"[通知] {params.get('message', '')}")
            return CommandResult(intent=intent, status="success")

        elif intent in ("play_sound", "no_op"):
            return CommandResult(intent=intent, status="success")

        else:
            return CommandResult(intent=intent, status="rejected",
                reason=f"Unknown intent: {intent}")

    async def subscribe_events(self, event_types: list[str], callback: EventCallback) -> None:
        self._event_callback = callback

    async def query_state(self, query: dict) -> dict:
        qt = query.get("type", "ping")
        if qt == "ping":
            return {"pong": True}
        elif qt == "player_stats":
            return self._player.get_player(self._world_id, self._player_id) or {}
        elif qt == "world_info":
            return self._world.get_world(self._world_id) or {}
        elif qt == "npc_list":
            return {"npcs": self._npc.list_npcs(self._world_id)}
        elif qt == "quest_list":
            return {"quests": self._quest.list_quests(self._world_id)}
        return {"error": f"Unknown query type: {qt}"}

    async def handle_player_input(self, raw_text: str) -> EngineEvent:
        """将玩家命令行输入转换为标准 EngineEvent"""
        event_type = "player_action"
        if any(kw in raw_text for kw in ["去", "走", "前往", "移动", "进入", "离开"]):
            event_type = "player_move"
        if any(kw in raw_text for kw in ["攻击", "战斗", "打", "杀", "使用技能"]):
            event_type = "combat_start"

        context_hints = []
        player = self._player.get_player(self._world_id, self._player_id)
        if player and player.get("location"):
            context_hints.append(f"locations/{player['location']}")
        for npc in self._npc.list_npcs(self._world_id):
            if npc.get("name", "") in raw_text:
                context_hints.append(f"npcs/{npc['name']}")

        game_state = {}
        if player:
            game_state = {"location": player.get("location", "unknown"),
                "player_hp": player.get("hp", 100), "player_level": player.get("level", 1)}

        event = EngineEvent(event_id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(), type=event_type,
            data={"raw_text": raw_text, "player_id": self._player_id},
            context_hints=context_hints, game_state=game_state)
        if self._event_callback:
            await self._event_callback(event)
        return event
```

**验收**: `python -c "from src.adapters.text_adapter import TextAdapter"` 成功

---

### 步骤 0.10 - 创建 5 个内置 Skill 文件

**目的**: 创建 Agent 的核心能力定义文件

**设计参考**: `docs/skill_system.md` 第 5 节

**执行**:
在 `skills/builtin/` 下创建 5 个 Skill 目录，每个包含 `SKILL.md`：

#### skills/builtin/combat/SKILL.md

```markdown
---
name: combat
description: 战斗系统管理。当涉及战斗、伤害计算、技能使用、战斗结果判定时使用此 Skill。
version: 1.0.0
tags: [combat, battle, damage, skill]
allowed-tools:
  - modify_stat
  - update_npc_state
  - show_notification
  - play_sound
triggers:
  - event_type: combat_start
  - event_type: combat_action
  - event_type: combat_end
  - keyword: ["战斗", "攻击", "防御", "技能", "伤害", "打", "杀"]
---

# 战斗系统

## 核心规则

### 伤害公式
- 基础伤害 = 攻击力 * (1 + 技能加成) - 防御力 * 0.5
- 暴击伤害 = 基础伤害 * 1.5 (暴击率 = 敏捷 / 100)
- 最终伤害 = max(基础伤害, 1)

### 战斗流程
1. 确定先手 (敏捷高者先行动)
2. 攻击方选择技能或普通攻击
3. 计算伤害并应用
4. 检查目标是否倒下
5. 交换攻守，重复 2-4
6. 一方 HP 归零时战斗结束

## 可用指令
| intent | params | 说明 |
|--------|--------|------|
| modify_stat | {player_id, stat: "hp", change: -15} | 修改玩家属性 |
| update_npc_state | {npc_id, field: "hp", value: 0} | 修改 NPC 状态 |
| show_notification | {message: "...", type: "damage"} | 显示通知 |

## 叙事要求
- 动作描写 (挥剑、闪避、格挡)
- 伤害反馈 (数字、效果描述)
- 氛围渲染 (紧张感、危机感)
- 战斗中不要突然切换到非战斗话题
```

#### skills/builtin/dialogue/SKILL.md

```markdown
---
name: dialogue
description: 对话系统管理。当玩家与NPC交谈、询问信息、建立关系时使用此 Skill。
version: 1.0.0
tags: [dialogue, npc, relationship]
allowed-tools:
  - update_npc_relationship
  - show_notification
triggers:
  - event_type: npc_interact
  - keyword: ["聊天", "对话", "询问", "说话", "谈谈", "聊聊"]
---

# 对话系统

## 核心规则

### 好感度影响
- 0-20: 冷淡，只回答必要问题
- 21-50: 友好，愿意分享一般信息
- 51-80: 信任，愿意分享秘密
- 81-100: 亲密，愿意付出帮助

### 信息透露控制
- 关键剧情信息需要好感度达到阈值
- NPC 不会一次性透露所有信息
- 信息透露应该自然

## 可用指令
| intent | params | 说明 |
|--------|--------|------|
| update_npc_relationship | {npc_id, change: 5} | 修改好感度 |

## 叙事要求
- 保持 NPC 性格一致性
- 对话要有个性
- 描写 NPC 的表情、动作、语气
```

#### skills/builtin/quest/SKILL.md

```markdown
---
name: quest
description: 任务系统管理。当涉及任务发布、进度追踪、任务完成、奖励发放时使用此 Skill。
version: 1.0.0
tags: [quest, mission, reward]
allowed-tools:
  - offer_quest
  - update_quest
  - give_item
  - show_notification
triggers:
  - event_type: quest_update
  - keyword: ["任务", "委托", "目标", "完成", "奖励"]
---

# 任务系统

## 核心规则

### 任务状态
- inactive: 未激活 / active: 进行中 / completed: 已完成 / failed: 已失败

## 可用指令
| intent | params | 说明 |
|--------|--------|------|
| offer_quest | {quest_id, title, description, objective, reward} | 发布任务 |
| update_quest | {quest_id, status, progress} | 更新任务状态 |
| give_item | {item_id, player_id, quantity} | 给予物品 |
```

#### skills/builtin/exploration/SKILL.md

```markdown
---
name: exploration
description: 探索系统管理。当玩家移动、探索新区域、搜索物品、调查环境时使用此 Skill。
version: 1.0.0
tags: [exploration, movement, discovery]
allowed-tools:
  - update_location
  - teleport_player
  - give_item
  - show_notification
triggers:
  - event_type: player_move
  - keyword: ["探索", "搜索", "调查", "查看", "周围"]
---

# 探索系统

## 核心规则

### 地点发现
- 首次进入新地点时详细描述
- 重复进入时简要描述或提示变化
- 隐藏区域需要特定条件才能发现

## 可用指令
| intent | params | 说明 |
|--------|--------|------|
| update_location | {location_id, field, value} | 修改地点状态 |
| teleport_player | {player_id, location_id} | 传送玩家 |
| give_item | {item_id, player_id} | 给予发现的物品 |
```

#### skills/builtin/narration/SKILL.md

```markdown
---
name: narration
description: 叙事风格控制。始终加载的默认 Skill，定义 Agent 的叙事风格和节奏把控规则。
version: 1.0.0
tags: [narration, style, atmosphere]
allowed-tools: []
triggers: []
---

# 叙事风格

## 核心规则

### 风格
- 使用中文自然语言，第二人称视角 ("你走进...")
- 适当使用感官描写 (视觉、听觉、触觉、嗅觉)
- 对话用引号包裹

### 节奏
- 日常场景: 简洁明快，100-200字
- 重要场景: 详细描写，300-500字
- 战斗场景: 紧凑有力，短句为主
- 情感场景: 细腻深入

### 氛围
- 安全区域: 轻松温暖
- 危险区域: 紧张压抑
- 神秘区域: 诡异未知
- 城镇区域: 热闹繁华
```

**验收**: 5 个 `SKILL.md` 都存在，`python -c "import frontmatter; print(frontmatter.load('skills/builtin/combat/SKILL.md')['name'])"` 输出 `combat`

---

### 步骤 0.11 - 初始化 workspace 目录

**目的**: 创建 Agent Workspace 的目录结构和索引文件

**设计参考**: `docs/memory_system.md` 第 4 节

**执行**:
1. 创建全局索引 `workspace/index.md`：

```markdown
---
type: global_index
total_entities: 0
last_updated: 2026-04-28T00:00:00
---

## 记忆概览

- **NPCs**: 0 个
- **地点**: 0 个
- **剧情**: 0 条
- **任务**: 0 个
- **物品**: 0 个

## 最近更新
(暂无)
```

2. 创建玩家档案 `workspace/player/profile.md`：

```markdown
---
name: 玩家
type: player
id: player_001
hp: 100
max_hp: 100
level: 1
version: 1
last_modified: 2026-04-28T00:00:00
modified_by: engine
created_at: 2026-04-28T00:00:00
tags: [player]
---

## 初始状态
[第1天] 冒险者踏上了旅程。
```

3. 创建会话记录 `workspace/session/current.md`：

```markdown
---
type: session
turn_count: 0
total_tokens: 0
session_start: 2026-04-28T00:00:00
version: 1
last_modified: 2026-04-28T00:00:00
modified_by: engine
---

## 会话记录
(等待第一次交互)
```

**验收**: 3 个文件都存在且格式正确

---

### 步骤 0.12 - 编写新模块的单元测试

**目的**: 确保所有新模块代码正确

**执行**:
创建以下测试文件：

#### tests/test_memory/test_file_io.py

```python
"""memory/file_io.py 单元测试"""
import pytest
from pathlib import Path
import frontmatter
from src.memory.file_io import atomic_write, update_memory_file


class TestAtomicWrite:
    def test_creates_file(self, tmp_path):
        target = str(tmp_path / "test.md")
        atomic_write(target, "# Test\n\nContent")
        assert Path(target).exists()
        assert "Content" in Path(target).read_text(encoding="utf-8")

    def test_overwrites_existing(self, tmp_path):
        target = str(tmp_path / "test.md")
        atomic_write(target, "first")
        atomic_write(target, "second")
        assert Path(target).read_text(encoding="utf-8") == "second"

    def test_creates_parent_dirs(self, tmp_path):
        target = str(tmp_path / "sub" / "dir" / "test.md")
        atomic_write(target, "nested")
        assert Path(target).exists()

    def test_atomic_no_corruption(self, tmp_path):
        target = str(tmp_path / "test.md")
        atomic_write(target, "first")
        atomic_write(target, "second")
        content = Path(target).read_text(encoding="utf-8")
        assert content in ("first", "second")

    def test_utf8_encoding(self, tmp_path):
        target = str(tmp_path / "test.md")
        atomic_write(target, "---\nname: 铁匠\n---\n## 记录\n[第1天] 铁匠铺。")
        assert "铁匠" in Path(target).read_text(encoding="utf-8")


class TestUpdateMemoryFile:
    def test_create_new_file(self, tmp_path):
        target = str(tmp_path / "new.md")
        update_memory_file(filepath=target,
            frontmatter_updates={"name": "新NPC", "type": "npc", "version": 1},
            append_content="\n## 初始印象\n[第1天] 新角色。")
        post = frontmatter.load(target)
        assert post["name"] == "新NPC"
        assert "初始印象" in post.content

    def test_append_preserves_existing(self, tmp_path):
        target = str(tmp_path / "npc.md")
        atomic_write(target, "---\nname: 铁匠\nversion: 1\n---\n## 记录\n[第1天] 初始。")
        update_memory_file(filepath=target, append_content="\n[第2天] 新记录。")
        post = frontmatter.load(target)
        assert "第1天" in post.content
        assert "第2天" in post.content
        assert post["version"] == 2

    def test_update_fm_preserves_body(self, tmp_path):
        target = str(tmp_path / "npc.md")
        atomic_write(target, "---\nname: 铁匠\nhp: 80\nversion: 1\n---\n## 记录\n原有内容。")
        update_memory_file(filepath=target, frontmatter_updates={"hp": 75})
        post = frontmatter.load(target)
        assert post["hp"] == 75
        assert "原有内容" in post.content

    def test_auto_increment_version(self, tmp_path):
        target = str(tmp_path / "npc.md")
        update_memory_file(filepath=target, frontmatter_updates={"name": "铁匠", "version": 1})
        update_memory_file(filepath=target, frontmatter_updates={"hp": 80})
        assert frontmatter.load(target)["version"] == 2

    def test_auto_update_last_modified(self, tmp_path):
        target = str(tmp_path / "npc.md")
        update_memory_file(filepath=target, frontmatter_updates={"name": "铁匠"})
        assert "last_modified" in frontmatter.load(target).metadata
```

#### tests/test_memory/test_loader.py

```python
"""memory/loader.py 单元测试"""
import pytest
from pathlib import Path
from src.memory.loader import MemoryLoader


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    npc_dir = ws / "npcs"
    npc_dir.mkdir()
    (npc_dir / "铁匠.md").write_text(
        "---\nname: 铁匠\ntype: npc\nhp: 80\nrelationship_with_player: 30\n"
        "version: 3\nlast_modified: 2026-04-28T14:00:00\nmodified_by: engine\n"
        "tags: [npc, 黑铁镇]\n---\n\n## 初始印象\n[第1天] 铁匠铺的老板。\n\n"
        "## 交互记录\n[第2天] 玩家来买剑。\n", encoding="utf-8")
    return ws


class TestMemoryLoader:
    def test_load_index_compact(self, workspace):
        loader = MemoryLoader(str(workspace))
        result = loader.load_index(["npcs/铁匠"])
        assert "铁匠" in result
        assert "npc" in result
        assert "v3" in result
        assert "铁匠铺的老板" not in result

    def test_load_index_missing(self, workspace):
        loader = MemoryLoader(str(workspace))
        result = loader.load_index(["npcs/不存在"])
        assert "不存在" in result

    def test_load_activation_metadata_and_headings(self, workspace):
        loader = MemoryLoader(str(workspace))
        result = loader.load_activation(["npcs/铁匠"])
        assert "hp: 80" in result
        assert "初始印象" in result
        assert "交互记录" in result
        assert "铁匠铺的老板" not in result

    def test_load_activation_skips_meta(self, workspace):
        loader = MemoryLoader(str(workspace))
        result = loader.load_activation(["npcs/铁匠"])
        assert "last_modified" not in result
        assert "modified_by" not in result

    def test_load_execution_full(self, workspace):
        loader = MemoryLoader(str(workspace))
        result = loader.load_execution(["npcs/铁匠"])
        assert "铁匠铺的老板" in result
        assert "玩家来买剑" in result

    def test_load_execution_missing_skipped(self, workspace):
        loader = MemoryLoader(str(workspace))
        assert loader.load_execution(["npcs/不存在"]) == ""
```

#### tests/test_memory/test_manager.py

```python
"""memory/manager.py 单元测试"""
import pytest
from pathlib import Path
import frontmatter
from src.memory.manager import MemoryManager
from src.memory.file_io import atomic_write


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def manager(workspace):
    return MemoryManager(str(workspace))


class TestMemoryManager:
    def test_load_context_default(self, manager):
        result = manager.load_context(["npcs/铁匠"])
        assert "相关实体索引" in result

    def test_append_creates_file(self, manager, workspace):
        (workspace / "npcs").mkdir()
        manager.apply_memory_updates([
            {"file": "npcs/铁匠.md", "action": "append", "content": "\n[第1天] 初始记录。"}])
        post = frontmatter.load(str(workspace / "npcs" / "铁匠.md"))
        assert "第1天" in post.content
        assert post["version"] == 1

    def test_create_file(self, manager, workspace):
        manager.apply_memory_updates([
            {"file": "npcs/新NPC.md", "action": "create",
             "content": "---\nname: 新NPC\n---\n## 初始印象\n新角色。"}])
        assert (workspace / "npcs" / "新NPC.md").exists()

    def test_state_changes_updates_fm(self, manager, workspace):
        (workspace / "npcs").mkdir()
        atomic_write(str(workspace / "npcs" / "铁匠.md"),
                     "---\nname: 铁匠\nhp: 80\nversion: 1\n---\n记录")
        manager.apply_state_changes([
            {"file": "npcs/铁匠.md", "frontmatter": {"hp": 75, "version": 2}}])
        assert frontmatter.load(str(workspace / "npcs" / "铁匠.md"))["hp"] == 75

    def test_initialize_workspace(self, manager):
        manager.initialize_workspace()
        assert (manager.workspace / "npcs" / "_index.md").exists()
        assert (manager.workspace / "locations" / "_index.md").exists()

    def test_load_full_file(self, manager, workspace):
        (workspace / "npcs").mkdir()
        atomic_write(str(workspace / "npcs" / "铁匠.md"),
                     "---\nname: 铁匠\nhp: 80\n---\n## 记录\n内容。")
        result = manager.load_full_file("npcs/铁匠.md")
        assert result["frontmatter"]["name"] == "铁匠"
        assert "内容" in result["content"]

    def test_load_full_file_missing(self, manager):
        assert manager.load_full_file("npcs/不存在") is None
```

#### tests/test_skills/test_loader.py

```python
"""skills/loader.py 单元测试"""
import pytest
from pathlib import Path
from src.skills.loader import SkillLoader


@pytest.fixture
def skills_dir(tmp_path):
    sd = tmp_path / "skills"
    builtin = sd / "builtin" / "combat"
    builtin.mkdir(parents=True)
    (builtin / "SKILL.md").write_text(
        "---\nname: combat\ndescription: 战斗系统管理。\nversion: 1.0.0\n"
        "tags: [combat, battle]\ntriggers:\n  - event_type: combat_start\n"
        "  - keyword: [\"战斗\", \"攻击\"]\nallowed-tools:\n  - modify_stat\n---\n\n"
        "# 战斗系统\n\n## 伤害公式\n基础伤害 = 攻击力 - 防御力 * 0.5\n", encoding="utf-8")
    return sd


class TestSkillLoader:
    def test_discover(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        skills = loader.discover_all()
        assert len(skills) == 1
        assert skills[0].name == "combat"

    def test_cache(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        assert loader.discover_all() is loader.discover_all()

    def test_relevant_by_event(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        result = loader.get_relevant_skills(event_type="combat_start")
        assert len(result) == 1

    def test_relevant_by_keyword(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        result = loader.get_relevant_skills(user_input="我要攻击哥布林")
        assert len(result) == 1

    def test_no_match(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        assert loader.get_relevant_skills(user_input="你好铁匠") == []

    def test_load_content(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        assert "伤害公式" in loader.load_skill_content("combat")

    def test_load_nonexistent_none(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        assert loader.load_skill_content("nonexistent") is None

    def test_invalidate_cache(self, skills_dir):
        loader = SkillLoader(str(skills_dir))
        loader.discover_all()
        dialogue_dir = skills_dir / "builtin" / "dialogue"
        dialogue_dir.mkdir()
        (dialogue_dir / "SKILL.md").write_text(
            "---\nname: dialogue\ndescription: 对话系统\nversion: 1.0.0\n---\n\n# 对话", encoding="utf-8")
        assert len(loader.discover_all()) == 1
        loader.invalidate_cache()
        assert len(loader.discover_all()) == 2
```

#### tests/test_adapters/test_base.py

```python
"""adapters/base.py 单元测试"""
import pytest
from src.adapters.base import EngineAdapter, EngineEvent, CommandResult, ConnectionStatus


class TestEngineEvent:
    def test_create(self):
        event = EngineEvent(event_id="evt_001", timestamp="t", type="player_action",
            data={"raw_text": "hello"}, context_hints=["npcs/铁匠"], game_state={"location": "town"})
        assert event.event_id == "evt_001"
        assert len(event.context_hints) == 1

    def test_defaults(self):
        event = EngineEvent(event_id="e1", timestamp="t", type="test")
        assert event.data == {}
        assert event.context_hints == []


class TestCommandResult:
    def test_success(self):
        r = CommandResult(intent="no_op", status="success")
        assert r.new_value is None

    def test_rejected(self):
        r = CommandResult(intent="fly", status="rejected", reason="Unknown", suggestion="Check skills")
        assert "Unknown" in r.reason


class TestEngineAdapter:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            EngineAdapter()

    def test_concrete(self):
        class MockAdapter(EngineAdapter):
            @property
            def name(self): return "mock"
            @property
            def connection_status(self): return ConnectionStatus.DISCONNECTED
            async def connect(self, **kw): pass
            async def disconnect(self): pass
            async def send_commands(self, cmds): return []
            async def subscribe_events(self, types, cb): pass
            async def query_state(self, q): return {}
        assert MockAdapter().name == "mock"
```

#### tests/test_adapters/test_text_adapter.py

```python
"""adapters/text_adapter.py 单元测试"""
import pytest
from unittest.mock import MagicMock
from src.adapters.text_adapter import TextAdapter
from src.adapters.base import ConnectionStatus


@pytest.fixture
def mock_services():
    s = {k: MagicMock() for k in ("world", "player", "npc", "item", "quest")}
    s["world"].list_worlds.return_value = [{"id": "w1"}]
    s["player"].list_players.return_value = [{"id": "p1"}]
    s["player"].get_player.return_value = {"id": "p1", "hp": 100, "level": 1, "location": "town", "version": 1}
    s["npc"].get_npc.return_value = {"id": "npc_1", "name": "铁匠", "relationship": 30, "version": 3}
    s["npc"].list_npcs.return_value = [{"id": "npc_1", "name": "铁匠"}, {"id": "npc_2", "name": "药剂师"}]
    return s


@pytest.fixture
def adapter(mock_services):
    return TextAdapter(mock_services["world"], mock_services["player"],
        mock_services["npc"], mock_services["item"], mock_services["quest"])


class TestTextAdapter:
    def test_name(self, adapter):
        assert adapter.name == "text"

    @pytest.mark.asyncio
    async def test_connect(self, adapter):
        await adapter.connect()
        assert adapter.connection_status == ConnectionStatus.CONNECTED
        assert adapter._world_id == "w1"

    @pytest.mark.asyncio
    async def test_connect_no_world(self, mock_services):
        mock_services["world"].list_worlds.return_value = []
        a = TextAdapter(mock_services["world"], mock_services["player"],
            mock_services["npc"], mock_services["item"], mock_services["quest"])
        with pytest.raises(ConnectionError, match="没有可用的游戏世界"):
            await a.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        await adapter.connect()
        await adapter.disconnect()
        assert adapter.connection_status == ConnectionStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_no_op(self, adapter):
        await adapter.connect()
        results = await adapter.send_commands([{"intent": "no_op", "params": {}}])
        assert results[0].status == "success"

    @pytest.mark.asyncio
    async def test_unknown_intent(self, adapter):
        await adapter.connect()
        results = await adapter.send_commands([{"intent": "fly", "params": {}}])
        assert results[0].status == "rejected"

    @pytest.mark.asyncio
    async def test_update_relationship(self, adapter):
        await adapter.connect()
        results = await adapter.send_commands([
            {"intent": "update_npc_relationship", "params": {"npc_id": "npc_1", "change": 5}}])
        assert results[0].status == "success"
        assert results[0].new_value == 35
        assert results[0].state_changes is not None

    @pytest.mark.asyncio
    async def test_npc_not_found(self, adapter):
        await adapter.connect()
        adapter._npc.get_npc.return_value = None
        results = await adapter.send_commands([
            {"intent": "update_npc_relationship", "params": {"npc_id": "missing", "change": 5}}])
        assert results[0].status == "rejected"

    @pytest.mark.asyncio
    async def test_query_ping(self, adapter):
        assert (await adapter.query_state({"type": "ping"}))["pong"] is True

    @pytest.mark.asyncio
    async def test_query_player(self, adapter):
        await adapter.connect()
        assert (await adapter.query_state({"type": "player_stats"}))["hp"] == 100

    @pytest.mark.asyncio
    async def test_handle_input(self, adapter):
        await adapter.connect()
        event = await adapter.handle_player_input("和铁匠聊聊")
        assert event.type == "player_action"
        assert "npcs/铁匠" in event.context_hints

    @pytest.mark.asyncio
    async def test_handle_input_combat(self, adapter):
        await adapter.connect()
        event = await adapter.handle_player_input("攻击哥布林")
        assert event.type == "combat_start"
```

**验收**: `pytest tests/test_memory/ tests/test_skills/ tests/test_adapters/ -v` 全部通过

---

### 步骤 0.13 - 全量回归测试

**目的**: 确认删除冗余 + 新增模块后，整体功能正常

**执行**:
1. 运行全量测试：`pytest tests/ -v`
2. 确认所有测试通过
3. 记录通过的测试总数

**验收**: 所有测试通过，0 个失败

---

## P0 完成检查清单

- [ ] Step 0.1: V1 冗余模块已删除（tools/, context_manager.py, plugins/）
- [ ] Step 0.2: V2 目录结构创建完毕
- [ ] Step 0.3: python-frontmatter 安装成功
- [ ] Step 0.4: memory/file_io.py 实现 + 10 个测试通过
- [ ] Step 0.5: memory/loader.py 实现 + 6 个测试通过
- [ ] Step 0.6: memory/manager.py 实现 + 7 个测试通过
- [ ] Step 0.7: skills/loader.py 实现 + 8 个测试通过
- [ ] Step 0.8: adapters/base.py 实现 + 5 个测试通过
- [ ] Step 0.9: adapters/text_adapter.py 实现 + 11 个测试通过
- [ ] Step 0.10: 5 个内置 SKILL.md 创建完毕
- [ ] Step 0.11: workspace 目录和索引文件初始化完毕
- [ ] Step 0.12: 新模块测试全部通过 (>=47 个)
- [ ] Step 0.13: 全量回归测试通过
