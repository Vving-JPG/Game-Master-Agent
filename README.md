# Game Master Agent V2 - GUI Edition

通用游戏驱动 Agent — 像 Trae 驱动代码一样驱动游戏。

## 架构

```
┌─────────────┐     ┌──────────────┐
│  游戏引擎    │────▶│  Agent 核心   │
│ (TextAdapter)│◀────│ (GameMaster) │
└─────────────┘     └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │  WorkBench   │
                    │  (PyQt6 GUI) │
                    └──────────────┘
                           │
                    ┌──────┴───────┐
                    │  DeepSeek    │
                    │  (LLM API)   │
                    └──────────────┘
```

### 核心组件

| 组件 | 路径 | 说明 |
|------|------|------|
| GameMaster | `src/agent/game_master.py` | 事件驱动主循环 |
| CommandParser | `src/agent/command_parser.py` | 4 级容错 JSON 解析 |
| PromptBuilder | `src/agent/prompt_builder.py` | Prompt 组装 |
| EventHandler | `src/agent/event_handler.py` | 事件分发 |
| MemoryManager | `src/memory/manager.py` | .md 记忆管理 |
| SkillLoader | `src/skills/loader.py` | SKILL.md 发现与加载 |
| TextAdapter | `src/adapters/text_adapter.py` | MUD 文字适配器 |
| LLMClient | `src/services/llm_client.py` | DeepSeek API (AsyncOpenAI) |
| WorkBench | `workbench/` | PyQt6 图形界面 |

### 记忆系统

Agent 使用 `.md` 文件作为记忆，采用 YAML Front Matter + Markdown Body 双层格式：

- **YAML Front Matter**: 引擎写入的结构化数据（HP、好感度等）
- **Markdown Body**: Agent 写入的认知记录（交互历史、剧情笔记等）

### Skill 系统

基于 SKILL.md 开放标准，Agent 可加载和使用技能：

- `skills/builtin/` — 内置技能（combat, dialogue, quest, exploration, narration）
- `skills/agent_created/` — Agent 自创技能

## 快速开始

### 安装

```bash
uv sync
```

### 配置

创建 `.env` 文件：
```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 启动 GUI

```bash
uv run python -m workbench
```

或直接运行：
```bash
python -m workbench
```

## 测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行特定模块
uv run pytest tests/test_memory/ -v
uv run pytest tests/test_skills/ -v
uv run pytest tests/test_adapters/ -v
uv run pytest tests/test_agent/ -v
```

## 项目结构

```
Game-Master-Agent/
├── src/
│   ├── agent/           # Agent 核心
│   │   ├── game_master.py
│   │   ├── command_parser.py
│   │   ├── prompt_builder.py
│   │   └── event_handler.py
│   ├── memory/          # 记忆系统
│   │   ├── file_io.py
│   │   ├── loader.py
│   │   └── manager.py
│   ├── skills/          # Skill 系统
│   │   └── loader.py
│   ├── adapters/        # 引擎适配层
│   │   ├── base.py
│   │   └── text_adapter.py
│   ├── services/        # 服务层
│   │   ├── llm_client.py
│   │   ├── cache.py
│   │   └── model_router.py
│   └── models/          # SQLite 数据模型
├── workbench/           # PyQt6 GUI
│   ├── app.py           # 应用入口
│   ├── main_window.py   # 主窗口
│   ├── bridge/          # 后端桥接层
│   └── widgets/         # UI 组件
├── prompts/
│   └── system_prompt.md
├── skills/
│   └── builtin/         # 内置 SKILL.md
├── workspace/           # Agent 记忆文件
├── tests/               # 测试
└── docs/                # 设计文档
```

## 技术栈

- **GUI**: PyQt6 / qasync
- **后端**: Python 3.11+ / SQLite / DeepSeek API
- **AI**: DeepSeek (OpenAI 兼容接口)
- **记忆**: python-frontmatter (YAML + Markdown)

## V2 新特性

- **事件驱动架构**: Agent 通过事件循环处理引擎输入
- **渐进式记忆加载**: 3 层记忆披露（Index → Activation → Execution）
- **Skill 系统**: 基于 SKILL.md 标准的可扩展技能
- **WorkBench**: PyQt6 管理端，支持文件浏览、MD 编辑、Agent 监控

## 许可证

MIT
