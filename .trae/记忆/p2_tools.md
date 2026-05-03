# P2-04: Tools LangGraph 工具

> 模块: `feature.ai.tools`
> 文件: `2workbench/feature/ai/tools.py`

---

## 9个内置工具

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `roll_dice` | 掷骰子 | sides, count |
| `check_skill` | 技能检定 | skill_name, difficulty |
| `get_npc_info` | 获取 NPC 信息 | npc_id |
| `get_location_info` | 获取地点信息 | location_id |
| `get_quest_info` | 获取任务信息 | quest_id |
| `search_memory` | 搜索记忆 | query, limit |
| `calculate_damage` | 计算伤害 | attacker, defender |
| `generate_loot` | 生成战利品 | enemy_type, level |
| `check_quest_completion` | 检查任务完成 | quest_id |

---

## 工具定义

```python
from langgraph.tools import tool

@tool
def roll_dice(sides: int = 20, count: int = 1) -> dict:
    """
    掷骰子
    
    Args:
        sides: 骰子面数 (默认20)
        count: 骰子数量 (默认1)
    
    Returns:
        {"rolls": [结果列表], "total": 总和}
    """
    import random
    rolls = [random.randint(1, sides) for _ in range(count)]
    return {"rolls": rolls, "total": sum(rolls)}

@tool
def check_skill(skill_name: str, difficulty: int = 15) -> dict:
    """
    技能检定
    
    Args:
        skill_name: 技能名称
        difficulty: 难度等级 (默认15)
    
    Returns:
        {"success": bool, "roll": 骰子结果, "difficulty": 难度}
    """
    roll = roll_dice(sides=20)["total"]
    return {
        "success": roll >= difficulty,
        "roll": roll,
        "difficulty": difficulty
    }
```

---

## 工具注册

```python
from feature.ai.tools import TOOLS

# 所有可用工具列表
print(f"可用工具数: {len(TOOLS)}")

# 获取特定工具
roll_dice_tool = next(t for t in TOOLS if t.name == "roll_dice")
```

---

## 在 StateGraph 中使用

```python
from langgraph.graph import StateGraph
from feature.ai.tools import TOOLS

# 工具节点可以调用这些工具
builder = StateGraph(AgentState)
builder.add_node("tools", ToolNode(TOOLS))
```

---

## 自定义工具

```python
from langgraph.tools import tool

@tool
def my_custom_tool(param: str) -> dict:
    """
    自定义工具描述
    
    Args:
        param: 参数说明
    """
    return {"result": f"处理了 {param}"}

# 添加到工具列表
CUSTOM_TOOLS = TOOLS + [my_custom_tool]
```
