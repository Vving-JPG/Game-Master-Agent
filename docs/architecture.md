# 架构设计

## 整体架构

```
玩家 → MUD前端/WebSocket → FastAPI → GameMaster → DeepSeek API
                           ↓
                      工具执行器 → 数据库(SQLite)
                           ↓
                      管理端 → Vue3/NaiveUI
```

## 核心模块

- **GameMaster** (`src/agent/game_master.py`): 核心循环，while循环 + 工具调用
- **LLMClient** (`src/services/llm_client.py`): DeepSeek API 封装
- **ToolExecutor** (`src/tools/executor.py`): 工具注册和执行
- **ContextManager** (`src/services/context_manager.py`): 对话历史管理

## 数据流

1. 玩家输入 → WebSocket → GameMaster.process()
2. 构建 System Prompt + 对话历史
3. 调用 DeepSeek API（带工具定义）
4. 如果返回工具调用 → 执行工具 → 结果加入历史 → 继续调用
5. 如果返回文本 → 流式输出给玩家
