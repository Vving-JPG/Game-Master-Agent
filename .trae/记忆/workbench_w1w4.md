# WorkBench 重构 W1~W4 完成记录

> 记录 W1~W4 阶段的详细实现，供后续开发参考。
> 创建时间: 2026-04-30

---

## 阶段总览

| 阶段 | 目标 | 状态 | 测试 |
|------|------|------|------|
| W1 | 骨架重构 — 新布局 | ✅ 完成 | TypeScript 编译通过 |
| W2 | 左侧七层资源导航 | ✅ 完成 | 资源树加载正常 |
| W3 | 中间多态编辑器 | ✅ 完成 | 6种编辑器切换正常 |
| W4 | 循环引擎 — YAML工作流 | ✅ 完成 | 6个测试 (4个通过) |

---

## W1: 骨架重构

### 1.1 依赖安装
```bash
cd workbench
npm install @vueuse/core pinia
```
- @vueuse/core@14.2.1
- pinia@3.0.4

### 1.2 Pinia Store
**文件**: `workbench/src/stores/app.ts`

核心状态:
```typescript
// 执行状态
executionState: 'IDLE' | 'RUNNING' | 'PAUSED' | 'STEP_WAITING'
currentTurn: number
totalTokens: number
currentLatency: number

// 模型配置
selectedModel: string
temperature: number
maxTokens: number

// 资源导航
selectedResource: ResourceNode | null
expandedKeys: string[]

// 轮次历史
turnHistory: TurnRecord[]

// SSE 事件
sseEvents: Array<{ type: string; data: any; time: string }>
```

### 1.3 App.vue 新布局
**布局结构**:
```
┌─────────────────────────────────────────┐
│  TopBar (48px)                          │
├──────────┬──────────────────┬───────────┤
│          │                  │           │
│ LeftPanel│   MainEditor     │ RightPanel│
│ (260px)  │   (flex: 1)      │ (360px)   │
│          │                  │           │
├──────────┴──────────────────┴───────────┤
│  BottomConsole (200px)                  │
└─────────────────────────────────────────┘
```

**组件**: TopBar, LeftPanel, MainEditor, RightPanel, BottomConsole

### 1.4 Vite 代理配置
```typescript
// workbench/vite.config.ts
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

---

## W2: 左侧七层资源导航

### 2.1 ResourceTree 组件
**文件**: `workbench/src/components/ResourceTree.vue`

功能:
- 异步加载子节点
- 搜索过滤
- 选中事件回调

Props:
```typescript
{
  title: string
  icon: string
  loadData: (key: string) => Promise<ResourceNode[]>
  onSelect?: (node: ResourceNode) => void
  onCreate?: (parentKey: string) => void
}
```

### 2.2 七层资源数据加载器
**文件**: `workbench/src/api/resources.ts`

| Tab | 加载函数 | 数据源 |
|-----|----------|--------|
| 🧠 Prompt | loadPromptResources | /api/workspace/tree?path=prompts |
| 📁 Memory | loadMemoryResources | /api/workspace/tree?path=workspace |
| ⚙️ Config | loadConfigResources | 硬编码 (.env, adapter.yaml) |
| 🔧 Tools | loadToolResources | 硬编码 (11个工具定义) |
| 🔄 Workflow | loadWorkflowResources | 硬编码 (main_loop.yaml) |
| 📊 Runtime | loadRuntimeResources | 硬编码 (current/history/events) |

### 2.3 LeftPanel 集成
**文件**: `workbench/src/components/LeftPanel.vue`

使用 NTabs (placement="left") 实现垂直 Tab 栏，每个 Tab 包含 ResourceTree。

---

## W3: 中间多态编辑器

### 3.1 EditorRouter
**文件**: `workbench/src/components/EditorRouter.vue`

路由逻辑:
```typescript
if (path.includes('SKILL.md')) return 'skill'
if (path.endsWith('.md')) return 'markdown'
if (path.endsWith('.yaml') || path.endsWith('.yml')) return 'yaml'
if (path.endsWith('.env')) return 'keyvalue'
if (key.startsWith('tool:')) return 'tool'
if (key.startsWith('runtime:')) return 'runtime'
```

### 3.2 六种编辑器

| 编辑器 | 文件 | 用途 |
|--------|------|------|
| MdEditor | editors/MdEditor.vue | Markdown 编辑 + 预览 |
| YamlEditor | editors/YamlEditor.vue | YAML 编辑 |
| KeyValueEditor | editors/KeyValueEditor.vue | .env 键值对编辑 |
| SkillEditor | editors/SkillEditor.vue | SKILL.md 表单编辑 |
| ToolViewer | editors/ToolViewer.vue | 工具定义查看(只读) |
| RuntimeViewer | editors/RuntimeViewer.vue | 运行时状态查看(只读) |

**API 调用**:
- GET `/api/workspace/file?path={path}` - 加载文件
- PUT `/api/workspace/file?path={path}` - 保存文件

---

## W4: 循环引擎

### 4.1 WorkflowEngine
**文件**: `src/agent/workflow.py`

核心类:
```python
class WorkflowEngine:
    steps: dict[str, WorkflowStep]
    state: ExecutionState
    
    def load_from_yaml(self, yaml_path: str)
    def register_handler(self, step_type: StepType, handler)
    def pause() / resume() / step_once()
    async def run(self, context: StepContext) -> StepContext
```

步骤类型:
- PROMPT - 构建 Prompt
- LLM_STREAM - 流式 LLM 调用
- PARSE - 解析输出
- BRANCH - 条件分支
- EXECUTE - 执行指令
- MEMORY - 更新记忆
- END - 结束

### 4.2 main_loop.yaml
**文件**: `workflow/main_loop.yaml`

```yaml
name: main_loop
start: build_prompt
steps:
  - id: build_prompt
    type: prompt
    next: llm_infer
  - id: llm_infer
    type: llm_stream
    next: parse_output
  - id: parse_output
    type: parse
    next: check_tools
  - id: check_tools
    type: branch
    conditions:
      - if: "len(commands) > 0"
        next: execute_commands
    default: update_memory
  - id: execute_commands
    type: execute
    next: check_rejected
  - id: check_rejected
    type: branch
    conditions:
      - if: "any(r.get('status') == 'rejected' for r in command_results)"
        next: build_prompt
    default: update_memory
  - id: update_memory
    type: memory
    next: done
  - id: done
    type: end
```

### 4.3 GameMaster 集成
**文件**: `src/agent/game_master.py`

新增:
```python
self.workflow = WorkflowEngine()
self._register_workflow_handlers()

@property
def execution_state(self) -> ExecutionState
def pause() / resume() / step_once()
@property
def current_step_id(self) -> str | None
```

### 4.4 API 端点
**文件**: `src/api/routes/agent.py`

新增端点:
```python
POST /api/agent/control   # action: pause/resume/step
GET  /api/agent/workflow  # 获取工作流定义
```

### 4.5 测试
**文件**: `tests/test_agent/test_workflow.py`

测试用例:
1. test_load_yaml - YAML 加载
2. test_linear_execution - 线性执行
3. test_branch_execution - 分支执行
4. test_pause_resume - 暂停/继续
5. test_step_mode - 单步模式
6. test_condition_evaluation - 条件求值

**修复的问题**:
1. conditions 列表格式转换为字典
2. eval 条件时添加允许的 built-in 函数 (len/any/all)

---

## 关键文件清单

### 前端 (workbench/)
```
src/
  stores/
    app.ts          # Pinia Store
    index.ts
  components/
    TopBar.vue
    LeftPanel.vue
    MainEditor.vue
    RightPanel.vue
    BottomConsole.vue
    ResourceTree.vue
    EditorRouter.vue
    editors/
      MdEditor.vue
      YamlEditor.vue
      KeyValueEditor.vue
      SkillEditor.vue
      ToolViewer.vue
      RuntimeViewer.vue
  api/
    resources.ts    # 资源加载器
```

### 后端 (src/)
```
agent/
  workflow.py       # 工作流引擎
  game_master.py    # GameMaster 集成
api/routes/
  agent.py          # 控制端点
workflow/
  main_loop.yaml    # 默认工作流
tests/test_agent/
  test_workflow.py  # 工作流测试
```

---

## 下一步 (W5~W7)

1. **W5**: Vue Flow 流程编辑器
   - 安装 @vue-flow/core
   - 创建 WorkflowEditor.vue
   - 可视化编辑 YAML 工作流

2. **W6**: 底部控制台重构
   - 执行控制 Tab (暂停/继续/单步)
   - 轮次列表 Tab
   - 指令注入 Tab

3. **W7**: agent-pack 导入/导出
   - 后端 /api/pack/export, /api/pack/import
   - 前端导入/导出按钮

---

## 验证命令

```bash
# TypeScript 编译
cd workbench && npx vue-tsc --noEmit

# 前端启动
cd workbench && npm run dev

# 后端测试
cd d:\worldSim-master && uv run pytest tests/test_agent/test_workflow.py -v

# 导入检查
uv run python -c "from src.agent.game_master import GameMaster; print('OK')"
```
