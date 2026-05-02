# P5: Presentation 层 — IDE 运营工具集

> 本文件记录 P5 阶段 Presentation 层运营工具集的实现细节。
> **前置条件**: P0 Foundation + P1 Core + P2 LangGraph Agent + P3 Feature Services + P4 GUI Editor 已完成。
> **创建日期**: 2026-05-02

---

## 1. 概述

### 1.1 目标
实现 Presentation 层的运营工具集，包括 7 个高级功能模块：
1. 运行时调试器 — Agent 运行控制、状态检查、变量监视
2. 评估工作台 — Prompt 评估、批量测试、指标统计
3. 知识库编辑器 — 世界观数据可视化管理
4. 安全护栏面板 — 内容过滤规则配置
5. 多 Agent 编排 — Agent 链配置、并行/串行编排
6. 日志追踪 — 运行日志查看、EventBus 事件追踪
7. 部署管理 — Agent 导出为服务、配置打包

### 1.2 技术栈
- **UI 框架**: PyQt6
- **架构**: 四层架构 (Foundation/Core/Feature/Presentation)
- **事件驱动**: EventBus
- **异步**: qasync (预留)

---

## 2. 模块结构

```
presentation/ops/
├── __init__.py                      # 统一导出所有运营工具
├── debugger/                        # 运行时调试器
│   ├── runtime_panel.py             # 主面板（控制台+变量监视+性能指标）
│   └── event_monitor.py             # EventBus 事件监视器
├── evaluator/                       # 评估工作台
│   └── eval_workbench.py            # Prompt 评估、批量测试、对比分析
├── knowledge/                       # 知识库编辑器
│   └── knowledge_editor.py          # NPC/地点/物品/任务编辑器
├── safety/                          # 安全护栏
│   └── safety_panel.py              # 过滤规则、安全级别、预览测试
├── multi_agent/                     # 多 Agent 编排
│   └── orchestrator.py              # Agent 实例、链式拓扑
├── logger_panel/                    # 日志追踪
│   └── log_viewer.py                # 日志查看、级别过滤
└── deploy/                          # 部署管理
    └── deploy_manager.py            # 打包配置、运行监控
```

---

## 3. 核心组件详解

### 3.1 运行时调试器 (debugger/)

#### RuntimePanel — 主面板
```python
class RuntimePanel(BaseWidget):
    """运行时调试器 — 主面板"""
    
    # 组件
    - _console: ConsoleOutput          # 控制台输出
    - _var_watcher: VariableWatcher    # 变量监视器
    - _perf_metrics: PerformanceMetrics # 性能指标
    
    # 运行控制
    - _on_run(): 启动 Agent
    - _on_pause(): 暂停 Agent
    - _on_stop(): 停止 Agent
    - _on_step(): 单步执行
    - _on_send_input(): 发送用户输入
```

#### ConsoleOutput — 控制台输出
```python
class ConsoleOutput(QWidget):
    """控制台输出组件"""
    
    # 消息类型
    - append_system(text): 系统消息（灰色）
    - append_user(text): 用户输入（白色）
    - append_assistant(text): Agent 回复（青色）
    - append_error(text): 错误消息（红色）
    - append_command(cmd, result): 命令执行（黄色）
    - append_stream_token(token): 流式 Token
```

#### VariableWatcher — 变量监视器
```python
class VariableWatcher(QWidget):
    """变量监视器 — AgentState 实时查看"""
    
    # 表格列
    - 变量名 | 类型 | 值
    
    # 方法
    - update_state(state: dict): 更新状态显示
    - refresh(): 刷新状态（通过 EventBus 请求）
```

#### PerformanceMetrics — 性能指标
```python
class PerformanceMetrics(QWidget):
    """性能指标面板"""
    
    # 指标项
    - 🔄 总轮次
    - 📊 总 Token
    - 💰 总费用
    - ⏱ 平均响应时间
    - ❌ 错误数
```

#### EventMonitor — 事件监视器
```python
class EventMonitor(BaseWidget):
    """EventBus 事件监视器"""
    
    # 功能
    - 实时捕获所有 EventBus 事件
    - 事件类型过滤
    - 暂停/继续
    - 自动限制行数（2000行）
    
    # 事件着色
    - error: 红色 (#f44747)
    - stream: 青色 (#4ec9b0)
    - turn: 蓝色 (#569cd6)
    - command: 黄色 (#dcdcaa)
```

---

### 3.2 评估工作台 (evaluator/)

#### EvalWorkbench — 评估工作台
```python
class EvalWorkbench(BaseWidget):
    """评估工作台 — Prompt 评估、批量测试、指标统计"""
    
    # 组件
    - _case_editor: EvalCaseEditor     # 用例编辑器
    - _result_table: QTableWidget      # 结果表格
    
    # 数据类
    - EvalCase: 评估用例
    - EvalResult: 评估结果
```

#### EvalCase — 评估用例
```python
@dataclass
class EvalCase:
    id: str
    input_text: str           # 输入
    expected_output: str      # 期望输出
    actual_output: str        # 实际输出
    model: str
    latency_ms: float
    tokens_used: int
    score: float              # 0-10 评分
    notes: str
```

#### EvalResult — 评估结果
```python
@dataclass
class EvalResult:
    model: str
    total_cases: int
    avg_score: float
    avg_latency_ms: float
    total_tokens: int
    pass_rate: float          # score >= 6 的比例
    cases: list[EvalCase]
```

---

### 3.3 知识库编辑器 (knowledge/)

#### KnowledgeEditor — 知识库编辑器
```python
class KnowledgeEditor(BaseWidget):
    """知识库编辑器 — 主面板"""
    
    # 标签页
    - _npc_editor: NPCEditor            # NPC 编辑器
    - _loc_editor: LocationEditor       # 地点编辑器
    - _item_placeholder: QLabel         # 物品编辑器（占位）
    - _quest_placeholder: QLabel        # 任务编辑器（占位）
    
    # 导入/导出
    - _import_data(): JSON 导入
    - _export_data(): JSON 导出
```

#### NPCEditor — NPC 编辑器
```python
class NPCEditor(QWidget):
    """NPC 编辑器"""
    
    # 左侧面板
    - NPC 列表表格（名称、位置、心情）
    - 添加 NPC 按钮
    
    # 右侧面板
    - 基本信息: 名称、心情、说话风格、背景、目标
    - 性格参数（大五人格 0.0-1.0）:
      - 开放性 (openness)
      - 尽责性 (conscientiousness)
      - 外向性 (extraversion)
      - 宜人性 (agreeableness)
      - 神经质 (neuroticism)
```

#### LocationEditor — 地点编辑器
```python
class LocationEditor(QWidget):
    """地点编辑器"""
    
    # 左侧面板
    - 地点列表表格（名称、描述）
    - 添加地点按钮
    
    # 右侧面板
    - 名称、描述
    - 出口连接: north:1, south:2, east:3
```

---

### 3.4 安全护栏面板 (safety/)

#### SafetyPanel — 安全护栏面板
```python
class SafetyPanel(BaseWidget):
    """安全护栏面板 — 内容过滤规则配置"""
    
    # 安全级别
    - STRICT: 严格（所有规则启用）
    - STANDARD: 标准（大部分规则启用）
    - RELAXED: 宽松（仅关键规则启用）
    
    # 组件
    - _rule_list: QListWidget           # 规则列表
    - _level_combo: QComboBox           # 安全级别选择
    
    # 默认规则
    - 暴力内容: (杀|砍|斩|刺|血腥)
    - 色情内容: (裸|性|色情)
    - 政治敏感: (政治|敏感|领导人)
```

#### FilterRule — 过滤规则
```python
@dataclass
class FilterRule:
    id: str
    name: str
    pattern: str              # 正则表达式
    category: str             # violence/sexual/political/custom
    level: str                # strict/standard/relaxed
    enabled: bool
    replacement: str = "***"  # 替换文本
```

---

### 3.5 多 Agent 编排 (multi_agent/)

#### MultiAgentOrchestrator — 多 Agent 编排器
```python
class MultiAgentOrchestrator(BaseWidget):
    """多 Agent 编排器 — Agent 链配置和消息路由"""
    
    # 数据
    - _agents: list[AgentInstance]      # Agent 实例列表
    - _chain: list[ChainStep]           # 编排链
    
    # 布局
    - 左侧: Agent 列表
    - 中央: Agent 配置（名称、角色、模型、System Prompt）
    - 右侧: 编排链拓扑
```

#### AgentInstance — Agent 实例
```python
@dataclass
class AgentInstance:
    id: str
    name: str
    role: str                 # gm/narrator/combat/dialogue/custom
    model: str
    system_prompt: str
    enabled: bool
```

#### ChainStep — 链式步骤
```python
@dataclass
class ChainStep:
    agent_id: str
    step_type: str            # sequential/parallel/conditional
    condition: str            # 条件表达式
    next_agent_id: str
```

---

### 3.6 日志追踪 (logger_panel/)

#### LogViewer — 日志查看器
```python
class LogViewer(BaseWidget):
    """日志追踪查看器"""
    
    # 功能
    - 打开日志文件
    - 级别过滤（DEBUG/INFO/WARNING/ERROR）
    - 自动滚动
    - 实时追加日志
    
    # 日志着色
    - DEBUG: 灰色 (#858585)
    - INFO: 白色 (#cccccc)
    - WARNING: 黄色 (#dcdcaa)
    - ERROR: 红色 (#f44747)
```

---

### 3.7 部署管理 (deploy/)

#### DeployManager — 部署管理器
```python
class DeployManager(BaseWidget):
    """部署管理器 — Agent 导出为服务"""
    
    # 状态
    - idle: 就绪
    - packaging: 打包中
    - deploying: 部署中
    - running: 运行中
    - error: 错误
    
    # 标签页
    - 📦 打包: 服务名称、版本、框架、端口、主机
    - 📊 监控: 状态、运行时间、请求数、错误数
```

---

## 4. 主窗口集成

### 4.1 Tools 菜单
```python
# presentation/main_window.py
tools_menu.addAction("🔧 运行时调试器", lambda: self._show_ops_panel("debugger"))
tools_menu.addAction("📊 评估工作台", lambda: self._show_ops_panel("evaluator"))
tools_menu.addAction("📖 知识库编辑器", lambda: self._show_ops_panel("knowledge"))
tools_menu.addAction("🔒 安全护栏", lambda: self._show_ops_panel("safety"))
tools_menu.addAction("🤖 多 Agent 编排", lambda: self._show_ops_panel("multi_agent"))
tools_menu.addAction("📋 日志追踪", lambda: self._show_ops_panel("logger"))
tools_menu.addAction("🚀 部署管理", lambda: self._show_ops_panel("deploy"))
```

### 4.2 面板映射
```python
panel_map = {
    "debugger": ("🔧 调试器", RuntimePanel),
    "evaluator": ("📊 评估", EvalWorkbench),
    "knowledge": ("📖 知识库", KnowledgeEditor),
    "safety": ("🔒 安全", SafetyPanel),
    "multi_agent": ("🤖 编排", MultiAgentOrchestrator),
    "logger": ("📋 日志", LogViewer),
    "deploy": ("🚀 部署", DeployManager),
}
```

---

## 5. 使用示例

### 5.1 打开运行时调试器
```python
from presentation.main_window import MainWindow

window = MainWindow()
window._show_ops_panel("debugger")  # 通过 Tools 菜单或代码调用
```

### 5.2 使用安全护栏过滤文本
```python
from presentation.ops.safety import SafetyPanel

panel = SafetyPanel()
filtered = panel.filter_text("包含暴力内容的文本")
# 输出: "包含***内容的文本"
```

### 5.3 评估 Prompt
```python
from presentation.ops.evaluator import EvalWorkbench, EvalCase

bench = EvalWorkbench()
bench._case_editor._cases = [
    EvalCase(id="c1", input_text="你好", expected_output="你好！"),
]
bench._run_eval()
```

---

## 6. 注意事项

### 6.1 异步操作
- LLM 调用和评估运行应使用 `qasync`，不阻塞 UI
- 评估工作台的 `_run_eval` 方法当前为同步模拟，后续应改为异步
- 部署管理的服务启动/停止应使用子进程

### 6.2 数据安全
- 安全护栏的过滤规则应存储在项目配置中
- 敏感词列表支持导入/导出，不应硬编码
- 过滤操作应在 Feature 层执行，Presentation 层仅负责配置

### 6.3 多 Agent 编排
- 当前为可视化配置面板，实际编排逻辑在 Feature 层实现
- Agent 实例配置应序列化为 JSON 存储在项目中
- 链式拓扑支持串行、并行和条件分支三种模式

---

## 7. 依赖关系

```
ops/
├── debugger/
│   ├── foundation.event_bus
│   ├── foundation.logger
│   └── presentation.widgets
├── evaluator/
│   ├── foundation.llm
│   └── presentation.widgets
├── knowledge/
│   └── presentation.widgets
├── safety/
│   └── presentation.widgets
├── multi_agent/
│   └── presentation.widgets
├── logger_panel/
│   └── presentation.widgets
└── deploy/
    ├── presentation.project.manager
    └── presentation.widgets
```

---

## 8. 后续扩展

- [ ] 评估工作台接入真实 LLM 调用（qasync）
- [ ] 知识库编辑器完成物品和任务编辑器
- [ ] 多 Agent 编排接入 Feature 层实际编排逻辑
- [ ] 部署管理实现真实的服务打包和启动
- [ ] 添加更多运营工具（性能分析器、Prompt 版本管理等）

---

*最后更新: 2026-05-02*
*阶段: P5 Presentation 层 IDE 运营工具集 ✅ 已完成*
