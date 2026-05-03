# P0-05: LLM Client 多模型抽象

> 模块: `foundation.llm`
> 文件: `2workbench/foundation/llm/base.py`, `openai_client.py`

---

## 数据类

```python
@dataclass
class LLMMessage:
    role: str      # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None  # tool 调用时使用

@dataclass
class LLMResponse:
    content: str
    tokens: int
    model: str
    provider: str
    latency_ms: int
    tool_calls: list[dict] | None = None

@dataclass
class StreamEvent:
    type: str      # "token" | "tool_call" | "complete" | "error"
    content: str | None = None
    data: dict | None = None
```

---

## OpenAI 兼容客户端

```python
from foundation.llm import OpenAICompatibleClient

client = OpenAICompatibleClient(
    provider_name="deepseek",
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
    model="deepseek-chat",
)

# 异步对话
response = await client.chat_async(messages)
print(response.content)

# 流式对话
async for event in client.stream(messages):
    if event.type == "token":
        print(event.content, end="")
```

---

## ModelRouter 模型路由

> 文件: `2workbench/foundation/llm/model_router.py`
> 全局单例: `model_router`

```python
from foundation.llm import model_router

# 自动路由（根据内容选择模型）
client, config = model_router.route(content="战斗开始！")

# 显式指定
client, config = model_router.route(provider="openai", model="gpt-4o")
```

### 默认路由规则

| 规则名 | 触发条件 | 目标模型 |
|--------|----------|----------|
| critical_narrative | 关键词: 战斗/boss/决战/死亡/结局... | deepseek-reasoner |
| npc_deep_dialogue | 关键词: 关系/信任/背叛/秘密... | deepseek-reasoner |
| standard_narrative | 默认 | deepseek-chat |

---

## 路由策略

1. 显式指定 → 跳过路由
2. 规则匹配 → 关键词+事件类型+对话长度评分
3. 默认回退 → `settings.default_provider`
