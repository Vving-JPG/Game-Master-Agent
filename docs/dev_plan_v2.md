# V2 开发计划

> **版本**: v2.0-draft
> **日期**: 2026-04-28
> **前置文档**: 所有 V2 设计文档
> **执行方式**: 分阶段 Trae 提示词文件
> **V1 基线**: 179 个测试全部通过

---

## 开发阶段总览

| 阶段 | 名称 | 步骤数 | 预计新增测试 | 说明 |
|------|------|--------|------------|------|
| P0 | 清理冗余 + 基础设施 | 13 | ~47 | 删除 V1 冗余 + 新模块 |
| P1 | 核心重构 | 10 | ~25 | 重写 Agent 主循环 |
| P2 | API 扩展 | 8 | ~20 | 新增 HTTP 端点 |
| P3 | WorkBench | 8 | ~5 | Vue 管理端 |
| P4 | 集成与清理 | 5 | ~10 | 端到端测试 + 清理 |
| **合计** | | **44** | **~107** | |

---

## P0: 清理冗余 + 基础设施 ✅

**目标**: 删除 V1 中已被 V2 方案替代的冗余模块，创建 V2 新模块，确保剩余 V1 测试不受影响。

### 步骤表

| # | 步骤 | 目的 | 方案 | 验收 |
|---|------|------|------|------|
| 0.1 | 删除 V1 冗余模块 | 砍掉被 V2 替代的代码 | 删除 `src/tools/`, `src/services/context_manager.py`, `src/plugins/` | 无 import 错误，剩余测试通过 |
| 0.2 | 创建目录结构 | 建立 V2 模块目录 | 创建 `src/memory/`, `src/skills/`, `src/adapters/`, `src/agent/`, `src/api/routes/`, `workspace/`, `skills/` | 所有目录存在，`__init__.py` 文件创建 |
| 0.3 | 安装 python-frontmatter | YAML+MD 解析依赖 | `uv pip install python-frontmatter` | `import frontmatter` 成功 |
| 0.4 | 实现 memory/file_io.py | 原子写入 + YAML/MD 解析 | 实现 `atomic_write()` 和 `update_memory_file()` | 测试: 创建/更新/原子性 (10个) |
| 0.5 | 实现 memory/loader.py | 渐进式记忆加载 | 实现 `MemoryLoader` 的 3 层加载 | 测试: index/activation/execution 三层 (6个) |
| 0.6 | 实现 memory/manager.py | 记忆管理主类 | 实现 `MemoryManager` 的读写/压缩/索引 | 测试: 加载/追加/更新 FM (7个) |
| 0.7 | 实现 skills/loader.py | Skill 发现与加载 | 实现 `SkillLoader` 的发现/匹配/加载 | 测试: 发现/关键词匹配/事件匹配 (8个) |
| 0.8 | 实现 adapters/base.py | 引擎适配器抽象接口 | 实现 `EngineAdapter` ABC + 数据类 | 测试: 接口定义正确 (5个) |
| 0.9 | 实现 adapters/text_adapter.py | MUD 文字适配器 | 实现 `TextAdapter`，复用 V1 Service 层 | 测试: connect/send_commands/query_state (11个) |
| 0.10 | 创建内置 Skill 文件 | 5 个核心 Skill | 创建 combat/dialogue/quest/exploration/narration 的 SKILL.md | 文件存在，格式正确 |
| 0.11 | 初始化 workspace | 创建记忆文件目录和索引 | 创建 `_index.md` 和全局 `index.md` | 目录结构完整 |
| 0.12 | 新模块单元测试 | 确保新代码正确 | 编写 memory/skills/adapters 的测试 | 所有新测试通过 (>=47个) |
| 0.13 | V1 回归测试 | 确保没破坏 V1 | 运行剩余 V1 测试 | 所有测试通过 |

### P0 详细代码参考

**Step 0.4: memory/file_io.py**

```python
# src/memory/file_io.py
import os
import tempfile
from pathlib import Path
import frontmatter
from datetime import datetime


def atomic_write(filepath: str, content: str, encoding: str = "utf-8") -> None:
    """原子写入文件。参考 docs/memory_system.md 第 6 节。"""
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
    """更新记忆文件。参考 docs/memory_system.md 第 6.3 节。"""
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

**Step 0.5: memory/loader.py**

```python
# src/memory/loader.py
import frontmatter
import re
from pathlib import Path
from typing import Optional


class MemoryLoader:
    """渐进式记忆加载器。参考 docs/memory_system.md 第 3 节。"""

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)

    def load_index(self, file_paths: list[str]) -> str:
        """Layer 1: ~100 tokens/file"""
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
        """Layer 2: ~500-2000 tokens/file"""
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
        """Layer 3: ~2000-5000 tokens/file"""
        blocks = []
        for fp in file_paths:
            full_path = self.workspace / f"{fp}.md"
            if not full_path.exists():
                continue
            post = frontmatter.load(str(full_path))
            blocks.append(f"### {post.get('name', fp)}\n{post.content}")
        return "\n\n".join(blocks)
```

---

## P1: 核心重构 ✅

**目标**: 重写 Agent 主循环，接入新模块。

### 步骤表

| # | 步骤 | 目的 | 方案 | 验收 |
|---|------|------|------|------|
| 1.1 | 实现 agent/command_parser.py | JSON 输出解析 | 4 级容错策略 (直接解析→代码块→花括号→兜底) | 测试: 正常JSON/代码块/纯文本 |
| 1.2 | 实现 agent/prompt_builder.py | Prompt 组装 | system + skills + memory + history + event | 测试: 各部分正确拼接 |
| 1.3 | 编写 system_prompt.md | Agent 主提示词 | 定义角色、输出格式、Skill 使用规则 | 提示词文件存在且完整 |
| 1.4 | LLMClient 新增 stream() | 流式调用支持 | 在现有 llm_client.py 新增方法 | 测试: yield 正确的事件 |
| 1.5 | 重写 agent/game_master.py | 事件驱动主循环 | handle_event() 替代 while 循环 | 测试: 接收事件→返回 JSON |
| 1.6 | 实现 EventHandler | 事件分发与 SSE 推送 | 接收引擎事件，调用 Agent，推送 SSE | 测试: 事件→Agent→SSE |
| 1.7 | TextAdapter 集成测试 | MUD 模式端到端 | 事件→Agent→指令→引擎→状态更新 | 测试: 完整流程 |
| 1.8 | 记忆更新集成测试 | memory_updates 流程 | Agent 输出→追加 MD→更新 FM | 测试: 文件正确更新 |
| 1.9 | Skill 加载集成测试 | Skill 触发和嵌入 | 事件→匹配 Skill→嵌入 Prompt | 测试: 正确匹配和加载 |
| 1.10 | 全流程端到端测试 | 完整回合测试 | 玩家输入→叙事→指令→记忆→状态 | 测试: 完整回合无错误 |

---

## P2: API 扩展 ✅

**目标**: 新增 HTTP 端点，支持 WorkBench。

### 步骤表

| # | 步骤 | 目的 | 方案 | 验收 |
|---|------|------|------|------|
| 2.1 | 新增 api/routes/workspace.py | Workspace 文件 API | tree/file CRUD 端点 | curl 测试: GET/PUT/POST/DELETE |
| 2.2 | 新增 api/routes/skills.py | Skill 管理 API | list/get/put/delete 端点 | curl 测试: CRUD |
| 2.3 | 新增 api/routes/agent.py | Agent 交互 API | event/status/context/interrupt/reset | curl 测试: 发送事件 |
| 2.4 | 新增 api/sse.py | SSE 流式推送 | EventSourceResponse + 事件类型 | curl 测试: 接收 SSE 流 |
| 2.5 | 注册路由到 app.py | 挂载新端点 | include_router | 服务启动无错误 |
| 2.6 | Workspace API 测试 | 文件操作测试 | pytest + tmp_path | 所有测试通过 |
| 2.7 | Agent API 测试 | 交互端点测试 | pytest + TestClient | 所有测试通过 |
| 2.8 | SSE 端点测试 | 流式推送测试 | pytest + httpx-sse | 接收到正确事件序列 |

---

## P3: WorkBench (Vue 前端) ✅

**目标**: 创建 Vue 管理端。

### 步骤表

| # | 步骤 | 目的 | 方案 | 验收 |
|---|------|------|------|------|
| 3.1 | 初始化 Vue 项目 | 搭建前端框架 | Vite + Vue3 + TS + Naive UI | `npm run dev` 启动成功 |
| 3.2 | 实现文件浏览器 | 浏览 workspace | Naive UI Tree + 异步加载 | 点击展开目录，点击打开文件 |
| 3.3 | 实现 MD 编辑器 | 查看/编辑 .md | md-editor-v3 + YAML FM 面板 | 编辑保存成功 |
| 3.4 | 实现 Agent 监控面板 | 状态/token/Skill | 轮询 /api/agent/status | 实时显示 Agent 状态 |
| 3.5 | 实现 SSE 事件流 | 实时事件日志 | EventSource API | 看到 token/command 事件 |
| 3.6 | 实现对话调试 | 手动发送事件 | 输入框 + 事件类型选择 | 发送事件，看到 Agent 回复 |
| 3.7 | 整体布局 | 三栏式布局 | NLayout + Sider + Tabs | 布局正确，响应式 |
| 3.8 | 前后端联调 | 端到端验证 | Vite proxy → FastAPI | 完整流程可用 |

---

## P4: 集成与清理 ✅

**目标**: 端到端测试 + 清理 V1 遗留。

### 步骤表

| # | 步骤 | 目的 | 方案 | 验收 |
|---|------|------|------|------|
| 4.1 | 清理 V1 遗留代码 | 移除 V1 旧测试和废弃引用 | 删除引用已删模块的测试，清理 game_master.py 旧代码 | 无 import 错误 |
| 4.2 | TextAdapter 命令行模式 | MUD 演示入口 | 实现 run_text_mode() | 命令行可交互 |
| 4.3 | 端到端集成测试 | 完整流程验证 | 启动→连接→事件→响应→记忆 | 全流程无错误 |
| 4.4 | 性能测试 | 基准测试 | 单回合延迟、token 消耗 | 延迟 < 5s |
| 4.5 | 文档更新 | README 和使用说明 | 更新项目文档 | 文档完整 |

---

## Trae 提示词文件规划

每个阶段对应一个 Trae 提示词文件：

| 文件 | 阶段 | 步骤数 | 说明 |
|------|------|--------|------|
| `GAME_MASTER_AGENT_V2_P0.md` | P0 清理冗余 + 基础设施 | 13 | 删除冗余 + 新模块 |
| `GAME_MASTER_AGENT_V2_P1.md` | P1 核心重构 | 10 | 重写 Agent 主循环 |
| `GAME_MASTER_AGENT_V2_P2.md` | P2 API 扩展 | 8 | 新增 HTTP 端点 |
| `GAME_MASTER_AGENT_V2_P3.md` | P3 WorkBench | 8 | Vue 管理端 |
| `GAME_MASTER_AGENT_V2_P4.md` | P4 集成清理 | 5 | 端到端 + 清理 |

### Trae 提示词文件模板

每个文件的结构：

```markdown
# V2 开发 - P{N}: {阶段名称}

## 项目背景
(简要说明 V2 目标和当前阶段目标)

## 参考文档
(列出相关设计文档的路径)

## V1 代码位置
(V1 项目路径)

## 步骤

### Step {N}.{M}: {步骤名称}
**目的**: {为什么做}
**方案**: {怎么做}
**代码参考**: {设计文档中的具体代码}
**验收**: {怎么验证}

(重复每个步骤)

## 注意事项
(从 V1 经验中总结的坑)
```

### V1 经验教训 (写入每个提示词文件)

1. **PowerShell `&&` 语法**: 用 `;` 分隔
2. **DeepSeek reasoning_content**: 用 `getattr(delta, 'reasoning_content', None)` 获取
3. **tool_call_id**: tool 消息必须包含
4. **tool_calls 增量拼接**: 用 dict 按 index 累积
5. **测试隔离**: 每个测试模块用 `teardown_module` 清理全局状态
6. **llm.chat() 返回 str**: V2 用 stream() 替代
7. **SQLite datetime('now')**: 同一秒内时间戳相同，测试用 `>=` 而非 `==`
8. **中文括号**: 测试中用英文括号
9. **原子写入**: 所有 .md 文件写入必须用 atomic_write()
10. **YAML Front Matter**: 引擎写 FM，Agent 写 Body，不要混淆

---

## 关键依赖版本

```
# requirements.txt (V2 新增)
python-frontmatter>=1.1.0
watchdog>=4.0.0  # WorkBench 文件监控

# V1 已有 (保留)
fastapi>=0.100.0
uvicorn>=0.23.0
openai>=1.0.0
aiosqlite>=0.19.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
httpx>=0.24.0
```

---

## 验收标准

### P0 完成标准
- [ ] Step 0.1: V1 冗余模块已删除（tools/, context_manager.py, plugins/）
- [ ] Step 0.2: V2 目录结构创建完毕
- [ ] Step 0.3: python-frontmatter 安装成功
- [ ] `memory/file_io.py` 测试通过 (>=10 个)
- [ ] `memory/loader.py` 测试通过 (>=6 个)
- [ ] `memory/manager.py` 测试通过 (>=7 个)
- [ ] `skills/loader.py` 测试通过 (>=8 个)
- [ ] `adapters/base.py` 测试通过 (>=5 个)
- [ ] `adapters/text_adapter.py` 测试通过 (>=11 个)
- [ ] 5 个内置 SKILL.md 文件创建
- [ ] workspace 目录和索引文件初始化
- [ ] 新模块测试全部通过 (>=47 个)
- [ ] **剩余 V1 测试全部通过**

### P1 完成标准
- [ ] `command_parser.py` 测试通过 (>=5 个)
- [ ] `prompt_builder.py` 测试通过 (>=3 个)
- [ ] `system_prompt.md` 创建
- [ ] `llm_client.stream()` 测试通过 (>=3 个)
- [ ] `game_master.py` 重写完成
- [ ] 端到端测试: 事件→JSON 响应 (>=3 个)
- [ ] 记忆更新测试通过 (>=3 个)
- [ ] Skill 加载测试通过 (>=3 个)

### P2 完成标准
- [ ] Workspace API 4 个端点可用
- [ ] Skills API 4 个端点可用
- [ ] Agent API 5 个端点可用
- [ ] SSE 端点推送正确事件
- [ ] 所有 API 测试通过 (>=15 个)

### P3 完成标准
- [ ] Vue 项目启动成功
- [ ] 文件浏览器可展开/选择
- [ ] MD 编辑器可编辑/保存
- [ ] Agent 监控实时刷新
- [ ] SSE 事件流实时显示
- [ ] 对话调试可发送/接收

### P4 完成标准
- [ ] V1 遗留代码已清理
- [ ] 所有测试通过 (V1+V2 合计 >=200 个)
- [ ] TextAdapter 命令行可交互
- [ ] 单回合延迟 < 5 秒
- [ ] 文档更新完成
