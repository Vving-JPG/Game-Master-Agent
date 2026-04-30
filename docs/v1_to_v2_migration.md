# V1 → V2 迁移指南

> **版本**: v2.0-draft
> **日期**: 2026-04-28
> **前置文档**: `architecture_v2.md`
> **关联文档**: 所有 V2 设计文档
> **策略**: Strangler Fig Pattern (绞杀者模式)

---

## 1. 迁移策略

### 1.1 Strangler Fig 模式

不推翻 V1 重写，而是**增量替换**：

```
V1 代码库
├── 保留模块 (不动)
├── 重构模块 (改接口，保留实现)
├── 重写模块 (删除，用新代码替代)
└── 新增模块 (全新代码)
```

**核心原则**:
1. **每一步都可运行** — 改完一步，测试通过，再进行下一步
2. **V1 测试先行** — 先确保 179 个测试全部通过，再开始改
3. **新模块独立** — 新增的 memory/、skills/、adapters/ 目录不影响现有代码
4. **接口先行** — 先定义新接口，再逐步迁移实现

### 1.2 迁移顺序

```
Phase 1: 基础设施 (不影响 V1)
    ├── 新建 memory/ 模块
    ├── 新建 skills/ 模块
    ├── 新建 adapters/ 模块
    └── 新建 workspace/ 目录

Phase 2: 核心重构 (改 Agent 主循环)
    ├── 重写 game_master.py (事件驱动)
    ├── 新增 command_parser.py
    ├── 新增 prompt_builder.py
    └── 修改 context_manager.py → MemoryManager

Phase 3: API 扩展 (新增端点)
    ├── 新增 workspace API
    ├── 新增 skills API
    ├── 新增 SSE 流式端点
    └── 新增 agent 控制端点

Phase 4: 前端 WorkBench (独立项目)
    ├── 初始化 Vue 项目
    ├── 文件浏览器 + MD 编辑器
    ├── Agent 监控 + 对话调试
    └── SSE 事件流

Phase 5: 清理 (删除 V1 遗留)
    ├── 删除旧 tools/executor.py
    ├── 删除旧 context_manager.py
    └── 更新测试
```

---

## 2. 模块级决策

### 2.1 决策总表

| V1 模块 | 路径 | 决策 | 说明 |
|---------|------|------|------|
| `llm_client.py` | `src/services/` | **保留** | DeepSeek API 封装，V2 直接复用 |
| `cache.py` | `src/services/` | **保留** | LRU 缓存，通用组件 |
| `model_router.py` | `src/services/` | **保留** | 模型路由，通用组件 |
| `game_master.py` | `src/agent/` | **重写** | 从 while 循环改为事件驱动 |
| `context_manager.py` | `src/services/` | **删除** | 被 memory/ 模块替代 |
| `tools/executor.py` | `src/tools/` | **删除** | 被 skills/ 模块替代 |
| `tools/*.py` | `src/tools/` | **删除** | 所有 V1 Tool 函数 |
| `api/app.py` | `src/api/` | **保留+扩展** | 新增路由 |
| `models/database.py` | `src/models/` | **保留** | SQLite 连接管理 |
| `models/world_repo.py` | `src/models/` | **保留** | 引擎侧数据 |
| `models/npc_repo.py` | `src/models/` | **保留** | 引擎侧数据 |
| `models/player_repo.py` | `src/models/` | **保留** | 引擎侧数据 |
| `models/item_repo.py` | `src/models/` | **保留** | 引擎侧数据 |
| `models/quest_repo.py` | `src/models/` | **保留** | 引擎侧数据 |
| `models/location_repo.py` | `src/models/` | **保留** | 引擎侧数据 |
| `models/log_repo.py` | `src/models/` | **保留** | 日志记录 |
| `plugins/` | `src/plugins/` | **评估** | 可能与 Skill 系统对齐 |

### 2.2 新增模块

| 模块 | 路径 | 说明 |
|------|------|------|
| `memory/manager.py` | `src/memory/` | MemoryManager 主类 |
| `memory/loader.py` | `src/memory/` | 渐进式加载器 |
| `memory/file_io.py` | `src/memory/` | 原子读写 + YAML/MD 解析 |
| `memory/compressor.py` | `src/memory/` | 定期压缩 |
| `memory/indexer.py` | `src/memory/` | 索引管理 |
| `skills/loader.py` | `src/skills/` | Skill 发现与加载 |
| `skills/registry.py` | `src/skills/` | Skill 注册表 |
| `adapters/base.py` | `src/adapters/` | EngineAdapter 抽象基类 |
| `adapters/text_adapter.py` | `src/adapters/` | MUD 适配器 |
| `adapters/godot_adapter.py` | `src/adapters/` | Godot 适配器 (V3) |
| `agent/command_parser.py` | `src/agent/` | JSON 输出解析 |
| `agent/prompt_builder.py` | `src/agent/` | Prompt 组装 |
| `api/routes/workspace.py` | `src/api/routes/` | Workspace 文件 API |
| `api/routes/skills.py` | `src/api/routes/` | Skill 管理 API |
| `api/routes/agent.py` | `src/api/routes/` | Agent 交互 API |
| `api/sse.py` | `src/api/` | SSE 流式推送 |

---

## 3. V1 代码分析

### 3.1 llm_client.py (保留)

V1 的 LLM 客户端封装，V2 直接复用。需要注意的改动：

```python
# V1 现有接口
class LLMClient:
    async def chat(self, messages, tools=None, model=None) -> str:
        """返回字符串"""
        ...

# V2 需要新增流式接口
class LLMClient:
    async def chat(self, messages, tools=None, model=None) -> str:
        """保留 V1 接口"""
        ...

    async def stream(self, messages, tools=None, model=None):
        """新增: 流式接口，yield SSE 事件"""
        ...
```

**改动量**: 小 — 只需新增 `stream()` 方法，不修改现有 `chat()`

### 3.2 game_master.py (重写)

V1 的核心循环：

```python
# V1: 同步 while 循环，直接读用户输入，直接写数据库
class GameMaster:
    def run(self):
        while True:
            user_input = input("> ")
            response = self.llm.chat(messages)
            self.context_manager.update_context(response)
            # 直接调用 tool 函数
            self.executor.execute(response)
```

V2 的事件驱动模式：

```python
# V2: 异步事件驱动，通过适配器收发
class GameMaster:
    def __init__(self, memory_manager, skill_loader, adapter, llm_client):
        self.memory = memory_manager
        self.skills = skill_loader
        self.adapter = adapter
        self.llm = llm_client

    async def handle_event(self, event: EngineEvent) -> AgentResponse:
        # 1. 加载记忆
        memory_context = self.memory.load_context(event.context_hints)

        # 2. 加载 Skill
        relevant_skills = self.skills.get_relevant_skills(
            event_type=event.type,
            user_input=event.data.get("raw_text", "")
        )

        # 3. 组装 Prompt
        messages = self.prompt_builder.build(
            system_prompt=self.system_prompt,
            memory=memory_context,
            skills=relevant_skills,
            event=event,
            history=self.history
        )

        # 4. 调用 LLM (流式)
        response = await self._stream_and_parse(messages)

        # 5. 更新记忆
        self.memory.apply_memory_updates(response.memory_updates)

        # 6. 发送指令到引擎
        results = await self.adapter.send_commands(response.commands)

        # 7. 引擎更新 YAML
        state_changes = [r.state_changes for r in results if r.state_changes]
        self.memory.apply_state_changes(state_changes)

        # 8. 更新对话历史
        self.history.append(event, response)

        return response
```

**改动量**: 大 — 完全重写，但可以保留 V1 的 while 循环作为 TextAdapter 的命令行入口

### 3.3 context_manager.py (删除)

V1 的上下文管理器直接操作 SQLite：

```python
# V1: SQLite 上下文管理
class ContextManager:
    def get_context(self, world_id, player_id) -> str:
        # 从 SQLite 读取 NPC、地点、任务等数据
        # 拼接成大段文本
        ...
```

V2 用 MemoryManager 替代：

```python
# V2: .md 文件记忆管理
class MemoryManager:
    def load_context(self, context_hints, depth="auto") -> str:
        # 从 .md 文件渐进式加载
        ...
```

**改动量**: 完全删除，新写替代

### 3.4 tools/executor.py (删除)

V1 的 Tool 注册和执行系统：

```python
# V1: Python 函数注册
TOOL_REGISTRY = {}

def register_tool(name, func):
    TOOL_REGISTRY[name] = func

@register_tool("get_npc")
def get_npc(world_id, npc_id):
    return npc_repo.get_npc(world_id, npc_id)
```

V2 用 Skill 系统替代：

```python
# V2: .md 文件 Skill
# skills/builtin/combat/SKILL.md 定义了 combat Skill
# Agent 通过 LLM 理解 Skill 规则，生成 commands
```

**改动量**: 完全删除，新写替代

---

## 4. 逐步迁移步骤

### Phase 1: 基础设施 (不影响 V1)

**目标**: 创建新模块，不修改任何 V1 代码，确保 V1 179 个测试仍然通过。

#### Step 1.1: 创建目录结构

```bash
mkdir -p src/memory
mkdir -p src/skills
mkdir -p src/adapters
mkdir -p src/agent
mkdir -p src/api/routes
mkdir -p workspace/npcs
mkdir -p workspace/locations
mkdir -p workspace/story
mkdir -p workspace/quests
mkdir -p workspace/items
mkdir -p workspace/player
mkdir -p workspace/session
mkdir -p skills/builtin/combat
mkdir -p skills/builtin/dialogue
mkdir -p skills/builtin/quest
mkdir -p skills/builtin/exploration
mkdir -p skills/builtin/narration
mkdir -p skills/agent_created
```

#### Step 1.2: 安装新依赖

```bash
pip install python-frontmatter --break-system-packages
```

#### Step 1.3: 实现 memory/file_io.py

原子写入 + YAML/MD 解析（参考 `memory_system.md` 第 6 节）

#### Step 1.4: 实现 memory/manager.py

MemoryManager 完整实现（参考 `memory_system.md` 第 7 节）

#### Step 1.5: 实现 memory/loader.py

渐进式加载器（参考 `memory_system.md` 第 3 节）

#### Step 1.6: 实现 skills/loader.py

Skill 发现与加载（参考 `skill_system.md` 第 3 节）

#### Step 1.7: 实现 adapters/base.py

EngineAdapter 抽象基类（参考 `engine_adapter.md` 第 2 节）

#### Step 1.8: 实现 adapters/text_adapter.py

TextAdapter 实现（参考 `engine_adapter.md` 第 3 节）

#### Step 1.9: 创建内置 Skill 文件

```
skills/builtin/combat/SKILL.md
skills/builtin/dialogue/SKILL.md
skills/builtin/quest/SKILL.md
skills/builtin/exploration/SKILL.md
skills/builtin/narration/SKILL.md
```

#### Step 1.10: 初始化 workspace

创建 `_index.md` 索引文件和 `index.md` 全局索引

#### Step 1.11: 编写新模块测试

```
tests/test_memory/test_file_io.py
tests/test_memory/test_manager.py
tests/test_memory/test_loader.py
tests/test_skills/test_loader.py
tests/test_adapters/test_base.py
tests/test_adapters/test_text_adapter.py
```

**验收**: V1 的 179 个测试全部通过 + 新模块测试全部通过

---

### Phase 2: 核心重构

**目标**: 重写 Agent 主循环，接入新模块

#### Step 2.1: 实现 agent/command_parser.py

JSON 输出解析器（参考 `communication_protocol.md` 第 8.3 节）

#### Step 2.2: 实现 agent/prompt_builder.py

Prompt 组装器

```python
class PromptBuilder:
    def build(self, system_prompt, memory, skills, event, history) -> list[dict]:
        """组装完整的 messages 列表"""
        messages = [{"role": "system", "content": system_prompt}]

        # 添加 Skill 内容
        if skills:
            skill_text = assemble_skills_prompt(skills)
            messages.append({"role": "system", "content": skill_text})

        # 添加记忆上下文
        if memory:
            messages.append({"role": "system", "content": f"## 当前记忆上下文\n{memory}"})

        # 添加对话历史
        for msg in history.get_recent(limit=10):
            messages.append(msg)

        # 添加当前事件
        event_text = f"玩家操作: {event.data.get('raw_text', '')}"
        messages.append({"role": "user", "content": event_text})

        return messages
```

#### Step 2.3: 重写 agent/game_master.py

从 V1 的 while 循环改为事件驱动（参考 `architecture_v2.md` 第 3.2 节）

#### Step 2.4: 修改 LLMClient 新增 stream() 方法

```python
# 在现有 llm_client.py 中新增
async def stream(self, messages, tools=None, model=None):
    """流式调用，yield (event_type, data) 元组"""
    ...
```

#### Step 2.5: 集成测试

编写端到端测试：事件输入 → Agent 处理 → JSON 输出 → 指令执行 → 记忆更新

**验收**: 新的 Agent 主循环能处理 player_action 事件，返回标准 JSON 响应

---

### Phase 3: API 扩展

**目标**: 新增 HTTP 端点，支持 WorkBench

#### Step 3.1: 新增 api/routes/workspace.py

Workspace 文件操作 API（参考 `workspace_design.md` 第 4.2 节）

#### Step 3.2: 新增 api/routes/skills.py

Skill 管理 API（参考 `skill_system.md` 第 6 节）

#### Step 3.3: 新增 api/routes/agent.py

Agent 交互和控制 API（参考 `communication_protocol.md` 第 6 节）

#### Step 3.4: 新增 api/sse.py

SSE 流式推送端点（参考 `communication_protocol.md` 第 5 节）

#### Step 3.5: 注册新路由到 app.py

```python
# 在现有 app.py 中添加
from src.api.routes import workspace, skills, agent

app.include_router(workspace.router)
app.include_router(skills.router)
app.include_router(agent.router)
```

#### Step 3.6: API 测试

**验收**: 所有新 API 端点可通过 curl/Postman 正常访问

---

### Phase 4: 前端 WorkBench

**目标**: 创建 Vue 管理端

#### Step 4.1: 初始化 Vue 项目

```bash
cd workbench
npm create vite@latest . -- --template vue-ts
npm install naive-ui @vicons/ionicons5 axios md-editor-v3
```

#### Step 4.2: 实现文件浏览器

FileTree.vue + 后端 API（参考 `workspace_design.md` 第 4 节）

#### Step 4.3: 实现 MD 编辑器

MdEditor.vue（参考 `workspace_design.md` 第 5 节）

#### Step 4.4: 实现 Agent 监控

AgentStatus.vue + SSEEventLog.vue（参考 `workspace_design.md` 第 6 节）

#### Step 4.5: 实现对话调试

ChatDebug.vue（参考 `workspace_design.md` 第 7 节）

**验收**: WorkBench 能连接 Agent 后端，浏览文件，发送调试事件

---

### Phase 5: 清理

**目标**: 删除 V1 遗留代码

#### Step 5.1: 删除旧模块

```bash
rm -rf src/tools/
rm src/services/context_manager.py
```

#### Step 5.2: 更新测试

- 删除 V1 Tool 相关测试
- 更新 game_master 测试为新的事件驱动模式
- 确保所有测试通过

#### Step 5.3: 更新依赖

清理 requirements.txt，移除不再需要的依赖

**验收**: 所有测试通过，代码库无 V1 遗留

---

## 5. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| V1 测试在迁移中失败 | 阻塞开发 | Phase 1 不改 V1 代码，先确保基线 |
| LLM 输出格式不稳定 | JSON 解析失败 | 4 级容错策略 (参考 communication_protocol.md) |
| .md 文件并发写入冲突 | 数据损坏 | 原子写入 + asyncio 锁 |
| workspace 目录被误删 | 记忆丢失 | 定期备份 + WorkBench 确认对话框 |
| DeepSeek API 变更 | 流式调用失败 | 封装 LLMClient，集中处理 |
| Vue 前端与后端 API 不一致 | 功能异常 | 先定义 API 契约，再分别实现 |

---

## 6. V1 保留代码的改动清单

以下是 V1 保留模块需要的最小改动：

### llm_client.py

```python
# 新增 stream() 方法 (约 50 行)
# 不修改现有 chat() 方法
```

### api/app.py

```python
# 新增路由注册 (约 5 行)
from src.api.routes import workspace, skills, agent
app.include_router(workspace.router)
app.include_router(skills.router)
app.include_router(agent.router)
```

### models/ (全部保留，不改)

所有 repo 文件保持原样，TextAdapter 会调用它们。

---

## 7. 迁移检查清单

- [ ] Phase 1: 基础设施
  - [ ] 1.1 创建目录结构
  - [ ] 1.2 安装 python-frontmatter
  - [ ] 1.3 实现 memory/file_io.py
  - [ ] 1.4 实现 memory/manager.py
  - [ ] 1.5 实现 memory/loader.py
  - [ ] 1.6 实现 skills/loader.py
  - [ ] 1.7 实现 adapters/base.py
  - [ ] 1.8 实现 adapters/text_adapter.py
  - [ ] 1.9 创建内置 Skill 文件
  - [ ] 1.10 初始化 workspace
  - [ ] 1.11 新模块测试通过
  - [ ] **V1 179 个测试仍然通过**

- [ ] Phase 2: 核心重构
  - [ ] 2.1 实现 command_parser.py
  - [ ] 2.2 实现 prompt_builder.py
  - [ ] 2.3 重写 game_master.py
  - [ ] 2.4 LLMClient 新增 stream()
  - [ ] 2.5 集成测试通过

- [ ] Phase 3: API 扩展
  - [ ] 3.1 workspace API
  - [ ] 3.2 skills API
  - [ ] 3.3 agent API
  - [ ] 3.4 SSE 端点
  - [ ] 3.5 注册路由
  - [ ] 3.6 API 测试通过

- [ ] Phase 4: WorkBench
  - [ ] 4.1 初始化 Vue 项目
  - [ ] 4.2 文件浏览器
  - [ ] 4.3 MD 编辑器
  - [ ] 4.4 Agent 监控
  - [ ] 4.5 对话调试

- [ ] Phase 5: 清理
  - [ ] 5.1 删除旧模块
  - [ ] 5.2 更新测试
  - [ ] 5.3 清理依赖
  - [ ] **所有测试通过**
