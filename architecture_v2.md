# V2 架构总览：通用游戏驱动 Agent

> **版本**: v2.0-draft
> **日期**: 2026-04-28
> **状态**: 设计阶段
> **前置文档**: 无
> **关联文档**: `communication_protocol.md`, `memory_system.md`, `skill_system.md`, `engine_adapter.md`, `workspace_design.md`, `v1_to_v2_migration.md`

---

## 1. 项目定位

### 1.1 核心目标

构建一个**通用游戏驱动 Agent 服务**——类似 Trae 驱动代码开发，我们的 Agent 驱动游戏运行。

Agent 不是游戏本身，而是一个**独立的服务层**，通过标准化协议与任意游戏引擎通信。

```
┌─────────────────────────────────────────────────────┐
│                   V2 核心架构                        │
│                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐  │
│  │ 游戏引擎  │◄──►│  Agent   │◄──►│ WorkBench    │  │
│  │ (任意)    │    │  服务    │    │ (Vue 管理端)  │  │
│  └──────────┘    └──────────┘    └──────────────┘  │
│       ▲               ▲                             │
│       │               │                             │
│  EngineAdapter    Agent Workspace                   │
│  (适配层)         (.md 记忆文件)                     │
└─────────────────────────────────────────────────────┘
```

### 1.2 V1 → V2 核心变化

| 维度 | V1 (MUD 游戏) | V2 (通用 Agent) |
|------|--------------|----------------|
| **本质** | 做了一个 MUD 文字游戏 | 做了一个驱动游戏的 Agent 服务 |
| **Agent 角色** | Agent 就是游戏本身 | Agent 是独立服务，通过协议驱动游戏 |
| **记忆存储** | SQLite 数据库 | .md 文件 (磁盘) + SQLite (引擎侧事实) |
| **输出格式** | 纯文本回复 | JSON 命令流 (narrative + commands) |
| **引擎连接** | 硬编码在 Agent 内部 | EngineAdapter 适配层 (可替换) |
| **能力扩展** | Tool 函数注册 | Skill 文件 (.md) |
| **管理界面** | 简单 API | Vue WorkBench (类 Trae) |

### 1.3 设计原则

1. **Agent 是服务，不是游戏** — Agent 不包含游戏逻辑，只负责"理解意图 → 生成叙事 → 发出指令"
2. **协议驱动** — 所有交互通过 JSON 协议，引擎和 Agent 完全解耦
3. **渐进式披露** — Agent 记忆按需加载，不一次性塞满上下文窗口
4. **Skill 即文件** — 能力定义是 .md 文件，开发者或 Agent 都能创建
5. **可观测** — WorkBench 实时监控 Agent 状态、记忆、决策过程

---

## 2. 系统架构

### 2.1 三大组件

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌─────────────────┐     ┌─────────────────────────────────┐   │
│  │   WorkBench     │     │         Agent Service            │   │
│  │   (Vue 3)       │     │                                 │   │
│  │                 │     │  ┌───────────┐  ┌────────────┐  │   │
│  │  ┌───────────┐  │     │  │  LLM      │  │  Memory    │  │   │
│  │  │ 文件浏览器 │  │     │  │  Client   │  │  Manager   │  │   │
│  │  └───────────┘  │     │  │(DeepSeek) │  │ (.md文件)  │  │   │
│  │  ┌───────────┐  │     │  └───────────┘  └────────────┘  │   │
│  │  │ MD编辑器  │  │     │  ┌───────────┐  ┌────────────┐  │   │
│  │  └───────────┘  │     │  │  Skill    │  │  Command   │  │   │
│  │  ┌───────────┐  │     │  │  Loader   │  │  Parser    │  │   │
│  │  │ Agent监控 │  │     │  └───────────┘  └────────────┘  │   │
│  │  └───────────┘  │     │                                 │   │
│  │  ┌───────────┐  │     │  ┌───────────┐  ┌────────────┐  │   │
│  │  │ 对话调试  │  │     │  │  Engine   │  │  Event     │  │   │
│  │  └───────────┘  │     │  │  Adapter  │  │  Handler   │  │   │
│  └─────────────────┘     │  └───────────┘  └────────────┘  │   │
│         │                └─────────────────────────────────┘   │
│         │                           │                         │
│         │                    ┌──────┴──────┐                  │
│         │                    │  FastAPI    │                  │
│         └────────────────────┤  HTTP API   │                  │
│                              └──────┬──────┘                  │
│                                     │                         │
│                              ┌──────┴──────┐                  │
│                              │  Game       │                  │
│                              │  Engine     │                  │
│                              │  (Text/Godot)│                 │
│                              └─────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 组件职责

#### Agent Service (Python)

Agent 的核心服务，包含以下模块：

| 模块 | 职责 | V1 对应 |
|------|------|---------|
| `LLMClient` | DeepSeek API 调用 (流式 + tool_calls) | `llm_client.py` (保留) |
| `MemoryManager` | .md 记忆文件的读写、版本管理、渐进式加载 | `context_manager.py` (重写) |
| `SkillLoader` | 发现、加载、管理 Skill 文件 | `executor.py` (重写) |
| `CommandParser` | 解析 Agent 的 JSON 输出 (narrative + commands) | 新增 |
| `EngineAdapter` | 抽象引擎连接层 | 新增 |
| `EventHandler` | 接收引擎事件，组装上下文，触发 Agent 回合 | `game_master.py` (重写) |
| `ModelRouter` | deepseek-chat / deepseek-reasoner 路由 | `model_router.py` (保留) |
| `CacheService` | LRU 缓存 | `cache.py` (保留) |

#### WorkBench (Vue 3 + Naive UI)

Agent 的管理和调试界面，参考 Trae Workspace + 腾讯 WorkBuddy：

| 面板 | 功能 |
|------|------|
| 文件浏览器 | 浏览 Agent Workspace 中的 .md 文件 |
| MD 编辑器 | 查看/编辑记忆文件、Skill 文件 |
| Agent 监控 | 实时查看 Agent 状态、当前上下文、token 用量 |
| 对话调试 | 手动发送事件，查看 Agent 响应 |
| 系统提示词 | 编辑 Agent 的 system prompt |

#### Game Engine (TextAdapter / GodotAdapter)

游戏引擎端，通过 EngineAdapter 与 Agent 通信：

| 适配器 | 说明 | 优先级 |
|--------|------|--------|
| `TextAdapter` | MUD 文字游戏演示，命令行交互 | V2 首要 |
| `GodotAdapter` | Godot 游戏引擎 HTTP/WS 连接 | V3 |

---

## 3. 核心数据流

### 3.1 单回合交互流程

```
玩家操作 ──► 游戏引擎 ──► EngineAdapter ──► EventHandler
                                                 │
                                          ┌──────┴──────┐
                                          │ 1. 接收事件  │
                                          │ 2. 加载记忆  │
                                          │ 3. 加载Skill │
                                          │ 4. 组装Prompt│
                                          │ 5. 调用LLM   │
                                          │ 6. 解析输出  │
                                          │ 7. 更新记忆  │
                                          │ 8. 发送指令  │
                                          └──────┬──────┘
                                                 │
                                          ┌──────┴──────┐
                                          │ JSON 输出:   │
                                          │ {            │
                                          │   narrative, │
                                          │   commands,  │
                                          │   memory_updates │
                                          │ }            │
                                          └──────┬──────┘
                                                 │
              ◄── 叙事文本(SSE流式) ────── EventHandler
              ◄── 游戏指令(批量) ────────── EngineAdapter ──► 游戏引擎
```

### 3.2 详细步骤

```python
# 伪代码 - 单回合处理
async def handle_turn(event: EngineEvent):
    # Step 1: 接收引擎事件
    # event = {"type": "player_action", "raw_text": "和铁匠聊聊", "context_hints": ["npcs/铁匠"]}

    # Step 2: 根据 context_hints 渐进式加载记忆
    memory_blocks = await memory_manager.load_context(event["context_hints"])
    # 返回: ["---\nname: 铁匠\nhp: 80\n---\n## 交互记录\n[第1天]..."]

    # Step 3: 加载相关 Skill
    skills = await skill_loader.get_relevant_skills(event)

    # Step 4: 组装 system prompt + 记忆 + Skill + 用户输入
    messages = assemble_prompt(system_prompt, memory_blocks, skills, event)

    # Step 5: 调用 LLM (流式)
    async for chunk in llm_client.stream(messages):
        # 实时推送 narrative 文本到前端 (SSE)
        await sse_send(chunk)

    # Step 6: 解析完整输出为 JSON
    response = command_parser.parse(full_response)
    # response = {"narrative": "...", "commands": [...], "memory_updates": [...]}

    # Step 7: Agent 更新记忆文件
    for update in response["memory_updates"]:
        await memory_manager.append_to_file(update["file"], update["content"])

    # Step 8: 发送 commands 到引擎
    results = await engine_adapter.send_commands(response["commands"])

    # Step 9: 引擎更新 YAML Front Matter (事实数据)
    for result in results:
        if result.get("state_changes"):
            await memory_manager.update_frontmatter(result["state_changes"])

    return response
```

---

## 4. 目录结构

### 4.1 V2 项目结构

```
worldSim-master/
├── src/
│   ├── agent/                    # Agent 核心逻辑
│   │   ├── __init__.py
│   │   ├── game_master.py        # 主循环 (重写: 事件驱动)
│   │   ├── command_parser.py     # JSON 输出解析 (新增)
│   │   └── prompt_builder.py     # Prompt 组装 (新增)
│   │
│   ├── memory/                   # 记忆系统 (全新)
│   │   ├── __init__.py
│   │   ├── manager.py            # MemoryManager 主类
│   │   ├── loader.py             # 渐进式加载器
│   │   ├── indexer.py            # 记忆索引 (B-tree 层级)
│   │   ├── compressor.py         # 定期压缩 (LLM 摘要)
│   │   └── file_io.py            # 原子读写 + YAML/MD 解析
│   │
│   ├── skills/                   # Skill 系统 (全新)
│   │   ├── __init__.py
│   │   ├── loader.py             # Skill 发现与加载
│   │   ├── registry.py           # Skill 注册表
│   │   └── builtin/              # 内置 Skill
│   │       ├── combat.md
│   │       ├── dialogue.md
│   │       └── quest.md
│   │
│   ├── adapters/                 # 引擎适配层 (全新)
│   │   ├── __init__.py
│   │   ├── base.py               # EngineAdapter 抽象基类
│   │   ├── text_adapter.py       # MUD 文字适配器
│   │   └── godot_adapter.py      # Godot 适配器 (V3)
│   │
│   ├── services/                 # 基础服务 (保留)
│   │   ├── llm_client.py         # DeepSeek API (保留)
│   │   ├── cache.py              # LRU 缓存 (保留)
│   │   └── model_router.py       # 模型路由 (保留)
│   │
│   ├── models/                   # 数据模型 (保留引擎侧)
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── world_repo.py
│   │   ├── npc_repo.py
│   │   ├── item_repo.py
│   │   ├── quest_repo.py
│   │   ├── location_repo.py
│   │   ├── player_repo.py
│   │   └── log_repo.py
│   │
│   └── api/                      # HTTP API (保留+扩展)
│       ├── app.py                # FastAPI 主应用
│       ├── routes/
│       │   ├── agent.py          # Agent 交互端点 (新增)
│       │   ├── workspace.py      # Workspace 文件操作 (新增)
│       │   ├── skills.py         # Skill 管理 (新增)
│       │   └── admin.py          # 管理端点 (保留)
│       └── sse.py                # SSE 流式推送 (新增)
│
├── workspace/                    # Agent Workspace (磁盘)
│   ├── index.md                  # 记忆索引文件
│   ├── npcs/                     # NPC 记忆
│   │   ├── _index.md
│   │   ├── 铁匠.md
│   │   └── 药剂师.md
│   ├── locations/                # 地点记忆
│   │   ├── _index.md
│   │   ├── 铁匠铺.md
│   │   └── 森林.md
│   ├── story/                    # 剧情记忆
│   │   ├── _index.md
│   │   └── 哥布林_威胁.md
│   ├── quests/                   # 任务记忆
│   │   └── ...
│   ├── player/                   # 玩家记忆
│   │   └── profile.md
│   └── session/                  # 会话记忆
│       └── current.md
│
├── skills/                       # Skill 文件目录
│   ├── builtin/                  # 开发者创建
│   │   ├── combat/SKILL.md
│   │   ├── dialogue/SKILL.md
│   │   └── quest/SKILL.md
│   └── agent_created/            # Agent 自主创建
│       └── ...
│
├── workbench/                    # Vue WorkBench 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── Workspace.vue     # 文件浏览器 + MD 编辑器
│   │   │   ├── Monitor.vue       # Agent 监控面板
│   │   │   ├── Chat.vue          # 对话调试
│   │   │   └── Settings.vue      # 系统设置
│   │   ├── components/
│   │   │   ├── FileTree.vue      # 文件树 (Naive UI Tree)
│   │   │   ├── MdEditor.vue      # Markdown 编辑器
│   │   │   ├── AgentStatus.vue   # Agent 状态卡片
│   │   │   └── TokenCounter.vue  # Token 用量
│   │   └── ...
│   └── ...
│
├── tests/                        # 测试
│   ├── test_memory/
│   ├── test_skills/
│   ├── test_adapters/
│   └── test_api/
│
├── prompts/                      # 系统提示词
│   └── system_prompt.md          # Agent 主提示词
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

### 4.2 关键新增依赖

```
# V2 新增依赖
python-frontmatter>=1.1.0    # YAML Front Matter + Markdown 解析
watchdog>=4.0.0              # 文件系统监控 (WorkBench 实时刷新)
```

---

## 5. 技术栈确认

| 层 | 技术 | 说明 |
|----|------|------|
| Agent 后端 | Python 3.11+ | FastAPI + asyncio |
| LLM | DeepSeek | deepseek-chat (默认) + deepseek-reasoner (复杂推理) |
| 记忆存储 | .md 文件 (磁盘) | YAML Front Matter + Markdown body |
| 引擎侧数据 | SQLite | NPC/物品/任务等结构化数据 |
| 前端管理 | Vue 3 + Naive UI | WorkBench 管理端 |
| 前端游戏 | Godot (V3) | V2 先用 TextAdapter 演示 |
| Skill 标准 | SKILL.md | Anthropic 主导的开放标准 |
| 文件解析 | python-frontmatter | YAML + MD 双层解析 |
| 原子写入 | tempfile + os.replace | 防止写入中断导致文件损坏 |

---

## 6. 部署架构

```
┌──────────────────────────────────────────┐
│              本地机器                      │
│                                          │
│  ┌────────────┐   ┌──────────────────┐   │
│  │  FastAPI   │   │  Vue WorkBench   │   │
│  │  :8000     │◄──►  :5173 (dev)     │   │
│  └─────┬──────┘   └──────────────────┘   │
│        │                                 │
│        │ HTTP / SSE                      │
│        │                                 │
│  ┌─────┴──────────────────────────┐      │
│  │        Agent Service            │      │
│  │  ┌──────────┐  ┌────────────┐  │      │
│  │  │ LLM      │  │ Memory     │  │      │
│  │  │ Client   │  │ Manager    │  │      │
│  │  └────┬─────┘  └─────┬──────┘  │      │
│  └───────┼───────────────┼─────────┘      │
│          │               │                │
│          │ HTTPS         │ 文件 I/O       │
│          ▼               ▼                │
│  ┌──────────────┐  ┌──────────┐          │
│  │ DeepSeek API │  │ workspace/│          │
│  │ (云端)       │  │ (.md文件) │          │
│  └──────────────┘  └──────────┘          │
│                                          │
│  ┌──────────────┐                        │
│  │ TextAdapter  │  (命令行 MUD 演示)     │
│  │ :8001/ws     │                        │
│  └──────────────┘                        │
└──────────────────────────────────────────┘
```

**关键决策**:
- 本地部署，同一台机器
- V2 单人游戏，V3 再考虑多人
- Agent Service 和 WorkBench 通过 HTTP API 通信
- DeepSeek API 通过 HTTPS 调用（云端）
- workspace/ 目录存放在本地磁盘

---

## 7. 关键设计决策记录

以下决策在架构讨论中已确认，记录在此供后续参考：

| # | 决策 | 选择 | 原因 |
|---|------|------|------|
| D1 | Agent 数量 | 单 Agent | 用户明确反对多 Agent，单 GM 足够 |
| D2 | 记忆存储 | .md 文件 | 类似 Trae workspace，可视化、可编辑 |
| D3 | 事实数据 | SQLite + YAML FM | 引擎侧用 SQLite，Agent 侧用 YAML Front Matter |
| D4 | 输出格式 | JSON 命令流 | narrative + commands + memory_updates |
| D5 | 引擎连接 | Adapter 模式 | TextAdapter 先行，Godot 后续 |
| D6 | Skill 格式 | SKILL.md | Anthropic 开放标准，27+ Agent 支持 |
| D7 | Skill 来源 | 混合 | 开发者 + Agent 都能创建 |
| D8 | 管理前端 | Vue 3 + Naive UI | AI 写得快，便于测试 |
| D9 | 游戏前端 | Godot (V3) | V2 用 TextAdapter 演示 |
| D10 | 重构方式 | Strangler Fig | 增量重构，不是推翻重来 |
| D11 | 叙事推送 | SSE 流式 | 先推 narrative，完成后发 commands |
| D12 | 引擎拒绝 | 回调 Agent | 不自动重试，让 Agent 生成替代方案 |
| D13 | 版本管理 | 内置版本号 | 不用 git，YAML FM 中的 version 字段 |
| D14 | 文件写入 | 原子写入 | tempfile + os.replace |
| D15 | 渐进披露 | 3 层 | Index → Activation → Execution |

---

## 8. 关联文档索引

| 文档 | 内容 | 优先级 |
|------|------|--------|
| `communication_protocol.md` | JSON 命令流格式、引擎事件格式、SSE 推送协议 | 最高 |
| `memory_system.md` | .md 记忆文件格式、渐进式加载、YAML+MD 双层、压缩策略 | 最高 |
| `skill_system.md` | SKILL.md 标准、发现机制、加载流程、Agent 创建 Skill | 高 |
| `engine_adapter.md` | EngineAdapter 接口、TextAdapter 实现、GodotAdapter 设计 | 高 |
| `workspace_design.md` | Workspace 目录结构、Vue WorkBench UI 设计、组件选型 | 高 |
| `v1_to_v2_migration.md` | 模块级 keep/rewrite/new 决策、Strangler Fig 步骤 | 高 |
| `dev_plan_v2.md` | V2 开发步骤、验收标准、Trae 提示词文件 | 最高 |
