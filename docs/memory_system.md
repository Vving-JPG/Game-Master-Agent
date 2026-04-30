# V2 记忆系统设计

> **版本**: v2.0-draft
> **日期**: 2026-04-28
> **前置文档**: `architecture_v2.md`
> **关联文档**: `communication_protocol.md`, `skill_system.md`
> **参考项目**: Claude-Mem (3-layer progressive disclosure), agent-memory ("No database. No embeddings. Just markdown files.")

---

## 1. 设计理念

### 1.1 核心原则

**"No database. No embeddings. Just markdown files."**

Agent 的记忆存储在磁盘上的 `.md` 文件中，类似 Trae 的 workspace。每个文件代表一个实体（NPC、地点、任务、剧情等），人类可以直接阅读和编辑。

### 1.2 双层存储架构

```
┌─────────────────────────────────────────────────────┐
│                    Agent 记忆层                       │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │         YAML Front Matter (引擎写入)          │    │
│  │  name: 铁匠                                  │    │
│  │  hp: 80                                      │    │
│  │  relationship_with_player: 30                │    │
│  │  version: 3                                  │    │
│  │  last_modified: 2026-04-28T14:30:00          │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │         Markdown Body (Agent 写入)            │    │
│  │  ## 初始印象                                  │    │
│  │  [第1天] 铁匠铺的老板，看起来很健壮...        │    │
│  │                                             │    │
│  │  ## 交互记录                                  │    │
│  │  [第2天] 玩家来买了一把铁剑，付了50金币。     │    │
│  │  [第3天] 玩家归还了铁锤，关系更友好了。       │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
├─────────────────────────────────────────────────────┤
│                    引擎数据层 (SQLite)               │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ worlds   │ │ npcs     │ │ items    │           │
│  │ players  │ │ quests   │ │ locations│           │
│  │ logs     │ │ ...      │ │ ...      │           │
│  └──────────┘ └──────────┘ └──────────┘           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**关键分离**:
- **YAML Front Matter**: 结构化事实数据，由**引擎**写入（通过 `state_changes`）
- **Markdown Body**: 非结构化认知，由 **Agent** 写入（通过 `memory_updates`）

### 1.3 为什么不用数据库存 Agent 记忆？

| 维度 | SQLite (V1) | .md 文件 (V2) |
|------|------------|--------------|
| 可读性 | 需要 SQL 查询 | 直接打开看 |
| 可编辑性 | 需要 SQL UPDATE | 任何文本编辑器 |
| 可调试性 | 需要管理端 | WorkBench 直接编辑 |
| 版本对比 | 需要 schema migration | git diff / 文件对比 |
| 灵活性 | 固定 schema | 任意结构 |
| Agent 自主性 | 受限于预定义字段 | 自由创建文件和内容 |

---

## 2. 文件格式规范

### 2.1 标准文件格式

每个记忆文件都是 YAML Front Matter + Markdown Body：

```markdown
---
name: 铁匠
type: npc
id: npc_blacksmith
hp: 80
max_hp: 100
location: locations/铁匠铺
relationship_with_player: 30
version: 3
last_modified: 2026-04-28T14:30:00
modified_by: engine
created_at: 2026-04-26T10:00:00
tags: [npc, 黑铁镇, 商人]
---

## 初始印象
[第1天] 铁匠铺的老板，看起来很健壮，说话很大声。对陌生人有些警惕，但谈起锻造就滔滔不绝。

## 交互记录
[第2天] 玩家来买了一把铁剑，付了50金币。铁匠对玩家的眼光表示赞赏。
[第3天] 玩家归还了铁锤（之前借走的），铁匠显得很高兴，赠送了一块磨刀石。

## 性格特征
- 粗犷豪爽，但内心细腻
- 对锻造工艺非常执着
- 不喜欢谈论自己的过去

## 当前任务关联
- q_cave_goblins: 提供了哥布林情报，等待玩家反馈
```

### 2.2 YAML Front Matter 字段规范

#### 通用字段 (所有文件类型)

| 字段 | 类型 | 必填 | 说明 | 写入者 |
|------|------|------|------|--------|
| `name` | string | 是 | 实体名称 | 引擎 |
| `type` | string | 是 | 实体类型: npc/location/quest/item/story/player/session | 引擎 |
| `id` | string | 是 | 唯一标识符 | 引擎 |
| `version` | int | 是 | 文件版本号，每次修改 +1 | 引擎/Agent |
| `last_modified` | datetime | 是 | 最后修改时间 (ISO 8601) | 引擎/Agent |
| `modified_by` | string | 是 | 最后修改者: engine/agent | 自动 |
| `created_at` | datetime | 是 | 创建时间 | 引擎 |
| `tags` | list[string] | 否 | 标签，用于搜索 | 引擎/Agent |

#### NPC 特有字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `hp` | int | 当前生命值 |
| `max_hp` | int | 最大生命值 |
| `location` | string | 当前位置 (路径引用) |
| `relationship_with_player` | int | 与玩家好感度 (0-100) |
| `mood` | string | 当前心情 |
| `alive` | bool | 是否存活 |

#### Location 特有字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `description` | string | 简短描述 |
| `danger_level` | int | 危险等级 (1-10) |
| `discovered` | bool | 玩家是否已发现 |
| `connected_locations` | list[string] | 相连地点路径 |

#### Quest 特有字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 状态: inactive/active/completed/failed |
| `reward` | string | 奖励描述 |
| `difficulty` | int | 难度 (1-5) |

#### Session 特有字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `turn_count` | int | 当前回合数 |
| `total_tokens` | int | 累计 token 消耗 |
| `session_start` | datetime | 会话开始时间 |

### 2.3 Markdown Body 写作规范

Agent 写入 Markdown Body 时应遵循以下规范：

```markdown
## 章节标题 (用 ## 二级标题)

[第X天 时间段] 描述内容。关键信息用**加粗**标记。

- 列表项用于枚举特征、物品等
- 每条记录一行，便于扫描
```

**规范要点**:
1. 每条记录以 `[第X天 时间段]` 开头，便于时间线追踪
2. 使用 `##` 二级标题分节（初始印象、交互记录、性格特征等）
3. 关键信息用 `**加粗**` 标记
4. 列表项用于枚举
5. 保持简洁，每条记录 1-2 句话
6. 不写冗余信息，Agent 会在压缩时处理

---

## 3. 渐进式披露 (Progressive Disclosure)

### 3.1 三层加载模型

参考 Claude-Mem 的 3-layer 架构，Agent 的记忆加载分为三层：

```
Layer 1: Index (索引层)
         ~100 tokens / 文件
         只加载 YAML Front Matter 中的 name + tags + version
         用途: 快速扫描所有相关实体

Layer 2: Activation (激活层)
         ~500-2000 tokens / 文件
         加载完整 YAML Front Matter + Markdown Body 的章节标题
         用途: 获取实体详细状态和结构概览

Layer 3: Execution (执行层)
         ~2000-5000 tokens / 文件
         加载完整文件内容
         用途: 需要完整上下文时的深度阅读
```

### 3.2 加载流程

```
引擎事件到达 (含 context_hints)
    │
    ▼
Layer 1: 加载 Index
    │  读取所有 hint 文件的 YAML Front Matter (name, tags, version)
    │  组装成紧凑的索引摘要
    │  ~100 tokens per file
    │
    ▼
Agent 判断: 是否需要更多细节？
    │
    ├─ 否 → 直接用 Index 层信息生成回复
    │
    └─ 是 → Layer 2: 加载 Activation
            │  读取完整 YAML + Markdown 章节标题
            │  ~500-2000 tokens per file
            │
            ▼
        Agent 判断: 是否需要完整内容？
            │
            ├─ 否 → 用 Activation 层信息生成回复
            │
            └─ 是 → Layer 3: 加载 Execution
                    │  读取完整文件
                    │  ~2000-5000 tokens per file
                    │
                    ▼
                生成回复
```

### 3.3 实现代码

```python
import frontmatter
from pathlib import Path
from typing import Optional


class MemoryLoader:
    """渐进式记忆加载器"""

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)

    def load_index(self, file_paths: list[str]) -> str:
        """
        Layer 1: 加载索引层。
        只读取 YAML Front Matter 的关键字段，生成紧凑摘要。

        每个文件约 100 tokens。
        """
        lines = ["## 相关实体索引\n"]
        for fp in file_paths:
            full_path = self.workspace / f"{fp}.md"
            if not full_path.exists():
                lines.append(f"- {fp}: [文件不存在]")
                continue

            post = frontmatter.load(str(full_path))
            name = post.get("name", fp)
            entity_type = post.get("type", "unknown")
            tags = post.get("tags", [])
            version = post.get("version", 0)

            tag_str = ", ".join(tags) if tags else ""
            lines.append(f"- [{entity_type}] {name} (v{version}) {tag_str}")

        return "\n".join(lines)

    def load_activation(self, file_paths: list[str]) -> str:
        """
        Layer 2: 加载激活层。
        读取完整 YAML Front Matter + Markdown 章节标题（不含正文）。

        每个文件约 500-2000 tokens。
        """
        import re

        blocks = []
        for fp in file_paths:
            full_path = self.workspace / f"{fp}.md"
            if not full_path.exists():
                continue

            post = frontmatter.load(str(full_path))

            # YAML Front Matter → 格式化为紧凑文本
            fm_lines = [f"### {post.get('name', fp)}"]
            for key, value in post.metadata.items():
                if key in ("version", "last_modified", "modified_by", "created_at"):
                    continue  # 跳过元数据字段
                fm_lines.append(f"- {key}: {value}")

            # Markdown Body → 只提取 ## 章节标题
            headings = re.findall(r'^## .+$', post.content, re.MULTILINE)
            if headings:
                fm_lines.append("- 章节: " + " | ".join(h[3:] for h in headings))

            blocks.append("\n".join(fm_lines))

        return "\n\n".join(blocks)

    def load_execution(self, file_paths: list[str]) -> str:
        """
        Layer 3: 加载执行层。
        读取完整文件内容（YAML + Markdown）。

        每个文件约 2000-5000 tokens。
        """
        blocks = []
        for fp in file_paths:
            full_path = self.workspace / f"{fp}.md"
            if not full_path.exists():
                continue

            post = frontmatter.load(str(full_path))
            # 直接返回完整内容
            blocks.append(f"### {post.get('name', fp)}\n{post.content}")

        return "\n\n".join(blocks)


# ========== 使用示例 ==========
loader = MemoryLoader("/path/to/workspace")

# Step 1: 引擎事件到达
context_hints = ["npcs/铁匠", "locations/铁匠铺", "story/哥布林_威胁"]

# Step 2: 加载 Index 层
index_text = loader.load_index(context_hints)
# 输出:
# ## 相关实体索引
# - [npc] 铁匠 (v3) npc, 黑铁镇, 商人
# - [location] 铁匠铺 (v2) location, 黑铁镇, 安全区域
# - [story] 哥布林威胁 (v1) story, 主线, 危险

# Step 3: Agent 决定需要更多细节，加载 Activation 层
activation_text = loader.load_activation(["npcs/铁匠"])
# 输出:
# ### 铁匠
# - name: 铁匠
# - hp: 80
# - relationship_with_player: 30
# - location: locations/铁匠铺
# - 章节: 初始印象 | 交互记录 | 性格特征 | 当前任务关联

# Step 4: Agent 需要完整交互记录，加载 Execution 层
execution_text = loader.load_execution(["npcs/铁匠"])
# 输出完整文件内容
```

---

## 4. 记忆索引系统

### 4.1 目录结构

```
workspace/
├── index.md                  # 全局索引文件
├── npcs/
│   ├── _index.md             # NPC 分类索引
│   ├── 铁匠.md
│   ├── 药剂师.md
│   └── 流浪商人.md
├── locations/
│   ├── _index.md             # 地点分类索引
│   ├── 铁匠铺.md
│   ├── 暗黑森林.md
│   └── 黑铁镇.md
├── story/
│   ├── _index.md             # 剧情线索索引
│   ├── 哥布林_威胁.md
│   └── 铁匠的秘密.md
├── quests/
│   ├── _index.md             # 任务索引
│   ├── q_cave_goblins.md
│   └── q_herb_collect.md
├── items/
│   ├── _index.md             # 物品索引
│   └── 铁剑.md
├── player/
│   └── profile.md            # 玩家档案
└── session/
    └── current.md            # 当前会话记录
```

### 4.2 _index.md 索引文件格式

每个子目录都有一个 `_index.md` 文件，作为该分类的索引：

```markdown
---
type: index
category: npcs
entity_count: 3
last_updated: 2026-04-28T14:30:00
---

## NPC 列表

| 名称 | ID | 位置 | 好感度 | 版本 |
|------|-----|------|--------|------|
| 铁匠 | npc_blacksmith | locations/铁匠铺 | 30 | v3 |
| 药剂师 | npc_alchemist | locations/药剂店 | 15 | v1 |
| 流浪商人 | npc_merchant | locations/暗黑森林 | 0 | v1 |
```

### 4.3 全局索引 index.md

```markdown
---
type: global_index
total_entities: 12
last_updated: 2026-04-28T14:30:00
---

## 记忆概览

- **NPCs**: 3 个 (铁匠, 药剂师, 流浪商人)
- **地点**: 3 个 (铁匠铺, 暗黑森林, 黑铁镇)
- **剧情**: 2 条 (哥布林威胁, 铁匠的秘密)
- **任务**: 2 个 (清除洞穴哥布林, 采集草药)
- **物品**: 1 个 (铁剑)

## 最近更新
- [v3] npcs/铁匠.md - 2026-04-28T14:30 (engine)
- [v1] story/哥布林_威胁.md - 2026-04-28T14:30 (agent)
- [v2] locations/铁匠铺.md - 2026-04-27T10:00 (engine)
```

---

## 5. 三种更新节奏

### 5.1 实时同步 (Engine → YAML Front Matter)

**触发**: 引擎执行 Agent 的 commands 后，返回 `state_changes`

**执行者**: 引擎 (通过 MemoryManager)

**内容**: 更新 YAML Front Matter 中的结构化字段

```python
async def apply_state_changes(self, state_changes: list[dict]):
    """
    引擎执行 commands 后，更新对应文件的 YAML Front Matter。

    state_changes 示例:
    [
        {
            "file": "npcs/铁匠.md",
            "frontmatter": {
                "relationship_with_player": 35,
                "version": 4,
                "last_modified": "2026-04-28T14:30:05Z",
                "modified_by": "engine"
            }
        }
    ]
    """
    for change in state_changes:
        file_path = self.workspace / change["file"]
        if not file_path.exists():
            continue

        post = frontmatter.load(str(file_path))

        # 更新 YAML 字段
        for key, value in change["frontmatter"].items():
            post[key] = value

        # 原子写入
        atomic_write(str(file_path), frontmatter.dumps(post))
```

### 5.2 回合更新 (Agent → Markdown Body)

**触发**: Agent 每回合生成 `memory_updates`

**执行者**: Agent (通过 MemoryManager)

**内容**: 追加内容到 Markdown Body

```python
async def apply_memory_updates(self, updates: list[dict]):
    """
    Agent 每回合追加记忆到 Markdown Body。

    updates 示例:
    [
        {
            "file": "npcs/铁匠.md",
            "action": "append",
            "content": "\n[第3天 上午] 玩家询问了哥布林的事..."
        }
    ]
    """
    for update in updates:
        if update["action"] != "append":
            continue

        file_path = self.workspace / update["file"]

        if not file_path.exists():
            # 文件不存在，创建新文件
            atomic_write(str(file_path), update["content"])
            continue

        post = frontmatter.load(str(file_path))

        # 追加到 Markdown Body 末尾
        post.content += update["content"]

        # 更新版本号
        post["version"] = post.get("version", 0) + 1
        post["last_modified"] = datetime.now().isoformat()
        post["modified_by"] = "agent"

        # 原子写入
        atomic_write(str(file_path), frontmatter.dumps(post))
```

### 5.3 定期压缩 (LLM 摘要)

**触发**: 文件超过阈值时（如 Markdown Body 超过 3000 字）

**执行者**: MemoryManager (后台任务)

**内容**: LLM 将旧记录压缩为摘要

```python
async def compress_if_needed(self, file_path: str, max_chars: int = 3000):
    """
    检查文件是否需要压缩。
    如果 Markdown Body 超过 max_chars，用 LLM 压缩旧内容。
    """
    post = frontmatter.load(str(file_path))
    body = post.content

    if len(body) <= max_chars:
        return False

    # 分离旧内容和新内容 (保留最近 500 字)
    split_point = len(body) - 500
    old_content = body[:split_point]
    recent_content = body[split_point:]

    # 用 LLM 压缩旧内容
    compressed = await self.llm_client.chat(
        system="你是一个记忆压缩助手。将以下游戏记录压缩为简洁的摘要，保留关键信息，删除冗余细节。输出格式与输入相同（用 ## 分节，[第X天] 开头）。",
        user=old_content
    )

    # 合并压缩后的旧内容 + 保留的最近内容
    post.content = compressed + "\n\n--- 压缩分割线 ---\n\n" + recent_content
    post["version"] = post.get("version", 0) + 1
    post["last_modified"] = datetime.now().isoformat()
    post["modified_by"] = "compressor"

    atomic_write(str(file_path), frontmatter.dumps(post))
    return True
```

---

## 6. 原子文件写入

### 6.1 为什么需要原子写入？

Agent 和引擎可能同时写入同一个文件。如果写入过程中断（崩溃、断电），文件可能损坏。原子写入确保文件要么完全更新，要么保持原样。

### 6.2 实现代码

```python
import os
import tempfile
from pathlib import Path


def atomic_write(filepath: str, content: str, encoding: str = "utf-8") -> None:
    """
    原子写入文件。

    1. 在目标文件同目录创建临时文件（确保同一文件系统）
    2. 写入内容并 flush + fsync
    3. 用 os.replace() 原子替换目标文件
    4. 失败时清理临时文件

    :param filepath: 目标文件路径
    :param content: 要写入的完整内容 (YAML + Markdown)
    :param encoding: 文件编码，默认 utf-8
    """
    path = Path(filepath)
    dirpath = path.parent

    # 确保目录存在
    dirpath.mkdir(parents=True, exist_ok=True)

    # 在同目录创建临时文件（保证同一文件系统，os.replace 才能原子操作）
    fd, tmp_path = tempfile.mkstemp(
        dir=str(dirpath),
        prefix=f".{path.stem}.tmp_",
        suffix=path.suffix
    )

    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()            # 刷到操作系统缓冲区
            os.fsync(f.fileno())  # 刷到磁盘

        # 原子替换：这一步要么完全成功，要么完全失败
        os.replace(tmp_path, str(path))

    except BaseException:
        # 出错时删除临时文件，避免残留
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

### 6.3 python-frontmatter 集成

```python
import frontmatter
from datetime import datetime


def update_memory_file(
    filepath: str,
    frontmatter_updates: dict = None,
    append_content: str = None
) -> None:
    """
    更新记忆文件的统一接口。

    :param filepath: 文件路径
    :param frontmatter_updates: 要更新的 YAML 字段 (None 则不更新)
    :param append_content: 要追加的 Markdown 内容 (None 则不追加)
    """
    path = Path(filepath)

    # 加载现有文件
    if path.exists():
        post = frontmatter.load(str(path))
    else:
        post = frontmatter.Post(content="")

    # 更新 YAML Front Matter
    if frontmatter_updates:
        for key, value in frontmatter_updates.items():
            post[key] = value

    # 追加 Markdown Body
    if append_content:
        post.content += append_content

    # 自动更新元数据
    post["version"] = post.get("version", 0) + 1
    post["last_modified"] = datetime.now().isoformat()

    # 原子写入
    atomic_write(str(path), frontmatter.dumps(post))
```

---

## 7. MemoryManager 完整接口

```python
from pathlib import Path
from typing import Optional
import frontmatter


class MemoryManager:
    """
    Agent 记忆管理器。

    职责:
    1. 渐进式加载记忆文件
    2. 应用引擎状态变化 (YAML FM)
    3. 应用 Agent 记忆更新 (MD Body)
    4. 定期压缩过大的文件
    5. 维护索引文件
    """

    def __init__(self, workspace_path: str, llm_client=None):
        self.workspace = Path(workspace_path)
        self.loader = MemoryLoader(workspace_path)
        self.llm_client = llm_client

    # ========== 读取 ==========

    def load_context(self, context_hints: list[str], depth: str = "auto") -> str:
        """
        根据 context_hints 加载记忆上下文。

        :param context_hints: 引擎提供的文件路径提示列表
        :param depth: 加载深度 "index" / "activation" / "execution" / "auto"
        :return: 组装好的上下文文本，可直接嵌入 prompt
        """
        if depth == "index":
            return self.loader.load_index(context_hints)
        elif depth == "activation":
            return self.loader.load_activation(context_hints)
        elif depth == "execution":
            return self.loader.load_execution(context_hints)
        else:  # auto: 默认加载 index 层，由 Agent 决定是否深入
            return self.loader.load_index(context_hints)

    def load_full_file(self, file_path: str) -> Optional[dict]:
        """加载完整文件，返回 {frontmatter: dict, content: str}"""
        full_path = self.workspace / file_path
        if not full_path.exists():
            return None
        post = frontmatter.load(str(full_path))
        return {
            "frontmatter": dict(post.metadata),
            "content": post.content
        }

    # ========== 写入 ==========

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

    # ========== 压缩 ==========

    async def check_and_compress(self, max_chars: int = 3000) -> list[str]:
        """检查所有文件，压缩过大的。返回被压缩的文件列表"""
        compressed = []
        for md_file in self.workspace.rglob("*.md"):
            if md_file.name.startswith("_"):
                continue  # 跳过索引文件
            if await self.compress_if_needed(str(md_file), max_chars):
                compressed.append(str(md_file.relative_to(self.workspace)))
        return compressed

    # ========== 索引 ==========

    def rebuild_index(self) -> None:
        """重建所有 _index.md 和全局 index.md"""
        # 实现略：遍历所有子目录，生成 _index.md
        # 然后汇总生成全局 index.md
        pass

    # ========== 初始化 ==========

    def initialize_workspace(self) -> None:
        """初始化 workspace 目录结构"""
        dirs = ["npcs", "locations", "story", "quests", "items", "player", "session"]
        for d in dirs:
            (self.workspace / d).mkdir(parents=True, exist_ok=True)
            index_path = self.workspace / d / "_index.md"
            if not index_path.exists():
                atomic_write(str(index_path), f"---\ntype: index\ncategory: {d}\nentity_count: 0\n---\n\n## {d} 列表\n\n(暂无)")
```

---

## 8. Token 预算管理

### 8.1 上下文窗口分配

假设 DeepSeek 上下文窗口为 64K tokens：

| 区域 | Token 预算 | 说明 |
|------|-----------|------|
| System Prompt | ~2000 | Agent 角色定义 + 输出格式要求 |
| Active Skills | ~3000 | 当前加载的 Skill 文件 |
| Memory (Index) | ~1000 | 3-5 个实体的索引摘要 |
| Memory (Activation/Execution) | ~5000 | 按需加载的详细记忆 |
| Conversation History | ~10000 | 最近 10-15 轮对话 |
| Current Event | ~500 | 当前引擎事件 |
| Output Space | ~4000 | Agent 的 JSON 输出 |
| **合计** | **~25500** | 留有余量，不塞满窗口 |

### 8.2 动态调整策略

```python
def calculate_memory_budget(
    system_prompt_tokens: int,
    active_skills_tokens: int,
    history_tokens: int,
    total_budget: int = 60000,
    output_reserve: int = 4000,
) -> int:
    """
    动态计算记忆可用的 token 预算。

    原则: 记忆预算 = 总预算 - 已占用 - 输出预留 - 安全余量
    """
    safety_margin = 5000
    available = total_budget - system_prompt_tokens - active_skills_tokens - history_tokens - output_reserve - safety_margin
    return max(available, 1000)  # 至少保留 1000 tokens 给记忆
```

---

## 9. WorkBench 集成

### 9.1 文件监控

WorkBench 使用 `watchdog` 监控 workspace 目录变化，实时刷新文件树：

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json


class WorkspaceWatcher(FileSystemEventHandler):
    """监控 workspace 目录变化，通过 WebSocket 通知 WorkBench"""

    def __init__(self, workspace_path: str, ws_broadcast=None):
        self.workspace = workspace_path
        self.ws_broadcast = ws_broadcast

    def on_modified(self, event):
        if event.src_path.endswith(".md"):
            rel_path = Path(event.src_path).relative_to(self.workspace)
            self._notify("file_modified", str(rel_path))

    def on_created(self, event):
        if event.src_path.endswith(".md"):
            rel_path = Path(event.src_path).relative_to(self.workspace)
            self._notify("file_created", str(rel_path))

    def on_deleted(self, event):
        if event.src_path.endswith(".md"):
            rel_path = Path(event.src_path).relative_to(self.workspace)
            self._notify("file_deleted", str(rel_path))

    def _notify(self, event_type: str, file_path: str):
        if self.ws_broadcast:
            self.ws_broadcast(json.dumps({
                "type": "workspace_change",
                "event": event_type,
                "path": file_path
            }))
```

### 9.2 WorkBench 编辑 → Agent 热更新

当用户在 WorkBench 中编辑记忆文件时：

1. WorkBench 通过 `PUT /api/workspace/file` 更新文件
2. Agent 端的 `WorkspaceWatcher` 检测到文件变化
3. Agent 在下一轮自动加载最新内容
4. **无需重启 Agent**

---

## 10. 测试要点

### 10.1 单元测试

```python
import pytest
import tempfile
import os
from pathlib import Path


class TestMemorySystem:
    """记忆系统测试"""

    @pytest.fixture
    def workspace(self, tmp_path):
        """创建临时 workspace 目录"""
        ws = tmp_path / "workspace"
        ws.mkdir()
        return ws

    @pytest.fixture
    def sample_npc(self, workspace):
        """创建示例 NPC 文件"""
        content = """---
name: 铁匠
type: npc
id: npc_blacksmith
hp: 80
relationship_with_player: 30
version: 1
last_modified: 2026-04-28T14:00:00
modified_by: engine
created_at: 2026-04-26T10:00:00
tags: [npc, 黑铁镇]
---

## 初始印象
[第1天] 铁匠铺的老板，看起来很健壮。
"""
        npc_path = workspace / "npcs" / "铁匠.md"
        npc_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(str(npc_path), content)
        return npc_path

    def test_atomic_write_creates_file(self, workspace):
        """原子写入应正确创建文件"""
        target = str(workspace / "test.md")
        atomic_write(target, "# Test\n\nContent")
        assert Path(target).exists()
        assert "Content" in Path(target).read_text()

    def test_atomic_write_is_atomic(self, workspace):
        """原子写入不应产生中间状态"""
        target = str(workspace / "test.md")
        atomic_write(target, "first")
        atomic_write(target, "second")
        content = Path(target).read_text()
        # 文件内容应该是完整的 "first" 或 "second"，不会是混合
        assert content in ("first", "second")

    def test_load_index_returns_compact_summary(self, workspace, sample_npc):
        """Index 层加载应返回紧凑摘要"""
        loader = MemoryLoader(str(workspace))
        index = loader.load_index(["npcs/铁匠"])
        assert "铁匠" in index
        assert "npc" in index
        # 不应包含完整正文
        assert "看起来很健壮" not in index

    def test_load_execution_returns_full_content(self, workspace, sample_npc):
        """Execution 层加载应返回完整内容"""
        loader = MemoryLoader(str(workspace))
        full = loader.load_execution(["npcs/铁匠"])
        assert "铁匠" in full
        assert "看起来很健壮" in full

    def test_append_memory_increments_version(self, workspace, sample_npc):
        """追加记忆应自动递增版本号"""
        update_memory_file(
            filepath=str(sample_npc),
            append_content="\n[第2天] 玩家来买剑了。"
        )
        post = frontmatter.load(str(sample_npc))
        assert post["version"] == 2
        assert "第2天" in post.content

    def test_update_frontmatter_preserves_body(self, workspace, sample_npc):
        """更新 YAML 应保留 Markdown Body"""
        update_memory_file(
            filepath=str(sample_npc),
            frontmatter_updates={"hp": 75, "relationship_with_player": 35}
        )
        post = frontmatter.load(str(sample_npc))
        assert post["hp"] == 75
        assert "初始印象" in post.content  # Body 不变

    def test_create_new_file(self, workspace):
        """创建不存在的文件"""
        new_path = str(workspace / "npcs" / "新NPC.md")
        update_memory_file(
            filepath=new_path,
            frontmatter_updates={"name": "新NPC", "type": "npc", "version": 1},
            append_content="\n## 初始印象\n[第1天] 新出现的角色。"
        )
        assert Path(new_path).exists()
        post = frontmatter.load(new_path)
        assert post["name"] == "新NPC"
```
