# V2 Skill 系统设计

> **版本**: v2.0-draft
> **日期**: 2026-04-28
> **前置文档**: `architecture_v2.md`, `memory_system.md`
> **关联文档**: `communication_protocol.md`
> **参考标准**: [SKILL.md Open Standard](https://agentskills.io) (Anthropic 主导, 27+ Agent 支持)

---

## 1. 什么是 Skill？

### 1.1 定义

Skill 是 Agent 的**能力定义文件**，采用 Markdown 格式，遵循 SKILL.md 开放标准。

类比：
- **MCP** 提供厨房（工具接口）
- **Skill** 提供菜谱（使用方法）

Agent 通过加载 Skill 来获得特定领域的能力（战斗、对话、任务管理等），而不需要硬编码在代码中。

### 1.2 Skill vs V1 Tool

| 维度 | V1 Tool (Python 函数) | V2 Skill (.md 文件) |
|------|----------------------|-------------------|
| 格式 | Python 代码 | Markdown 文件 |
| 创建者 | 只有开发者 | 开发者 + Agent |
| 修改方式 | 改代码 → 重启 | 编辑 .md → 立即生效 |
| 可读性 | 需要读代码 | 任何人都能读 |
| 灵活性 | 固定参数 | 自然语言描述 |
| 扩展方式 | 注册新函数 | 添加新 .md 文件 |

### 1.3 Skill 来源

| 来源 | 目录 | 说明 |
|------|------|------|
| **内置 Skill** | `skills/builtin/` | 开发者预置的核心能力 |
| **Agent 创建** | `skills/agent_created/` | Agent 在运行中自主创建的新能力 |

---

## 2. SKILL.md 文件格式

### 2.1 目录结构

```
skills/
├── builtin/
│   ├── combat/
│   │   └── SKILL.md          # 战斗系统 Skill
│   ├── dialogue/
│   │   └── SKILL.md          # 对话系统 Skill
│   ├── quest/
│   │   └── SKILL.md          # 任务管理 Skill
│   ├── exploration/
│   │   └── SKILL.md          # 探索系统 Skill
│   └── narration/
│       └── SKILL.md          # 叙事风格 Skill
└── agent_created/
    ├── negotiation/
    │   └── SKILL.md          # Agent 学会的谈判 Skill
    └── ...
```

**规则**: 每个 Skill 一个独立目录，目录名即 Skill 名称（kebab-case），目录内必须有 `SKILL.md`。

### 2.2 SKILL.md 完整格式

遵循 [agentskills.io](https://agentskills.io) 规范：

```markdown
---
name: combat
description: 战斗系统管理。当涉及战斗、伤害计算、技能使用、战斗结果判定时使用此 Skill。提供伤害公式、战斗流程、技能效果等规则。
version: 1.0.0
license: MIT
compatibility:
  - agent: game-master-agent
    version: ">=2.0"
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
  - keyword: ["战斗", "攻击", "防御", "技能", "伤害"]
---

# 战斗系统

## 核心规则

### 伤害公式
```
基础伤害 = 攻击力 * (1 + 技能加成) - 防御力 * 0.5
暴击伤害 = 基础伤害 * 1.5 (暴击率 = 敏捷 / 100)
最终伤害 = max(基础伤害, 1)  // 最低 1 点伤害
```

### 战斗流程
1. 确定先手（敏捷高者先行动）
2. 攻击方选择技能或普通攻击
3. 计算伤害并应用
4. 检查目标是否倒下
5. 交换攻守，重复 2-4
6. 一方 HP 归零时战斗结束

## 可用指令

当使用此 Skill 时，你可以发出以下 commands：

| intent | params | 说明 |
|--------|--------|------|
| `modify_stat` | `{player_id, stat: "hp", change: -15, reason: "哥布林攻击"}` | 修改玩家属性 |
| `update_npc_state` | `{npc_id, field: "hp", value: 0}` | 修改 NPC 状态 |
| `show_notification` | `{message: "你受到了 15 点伤害！", type: "damage"}` | 显示通知 |
| `play_sound` | `{sound_id: "hit"}` | 播放音效 |

## 叙事要求

战斗叙事应包含：
- 动作描写（挥剑、闪避、格挡）
- 伤害反馈（数字、效果描述）
- 氛围渲染（紧张感、危机感）
- NPC 反应（敌人的表情、台词）

**示例叙事**:
> 哥布林挥舞着生锈的短刀向你扑来！你侧身闪过，反手一剑划过它的手臂。哥布林惨叫一声，鲜血飞溅——它受到了 12 点伤害！

## 注意事项

- 战斗中不要突然切换到非战斗话题
- 伤害数值要合理，不要出现秒杀或无限战斗
- NPC 倒下后要描述倒下的场景
- 玩家 HP 低时要提醒危险
```

### 2.3 YAML Front Matter 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | Skill 名称，kebab-case，最长 64 字符 |
| `description` | string | 是 | 功能描述，最长 1024 字符。格式：[做什么] + [何时使用] + [关键能力] |
| `version` | string | 是 | 语义化版本号 |
| `license` | string | 否 | 开源协议 |
| `compatibility` | list | 否 | 兼容性要求 |
| `tags` | list[string] | 否 | 标签，用于搜索和分类 |
| `allowed-tools` | list[string] | 否 | 此 Skill 允许使用的 command intent 列表 |
| `triggers` | list | 否 | 触发条件（事件类型或关键词） |

### 2.4 triggers 触发机制

```yaml
triggers:
  # 事件触发：引擎事件类型匹配时自动加载
  - event_type: combat_start
  - event_type: combat_action

  # 关键词触发：用户输入包含关键词时考虑加载
  - keyword: ["战斗", "攻击", "防御", "技能", "伤害"]

  # 记忆触发：context_hints 包含特定路径时加载
  - memory_hint: ["quests/q_boss"]
```

---

## 3. Skill 加载流程

### 3.1 渐进式加载

与记忆系统一样，Skill 也采用渐进式披露：

```
Layer 1: Discovery (~100 tokens)
    只读取 YAML Front Matter 的 name + description
    用途: 判断哪些 Skill 与当前事件相关

Layer 2: Activation (~1000-3000 tokens)
    读取完整 YAML + Markdown 核心规则部分
    用途: Agent 了解 Skill 的具体规则

Layer 3: Execution (on demand)
    读取完整 SKILL.md
    用途: 需要参考完整指令和示例时
```

### 3.2 加载决策流程

```
引擎事件到达
    │
    ▼
Step 1: 扫描所有 Skill 的 Discovery 层
    │  读取每个 SKILL.md 的 name + description
    │  ~100 tokens per skill
    │
    ▼
Step 2: 匹配触发条件
    │  检查 event_type 是否匹配 triggers
    │  检查用户输入是否包含 keyword
    │  检查 context_hints 是否匹配 memory_hint
    │
    ▼
Step 3: 加载匹配 Skill 的 Activation 层
    │  读取完整 YAML + 核心规则
    │  ~1000-3000 tokens per skill
    │
    ▼
Step 4: 嵌入 Prompt
    │  将 Skill 内容作为系统消息的一部分
    │
    ▼
Agent 生成回复
```

### 3.3 SkillLoader 实现代码

```python
import frontmatter
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class SkillMetadata:
    """Skill 元数据 (Discovery 层)"""
    name: str
    description: str
    version: str
    tags: list[str]
    triggers: list[dict]
    file_path: str
    source: str  # "builtin" or "agent_created"


class SkillLoader:
    """Skill 发现与加载器"""

    def __init__(self, skills_path: str):
        self.skills_path = Path(skills_path)
        self._cache: dict[str, SkillMetadata] = {}

    def discover_all(self) -> list[SkillMetadata]:
        """
        Layer 1: 发现所有 Skill。
        扫描 skills 目录，读取每个 SKILL.md 的 YAML Front Matter。

        返回所有 Skill 的元数据列表，每个约 100 tokens。
        """
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
        """
        根据当前事件匹配相关 Skill。

        匹配规则:
        1. event_type 匹配 triggers.event_type
        2. user_input 包含 triggers.keyword
        3. context_hints 匹配 triggers.memory_hint
        """
        all_skills = self.discover_all()
        relevant = []

        for skill in all_skills:
            score = 0

            for trigger in skill.triggers:
                # 事件类型匹配 (权重最高)
                if event_type and trigger.get("event_type") == event_type:
                    score += 10

                # 关键词匹配
                if user_input and "keyword" in trigger:
                    keywords = trigger["keyword"]
                    if isinstance(keywords, str):
                        keywords = [keywords]
                    for kw in keywords:
                        if kw in user_input:
                            score += 5

                # 记忆路径匹配
                if context_hints and "memory_hint" in trigger:
                    hints = trigger["memory_hint"]
                    if isinstance(hints, str):
                        hints = [hints]
                    for hint in hints:
                        if any(hint in ch for ch in context_hints):
                            score += 3

            if score > 0:
                relevant.append((skill, score))

        # 按相关度排序
        relevant.sort(key=lambda x: x[1], reverse=True)
        return [skill for skill, score in relevant]

    def load_skill_content(self, skill_name: str) -> Optional[str]:
        """
        Layer 2/3: 加载 Skill 的完整内容。

        返回 Markdown body 部分（不含 YAML Front Matter）。
        """
        if skill_name not in self._cache:
            return None

        skill = self._cache[skill_name]
        post = frontmatter.load(skill.file_path)
        return post.content

    def load_skill_activation(self, skill_name: str) -> Optional[str]:
        """
        Layer 2: 加载 Skill 的激活层。
        返回 YAML 关键字段 + Markdown 前 2000 字符。
        """
        if skill_name not in self._cache:
            return None

        skill = self._cache[skill_name]
        post = frontmatter.load(skill.file_path)

        # YAML 关键信息
        info_lines = [
            f"## Skill: {skill.name} (v{skill.version})",
            f"**描述**: {skill.description}",
        ]

        if skill.tags:
            info_lines.append(f"**标签**: {', '.join(skill.tags)}")

        allowed_tools = post.get("allowed-tools", [])
        if allowed_tools:
            info_lines.append(f"**可用指令**: {', '.join(allowed_tools)}")

        # Markdown 前 2000 字符
        body_preview = post.content[:2000]
        if len(post.content) > 2000:
            body_preview += "\n\n... (内容已截断，如需完整内容请请求加载)"

        return "\n".join(info_lines) + "\n\n" + body_preview

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

    def invalidate_cache(self):
        """清除缓存（Skill 文件变更时调用）"""
        self._cache.clear()
```

### 3.4 Skill 嵌入 Prompt

```python
def assemble_skills_prompt(skill_loader: SkillLoader, relevant_skills: list[SkillMetadata]) -> str:
    """
    将相关 Skill 的内容组装为 prompt 片段。
    """
    if not relevant_skills:
        return ""

    sections = ["## 可用能力 (Skills)\n"]

    for skill in relevant_skills:
        content = skill_loader.load_skill_activation(skill.name)
        if content:
            sections.append(content)
            sections.append("")  # 空行分隔

    return "\n".join(sections)
```

---

## 4. Agent 自主创建 Skill

### 4.1 创建时机

Agent 在以下情况可以自主创建新 Skill：

1. **重复模式识别**: Agent 发现自己在多次对话中重复使用相同的规则/流程
2. **玩家引入新玩法**: 玩家提出了系统没有覆盖的新玩法
3. **剧情需要**: 新剧情线需要特定的规则支持

### 4.2 创建流程

```
Agent 检测到需要新 Skill
    │
    ▼
Step 1: Agent 在 memory_updates 中请求创建
    │  {"action": "create_skill", "name": "negotiation", "content": "..."}
    │
    ▼
Step 2: MemoryManager 验证
    │  - 名称是否已存在
    │  - 内容格式是否合法
    │  - YAML Front Matter 是否完整
    │
    ▼
Step 3: 写入 skills/agent_created/{name}/SKILL.md
    │
    ▼
Step 4: SkillLoader.invalidate_cache()
    │  清除缓存，下次发现时自动加载
    │
    ▼
Step 5: 通知 WorkBench
    │  SSE: {"event": "skill_created", "name": "negotiation"}
```

### 4.3 Agent 创建 Skill 的 Prompt 指导

在 system prompt 中包含以下指导：

```markdown
## 创建新 Skill

当你发现以下情况时，可以创建新的 Skill 文件：

1. 你在多次对话中重复使用相同的规则或流程
2. 玩家引入了系统没有覆盖的新玩法
3. 新剧情线需要特定的规则支持

创建方式：在 memory_updates 中添加一条：
```json
{
  "file": "skills/agent_created/{skill-name}/SKILL.md",
  "action": "create_skill",
  "content": "---\nname: {skill-name}\ndescription: ...\nversion: 1.0.0\n---\n\n# {Skill 标题}\n\n## 规则\n..."
}
```

Skill 文件应包含：
- 清晰的 YAML Front Matter（name, description, version, triggers）
- 核心规则和流程
- 可用的 commands 列表
- 叙事要求和示例
```

### 4.4 示例：Agent 创建谈判 Skill

```markdown
---
name: negotiation
description: 谈判与交易系统。当玩家尝试讨价还价、说服NPC、进行交易谈判时使用。提供价格计算、说服判定、交易流程等规则。
version: 1.0.0
tags: [negotiation, trade, persuasion]
allowed-tools:
  - update_npc_relationship
  - give_item
  - remove_item
  - show_notification
triggers:
  - keyword: ["讨价还价", "便宜", "说服", "交易", "谈判", "价格"]
---

# 谈判与交易系统

## 核心规则

### 价格谈判
- 基础价格由物品稀有度决定
- 好感度影响价格：每 10 点好感度 = 5% 折扣
- 玩家的说服能力影响最终价格
- 谈判失败可能降低好感度

### 说服判定
```
说服成功率 = 基础率(30%) + 好感度加成(好感度/2)% + 玩家等级加成(等级*2)%
```

## 可用指令
| intent | 说明 |
|--------|------|
| `update_npc_relationship` | 谈判成功/失败影响好感度 |
| `give_item` | 交易成功给予物品 |
| `remove_item` | 交易成功移除金币 |
| `show_notification` | 显示交易结果 |

## 叙事要求
- 描写 NPC 的表情和语气变化
- 体现讨价还价的拉锯过程
- 交易成功时要有满足感
```

---

## 5. 内置 Skill 设计

### 5.1 combat (战斗)

**触发**: `combat_start`, `combat_action`, `combat_end`, 关键词 "战斗/攻击/防御"

**核心能力**:
- 伤害计算公式
- 战斗流程管理
- 技能效果判定
- 战斗叙事生成

### 5.2 dialogue (对话)

**触发**: `npc_interact`, 关键词 "聊天/对话/询问"

**核心能力**:
- NPC 性格一致性维护
- 对话选项生成
- 好感度影响对话风格
- 信息透露控制

### 5.3 quest (任务)

**触发**: `quest_update`, 关键词 "任务/委托/目标"

**核心能力**:
- 任务发布流程
- 任务进度追踪
- 任务奖励发放
- 多任务并行管理

### 5.4 exploration (探索)

**触发**: `player_move`, 关键词 "探索/搜索/调查"

**核心能力**:
- 地点描述生成
- 隐藏物品发现
- 环境互动
- 地图信息管理

### 5.5 narration (叙事)

**触发**: 始终加载（默认 Skill）

**核心能力**:
- 叙事风格控制
- 节奏把控
- 氛围渲染
- 多感官描写

---

## 6. Skill 管理 API

### 6.1 REST 端点

```python
# 列出所有 Skill (Discovery 层)
GET /api/skills
# Response: [
#   {"name": "combat", "description": "战斗系统...", "version": "1.0.0", "source": "builtin", "tags": [...]},
#   {"name": "negotiation", "description": "谈判系统...", "version": "1.0.0", "source": "agent_created", "tags": [...]}
# ]

# 获取 Skill 完整内容
GET /api/skills/{skill_name}
# Response: {"frontmatter": {...}, "content": "...", "file_path": "skills/builtin/combat/SKILL.md"}

# 更新 Skill (WorkBench 编辑后保存)
PUT /api/skills/{skill_name}
# Body: {"content": "---\nname: combat\n---\n\n# 新内容..."}
# 注意: builtin Skill 可以更新内容，但不能改 name

# 删除 Skill (仅限 agent_created)
DELETE /api/skills/{skill_name}
# Response: {"status": "deleted"}

# 获取 Skill 的触发统计
GET /api/skills/{skill_name}/stats
# Response: {"trigger_count": 42, "last_triggered": "2026-04-28T14:30:00", "avg_tokens": 1500}
```

### 6.2 WorkBench 中的 Skill 管理

WorkBench 提供 Skill 管理面板：

| 功能 | 说明 |
|------|------|
| Skill 列表 | 显示所有 Skill，标记 builtin/agent_created |
| Skill 编辑 | 使用 MD 编辑器编辑 Skill 内容 |
| 触发统计 | 显示每个 Skill 的触发次数和 token 消耗 |
| 热更新 | 编辑保存后立即生效，无需重启 Agent |
| 新建 Skill | 开发者手动创建新 Skill |

---

## 7. Skill 与 Memory 的协作

### 7.1 协作模式

```
引擎事件到达
    │
    ├─► SkillLoader.get_relevant_skills(event)
    │   返回: [combat, dialogue]
    │
    ├─► MemoryLoader.load_index(context_hints)
    │   返回: "NPC 索引: 铁匠 (hp:80, 关系:30)"
    │
    ▼
Prompt 组装
    │
    ├── System Prompt (固定)
    ├── Active Skills (combat + dialogue 的规则)
    ├── Memory Context (铁匠的状态和记录)
    ├── Conversation History (历史对话)
    └── Current Event (当前事件)
    │
    ▼
Agent 生成回复
    │
    ├── narrative: "铁匠举起锤子..."
    ├── commands: [modify_stat, ...]  ← 来自 Skill 定义的 intent
    └── memory_updates: [...]  ← 更新记忆文件
```

### 7.2 Skill 定义 commands，Memory 记录结果

- **Skill** 告诉 Agent "你可以做什么"（可用 commands 列表）
- **Memory** 告诉 Agent "之前发生了什么"（历史记录）
- Agent 结合两者做出决策

---

## 8. 测试要点

```python
import pytest
import tempfile
from pathlib import Path


class TestSkillSystem:
    """Skill 系统测试"""

    @pytest.fixture
    def skills_dir(self, tmp_path):
        """创建临时 skills 目录"""
        builtin = tmp_path / "skills" / "builtin"
        builtin.mkdir(parents=True)
        return tmp_path / "skills"

    @pytest.fixture
    def combat_skill(self, skills_dir):
        """创建示例 combat Skill"""
        skill_dir = skills_dir / "builtin" / "combat"
        skill_dir.mkdir(parents=True)
        content = """---
name: combat
description: 战斗系统管理。当涉及战斗时使用。
version: 1.0.0
tags: [combat, battle]
triggers:
  - event_type: combat_start
  - keyword: ["战斗", "攻击"]
allowed-tools:
  - modify_stat
---

# 战斗系统

## 伤害公式
基础伤害 = 攻击力 - 防御力 * 0.5
"""
        (skill_dir / "SKILL.md").write_text(content)
        return skill_dir

    def test_discover_finds_all_skills(self, skills_dir, combat_skill):
        """发现应找到所有 Skill"""
        loader = SkillLoader(str(skills_dir))
        skills = loader.discover_all()
        assert len(skills) == 1
        assert skills[0].name == "combat"

    def test_discover_returns_metadata_only(self, skills_dir, combat_skill):
        """Discovery 层应只返回元数据"""
        loader = SkillLoader(str(skills_dir))
        skills = loader.discover_all()
        assert skills[0].description == "战斗系统管理。当涉及战斗时使用。"
        assert skills[0].version == "1.0.0"

    def test_relevant_skills_by_event_type(self, skills_dir, combat_skill):
        """事件类型应正确匹配 Skill"""
        loader = SkillLoader(str(skills_dir))
        relevant = loader.get_relevant_skills(event_type="combat_start")
        assert len(relevant) == 1
        assert relevant[0].name == "combat"

    def test_relevant_skills_by_keyword(self, skills_dir, combat_skill):
        """关键词应正确匹配 Skill"""
        loader = SkillLoader(str(skills_dir))
        relevant = loader.get_relevant_skills(user_input="我要攻击哥布林")
        assert len(relevant) == 1

    def test_no_match_returns_empty(self, skills_dir, combat_skill):
        """无匹配时应返回空列表"""
        loader = SkillLoader(str(skills_dir))
        relevant = loader.get_relevant_skills(user_input="你好铁匠")
        assert len(relevant) == 0

    def test_load_skill_content(self, skills_dir, combat_skill):
        """加载应返回完整内容"""
        loader = SkillLoader(str(skills_dir))
        content = loader.load_skill_content("combat")
        assert "伤害公式" in content

    def test_load_nonexistent_skill_returns_none(self, skills_dir):
        """加载不存在的 Skill 应返回 None"""
        loader = SkillLoader(str(skills_dir))
        assert loader.load_skill_content("nonexistent") is None

    def test_invalidate_cache(self, skills_dir, combat_skill):
        """清除缓存后应重新扫描"""
        loader = SkillLoader(str(skills_dir))
        loader.discover_all()  # 填充缓存
        assert len(loader._cache) == 1

        # 添加新 Skill
        dialogue_dir = skills_dir / "builtin" / "dialogue"
        dialogue_dir.mkdir()
        (dialogue_dir / "SKILL.md").write_text("---\nname: dialogue\ndescription: 对话系统\nversion: 1.0.0\n---\n\n# 对话")

        # 缓存未清除，仍然只有 1 个
        assert len(loader.discover_all()) == 1

        # 清除缓存后，应该有 2 个
        loader.invalidate_cache()
        assert len(loader.discover_all()) == 2
```
