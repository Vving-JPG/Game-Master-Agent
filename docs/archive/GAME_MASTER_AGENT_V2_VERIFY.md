# Game Master Agent V2 - 最终验证

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤执行验证。

## 目标

V2 全部开发阶段（P0-P4）已完成。本文件用于**全面验证系统健康状态**，确认所有模块正常工作。

## 行为准则

1. **每一步都执行**：不要跳过任何检查
2. **如实报告**：成功就报告成功，失败就报告失败，不要隐藏错误
3. **遇到错误先尝试修复**：如果是简单问题（import 缺失、路径错误），直接修复并重新验证；3 次失败后停止并报告
4. **每步完成后汇报**：用表格形式汇报每项检查的结果

---

## 检查步骤（共 8 步）

### 步骤 1 - Python 环境检查

**执行**:

```powershell
cd d:\worldSim-master
uv run python -c "import sys; print(f'Python {sys.version}')"
uv run python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
uv run python -c "import openai; print(f'OpenAI {openai.__version__}')"
uv run python -c "import frontmatter; print('python-frontmatter OK')"
uv run python -c "import pytest; print(f'pytest {pytest.__version__}')"
```

**验收**: 所有依赖导入成功，无 ModuleNotFoundError

---

### 步骤 2 - V2 核心模块导入检查

**执行**:

```powershell
cd d:\worldSim-master
uv run python -c "from src.memory.file_io import atomic_write, update_memory_file; print('memory.file_io OK')"
uv run python -c "from src.memory.loader import MemoryLoader; print('memory.loader OK')"
uv run python -c "from src.memory.manager import MemoryManager; print('memory.manager OK')"
uv run python -c "from src.skills.loader import SkillLoader; print('skills.loader OK')"
uv run python -c "from src.adapters.base import EngineAdapter, EngineEvent, CommandResult; print('adapters.base OK')"
uv run python -c "from src.adapters.text_adapter import TextAdapter; print('adapters.text_adapter OK')"
uv run python -c "from src.agent.command_parser import CommandParser; print('agent.command_parser OK')"
uv run python -c "from src.agent.prompt_builder import PromptBuilder; print('agent.prompt_builder OK')"
uv run python -c "from src.agent.game_master import GameMaster; print('agent.game_master OK')"
uv run python -c "from src.agent.event_handler import EventHandler; print('agent.event_handler OK')"
uv run python -c "from src.services.llm_client import LLMClient; print('services.llm_client OK')"
uv run python -c "from src.api.routes.workspace import router as ws_router; print('api.routes.workspace OK')"
uv run python -c "from src.api.routes.skills import router as sk_router; print('api.routes.skills OK')"
uv run python -c "from src.api.routes.agent import router as ag_router; print('api.routes.agent OK')"
uv run python -c "from src.api.sse import router as sse_router; print('api.sse OK')"
uv run python -c "from src.cli_v2 import main; print('cli_v2 OK')"
```

**验收**: 全部 16 个模块导入成功

---

### 步骤 3 - 运行全部测试

**执行**:

```powershell
cd d:\worldSim-master
uv run pytest tests/ -v --tb=short 2>&1
```

**验收**: 
- 0 failures, 0 errors
- 记录总测试数和通过数

---

### 步骤 4 - 按模块统计测试

**执行**:

```powershell
cd d:\worldSim-master
uv run pytest tests/test_memory/ -v --tb=short 2>&1 | Select-Object -Last 3
uv run pytest tests/test_skills/ -v --tb=short 2>&1 | Select-Object -Last 3
uv run pytest tests/test_adapters/ -v --tb=short 2>&1 | Select-Object -Last 3
uv run pytest tests/test_agent/ -v --tb=short 2>&1 | Select-Object -Last 3
uv run pytest tests/test_api/ -v --tb=short 2>&1 | Select-Object -Last 3
uv run pytest tests/test_integration/ -v --tb=short 2>&1 | Select-Object -Last 3
```

**验收**: 每个模块的测试都通过，记录各模块测试数

---

### 步骤 5 - V1 遗留清理检查

**执行**:

```powershell
cd d:\worldSim-master

# 检查废弃目录是否已删除
Test-Path "src\web"       # 应该返回 False
Test-Path "src\admin"     # 应该返回 False
Test-Path "src\tools"     # 应该返回 False
Test-Path "src\plugins"   # 应该返回 False

# 检查废弃文件是否已删除
Test-Path "src\services\context_manager.py"  # 应该返回 False
Test-Path "src\prompts\gm_system.py"         # 应该返回 False

# 检查是否还有对废弃模块的引用
Select-String -Path "src\**\*.py" -Pattern "from src\.tools|from src\.plugins|from src\.services\.context_manager|gm_system" -Recurse
```

**验收**: 
- 废弃目录/文件全部不存在
- 无残留 import 引用

---

### 步骤 6 - API 端点检查

**执行**:

```powershell
cd d:\worldSim-master

# 启动服务（后台）
$proc = Start-Process -FilePath "uv" -ArgumentList "run", "uvicorn", "src.api.app:app", "--port", "8000" -PassThru -NoNewWindow
Start-Sleep -Seconds 5

# 检查 API 文档可访问
Invoke-WebRequest -Uri "http://localhost:8000/docs" -UseBasicParsing | Select-Object StatusCode

# 检查 V2 端点
Invoke-RestMethod -Uri "http://localhost:8000/api/workspace/tree" -UseBasicParsing | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/skills" -UseBasicParsing | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/agent/status" -UseBasicParsing | ConvertTo-Json

# 停止服务
Stop-Process -Id $proc.Id -Force
```

**验收**: 
- `/docs` 返回 200
- `/api/workspace/tree` 返回 JSON
- `/api/skills` 返回 Skill 列表
- `/api/agent/status` 返回 Agent 状态

---

### 步骤 7 - 前端构建检查

**执行**:

```powershell
cd d:\worldSim-master\workbench

# 检查 node_modules 存在
Test-Path "node_modules"

# 构建生产版本
npm run build 2>&1
```

**验收**: 
- `node_modules` 存在
- `npm run build` 成功，`dist/` 目录生成

---

### 步骤 8 - Workspace 和 Skills 文件完整性

**执行**:

```powershell
cd d:\worldSim-master

# 检查 workspace 目录结构
Get-ChildItem -Path "workspace" -Recurse -Name

# 检查 skills 目录结构
Get-ChildItem -Path "skills" -Recurse -Name

# 检查 system_prompt.md 存在
Test-Path "prompts\system_prompt.md"

# 检查每个内置 SKILL.md 格式正确
uv run python -c "
import frontmatter, pathlib
for p in pathlib.Path('skills/builtin').glob('*/SKILL.md'):
    post = frontmatter.load(str(p))
    assert 'name' in post.metadata, f'{p}: missing name'
    assert 'description' in post.metadata, f'{p}: missing description'
    assert 'version' in post.metadata, f'{p}: missing version'
    print(f'{p.parent.name}: OK (v{post.metadata[\"version\"]})')
"
```

**验收**: 
- workspace 目录包含 `index.md`、`player/profile.md`、`session/current.md`
- skills 目录包含 5 个内置 SKILL.md
- 每个 SKILL.md 格式正确（有 name、description、version）
- `prompts/system_prompt.md` 存在

---

## 验证结果汇报模板

完成所有步骤后，按以下格式汇报：

```
## V2 最终验证报告

### 1. Python 环境
| 检查项 | 结果 |
|--------|------|
| Python 版本 | ✅/❌ |
| FastAPI | ✅/❌ |
| OpenAI | ✅/❌ |
| python-frontmatter | ✅/❌ |
| pytest | ✅/❌ |

### 2. 模块导入 (16/16)
| 模块 | 结果 |
|------|------|
| memory.file_io | ✅/❌ |
| memory.loader | ✅/❌ |
| ... | ... |

### 3. 全部测试
| 指标 | 数值 |
|------|------|
| 总测试数 | ? |
| 通过 | ? |
| 失败 | ? |
| 错误 | ? |

### 4. 按模块测试
| 模块 | 测试数 | 通过 | 失败 |
|------|--------|------|------|
| test_memory | ? | ? | ? |
| test_skills | ? | ? | ? |
| test_adapters | ? | ? | ? |
| test_agent | ? | ? | ? |
| test_api | ? | ? | ? |
| test_integration | ? | ? | ? |

### 5. V1 清理
| 检查项 | 结果 |
|--------|------|
| src/web 已删除 | ✅/❌ |
| src/admin 已删除 | ✅/❌ |
| src/tools 已删除 | ✅/❌ |
| src/plugins 已删除 | ✅/❌ |
| context_manager.py 已删除 | ✅/❌ |
| gm_system.py 已删除 | ✅/❌ |
| 无残留引用 | ✅/❌ |

### 6. API 端点
| 端点 | 结果 |
|------|------|
| /docs | ✅/❌ |
| /api/workspace/tree | ✅/❌ |
| /api/skills | ✅/❌ |
| /api/agent/status | ✅/❌ |

### 7. 前端
| 检查项 | 结果 |
|--------|------|
| node_modules 存在 | ✅/❌ |
| npm run build 成功 | ✅/❌ |

### 8. 文件完整性
| 检查项 | 结果 |
|--------|------|
| workspace 目录完整 | ✅/❌ |
| 5 个内置 SKILL.md | ✅/❌ |
| SKILL.md 格式正确 | ✅/❌ |
| system_prompt.md 存在 | ✅/❌ |

### 总结
- 总检查项: ?/?
- 通过: ?
- 失败: ?
- V2 状态: ✅ 全部通过 / ⚠️ 部分问题 / ❌ 需要修复
```
