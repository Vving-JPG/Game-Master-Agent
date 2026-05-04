# 修改文档：让 AI 通过 Skill 自动创建角色/剧情/道具

> 本文档基于 2026-05-03 GitHub main 分支最新源码分析，列出需要修改的文件和具体代码，交给 Trae 执行。
> 仓库地址：https://github.com/Vving-JPG/Game-Master-Agent

---

## 一、现状分析

### 1.1 已有的基础设施（不需要修改）

| 组件 | 文件 | 状态 |
|------|------|------|
| `NPCRepo.create()` | `core/models/repository.py` | ✅ 已实现，支持 `**kwargs` |
| `LocationRepo.create()` | `core/models/repository.py` | ✅ 已实现 |
| `ItemRepo.create()` | `core/models/repository.py` | ✅ 已实现 |
| `QuestRepo.create()` | `core/models/repository.py` | ✅ 已实现 |
| `NPCRepo.update()` | `core/models/repository.py` | ✅ 已实现 |
| `LocationRepo.update()` | `core/models/repository.py` | ✅ 已实现 |
| `MemoryRepo.store()` | `core/models/repository.py` | ⚠️ 已实现但引用不存在的 `memories` 表（见修改 0） |
| `SkillLoader` | `feature/ai/skill_loader.py` | ✅ 完整实现（评分、加载、SKILL.md 解析） |
| `PromptBuilder.build()` | `feature/ai/prompt_builder.py` | ✅ 已支持 `skill_contents` 参数 |

### 1.2 需要修改的部分

| 组件 | 文件 | 问题 |
|------|------|------|
| **数据库 Schema** | `core/models/schema.sql` | `MemoryRepo` 引用不存在的 `memories` 表，只有旧版 `npc_memories` |
| **AI 工具** | `feature/ai/tools.py` | 缺少知识库 CRUD 工具（create_npc, search_npc 等）；现有 9 个工具全是 placeholder |
| **工具注册** | `feature/ai/tools.py` | `ALL_TOOLS` 是手动列表，新工具需要手动追加 |
| **Skill 接入** | `feature/ai/nodes.py` | SkillLoader 未被接入（TODO 注释） |
| **System Prompt** | `feature/ai/nodes.py` | 需要添加世界构建命令说明 |
| **工具结果反馈** | `feature/ai/nodes.py` | 工具执行结果不反馈给 LLM |
| **GMAgent 参数** | `feature/ai/gm_agent.py` | `system_prompt` 和 `skills_dir` 参数被接收但未使用 |
| **Repository 补全** | `core/models/repository.py` | 多个 Repo 缺少 delete/update 方法 |

---

## 二、修改清单

### 修改 0（前置修复）：`core/models/schema.sql` — 添加 memories 表

**目标**：`MemoryRepo` 的所有方法都操作 `memories` 表，但 schema.sql 中只有旧版 `npc_memories` 表。不修复会导致运行时 `no such table: memories` 错误。

**在 `schema.sql` 文件末尾（最后一个 `);` 之后）添加**：

```sql
-- 统一记忆表（替代旧版 npc_memories）
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL DEFAULT 1,
    category TEXT NOT NULL DEFAULT 'session',
    source TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    tags TEXT NOT NULL DEFAULT '[]',
    metadata TEXT NOT NULL DEFAULT '{}',
    turn_created INTEGER NOT NULL DEFAULT 0,
    turn_last_referenced INTEGER NOT NULL DEFAULT 0,
    compressed INTEGER NOT NULL DEFAULT 0,
    reference_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_memories_world ON memories(world_id);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(world_id, category);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(world_id, importance DESC);
```

---

### 修改 1（核心）：`feature/ai/tools.py` — 添加知识库管理工具

**目标**：添加 7 个新工具函数，让 AI 能通过 Function Calling 自动创建/查询/修改知识库实体。

#### 1.1 添加导入

**在文件顶部的导入区域**（`from langchain_core.tools import tool` 之后）添加：

```python
from core.models.repository import NPCRepo, LocationRepo, ItemRepo, QuestRepo
from core.models.entities import ItemType, QuestType, QuestStatus
from foundation.config import settings
```

#### 1.2 添加辅助函数

**在 `@tool` 装饰的第一个函数之前**添加：

```python
def _get_db_path() -> str:
    """获取数据库路径"""
    return getattr(settings, 'database_path', 'data/game.db')
```

#### 1.3 添加 7 个新工具函数

**在现有最后一个工具函数 `check_quest_prerequisites` 之后、`ALL_TOOLS` 列表之前**添加：

```python
# ============================================================
# 知识库管理工具 — 让 AI 自动创建/查询世界元素
# ============================================================

@tool
def create_npc(name: str, location_name: str = "", personality: str = "neutral",
               backstory: str = "", speech_style: str = "", goals: str = "",
               mood: str = "neutral") -> str:
    """创建一个新的 NPC 角色。

    Args:
        name: NPC 名称（必填）
        location_name: 所在地点名称（可选）
        personality: 性格描述，如"热情好客"（可选）
        backstory: 背景故事（可选）
        speech_style: 说话风格描述（可选）
        goals: 目标列表，用逗号分隔（可选）
        mood: 当前心情，可选值: serene/happy/neutral/sad/angry/fearful（默认 neutral）

    Returns:
        创建结果描述
    """
    try:
        db_path = _get_db_path()
        repo = NPCRepo()

        # 如果指定了地点，查找地点 ID
        location_id = 0
        if location_name:
            loc_repo = LocationRepo()
            locations = loc_repo.get_by_world(world_id=1, db_path=db_path)
            for loc in locations:
                if loc.name == location_name:
                    location_id = loc.id
                    break

        # 解析目标
        goal_list = [g.strip() for g in goals.split(",") if g.strip()] if goals else []

        npc = repo.create(
            world_id=1,
            name=name,
            location_id=location_id,
            mood=mood,
            backstory=backstory,
            speech_style=speech_style,
            goals=goal_list,
            db_path=db_path
        )

        result = f"已创建 NPC: {npc.name} (ID: {npc.id})"
        if location_id:
            result += f"，位于 {location_name}"
        if backstory:
            result += f"。背景: {backstory[:50]}..."
        return result
    except Exception as e:
        return f"创建 NPC 失败: {str(e)}"


@tool
def search_npcs(location_name: str = "", name_keyword: str = "") -> str:
    """搜索 NPC，可按地点或名称关键词过滤。

    Args:
        location_name: 地点名称（可选）
        name_keyword: 名称关键词（可选）

    Returns:
        匹配的 NPC 列表
    """
    try:
        db_path = _get_db_path()
        repo = NPCRepo()

        npcs = repo.get_by_world(world_id=1, db_path=db_path)

        results = []
        for npc in npcs:
            # 按地点过滤
            if location_name and npc.location_id != 0:
                loc_repo = LocationRepo()
                loc = loc_repo.get_by_id(npc.location_id, db_path=db_path)
                if loc and loc.name != location_name:
                    continue

            # 按名称关键词过滤
            if name_keyword and name_keyword.lower() not in npc.name.lower():
                continue

            results.append(f"- {npc.name} (ID:{npc.id}, 心情:{npc.mood}, 位置ID:{npc.location_id})")

        if not results:
            return "未找到匹配的 NPC"
        return f"找到 {len(results)} 个 NPC:\n" + "\n".join(results)
    except Exception as e:
        return f"搜索 NPC 失败: {str(e)}"


@tool
def create_location(name: str, description: str = "", connections: str = "") -> str:
    """创建一个新的地点。

    Args:
        name: 地点名称（必填）
        description: 地点描述（可选）
        connections: 出口连接，格式 "方向:目标地点ID"，用逗号分隔。如 "north:2, south:3"（可选）

    Returns:
        创建结果描述
    """
    try:
        db_path = _get_db_path()
        repo = LocationRepo()

        # 解析连接
        conn_dict = {}
        if connections:
            for part in connections.split(","):
                part = part.strip()
                if ":" in part:
                    direction, target_id = part.split(":", 1)
                    conn_dict[direction.strip()] = int(target_id.strip())

        location = repo.create(
            world_id=1,
            name=name,
            description=description,
            connections=conn_dict if conn_dict else None,
            db_path=db_path
        )

        result = f"已创建地点: {location.name} (ID: {location.id})"
        if description:
            result += f"。{description[:80]}"
        if conn_dict:
            result += f"。出口: {connections}"
        return result
    except Exception as e:
        return f"创建地点失败: {str(e)}"


@tool
def create_item(name: str, item_type: str = "misc", description: str = "",
                rarity: str = "common") -> str:
    """创建一个新的物品/道具模板。

    Args:
        name: 物品名称（必填）
        item_type: 物品类型，可选: weapon/armor/consumable/material/quest/misc（默认 misc）
        description: 物品描述（可选）
        rarity: 稀有度，可选: common/uncommon/rare/epic/legendary（默认 common）

    Returns:
        创建结果描述
    """
    try:
        db_path = _get_db_path()
        repo = ItemRepo()

        item = repo.create(
            name=name,
            item_type=item_type,
            description=description,
            db_path=db_path
        )

        result = f"已创建物品: {item.name} (ID: {item.id}, 类型: {item_type}, 稀有度: {rarity})"
        if description:
            result += f"。{description[:80]}"
        return result
    except Exception as e:
        return f"创建物品失败: {str(e)}"


@tool
def create_quest(title: str, description: str = "", quest_type: str = "side",
                 rewards: str = "", prerequisites: str = "") -> str:
    """创建一个新的任务/剧情。

    Args:
        title: 任务标题（必填）
        description: 任务描述（可选）
        quest_type: 任务类型，可选: main/side/daily/hidden（默认 side）
        rewards: 奖励描述（可选）
        prerequisites: 前置条件描述（可选）

    Returns:
        创建结果描述
    """
    try:
        db_path = _get_db_path()
        repo = QuestRepo()

        quest = repo.create(
            world_id=1,
            title=title,
            description=description,
            db_path=db_path
        )

        result = f"已创建任务: {quest.title} (ID: {quest.id}, 类型: {quest_type})"
        if description:
            result += f"。{description[:80]}"
        if rewards:
            result += f"。奖励: {rewards}"
        return result
    except Exception as e:
        return f"创建任务失败: {str(e)}"


@tool
def get_world_state() -> str:
    """获取当前世界的完整状态概览，包括所有地点、NPC、物品和任务。

    Returns:
        世界状态摘要
    """
    try:
        db_path = _get_db_path()

        parts = []

        # 地点
        loc_repo = LocationRepo()
        locations = loc_repo.get_by_world(world_id=1, db_path=db_path)
        parts.append(f"=== 地点 ({len(locations)}) ===")
        for loc in locations:
            conn_str = ", ".join([f"{d}:{tid}" for d, tid in (loc.connections or {}).items()]) if loc.connections else "无"
            parts.append(f"  [{loc.id}] {loc.name} - 出口: {conn_str}")

        # NPC
        npc_repo = NPCRepo()
        npcs = npc_repo.get_by_world(world_id=1, db_path=db_path)
        parts.append(f"\n=== NPC ({len(npcs)}) ===")
        for npc in npcs:
            parts.append(f"  [{npc.id}] {npc.name} - 心情:{npc.mood}, 位置ID:{npc.location_id}")

        # 物品
        item_repo = ItemRepo()
        items = item_repo.search(name="", db_path=db_path)
        parts.append(f"\n=== 物品 ({len(items)}) ===")
        for item in items:
            parts.append(f"  [{item.id}] {item.name} - 类型:{item.item_type.value}, 稀有度:{item.rarity.value}")

        # 任务
        quest_repo = QuestRepo()
        quests = quest_repo.list_all(db_path=db_path)
        parts.append(f"\n=== 任务 ({len(quests)}) ===")
        for quest in quests:
            parts.append(f"  [{quest.id}] {quest.title} - 状态:{quest.status.value}, 类型:{quest.quest_type.value}")

        return "\n".join(parts)
    except Exception as e:
        return f"获取世界状态失败: {str(e)}"


@tool
def update_npc_state(npc_name: str, mood: str = None, location_name: str = None,
                     add_goal: str = None, remove_goal: str = None) -> str:
    """更新 NPC 的状态（心情、位置、目标等）。

    Args:
        npc_name: NPC 名称（必填，用于查找）
        mood: 新的心情（可选）
        location_name: 移动到的新地点名称（可选）
        add_goal: 添加一个目标（可选）
        remove_goal: 移除一个目标（可选）

    Returns:
        更新结果描述
    """
    try:
        db_path = _get_db_path()
        repo = NPCRepo()

        # 查找 NPC
        npcs = repo.get_by_world(world_id=1, db_path=db_path)
        target = None
        for npc in npcs:
            if npc.name == npc_name:
                target = npc
                break

        if not target:
            return f"未找到名为 '{npc_name}' 的 NPC"

        updates = {}
        if mood:
            updates["mood"] = mood
        if location_name:
            loc_repo = LocationRepo()
            locations = loc_repo.get_by_world(world_id=1, db_path=db_path)
            for loc in locations:
                if loc.name == location_name:
                    updates["location_id"] = loc.id
                    break

        if updates:
            updated = repo.update(npc.id, db_path=db_path, **updates)
            if updated:
                result = f"已更新 NPC: {npc_name}"
                if mood:
                    result += f"，心情 → {mood}"
                if location_name:
                    result += f"，移动到 {location_name}"
                return result

        return f"NPC {npc_name} 无需更新"
    except Exception as e:
        return f"更新 NPC 失败: {str(e)}"
```

#### 1.4 注册新工具到 ALL_TOOLS

**找到现有的 `ALL_TOOLS` 列表**（大约在文件末尾），将新工具追加进去。

现有代码类似：
```python
ALL_TOOLS = [
    roll_dice, update_player_stat, give_item, remove_item,
    move_to_location, update_npc_relationship, update_quest_status,
    store_memory, check_quest_prerequisites
]
```

**替换为**：
```python
ALL_TOOLS = [
    # 原有工具
    roll_dice, update_player_stat, give_item, remove_item,
    move_to_location, update_npc_relationship, update_quest_status,
    store_memory, check_quest_prerequisites,
    # 知识库管理工具
    create_npc, search_npcs, create_location, create_item,
    create_quest, get_world_state, update_npc_state
]
```

> **注意**：`tools.py` 中 `ALL_TOOLS` 是手动维护的列表，没有自动注册机制。新工具必须手动追加。

---

### 修改 2（核心）：`feature/ai/nodes.py` — 接入 SkillLoader

**目标**：在 `node_build_prompt` 中接入 SkillLoader，让 Skill 内容被注入到 Prompt 中。

**找到 `node_build_prompt` 函数**，定位到以下代码：

```python
# 获取 Skill 内容（简化版，实际应从 SkillLoader 获取）
skill_contents = []
active_skills = state.get("active_skills", [])
# TODO: P3 阶段接入 SkillLoader
```

**替换为**：

```python
# 获取 Skill 内容
skill_contents = []
active_skills = state.get("active_skills", [])
if not active_skills:
    # 自动加载 Skill
    try:
        from feature.ai.skill_loader import SkillLoader
        skills_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'skills')
        if os.path.isdir(skills_dir):
            loader = SkillLoader(skills_dir)
            relevant = loader.get_relevant_skills(
                user_input=state.get("current_event", ""),
                event_type="player_action",
                context_hints=["narrative", "world_building"]
            )
            for skill in relevant:
                content = loader.load_activation(skill)
                if content:
                    skill_contents.append(content)
    except Exception:
        pass  # Skill 加载失败不影响主流程
```

> **注意**：需要确认 `nodes.py` 文件顶部有 `import os`。如果没有，在文件顶部导入区域添加 `import os`。

---

### 修改 3：`feature/ai/nodes.py` — 更新 System Prompt

**目标**：在 `_get_system_prompt()` 函数中添加新的知识库管理命令说明。

**找到 `_get_system_prompt()` 函数**，在返回的 prompt 字符串中，找到可用命令列表部分（类似 `- roll_dice: 掷骰子` 的列表），**在列表末尾追加**：

```python
## 世界构建命令（可随时使用）
- create_npc: 创建新的 NPC 角色（需提供名称，可选地点/性格/背景/说话风格/目标/心情）
- search_npcs: 搜索/查询 NPC（可按地点或名称过滤）
- create_location: 创建新的地点（需提供名称，可选描述和出口连接）
- create_item: 创建新的物品/道具（需提供名称，可选类型/稀有度/描述）
- create_quest: 创建新的任务/剧情（需提供标题，可选描述/类型/奖励/前置条件）
- get_world_state: 获取完整世界状态概览（所有地点/NPC/物品/任务）
- update_npc_state: 更新 NPC 状态（心情/位置/目标）

## 世界构建指导原则
1. 在故事推进过程中，根据需要动态创建 NPC、地点和物品
2. 创建前先用 get_world_state 或 search_npcs 检查是否已存在同名实体
3. 创建的实体应与当前故事情境一致，符合世界观设定
4. 每个新地点应有独特的描述和氛围（包含视觉/听觉/嗅觉细节）
5. NPC 应有鲜明的个性和说话风格，心情应反映当前情境
6. 物品应有合理的属性和背景故事，稀有度要适当
7. 任务应有明确的目标和合理的奖励
8. 创建后通过叙事自然地介绍给玩家，不要生硬地列出属性
```

---

### 修改 4：`feature/ai/nodes.py` — 工具执行结果反馈

**目标**：让工具执行结果能反馈回 LLM，使 AI 知道创建/修改是否成功。

**找到 `node_execute_commands` 函数**，在命令执行循环结束后、`return` 语句之前，添加结果反馈逻辑：

```python
# 在 node_execute_commands 的 return 之前添加：

# 将工具执行结果格式化并追加到对话历史，让 LLM 知道执行结果
if command_results:
    results_text = "\n".join([
        f"[工具结果] {r.get('command', 'unknown')}: {r.get('result', '无结果')}"
        for r in command_results
    ])
    if results_text:
        state["messages"].append({
            "role": "tool",
            "content": results_text
        })
```

---

### 修改 5：`feature/ai/gm_agent.py` — 启用 system_prompt 和 skills_dir 参数

**目标**：让 `GMAgent` 构造函数接收的 `system_prompt` 和 `skills_dir` 参数真正生效。

**找到 `GMAgent.__init__` 方法**，定位到参数接收但未使用的部分。

**在 `__init__` 方法体中**，添加以下逻辑（在 `self._world_id = world_id` 之后）：

```python
# 保存 system_prompt 和 skills_dir
self._custom_system_prompt = system_prompt
self._skills_dir = skills_dir

# 初始化 SkillLoader
self._skill_loader = None
if skills_dir:
    try:
        from feature.ai.skill_loader import SkillLoader
        self._skill_loader = SkillLoader(skills_dir)
    except Exception as e:
        from foundation.logger import get_logger
        get_logger(__name__).warning(f"SkillLoader 初始化失败: {e}")
```

**找到 `_load_initial_state` 方法**，在返回 `state` 之前，添加：

```python
# 注入自定义 system_prompt
if self._custom_system_prompt:
    state["system_prompt"] = self._custom_system_prompt
```

---

### 修改 6：`core/models/repository.py` — 补全缺失方法

**目标**：为 LocationRepo、NPCRepo、ItemRepo、QuestRepo 补全缺失的 delete/update 方法。

> **注意**：所有 Repo 方法都使用 `from foundation.database import get_connection` 获取数据库连接。确保导入存在。

#### 6.1 在 `LocationRepo` 类中添加 delete 方法

```python
def delete(self, location_id: int, db_path: str | Path | None = None) -> bool:
    """删除地点"""
    db = get_connection(db_path)
    try:
        cursor = db.execute("DELETE FROM locations WHERE id = ?", (location_id,))
        db.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        db.close()
```

#### 6.2 在 `NPCRepo` 类中添加 delete 方法

```python
def delete(self, npc_id: int, db_path: str | Path | None = None) -> bool:
    """删除 NPC"""
    db = get_connection(db_path)
    try:
        cursor = db.execute("DELETE FROM npcs WHERE id = ?", (npc_id,))
        db.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        db.close()
```

#### 6.3 在 `ItemRepo` 类中添加 update、delete、list_all 方法

```python
def update(self, item_id: int, db_path: str | Path | None = None, **kwargs) -> Item | None:
    """更新道具"""
    db = get_connection(db_path)
    try:
        item = self.get_by_id(item_id, db_path)
        if not item:
            return None
        sets = []
        values = []
        for key, value in kwargs.items():
            if hasattr(item, key):
                sets.append(f"{key} = ?")
                values.append(value)
        if not sets:
            return item
        values.append(item_id)
        db.execute(f"UPDATE items SET {', '.join(sets)} WHERE id = ?", values)
        db.commit()
        return self.get_by_id(item_id, db_path)
    except Exception:
        return None
    finally:
        db.close()

def delete(self, item_id: int, db_path: str | Path | None = None) -> bool:
    """删除道具"""
    db = get_connection(db_path)
    try:
        cursor = db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        db.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        db.close()

def list_all(self, db_path: str | Path | None = None) -> list[Item]:
    """列出所有道具"""
    db = get_connection(db_path)
    try:
        rows = db.execute("SELECT * FROM items ORDER BY id").fetchall()
        return [self._row_to_item(dict(r)) for r in rows]
    except Exception:
        return []
    finally:
        db.close()
```

#### 6.4 在 `QuestRepo` 类中添加 delete 和通用 update 方法

```python
def delete(self, quest_id: int, db_path: str | Path | None = None) -> bool:
    """删除任务及其步骤"""
    db = get_connection(db_path)
    try:
        db.execute("DELETE FROM quest_steps WHERE quest_id = ?", (quest_id,))
        cursor = db.execute("DELETE FROM quests WHERE id = ?", (quest_id,))
        db.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        db.close()

def update(self, quest_id: int, db_path: str | Path | None = None, **kwargs) -> Quest | None:
    """通用更新任务"""
    db = get_connection(db_path)
    try:
        quest = self.get_by_id(quest_id, db_path)
        if not quest:
            return None
        sets = []
        values = []
        for key, value in kwargs.items():
            if hasattr(quest, key):
                sets.append(f"{key} = ?")
                values.append(value)
        if not sets:
            return quest
        values.append(quest_id)
        db.execute(f"UPDATE quests SET {', '.join(sets)} WHERE id = ?", values)
        db.commit()
        return self.get_by_id(quest_id, db_path)
    except Exception:
        return None
    finally:
        db.close()
```

---

### 修改 7：创建 Skill 文件

**目标**：创建 `skills/world_building/SKILL.md`，定义 AI 自动构建世界的规则。

**新建文件** `2workbench/skills/world_building/SKILL.md`：

```markdown
---
name: world_building
description: 世界构建技能 - 指导 AI 动态创建和管理游戏世界元素
version: 1.0.0
tags: [world-building, npc, location, item, quest]
allowed-tools: [create_npc, search_npcs, create_location, create_item, create_quest, get_world_state, update_npc_state]
triggers:
  - event_type: player_action
keywords: [创建, 新的, 出现, 发现, 遇到, 前往, 探索]
---

# 世界构建规则

## 何时创建新元素

1. **创建 NPC**：当玩家进入新区域、故事需要新角色、或玩家与未记录的 NPC 交互时
2. **创建地点**：当玩家探索到新区域、或故事推进需要新场景时
3. **创建物品**：当玩家获得新道具、发现宝箱、或 NPC 给予物品时
4. **创建任务**：当故事发展出新的目标、NPC 发布委托、或玩家触发事件时

## 创建原则

### NPC 创建
- 每个 NPC 必须有独特的名字（不能重名）
- 必须指定所在地点
- 性格和说话风格要鲜明
- 背景故事应与世界观一致
- 心情应反映当前情境

### 地点创建
- 描述要包含视觉、听觉、嗅觉等多感官细节
- 必须定义与其他地点的连接关系
- 氛围要符合区域主题（如森林阴暗、城镇热闹）

### 物品创建
- 类型要准确（weapon/armor/consumable/quest 等）
- 描述要包含外观和使用方式
- 稀有度要合理（普通物品不要设为 legendary）

### 任务创建
- 标题要简洁明确
- 描述要说明目标和奖励
- 类型要准确（main=主线, side=支线）

## 注意事项
- 创建前先用 search_npcs 或 get_world_state 检查是否已存在
- 不要过度创建，保持世界元素的精简和有意义
- 创建后通过叙事自然地介绍给玩家，不要生硬地列出
```

---

### 修改 8：`feature/ai/prompt_builder.py` — 增强知识库上下文

**目标**：在 `_format_game_state()` 中注入更详细的知识库信息，让 LLM 了解当前场景的 NPC 和地点详情。

**找到 `_format_game_state(self, state)` 方法**，在现有的 "场景 NPC" 部分之后添加：

```python
# 当前地点详情
current_loc_id = state.get("current_location", 0)
if current_loc_id:
    try:
        from core.models.repository import LocationRepo
        loc_repo = LocationRepo()
        location = loc_repo.get_by_id(current_loc_id, db_path=db_path)
        if location:
            parts.append(f"**当前地点详情**: {location.name}")
            if location.description:
                parts.append(f"  {location.description}")
            if location.connections:
                exits = ", ".join([f"{d}" for d in location.connections.keys()])
                parts.append(f"  可用出口: {exits}")
    except Exception:
        pass

# 当前场景 NPC 详情
active_npcs = state.get("active_npcs", [])
if active_npcs:
    try:
        from core.models.repository import NPCRepo
        npc_repo = NPCRepo()
        for npc_ref in active_npcs[:3]:  # 最多显示 3 个
            npc_id = npc_ref if isinstance(npc_ref, int) else getattr(npc_ref, 'id', 0)
            if npc_id:
                npc = npc_repo.get_by_id(npc_id, db_path=db_path)
                if npc:
                    parts.append(f"**NPC {npc.name}**: 心情={npc.mood}, 说话风格={npc.speech_style or '未知'}")
                    if npc.backstory:
                        parts.append(f"  背景: {npc.backstory[:100]}")
    except Exception:
        pass
```

> **注意**：`_format_game_state` 方法签名中需要确认有 `db_path` 参数可用。如果方法签名中没有 `db_path`，需要从 `self` 或 `state` 中获取。检查方法签名：
> ```python
> def _format_game_state(self, state: AgentState) -> list[str]:
> ```
> 如果没有 `db_path` 参数，改用 `getattr(settings, 'database_path', 'data/game.db')` 获取路径。

---

## 三、修改优先级

| 优先级 | 修改 | 文件 | 说明 |
|--------|------|------|------|
| 🔴 P0 | 修改 0 | `core/models/schema.sql` | 添加 memories 表（前置修复，否则 MemoryRepo 报错） |
| 🔴 P0 | 修改 1 | `feature/ai/tools.py` | 添加 7 个知识库管理工具（核心功能） |
| 🔴 P0 | 修改 2 | `feature/ai/nodes.py` | 接入 SkillLoader |
| 🟠 P1 | 修改 3 | `feature/ai/nodes.py` | 更新 System Prompt |
| 🟠 P1 | 修改 4 | `feature/ai/nodes.py` | 工具执行结果反馈 |
| 🟠 P1 | 修改 5 | `feature/ai/gm_agent.py` | 启用 system_prompt/skills_dir 参数 |
| 🟡 P2 | 修改 6 | `core/models/repository.py` | 补全 delete/update 方法 |
| 🟡 P2 | 修改 7 | 新建 `skills/world_building/SKILL.md` | 世界构建 Skill |
| 🟡 P2 | 修改 8 | `feature/ai/prompt_builder.py` | 增强知识库上下文 |

---

## 四、文件修改清单（Trae 执行顺序）

1. `2workbench/core/models/schema.sql` — 修改（添加 memories 表）
2. `2workbench/feature/ai/tools.py` — 修改（添加导入 + 7 个工具 + 更新 ALL_TOOLS）
3. `2workbench/feature/ai/nodes.py` — 修改（接入 SkillLoader + 更新 System Prompt + 工具结果反馈）
4. `2workbench/feature/ai/gm_agent.py` — 修改（启用参数）
5. `2workbench/core/models/repository.py` — 修改（补全方法）
6. `2workbench/skills/world_building/SKILL.md` — 新建
7. `2workbench/feature/ai/prompt_builder.py` — 修改（增强上下文）

---

## 五、验证方式

修改完成后，运行以下测试验证：

### 测试 1：验证工具注册

```bash
cd Game-Master-Agent
QT_QPA_PLATFORM=offscreen python3.11 -c "
import sys; sys.path.insert(0, '2workbench')
from feature.ai.tools import ALL_TOOLS, get_tools_schema
names = [t.name for t in ALL_TOOLS]
print('所有工具:', names)
print('知识库工具存在:', all(n in names for n in [
    'create_npc', 'search_npcs', 'create_location', 'create_item',
    'create_quest', 'get_world_state', 'update_npc_state'
]))
print('工具总数:', len(names))
"
```

预期输出：
```
所有工具: ['roll_dice', ..., 'create_npc', 'search_npcs', 'create_location', 'create_item', 'create_quest', 'get_world_state', 'update_npc_state']
知识库工具存在: True
工具总数: 16
```

### 测试 2：验证 SkillLoader 接入

```bash
cd Game-Master-Agent
QT_QPA_PLATFORM=offscreen python3.11 -c "
import sys, os; sys.path.insert(0, '2workbench')
from feature.ai.skill_loader import SkillLoader
loader = SkillLoader('2workbench/skills')
skills = loader.discover_all()
print('发现的 Skill:', skills)
if skills:
    relevant = loader.get_relevant_skills('player_action', '创建', ['world_building'])
    print('匹配的 Skill:', [s.metadata.name for s in relevant])
"
```

预期输出：
```
发现的 Skill: ['world_building']
匹配的 Skill: ['world_building']
```

### 测试 3：验证 memories 表

```bash
cd Game-Master-Agent
QT_QPA_PLATFORM=offscreen python3.11 -c "
import sys; sys.path.insert(0, '2workbench')
from foundation.database import init_db, get_connection
init_db('2workbench/core/models/schema.sql', ':memory:')
db = get_connection(':memory:')
tables = [r[0] for r in db.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
print('memories 表存在:', 'memories' in tables)
db.close()
"
```

预期输出：
```
memories 表存在: True
```
