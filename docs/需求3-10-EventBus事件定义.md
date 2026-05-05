# 10 — EventBus 事件定义

> 目标执行者：Trae AI
> 依赖：无
> 产出：无新文件（本文档为参考文档，定义所有 AI 助手相关的 EventBus 事件）

---

## 1. 事件总览

AI 助手功能通过 EventBus 实现跨层通信，遵循项目的四层架构规范：
- **Presentation → Feature**：用户操作事件（由 UI 发出，Service 订阅）
- **Feature → Presentation**：状态更新事件（由 Service 发出，UI 订阅）
- **Feature → Feature**：内部协调事件（由 Executor 发出，Service 订阅）

### 事件命名规范

```
ai_assistant.{domain}.{action}

domain:
  - (无)     : 核心交互（消息、响应、状态）
  - plan     : 计划相关
  - step     : 步骤相关
  - session  : 会话相关

action:
  - user_message      : 用户发送消息
  - response          : AI 响应
  - state_changed     : 状态变更
  - error             : 错误
  - plan_ready        : 计划就绪
  - plan_action       : 计划操作
  - plan_cancelled    : 计划取消
  - step_started      : 步骤开始
  - step_completed    : 步骤完成
  - step_failed       : 步骤失败
  - step_skipped      : 步骤跳过
  - step_rejected     : 步骤拒绝
  - step_action       : 步骤操作
  - execution_finished: 执行完成
  - execution_paused  : 执行暂停
  - next_step_ready   : 下一步就绪
  - session_reset     : 会话重置
  - new_session       : 新建会话
```

---

## 2. 事件详细定义

### 2.1 核心交互事件

#### `ai_assistant.user_message`

| 属性 | 值 |
|------|------|
| 方向 | Presentation → Feature |
| 发送者 | `AIAssistantPanel` |
| 订阅者 | `AIAssistantService._on_user_message` |
| 说明 | 用户在输入框中发送消息 |

**data 结构**：
```python
{
    "message": str,  # 用户输入的文本
}
```

---

#### `ai_assistant.response`

| 属性 | 值 |
|------|------|
| 方向 | Feature → Presentation |
| 发送者 | `AIAssistantService` |
| 订阅者 | `AIAssistantPanel._on_response` |
| 说明 | AI 的文本响应（闲聊/错误/信息） |

**data 结构**：
```python
{
    "content": str,     # 响应文本
    "mode": str,        # "chat" | "error" | "info"
}
```

---

#### `ai_assistant.state_changed`

| 属性 | 值 |
|------|------|
| 方向 | Feature → Presentation |
| 发送者 | `AIAssistantService._set_state` |
| 订阅者 | `AIAssistantPanel._on_state_changed` |
| 说明 | 服务状态变更 |

**data 结构**：
```python
{
    "old_state": str,   # 旧状态值
    "new_state": str,   # 新状态值
}
# 状态值: idle | analyzing | planning | waiting_confirm | executing | chatting
```

---

#### `ai_assistant.error`

| 属性 | 值 |
|------|------|
| 方向 | Feature → Presentation |
| 发送者 | `AIAssistantService._emit_error` |
| 订阅者 | `AIAssistantPanel._on_error` |
| 说明 | 错误通知 |

**data 结构**：
```python
{
    "message": str,  # 错误描述
}
```

---

### 2.2 计划相关事件

#### `ai_assistant.plan_ready`

| 属性 | 值 |
|------|------|
| 方向 | Feature → Presentation |
| 发送者 | `AIAssistantService._handle_plan_and_execute` |
| 订阅者 | `AIAssistantPanel._on_plan_ready` |
| 说明 | 计划生成完成，等待用户确认 |

**data 结构**：
```python
{
    "plan": {                          # ExecutionPlan.to_dict()
        "goal": str,
        "steps": [
            {
                "step_id": int,
                "tool_name": str,
                "description": str,
                "parameters": dict,
                "status": str,
            }
        ],
        "context_summary": str,
    },
    "thinking": str,                   # AI 的规划思路
    "is_modified": bool,               # 是否是修改后的计划（可选）
}
```

---

#### `ai_assistant.plan_action`

| 属性 | 值 |
|------|------|
| 方向 | Presentation → Feature |
| 发送者 | `AIAssistantPanel._on_plan_panel_action` |
| 订阅者 | `AIAssistantService._on_plan_action` |
| 说明 | 用户对计划的操作 |

**data 结构**：
```python
{
    "action": str,     # "confirm" | "confirm_all" | "modify" | "cancel"
    "feedback": str,   # 修改意见（action="modify" 时有值）
}
```

---

#### `ai_assistant.plan_cancelled`

| 属性 | 值 |
|------|------|
| 方向 | Feature → Presentation |
| 发送者 | `AIAssistantService._cancel_plan` |
| 订阅者 | `AIAssistantPanel._on_plan_cancelled` |
| 说明 | 计划被取消 |

**data 结构**：
```python
{}  # 无额外数据
```

---

### 2.3 步骤相关事件

#### `ai_assistant.step_started`

| 属性 | 值 |
|------|------|
| 方向 | Feature(Executor) → Feature(Service) |
| 发送者 | `ToolExecutor.execute_step` |
| 订阅者 | `AIAssistantService`（内部协调） |
| 说明 | 步骤开始执行 |

**data 结构**：
```python
{
    "step_id": int,
    "tool": str,
}
```

---

#### `ai_assistant.step_completed`

| 属性 | 值 |
|------|------|
| 方向 | Feature(Executor) → Feature(Service) |
| 发送者 | `ToolExecutor.execute_step` |
| 订阅者 | `AIAssistantService`（内部协调） |
| 说明 | 步骤执行成功 |

**data 结构**：
```python
{
    "step_id": int,
    "tool": str,
    "message": str,
    "diff": str,         # 文件变更的 diff
    "file_path": str,    # 被修改的文件路径
}
```

---

#### `ai_assistant.step_failed`

| 属性 | 值 |
|------|------|
| 方向 | Feature(Executor) → Feature(Service) |
| 发送者 | `ToolExecutor.execute_step` |
| 订阅者 | `AIAssistantService`（内部协调） |
| 说明 | 步骤执行失败 |

**data 结构**：
```python
{
    "step_id": int,
    "tool": str,
    "error": str,
}
```

---

#### `ai_assistant.step_skipped`

| 属性 | 值 |
|------|------|
| 方向 | Feature(Service) → Presentation |
| 发送者 | `AIAssistantService._skip_step` |
| 订阅者 | `PlanPanel.update_step_status` |
| 说明 | 步骤被跳过 |

**data 结构**：
```python
{
    "step_id": int,
}
```

---

#### `ai_assistant.step_rejected`

| 属性 | 值 |
|------|------|
| 方向 | Feature(Executor) → Feature(Service) |
| 发送者 | `ToolExecutor.reject_step` |
| 订阅者 | `AIAssistantService`（内部协调） |
| 说明 | 用户拒绝步骤变更 |

**data 结构**：
```python
{
    "step_id": int,
}
```

---

#### `ai_assistant.step_action`

| 属性 | 值 |
|------|------|
| 方向 | Presentation → Feature |
| 发送者 | `AIAssistantPanel._on_diff_action` |
| 订阅者 | `AIAssistantService._on_step_action` |
| 说明 | 用户对步骤的操作（确认/跳过/拒绝） |

**data 结构**：
```python
{
    "action": str,     # "confirm" | "skip" | "reject"
    "step_id": int,
}
```

---

### 2.4 执行流程事件

#### `ai_assistant.next_step_ready`

| 属性 | 值 |
|------|------|
| 方向 | Feature → Presentation |
| 发送者 | `AIAssistantService._execute_next_step` |
| 订阅者 | `AIAssistantPanel`（更新 PlanPanel 状态） |
| 说明 | 当前步骤完成，下一步准备执行 |

**data 结构**：
```python
{
    "completed_step_id": int,
    "next_step_id": int,
}
```

---

#### `ai_assistant.execution_finished`

| 属性 | 值 |
|------|------|
| 方向 | Feature → Presentation |
| 发送者 | `AIAssistantService._finish_execution` |
| 订阅者 | `AIAssistantPanel._on_execution_finished` |
| 说明 | 全部步骤执行完成 |

**data 结构**：
```python
{
    "summary": str,       # 执行摘要文本
    "total": int,         # 总步骤数
    "completed": int,     # 成功数
    "failed": int,        # 失败数
    "skipped": int,       # 跳过数
}
```

---

#### `ai_assistant.execution_paused`

| 属性 | 值 |
|------|------|
| 方向 | Feature → Presentation |
| 发送者 | `AIAssistantService._execute_all_steps` |
| 订阅者 | `AIAssistantPanel`（显示暂停信息） |
| 说明 | 一键执行模式下因步骤失败暂停 |

**data 结构**：
```python
{
    "step_id": int,
    "error": str,
    "remaining": int,     # 剩余步骤数
}
```

---

### 2.5 会话相关事件

#### `ai_assistant.session_reset`

| 属性 | 值 |
|------|------|
| 方向 | Feature → Presentation |
| 发送者 | `AIAssistantService.new_session` |
| 订阅者 | `AIAssistantPanel._on_session_reset` |
| 说明 | 会话重置 |

**data 结构**：
```python
{
    "session_id": str,
}
```

---

#### `ai_assistant.new_session`

| 属性 | 值 |
|------|------|
| 方向 | Presentation → Feature |
| 发送者 | `AIAssistantPanel._on_new_chat` |
| 订阅者 | `AIAssistantService.new_session` |
| 说明 | 用户请求新建会话 |

**data 结构**：
```python
{}  # 无额外数据
```

---

## 3. 事件流转图

```
用户输入消息
    │
    ▼
[ai_assistant.user_message] ──── Presentation → Feature
    │
    ▼
AIAssistantService 分析意图
    │
    ├── 闲聊模式 ──→ [ai_assistant.state_changed: chatting]
    │                  [ai_assistant.response] ──── Feature → Presentation
    │
    └── 执行模式 ──→ [ai_assistant.state_changed: planning]
                       │
                       ▼
                   TaskPlanner 生成计划
                       │
                       ▼
                   [ai_assistant.state_changed: waiting_confirm]
                   [ai_assistant.plan_ready] ──── Feature → Presentation
                       │
                       ▼
                   用户操作计划
                       │
                   [ai_assistant.plan_action] ──── Presentation → Feature
                       │
                       ├── confirm ──→ 执行步骤
                       │                 │
                       │                 ▼
                       │             [ai_assistant.step_started]
                       │             ToolExecutor 执行
                       │                 │
                       │             [ai_assistant.step_completed]
                       │                 │
                       │             [ai_assistant.next_step_ready]
                       │                 │
                       │             [ai_assistant.step_action] ──→ 确认下一步
                       │                 │
                       │             ... 循环直到全部完成 ...
                       │                 │
                       │             [ai_assistant.execution_finished]
                       │
                       ├── modify ──→ 重新规划
                       │
                       └── cancel ──→ [ai_assistant.plan_cancelled]
```

---

## 4. 与现有事件的关系

AI 助手事件使用 `ai_assistant.` 前缀，与现有事件命名空间不冲突：

| 现有事件前缀 | 用途 |
|-------------|------|
| `feature.ai.*` | Agent 运行时事件 |
| `ui.*` | UI 操作事件 |
| `project.*` | 项目管理事件 |
| `ai_assistant.*` | AI 助手事件（新增） |

AI 助手订阅了以下现有事件：

| 事件 | 用途 |
|------|------|
| `project.closed` | 项目关闭时清理会话和快照 |
