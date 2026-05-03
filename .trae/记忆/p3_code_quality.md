# P3: 代码质量与工程规范

> **阶段**: P3 - 代码质量 | **状态**: ✅ 已完成 | **日期**: 2026-05-03

---

## 概述

统一代码风格，消除潜在隐患，建立质量基线。配置 Ruff 代码检查和 Mypy 类型检查，修复已知低优先级问题。

---

## 1. Ruff 代码检查配置

**文件**: `pyproject.toml`

```toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "TCH",  # flake8-type-checking
]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["foundation", "core", "feature", "presentation"]
```

**执行**:
```bash
pip install ruff
ruff check 2workbench/ --fix
```

---

## 2. Mypy 类型检查配置

**文件**: `pyproject.toml`

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true  # 暂时忽略第三方库
```

**执行**:
```bash
pip install mypy
mypy 2workbench/ --ignore-missing-imports
```

---

## 3. 修复已知问题

### 3.1 CORS Header 缺失

**文件**: `2workbench/presentation/server.py`

```python
def do_OPTIONS(self):
    self.send_response(200)
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Token")  # ← 新增
    self.end_headers()
```

---

### 3.2 重复 import

**文件**: `2workbench/presentation/ops/evaluator/eval_workbench.py`

```python
# 文件顶部已有
import json
from datetime import datetime

# _export_report 方法内部删除重复导入
def _export_report(self) -> None:
    try:
        # 删除: import json
        # 删除: from datetime import datetime
        # 直接使用顶部的导入
        report = {
            "timestamp": datetime.now().isoformat(),
            ...
        }
```

---

### 3.3 循环检测去重

**文件**: `2workbench/presentation/ops/multi_agent/orchestrator.py`

```python
def _validate_chain(self) -> list[str]:
    errors = []
    reported_cycles = set()  # ← 新增：记录已报告的环
    
    # ... 其他验证逻辑 ...
    
    def dfs(node, path):
        if node in path:
            cycle = path[path.index(node):] + [node]
            cycle_key = tuple(sorted(cycle))  # ← 生成唯一键
            if cycle_key not in reported_cycles:  # ← 去重检查
                reported_cycles.add(cycle_key)
                errors.append(f"检测到循环: {' → '.join(cycle)}")
            return
        # ...
```

---

## 4. 清理空目录和占位文件

**删除**:
```bash
# 空占位目录
rm -rf 2workbench/presentation/editors/
rm -rf 2workbench/presentation/panels/
rm -rf 2workbench/presentation/styles/
rm -rf 2workbench/feature/skill/

# AI 操作日志（非项目文档）
rm -f 0.md
```

---

## 5. dev 依赖分离

**文件**: `pyproject.toml`

```toml
[project]
dependencies = [
    "openai>=2.32.0",
    "pydantic>=2.13.3",
    "pydantic-settings>=2.14.0",
    "python-frontmatter>=1.1.0",
    "tenacity>=9.1.4",
    "PyQt6>=6.6.0",
    "qasync>=0.27.0",
    "pyyaml>=6.0.1",
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
]

[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
    "pytest-qt>=4.0.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
]
```

---

## 6. .env.template

**文件**: `.env.template`

```
# LLM 配置
DEEPSEEK_API_KEY=YOUR_VALUE_HERE
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

# OpenAI（可选）
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Anthropic（可选）
ANTHROPIC_API_KEY=
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# 应用配置
DATABASE_PATH=./data/game.db
LOG_LEVEL=INFO
HTTP_PORT=18080
```

---

## 验证清单

- [x] `ruff check 2workbench/` — 零 warning
- [x] `mypy 2workbench/ --ignore-missing-imports` — 零 error
- [x] 空目录和占位文件已清理
- [x] `pytest` 在 `[dependency-groups] dev` 中
- [x] `.env.template` 包含所有供应商配置项

---

## 触发关键词

code_quality, ruff, mypy, pyproject.toml, CORS, 重复import, 循环检测, .env.template, dev依赖
