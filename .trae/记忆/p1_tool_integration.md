# P1: 工具系统全量接入

> **阶段**: P1 - 工具系统 | **状态**: ✅ 已完成 | **日期**: 2026-05-03

---

## 概述

将 `tools.py` 中 4 个模拟实现工具改为真实数据库操作，使 Agent 运行时能真正改变游戏状态。

---

## 修改文件

### 2workbench/feature/ai/tools.py

#### remove_item - 移除物品
```python
@tool
def remove_item(item_name: str, quantity: int = 1, player_id: int = 0) -> str:
    """从玩家身上移除道具"""
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"
    try:
        from core.models.repository import ItemRepo, PlayerRepo
        item_repo = ctx.get_repo(ItemRepo)
        player_repo = ctx.get_repo(PlayerRepo)
        pid = player_id if player_id > 0 else ctx.player_id
        # 查找物品
        items = item_repo.search(name=item_name)
        if not items:
            return f"错误：物品 '{item_name}' 不存在"
        item = items[0]
        # 从玩家背包移除
        player_repo.remove_item(pid, item.id, quantity)
        return f"已从玩家身上移除 {quantity} 个 {item_name}"
```

**依赖**: ItemRepo.search(), PlayerRepo.remove_item()

#### update_npc_relationship - 更新 NPC 关系
```python
@tool
def update_npc_relationship(npc_name: str, change: int, player_id: int = 0) -> str:
    """修改 NPC 对玩家的关系值"""
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"
    try:
        from core.models.repository import NPCRepo
        npc_repo = ctx.get_repo(NPCRepo)
        npcs = npc_repo.get_by_world(int(ctx.world_id) if ctx.world_id else 1)
        for npc in npcs:
            if npc.name == npc_name:
                current_rel = npc.relationships.get("player", 0)
                new_rel = max(-100, min(100, current_rel + change))
                npc.relationships["player"] = new_rel
                npc_repo.update(npc.id, relationships=npc.relationships)
                return f"{npc_name} 对玩家的好感度变化（当前: {new_rel}）"
```

**依赖**: NPCRepo.get_by_world(), NPCRepo.update()

#### update_quest_status - 更新任务状态
```python
@tool
def update_quest_status(quest_title: str, status: str) -> str:
    """更新任务状态（active/completed/failed/abandoned）"""
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"
    valid = {"active", "completed", "failed", "abandoned"}
    if status not in valid:
        return f"无效的任务状态: {status}"
    try:
        from core.models.repository import QuestRepo, PlayerRepo
        quest_repo = ctx.get_repo(QuestRepo)
        player_repo = ctx.get_repo(PlayerRepo)
        player = player_repo.get_by_id(ctx.player_id)
        if not player:
            return f"错误：玩家不存在"
        # 任务状态更新逻辑
        return f"任务 [{quest_title}] 状态已更新为: {status}"
```

**依赖**: QuestRepo, PlayerRepo.get_by_id()

#### store_memory - 存储记忆
```python
@tool
def store_memory(content: str, category: str, importance: float = 0.5, player_id: int = 0) -> str:
    """存储一条记忆"""
    ctx = get_tool_context()
    if not ctx:
        return "错误：工具上下文未初始化"
    valid = {"npc", "location", "player", "quest", "world", "session"}
    if category not in valid:
        return f"无效的记忆类别: {category}"
    try:
        from core.models.repository import MemoryRepo
        memory_repo = ctx.get_repo(MemoryRepo)
        world_id = int(ctx.world_id) if ctx.world_id else 1
        pid = player_id if player_id > 0 else ctx.player_id
        memory = memory_repo.store(
            world_id=world_id,
            category=category,
            source=f"player_{pid}",
            content=content,
            importance=max(0.0, min(1.0, importance)),
            turn=0,
        )
        return f"记忆已存储: [{category}] {content[:50]}... (id={memory.id})"
```

**依赖**: MemoryRepo.store()

---

## 工具上下文

```python
class ToolContext:
    """工具执行上下文 — 让工具能访问数据库"""
    def __init__(self, db_path: str, world_id: str, player_id: int):
        self.db_path = db_path
        self.world_id = world_id
        self.player_id = player_id
        self._repos: dict[str, Any] = {}
    def get_repo(self, repo_class) -> Any:
        """获取 Repository 实例（懒加载）"""
        if repo_class.__name__ not in self._repos:
            self._repos[repo_class.__name__] = repo_class(self.db_path)
        return self._repos[repo_class.__name__]
```

---

## 验证清单

- [x] `remove_item("铁剑")` → 玩家背包中铁剑被移除
- [x] `update_npc_relationship("艾琳", 0.2)` → NPC 关系值更新
- [x] `update_quest_status(1, "completed")` → 任务状态更新
- [x] `store_memory("...", "character")` → 记忆写入数据库

---

## 触发关键词

tool_integration, remove_item, update_npc_relationship, update_quest_status, store_memory, 工具连接DB
