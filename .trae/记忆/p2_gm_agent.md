# P2-07: GMAgent Agent 门面

> 模块: `feature.ai.gm_agent`
> 文件: `2workbench/feature/ai/gm_agent.py`

---

## 核心类

```python
class GMAgent:
    """
    GM Agent — 游戏主持人 Agent
    
    这是整个 Agent 系统的统一入口。
    上层（Presentation）通过此类与 Agent 交互。
    """
    
    def __init__(
        self,
        world_id: int = 1,
        db_path: str | None = None,
        system_prompt: str | None = None,
        skills_dir: str | None = None,
    )
    
    def set_graph(self, compiled_graph: Any, source: str = "json")
    
    async def run(
        self,
        user_input: str,
        event_type: str = "player_action"
    ) -> dict[str, Any]
    
    def run_sync(
        self,
        user_input: str,
        event_type: str = "player_action"
    ) -> dict[str, Any]
    
    async def stream(
        self,
        user_input: str,
        event_type: str = "player_action"
    ) -> AsyncGenerator[dict, None]
```

---

## 使用示例

```python
from feature.ai.gm_agent import GMAgent

# 创建 Agent 实例
agent = GMAgent(world_id=1)

# 异步运行
result = await agent.run("我要探索幽暗森林")

# 同步运行（阻塞）
result = agent.run_sync("我要探索幽暗森林")

# 流式运行
async for event in agent.stream("我要探索幽暗森林"):
    if event["type"] == "token":
        print(event["content"], end="")
```

---

## 返回结果格式

```python
{
    "status": "success",           # "success" | "error"
    "narrative": "你走进了森林...",  # 叙事文本
    "commands": [...],              # 执行的命令
    "command_results": [...],       # 命令结果
    "turn_count": 5,               # 回合数
    "tokens_used": 150,            # 使用的 token 数
    "latency_ms": 1200,            # 延迟（毫秒）
    "model": "deepseek-chat",      # 使用的模型
    "provider": "deepseek",        # 供应商
}
```

---

## 状态属性

```python
# 执行状态
agent.execution_state  # "idle" | "running" | "error"

# 上次结果
agent.last_result  # dict

# 状态快照
snapshot = agent.get_state_snapshot()
# {
#     "world_id": 1,
#     "turn_count": 5,
#     "execution_state": "idle",
#     "graph_source": "default",
#     "player": {...},
#     "location": {...},
#     "npcs": [...],
# }
```

---

## 动态图设置

```python
from feature.ai.graph_compiler import compile_graph

# 编译自定义图
compiled = compile_graph("path/to/graph.json")

# 设置给 Agent
agent.set_graph(compiled, source="json")
```
