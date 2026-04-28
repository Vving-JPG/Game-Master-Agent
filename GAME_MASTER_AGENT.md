# Game Master Agent - 项目上下文

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户开发一个 **Game Master Agent（游戏驱动智能体）**，用于驱动 RPG MUD 游戏。
- **技术栈**: Python 3.11+ / DeepSeek API / FastAPI / SQLite / WebSocket
- **包管理器**: uv（不是 pip）
- **LLM**: DeepSeek（通过 OpenAI 兼容接口调用）
- **架构**: 单 GM 智能体 + 工具调用（Tool Calling）
- **开发IDE**: Trae

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
7. **不要跳步**：即使用户让你跳过，也要提醒风险后再决定

---

## P0: 环境搭建与基础设施（共17步）

### 步骤 0.1 - 安装 Python 3.11+

**目的**: 确保开发环境有正确的 Python 版本

**执行**:
1. 在终端执行 `python --version` 检查当前版本
2. 如果版本低于 3.11 或未安装，提示用户访问 https://www.python.org/downloads/ 下载安装
3. 安装时务必勾选 "Add to PATH"
4. 安装完成后重新打开终端，再次验证

**验收**: `python --version` 输出 ≥ 3.11

---

### 步骤 0.2 - 安装 Git 版本控制

**目的**: 代码版本管理

**执行**:
1. 在终端执行 `git --version` 检查是否已安装
2. 如果未安装，提示用户访问 https://git-scm.com/downloads 下载
3. 安装后配置用户信息：
   ```bash
   git config --global user.name "用户的名字"
   git config --global user.email "用户的邮箱"
   ```
4. 验证配置：`git config --global --list`

**验收**: `git --version` 正常输出版本号

---

### 步骤 0.3 - 安装 uv 包管理器

**目的**: 使用现代化包管理器替代 pip + venv（速度快10-100倍）

**执行**:
1. 在终端执行 `uv --version` 检查是否已安装
2. 如果未安装，根据操作系统执行：
   - **Windows (PowerShell)**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - **Mac/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. 安装后重新打开终端验证

**验收**: `uv --version` 正常输出版本号

---

### 步骤 0.4 - 创建 GitHub/Gitee 仓库

**目的**: 远程托管代码

**执行**:
1. 提示用户在 GitHub 或 Gitee 上创建新仓库
2. 仓库名: `game-master-agent`
3. 选择 Private（私有）
4. 勾选 Add README
5. 创建完成后获取仓库 URL

**验收**: 仓库页面能正常访问，有 URL

---

### 步骤 0.5 - 克隆仓库到本地并在 Trae 中打开

**目的**: 在 Trae 中建立项目工作区

**执行**:
1. 使用 Trae 的"克隆Git仓库"功能
2. 粘贴仓库 URL
3. 选择本地保存路径
4. 克隆完成后确认 Trae 左侧文件树显示仓库内容

**验收**: Trae 文件树能看到 README.md 等仓库文件

---

### 步骤 0.6 - 初始化 uv 项目并创建目录结构

**目的**: 建立项目骨架

**执行**:
1. 在项目根目录终端执行：
   ```bash
   uv init --name game-master-agent
   ```
2. 删除自动生成的 `hello.py`
3. 创建项目目录结构：
   ```bash
   mkdir -p src/tools src/models src/prompts src/services src/utils src/data tests configs docs data logs
   ```
4. 在每个 src 子目录创建 `__init__.py`：
   ```bash
   touch src/__init__.py src/tools/__init__.py src/models/__init__.py src/prompts/__init__.py src/services/__init__.py src/utils/__init__.py
   ```

**验收**: `pyproject.toml` 存在，所有目录和 `__init__.py` 文件已创建

---

### 步骤 0.7 - 创建 .gitignore 文件

**目的**: 忽略不需要提交的文件

**执行**:
在项目根目录创建 `.gitignore`，内容如下：

```
# Python
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/
dist/
build/

# 环境和密钥
.env
*.db

# IDE
.idea/
.vscode/
*.swp
*.swo

# 日志和缓存
logs/
.ruff_cache/
.mypy_cache/

# OS
.DS_Store
Thumbs.db
```

**验收**: `git status` 不显示 `.env`、`.venv/`、`*.db` 等文件

---

### 步骤 0.8 - 安装核心依赖

**目的**: 安装项目所需的所有基础库

**执行**:
在项目根目录终端依次执行：
```bash
uv add openai
uv add fastapi "uvicorn[standard]"
uv add websockets
uv add pydantic pydantic-settings
uv add httpx
uv add pytest pytest-asyncio
uv add tenacity
```

uv 会自动：创建 `.venv/`、更新 `pyproject.toml`、生成 `uv.lock`

**验收**: `uv run python -c "import openai, fastapi, pydantic, pytest, tenacity"` 无报错

---

### 步骤 0.9 - 配置 .env 环境变量和 Settings 模块

**目的**: 安全存储 API 密钥，统一配置管理

**执行**:
1. 在项目根目录创建 `.env` 文件：
   ```
   DEEPSEEK_API_KEY=sk-你的密钥
   DEEPSEEK_BASE_URL=https://api.deepseek.com
   DEEPSEEK_MODEL=deepseek-chat
   DATABASE_PATH=./data/game.db
   LOG_LEVEL=INFO
   ```
2. 创建 `src/config.py`：
   ```python
   """项目配置模块 - 从.env文件读取配置"""
   from pydantic_settings import BaseSettings


   class Settings(BaseSettings):
       """应用配置，自动从.env文件加载"""

       # DeepSeek API 配置
       deepseek_api_key: str
       deepseek_base_url: str = "https://api.deepseek.com"
       deepseek_model: str = "deepseek-chat"

       # 数据库配置
       database_path: str = "./data/game.db"

       # 日志配置
       log_level: str = "INFO"

       model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


   # 全局单例
   settings = Settings()
   ```
3. 提示用户将真实的 DeepSeek API Key 填入 `.env` 文件

**验收**: `uv run python -c "from src.config import settings; print(settings.deepseek_model)"` 输出 `deepseek-chat`

---

### 步骤 0.10 - 注册 DeepSeek 并配置 API Key

**目的**: 获取 LLM API 访问权限

**执行**:
1. 提示用户访问 https://platform.deepseek.com 注册账号
2. 进入 API Keys 页面创建密钥
3. 将密钥填入 `.env` 文件的 `DEEPSEEK_API_KEY`
4. **重要提醒**: 确认 `.env` 已在 `.gitignore` 中，绝不能提交到 Git

**验收**: `.env` 中有有效的 API Key，且 `git status` 不显示 `.env`

---

### 步骤 0.11 - 测试 DeepSeek 基础调用

**目的**: 验证 API 能正常工作

**执行**:
1. 创建 `tests/test_deepseek.py`：
   ```python
   """DeepSeek API 基础调用测试"""
   from src.config import settings
   from openai import OpenAI


   def test_basic_chat():
       """测试基础对话功能"""
       client = OpenAI(
           api_key=settings.deepseek_api_key,
           base_url=settings.deepseek_base_url,
       )
       response = client.chat.completions.create(
           model=settings.deepseek_model,
           messages=[{"role": "user", "content": "你好，用一句话介绍你自己"}],
       )
       content = response.choices[0].message.content
       print(f"\nDeepSeek回复: {content}")
       assert content is not None
       assert len(content) > 0
   ```
2. 运行测试：`uv run pytest tests/test_deepseek.py::test_basic_chat -v -s`

**验收**: 测试通过，终端输出 DeepSeek 的中文回复

---

### 步骤 0.12 - 测试 DeepSeek 工具调用（Function Calling）

**目的**: 验证 DeepSeek 的 function calling 能力（这是整个项目的核心能力）

**执行**:
1. 在 `tests/test_deepseek.py` 中添加：
   ```python
   def test_tool_calling():
       """测试工具调用(function calling)功能"""
       client = OpenAI(
           api_key=settings.deepseek_api_key,
           base_url=settings.deepseek_base_url,
       )

       tools = [
           {
               "type": "function",
               "function": {
                   "name": "get_weather",
                   "description": "获取指定城市的天气信息",
                   "parameters": {
                       "type": "object",
                       "properties": {
                           "city": {"type": "string", "description": "城市名称"},
                       },
                       "required": ["city"],
                   },
               },
           }
       ]

       response = client.chat.completions.create(
           model=settings.deepseek_model,
           messages=[{"role": "user", "content": "北京天气怎么样？"}],
           tools=tools,
       )

       message = response.choices[0].message
       print(f"\ntool_calls: {message.tool_calls}")

       assert message.tool_calls is not None, "应该返回tool_calls"
       assert message.tool_calls[0].function.name == "get_weather"
       assert "北京" in message.tool_calls[0].function.arguments
   ```
2. 运行测试：`uv run pytest tests/test_deepseek.py::test_tool_calling -v -s`

**验收**: 测试通过，输出 `tool_calls` 包含 `function.name = "get_weather"`

---

### 步骤 0.13 - 测试 DeepSeek 流式输出

**目的**: 验证 streaming 能力（用于后续GM逐字输出叙事）

**执行**:
1. 在 `tests/test_deepseek.py` 中添加：
   ```python
   def test_streaming():
       """测试流式输出功能"""
       client = OpenAI(
           api_key=settings.deepseek_api_key,
           base_url=settings.deepseek_base_url,
       )

       print("\n--- 流式输出开始 ---")
       collected = []
       for chunk in client.chat.completions.create(
           model=settings.deepseek_model,
           messages=[{"role": "user", "content": "讲一个30字的短故事"}],
           stream=True,
       ):
           if chunk.choices[0].delta.content:
               text = chunk.choices[0].delta.content
               print(text, end="", flush=True)
               collected.append(text)
       print("\n--- 流式输出结束 ---")

       full_text = "".join(collected)
       assert len(full_text) > 0, "应该有输出内容"
   ```
2. 运行测试：`uv run pytest tests/test_deepseek.py::test_streaming -v -s`

**验收**: 测试通过，终端逐字显示故事内容

---

### 步骤 0.14 - 编写日志模块

**目的**: 统一日志输出格式，同时输出到控制台和文件

**执行**:
1. 创建 `src/utils/logger.py`：
   ```python
   """日志模块 - 统一日志输出格式"""
   import logging
   import os
   from logging.handlers import RotatingFileHandler
   from src.config import settings


   def get_logger(name: str) -> logging.Logger:
       """获取logger实例

       Args:
           name: logger名称，通常使用模块名 __name__

       Returns:
           配置好的Logger实例
       """
       logger = logging.getLogger(name)

       # 避免重复添加handler
       if logger.handlers:
           return logger

       logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

       # 日志格式
       formatter = logging.Formatter(
           "[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
           datefmt="%Y-%m-%d %H:%M:%S",
       )

       # 控制台handler
       console_handler = logging.StreamHandler()
       console_handler.setFormatter(formatter)
       logger.addHandler(console_handler)

       # 文件handler（自动轮转）
       log_dir = "logs"
       os.makedirs(log_dir, exist_ok=True)
       file_handler = RotatingFileHandler(
           os.path.join(log_dir, "app.log"),
           maxBytes=10 * 1024 * 1024,  # 10MB
           backupCount=5,
           encoding="utf-8",
       )
       file_handler.setFormatter(formatter)
       logger.addHandler(file_handler)

       return logger
   ```
2. 创建 `tests/test_logger.py` 验证：
   ```python
   """日志模块测试"""
   from src.utils.logger import get_logger


   def test_logger():
       """测试日志模块能正常输出"""
       logger = get_logger("test")
       logger.info("这是一条测试日志")
       assert logger.handlers  # 应该有handler
   ```

**验收**: `uv run pytest tests/test_logger.py -v -s` 通过，`logs/app.log` 文件被创建

---

### 步骤 0.15 - 搭建 pytest 测试框架

**目的**: 建立测试规范和公共 fixture

**执行**:
1. 在 `pyproject.toml` 中添加 pytest 配置：
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   asyncio_mode = "auto"
   ```
2. 创建 `tests/conftest.py`：
   ```python
   """pytest 公共 fixture"""
   import pytest
   from src.config import settings


   @pytest.fixture
   def app_settings():
       """提供应用配置"""
       return settings
   ```
3. 运行全部测试确认框架正常：`uv run pytest tests/ -v`

**验收**: 所有测试通过，pytest 能发现 `tests/` 下所有测试文件

---

### 步骤 0.16 - 编写 LLMClient 封装类

**目的**: 统一管理 DeepSeek API 调用，内置重试和 Token 计数

**执行**:
1. 创建 `src/services/llm_client.py`：
   ```python
   """LLM客户端封装 - 统一管理DeepSeek API调用"""
   from openai import OpenAI
   from tenacity import retry, stop_after_attempt, wait_exponential
   from src.config import settings
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   class LLMClient:
       """DeepSeek API 客户端封装

       功能:
       - 普通对话
       - 带工具调用的对话
       - 流式输出
       - 自动重试（3次，指数退避）
       - Token 用量统计
       """

       def __init__(self):
           self.client = OpenAI(
               api_key=settings.deepseek_api_key,
               base_url=settings.deepseek_base_url,
           )
           self.model = settings.deepseek_model
           # Token 统计
           self.total_prompt_tokens = 0
           self.total_completion_tokens = 0

       @retry(
           stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=1, max=10),
       )
       def chat(self, messages: list[dict]) -> str:
           """普通对话

           Args:
               messages: 消息列表，格式 [{"role": "user", "content": "..."}]

           Returns:
               模型回复文本
           """
           logger.info(f"调用LLM，消息数: {len(messages)}")
           response = self.client.chat.completions.create(
               model=self.model,
               messages=messages,
           )
           # 累计Token
           usage = response.usage
           self.total_prompt_tokens += usage.prompt_tokens
           self.total_completion_tokens += usage.completion_tokens
           logger.info(
               f"Token使用 - 本次: prompt={usage.prompt_tokens}, "
               f"completion={usage.completion_tokens} | "
               f"累计: prompt={self.total_prompt_tokens}, "
               f"completion={self.total_completion_tokens}"
           )
           return response.choices[0].message.content

       @retry(
           stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=1, max=10),
       )
       def chat_with_tools(self, messages: list[dict], tools: list[dict]):
           """带工具调用的对话

           Args:
               messages: 消息列表
               tools: 工具定义列表

           Returns:
               完整的API响应对象（包含tool_calls）
           """
           logger.info(f"调用LLM(带工具)，消息数: {len(messages)}, 工具数: {len(tools)}")
           response = self.client.chat.completions.create(
               model=self.model,
               messages=messages,
               tools=tools,
           )
           usage = response.usage
           self.total_prompt_tokens += usage.prompt_tokens
           self.total_completion_tokens += usage.completion_tokens
           return response

       def chat_stream(self, messages: list[dict]):
           """流式对话

           Args:
               messages: 消息列表

           Yields:
               每个文本片段
           """
           logger.info(f"调用LLM(流式)，消息数: {len(messages)}")
           for chunk in self.client.chat.completions.create(
               model=self.model,
               messages=messages,
               stream=True,
           ):
               if chunk.choices[0].delta.content:
                   yield chunk.choices[0].delta.content

       def get_usage_stats(self) -> dict:
           """获取Token使用统计"""
           return {
               "total_prompt_tokens": self.total_prompt_tokens,
               "total_completion_tokens": self.total_completion_tokens,
               "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
           }
   ```
2. 创建 `tests/test_llm_client.py`：
   ```python
   """LLMClient 测试"""
   from src.services.llm_client import LLMClient


   def test_llm_client_init():
       """测试LLMClient能正常初始化"""
       client = LLMClient()
       assert client.model == "deepseek-chat"
       assert client.total_prompt_tokens == 0


   def test_llm_client_chat():
       """测试基础对话"""
       client = LLMClient()
       response = client.chat([{"role": "user", "content": "说一个字：好"}])
       assert response is not None
       assert len(response) > 0
       assert client.total_prompt_tokens > 0
       print(f"\n回复: {response}")
       print(f"Token统计: {client.get_usage_stats()}")


   def test_llm_client_tool_calling():
       """测试工具调用"""
       client = LLMClient()
       tools = [
           {
               "type": "function",
               "function": {
                   "name": "roll_dice",
                   "description": "掷骰子",
                   "parameters": {
                       "type": "object",
                       "properties": {"sides": {"type": "integer"}},
                       "required": ["sides"],
                   },
               },
           }
       ]
       response = client.chat_with_tools(
           messages=[{"role": "user", "content": "帮我掷一个20面骰子"}],
           tools=tools,
       )
       assert response.choices[0].message.tool_calls is not None
       print(f"\ntool_calls: {response.choices[0].message.tool_calls}")
   ```

**验收**: `uv run pytest tests/test_llm_client.py -v -s` 全部通过

---

### 步骤 0.17 - 首次 Git 提交

**目的**: 保存初始项目结构到远程仓库

**执行**:
1. 确认 `.env` 不在暂存区：`git status`（不应看到 `.env`）
2. 添加所有文件：`git add .`
3. 提交：
   ```bash
   git commit -m "init: 项目初始化 - uv+FastAPI+DeepSeek+pytest+LLMClient"
   ```
4. 推送到远程：`git push origin main`
5. 在 GitHub/Gitee 页面确认文件已上传，且 `.env` 不在其中

**验收**: 远程仓库能看到所有项目文件，`.env` 和 `.venv/` 不在仓库中

---

## P0 里程碑验收清单

完成以上17步后，逐项确认：

- [ ] 0.1 `python --version` ≥ 3.11
- [ ] 0.2 `git --version` 正常
- [ ] 0.3 `uv --version` 正常
- [ ] 0.4 GitHub/Gitee 仓库已创建
- [ ] 0.5 Trae 中能看到项目文件
- [ ] 0.6 `pyproject.toml` 存在，目录结构完整
- [ ] 0.7 `.gitignore` 配置正确
- [ ] 0.8 所有依赖可正常 import
- [ ] 0.9 `src/config.py` 能读取 `.env`
- [ ] 0.10 DeepSeek API Key 已配置
- [ ] 0.11 基础对话测试通过
- [ ] 0.12 工具调用测试通过
- [ ] 0.13 流式输出测试通过
- [ ] 0.14 日志模块正常工作
- [ ] 0.15 pytest 框架就绪
- [ ] 0.16 LLMClient 封装完成
- [ ] 0.17 Git 首次提交成功

**全部 ✅ 后，P0 阶段完成，可以进入 P1'（核心骨架与持久化）。**

---

## 项目目录结构（P0 完成后）

```
game-master-agent/
├── .env                    # 环境变量（API Key等，不提交Git）
├── .gitignore              # Git忽略规则
├── pyproject.toml          # 项目配置和依赖（uv管理）
├── uv.lock                 # 依赖锁定文件
├── .python-version         # Python版本锁定
├── data/                   # 数据库文件目录
├── logs/                   # 日志文件目录
├── docs/                   # 文档目录
├── configs/                # 配置文件目录
├── src/
│   ├── __init__.py
│   ├── config.py           # 配置模块（pydantic-settings）
│   ├── tools/              # 工具函数目录（后续阶段填充）
│   │   └── __init__.py
│   ├── models/             # 数据模型目录（后续阶段填充）
│   │   └── __init__.py
│   ├── prompts/            # Prompt模板目录（后续阶段填充）
│   │   └── __init__.py
│   ├── services/           # 业务服务目录
│   │   ├── __init__.py
│   │   └── llm_client.py   # LLM客户端封装
│   ├── utils/              # 工具模块目录
│   │   ├── __init__.py
│   │   └── logger.py       # 日志模块
│   └── data/               # 种子数据目录（后续阶段填充）
└── tests/
    ├── conftest.py         # pytest公共fixture
    ├── test_deepseek.py    # DeepSeek API测试
    ├── test_llm_client.py  # LLMClient测试
    └── test_logger.py      # 日志模块测试
```
