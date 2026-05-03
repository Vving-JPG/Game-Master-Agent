# P2-02: CommandParser 命令解析器

> 模块: `feature.ai.command_parser`
> 文件: `2workbench/feature/ai/command_parser.py`

---

## 4级容错策略

1. **直接 JSON 解析** - 标准格式
2. **提取代码块** - 提取 ```json ... ``` 内容
3. **提取大括号** - 提取最外层 `{ ... }`
4. **兜底处理** - 整个文本作为 narrative

---

## 核心类

```python
class CommandParser:
    def parse(self, llm_output: str) -> ParseResult:
        """
        解析 LLM 输出
        
        返回: {
            "narrative": str,      # 叙事文本
            "commands": list,      # 命令列表
            "raw": str,            # 原始输出
            "parse_method": str,   # 解析方法
        }
        """
    
    def parse_with_recovery(self, llm_output: str) -> ParseResult:
        """带恢复的解析（尝试多种策略）"""
```

---

## 命令格式

```json
{
    "narrative": "你走进了幽暗森林，树木高耸入云...",
    "commands": [
        {
            "type": "spawn_npc",
            "params": {
                "npc_id": "forest_guardian",
                "location": "dark_forest"
            }
        },
        {
            "type": "update_quest",
            "params": {
                "quest_id": "main_001",
                "status": "active"
            }
        }
    ]
}
```

---

## 使用示例

```python
from feature.ai.command_parser import CommandParser

parser = CommandParser()

# 解析 LLM 输出
result = parser.parse(llm_output)
print(f"叙事: {result['narrative']}")
print(f"命令数: {len(result['commands'])}")

# 遍历命令
for cmd in result['commands']:
    print(f"命令类型: {cmd['type']}")
    print(f"参数: {cmd['params']}")
```

---

## 支持的命令类型

| 命令类型 | 说明 | 参数 |
|---------|------|------|
| `spawn_npc` | 生成 NPC | npc_id, location |
| `move_player` | 移动玩家 | location_id |
| `update_quest` | 更新任务 | quest_id, status |
| `add_item` | 添加物品 | item_id, quantity |
| `remove_item` | 移除物品 | item_id, quantity |
| `start_combat` | 开始战斗 | enemy_ids |
| `update_npc_mood` | 更新 NPC 心情 | npc_id, mood |
| `store_memory` | 存储记忆 | content, category |
