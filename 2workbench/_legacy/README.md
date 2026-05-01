# _legacy/ 目录说明

> ⚠️ **此目录包含旧代码，仅供重构参考使用**

## 目录内容

这是 Game Master Agent V2 重构前的旧代码，在 P0 ~ P5 重构期间保留供参考。

### 原目录结构

```
_legacy/
├── bridge/           # AgentBridge - PyQt6 Signal 桥接
├── core/             # 核心服务（配置、数据库、LLM、缓存等）
│   ├── data/         # NPC模板、故事模板、种子数据
│   ├── models/       # 数据模型、Repository、schema.sql
│   ├── prompts/      # Prompt 模板
│   ├── services/     # 业务服务（战斗、对话、LLM客户端等）
│   └── utils/        # 工具函数
├── scripts/          # 健康检查、Token审计脚本
├── styles/           # QSS 样式文件
├── widgets/          # PyQt6 UI 组件
├── app.py            # 应用入口
├── main_window.py    # 主窗口
├── server.py         # HTTP/WebSocket 服务器
└── __main__.py       # 模块入口
```

## 重构计划

| Phase | 新目录 | 对应旧代码 | 说明 |
|-------|--------|-----------|------|
| P0 | `foundation/` | `core/config.py`, `core/utils/logger.py`, `core/services/database.py`, `core/services/llm_client.py` 等 | Foundation 层基础设施 |
| P1 | `core/` | `core/models/`, `core/data/` | 纯数据 + 纯规则 |
| P2 | `feature/battle/`, `feature/dialogue/` 等 | `core/services/combat.py`, `core/services/npc_dialog.py` 等 | 业务功能 |
| P3 | `feature/ai/` | `bridge/agent_bridge.py` | LangGraph AI 编排 |
| P4/P5 | `presentation/` | `widgets/`, `main_window.py`, `styles/` | UI 系统 |

## 使用方式

重构新代码时，可以参考旧实现：

1. **复制逻辑**：将旧代码的业务逻辑复制到新架构中
2. **改进设计**：按四层架构规范重新组织
3. **更新接口**：使用新的 EventBus、基类等基础设施

## 清理计划

当 P0 ~ P5 全部完成后，此目录将被删除。

---
*最后更新: 2026-05-01*
