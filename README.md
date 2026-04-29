# Game Master Agent

AI 驱动的 RPG 游戏 Master Agent，使用 DeepSeek 大模型实时生成叙事、驱动 NPC、管理战斗。

## 功能特性

- 🎭 **AI 叙事引擎**: DeepSeek 大模型实时生成沉浸式 RPG 叙事
- 🧙 **NPC 系统**: 6 种性格模板，NPC 有记忆、有性格、有关系网
- ⚔️ **战斗系统**: D&D 5e 简化版回合制战斗
- 📜 **剧情系统**: 5 种剧情模板，分支选择，多结局
- 🎮 **MUD 前端**: 经典文字冒险游戏界面
- 🔧 **管理后台**: Vue 3 + Naive UI，Prompt 管理、AI 监控、数据管理
- 🔌 **插件系统**: 可扩展的插件架构

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+（管理端构建）
- DeepSeek API Key

### 安装

```bash
git clone https://github.com/Vving-JPG/Game-Master-Agent.git
cd Game-Master-Agent
uv sync
```

### 配置

创建 `.env` 文件：
```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 启动

```bash
# CLI 模式
uv run python src/cli.py

# Web 模式
uv run uvicorn src.api.app:app --reload --port 8000
# 游戏界面: http://localhost:8000/static/index.html
# 管理后台: http://localhost:8000/admin
# API 文档: http://localhost:8000/docs
```

### 测试

```bash
uv run pytest tests/ -v
```

## 项目结构

```
src/
├── agent/          # GM Agent 核心
├── api/            # FastAPI 后端 + 管理端路由
├── admin/          # Vue 3 管理端前端
├── data/           # 种子数据 + 模板
├── models/         # 数据访问层
├── plugins/        # 插件系统
├── prompts/        # System Prompt
├── services/       # 业务逻辑层
├── tools/          # GM 工具集
├── utils/          # 工具函数
└── web/            # MUD 前端
```

## 技术栈

- **后端**: Python 3.11 + FastAPI + SQLite
- **AI**: DeepSeek API (V3/R1)
- **前端**: HTML/CSS/JS (MUD) + Vue 3 + Naive UI (管理端)
- **工具**: uv + pytest
