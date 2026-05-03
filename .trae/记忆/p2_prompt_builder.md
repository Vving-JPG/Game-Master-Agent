# P2-03: PromptBuilder Prompt 组装器

> 模块: `feature.ai.prompt_builder`
> 文件: `2workbench/feature/ai/prompt_builder.py`

---

## 核心类

```python
class PromptBuilder:
    def build(
        self,
        state: AgentState,
        template_name: str = "default",
        custom_vars: dict | None = None
    ) -> list[LLMMessage]:
        """
        构建 LLM 对话消息列表
        
        返回: [system_message, user_message, ...]
        """
    
    def add_context(
        self,
        messages: list[LLMMessage],
        context_type: str,
        data: dict
    ) -> list[LLMMessage]:
        """添加上下文信息"""
```

---

## Prompt 模板结构

```python
DEFAULT_TEMPLATE = """你是游戏主持人(GM)，负责引导玩家进行文字冒险游戏。

## 当前游戏状态
- 世界: {world_name}
- 地点: {location_name}
- 回合: {turn_count}

## 玩家信息
{player_info}

## 相关记忆
{memories}

## 当前事件
{event_description}

## 指令
请根据以上信息生成叙事和可能的命令。
输出必须是 JSON 格式:
{
    "narrative": "叙事文本...",
    "commands": [...]
}
"""
```

---

## 使用示例

```python
from feature.ai.prompt_builder import PromptBuilder

builder = PromptBuilder()

# 构建 Prompt
messages = builder.build(
    state=agent_state,
    template_name="combat",  # 使用战斗模板
    custom_vars={
        "enemy_name": "哥布林",
        "enemy_hp": 50
    }
)

# messages 可以直接传给 LLM
response = await llm_client.chat_async(messages)
```

---

## 模板变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `world_name` | 世界名称 | "幻想大陆" |
| `location_name` | 当前地点 | "幽暗森林" |
| `turn_count` | 回合数 | 5 |
| `player_info` | 玩家信息 | 格式化后的属性 |
| `memories` | 相关记忆 | 最近5条记忆 |
| `event_description` | 事件描述 | 玩家输入 |
| `active_npcs` | 在场 NPC | NPC 列表 |
| `active_quests` | 进行中的任务 | 任务列表 |

---

## 内置模板

- `default` - 默认叙事模板
- `combat` - 战斗场景模板
- `dialogue` - 对话场景模板
- `exploration` - 探索场景模板
