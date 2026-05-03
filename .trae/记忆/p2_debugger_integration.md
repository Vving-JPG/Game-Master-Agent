# P2: 调试面板与运行体验打通

> **阶段**: P2 - 调试面板 | **状态**: ✅ 已完成 | **日期**: 2026-05-03

---

## 概述

将调试面板（RuntimePanel）与 MainWindow 中的 GMAgent 运行逻辑连接，使调试面板能真正控制 Agent 运行。

---

## 修改文件

### 2workbench/presentation/main_window.py

#### 调试面板事件连接
```python
def _setup_eventbus(self) -> None:
    """设置 EventBus 订阅"""
    event_bus.subscribe("feature.ai.turn_start", self._on_turn_start)
    event_bus.subscribe("feature.ai.turn_end", self._on_turn_end)
    event_bus.subscribe("feature.ai.agent_error", self._on_agent_error)
    event_bus.subscribe("feature.ai.llm_stream_token", self._on_stream_token)
    # 调试面板事件
    self._setup_debugger_connections()

def _setup_debugger_connections(self) -> None:
    """连接调试面板到 Agent"""
    event_bus.subscribe("ui.debugger.run", self._on_debugger_run)
    event_bus.subscribe("ui.debugger.stop", self._on_debugger_stop)
    event_bus.subscribe("ui.debugger.input", self._on_debugger_input)
    event_bus.subscribe("ui.debugger.request_state", self._on_request_state)
```

#### 运行控制
```python
def _on_debugger_run(self, event: Event) -> None:
    """调试面板触发运行"""
    self._on_run_agent()

def _on_debugger_stop(self, event: Event) -> None:
    """调试面板触发停止"""
    self._on_stop_agent()
```

#### 输入处理
```python
def _on_debugger_input(self, event: Event) -> None:
    """调试面板发送用户输入"""
    text = event.get("text", "")
    if not text:
        return
    if hasattr(self, '_current_agent') and self._current_agent:
        event_bus.emit("feature.ai.user_input", {"text": text})
```

#### 状态请求响应
```python
def _on_request_state(self, event: Event) -> None:
    """响应调试面板的状态请求"""
    if not hasattr(self, '_current_agent') or not self._current_agent:
        return
    try:
        snapshot = self._current_agent.get_state_snapshot()
        event_bus.emit("ui.debugger.state_update", {"state": snapshot})
    except Exception as e:
        logger.error(f"获取 Agent 状态失败: {e}")
```

---

## 调试面板事件流

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  RuntimePanel   │────▶│   EventBus       │────▶│   MainWindow    │
│                 │     │                  │     │                 │
│ _on_run()       │     │ ui.debugger.run  │     │ _on_debugger_run│
│ _on_stop()      │     │ ui.debugger.stop │     │ _on_debugger_stop│
│ _on_send_input()│     │ ui.debugger.input│     │ _on_debugger_input│
│ refresh()       │     │ ui.debugger.request_state │ _on_request_state│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                              │
                                                              ▼
                                                       ┌─────────────┐
                                                       │   GMAgent   │
                                                       │             │
                                                       │ run()       │
                                                       │ stop()      │
                                                       │ get_state() │
                                                       └─────────────┘
```

---

## 关键 EventBus 事件

| 事件名 | 方向 | 数据 | 说明 |
|--------|------|------|------|
| `ui.debugger.run` | Panel → MainWindow | `{model: str}` | 启动 Agent |
| `ui.debugger.stop` | Panel → MainWindow | `{}` | 停止 Agent |
| `ui.debugger.input` | Panel → MainWindow | `{text: str}` | 用户输入 |
| `ui.debugger.request_state` | Panel → MainWindow | `{}` | 请求状态 |
| `ui.debugger.state_update` | MainWindow → Panel | `{state: dict}` | 状态更新 |
| `feature.ai.turn_start` | GMAgent → Panel | `{turn: int}` | 回合开始 |
| `feature.ai.turn_end` | GMAgent → Panel | `{turn: int, duration_ms: int, tokens: int}` | 回合结束 |
| `feature.ai.llm_stream_token` | GMAgent → Panel | `{token: str}` | 流式输出 |

---

## 验证清单

- [x] 调试面板点击"运行" → Agent 开始执行
- [x] 调试面板点击"停止" → Agent 停止
- [x] 调试面板输入框发送文本 → Agent 接收并处理
- [x] 变量监视器显示 AgentState 中的实时数据

---

## 触发关键词

debugger_integration, runtime_panel, _on_debugger_run, _on_debugger_stop, _on_debugger_input, _on_request_state, ui.debugger.run, ui.debugger.stop
