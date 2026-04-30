# Game Master Agent - WorkBench 重构 W5~W7

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户重构 **Game Master Agent 的 WorkBench（管理端）**。
- **技术栈**: Vue 3 + TypeScript + Naive UI + Vite + Vue Flow
- **包管理器**: npm
- **后端**: Python FastAPI（已有）
- **前端目录**: `workbench/`
- **开发IDE**: Trae

### 前置条件

**W1~W4 已完成**。以下模块已就绪：
- 新布局：顶部控制栏 + 三栏 + 底部控制台
- Pinia Store：全局状态管理
- 左侧七层资源导航：ResourceTree + 数据加载器
- 中间多态编辑器：MD/YAML/KV/Skill/Tool/Runtime
- 后端工作流引擎：WorkflowEngine + main_loop.yaml
- GameMaster 集成工作流：pause/resume/step
- 控制端点：POST /api/agent/control, GET /api/agent/workflow

### W5~W7 阶段目标

1. **W5**: 流程编辑器 — Vue Flow 状态机可视化 + 编辑 + 保存为 YAML
2. **W6**: 底部控制台 — 执行控制 + 轮次列表 + 指令注入
3. **W7**: agent-pack 导入/导出

## 行为准则

1. **一步一步执行**：严格按照步骤顺序
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始"后主动执行
4. **遇到错误先尝试解决**：3 次失败后再询问
5. **代码规范**：TypeScript 严格模式、Vue 3 Composition API、中文注释

## 参考文档

| 文档 | 内容 |
|------|------|
| `docs/workspace_design.md` | WorkBench 原始设计 |
| `docs/architecture_v2.md` | V2 架构总览 |
| `workflow/main_loop.yaml` | 默认工作流定义 |

---

## W5: 流程编辑器（Vue Flow 状态机可视化）

### 步骤 5.1 - 安装 Vue Flow

**执行**:

```powershell
cd d:\worldSim-master\workbench
npm install @vue-flow/core @vue-flow/background @vue-flow/controls
```

**验收**: `npm ls @vue-flow/core` 显示已安装

---

### 步骤 5.2 - 创建流程编辑器组件

**目的**: 用 Vue Flow 实现可视化状态机编辑器，类似 Godot 的 StateMachine

**设计**:
- 7 种固定节点类型：prompt / llm_stream / parse / branch / execute / memory / end
- 节点间单向连线（step → next）
- branch 节点支持多输出（条件分支）
- 双击节点编辑参数
- 保存时序列化为 YAML

**执行**:
创建 `workbench/src/components/editors/WorkflowEditor.vue`：

```vue
<script setup lang="ts">
/**
 * 工作流可视化编辑器
 * 基于 Vue Flow 的状态机编辑器，类似 Godot StateMachine
 */
import { ref, watch, computed, onMounted, h, markRaw } from 'vue'
import { VueFlow, useVueFlow, type Node, type Edge } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { NButton, NModal, NForm, NFormItem, NInput, NSelect, NSpace, NAlert } from 'naive-ui'
import { useAppStore } from '../../stores/app'

const store = useAppStore()
const filePath = computed(() => store.selectedResource?.path ?? 'workflow/main_loop.yaml')

// Vue Flow 实例
const { onConnect, addEdges, getNodes, getEdges, setViewport, fitView } = useVueFlow({
  defaultViewport: { x: 0, y: 0, zoom: 0.8 },
})

// 节点和边
const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')

// 节点编辑弹窗
const editingNode = ref<Node | null>(null)
const showEditModal = ref(false)
const editForm = ref({ id: '', next: '', condition: '', conditionTarget: '' })

// === 节点类型定义 ===
const nodeTypes = {
  prompt: { label: '📝 构建 Prompt', color: '#e3f2fd', borderColor: '#1976d2' },
  llm_stream: { label: '🤖 LLM 推理', color: '#f3e5f5', borderColor: '#7b1fa2' },
  parse: { label: '📋 解析输出', color: '#e8f5e9', borderColor: '#388e3c' },
  branch: { label: '🔀 条件分支', color: '#fff3e0', borderColor: '#f57c00' },
  execute: { label: '⚡ 执行指令', color: '#fce4ec', borderColor: '#c62828' },
  memory: { label: '💾 更新记忆', color: '#e0f2f1', borderColor: '#00796b' },
  end: { label: '✅ 结束', color: '#f5f5f5', borderColor: '#757575' },
}

// === 从 YAML 加载工作流 ===
async function loadWorkflow() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    const content = data.content ?? ''

    // 解析 YAML（简单解析，不依赖 js-yaml）
    const parsed = parseSimpleYaml(content)
    const steps = parsed.steps ?? []

    // 转换为 Vue Flow 节点
    const newNodes: Node[] = steps.map((step: any, i: number) => {
      const type = step.type ?? 'prompt'
      const meta = nodeTypes[type] ?? nodeTypes.prompt
      const x = 100 + (i % 4) * 250
      const y = 80 + Math.floor(i / 4) * 150
      return {
        id: step.id,
        type: 'workflowStep',
        position: { x, y },
        data: {
          label: meta.label,
          stepType: type,
          color: meta.color,
          borderColor: meta.borderColor,
          stepData: step,
        },
      }
    })

    // 转换为 Vue Flow 边
    const newEdges: Edge[] = []
    for (const step of steps) {
      if (step.next && step.next !== 'done') {
        newEdges.push({
          id: `e-${step.id}-${step.next}`,
          source: step.id,
          target: step.next,
          animated: true,
          style: { stroke: '#666', strokeWidth: 2 },
        })
      }
      // branch 条件边
      if (step.conditions) {
        for (const [cond, target] of Object.entries(step.conditions)) {
          if (Array.isArray(target) && target.length > 0) {
            const t = target[0]
            if (typeof t === 'object' && t.if && t.next) {
              newEdges.push({
                id: `e-${step.id}-${t.next}`,
                source: step.id,
                target: t.next,
                label: t.if,
                animated: true,
                style: { stroke: '#f57c00', strokeWidth: 2 },
              })
            }
          }
        }
      }
    }

    nodes.value = newNodes
    edges.value = newEdges

    // 延迟 fitView
    setTimeout(() => fitView(), 100)
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

/** 简单 YAML 解析（不依赖外部库） */
function parseSimpleYaml(text: string): any {
  const result: any = { steps: [] }
  const lines = text.split('\n')
  let currentStep: any = null
  let inSteps = false

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue

    if (trimmed.startsWith('steps:')) {
      inSteps = true
      continue
    }

    if (inSteps && trimmed.startsWith('- id:')) {
      if (currentStep) result.steps.push(currentStep)
      currentStep = { id: trimmed.replace('- id:', '').trim() }
      continue
    }

    if (currentStep && trimmed.startsWith('- ')) {
      // 条件列表项
      const match = trimmed.match(/- if:\s*"(.+?)"\s*$/)
      if (match) {
        currentStep.conditions = currentStep.conditions ?? []
        currentStep.conditions.push(match[1])
      }
      continue
    }

    if (currentStep && trimmed.includes(':')) {
      const idx = trimmed.indexOf(':')
      const key = trimmed.slice(0, idx).trim()
      const val = trimmed.slice(idx + 1).trim().replace(/^["']|["']$/g, '')
      if (key === 'type' || key === 'next' || key === 'default') {
        currentStep[key] = val
      }
    }
  }
  if (currentStep) result.steps.push(currentStep)
  return result
}

// === 保存为 YAML ===
async function saveWorkflow() {
  saving.value = true
  error.value = ''
  try {
    const yamlContent = nodesToYaml(nodes.value, edges.value)
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: yamlContent }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

function nodesToYaml(nodes: Node[], edges: Edge[]): string {
  let yaml = 'name: main_loop\nstart: ' + (nodes[0]?.id ?? 'step_1') + '\nsteps:\n'

  for (const node of nodes) {
    const data = node.data
    yaml += `  - id: ${node.id}\n`
    yaml += `    type: ${data.stepType}\n`

    // 找到从这个节点出发的边
    const outEdges = edges.filter(e => e.source === node.id)
    if (data.stepType === 'branch') {
      yaml += '    conditions:\n'
      for (const edge of outEdges) {
        yaml += `      - if: "${edge.label || 'true'}"\n`
        yaml += `        next: ${edge.target}\n`
      }
      yaml += '    default: done\n'
    } else if (outEdges.length > 0) {
      yaml += `    next: ${outEdges[0].target}\n`
    } else {
      yaml += '    next: done\n'
    }
  }

  return yaml
}

// === 连线处理 ===
onConnect((params) => {
  addEdges([{
    ...params,
    animated: true,
    style: { stroke: '#666', strokeWidth: 2 },
  }])
})

// === 双击编辑节点 ===
function onNodeDoubleClick({ node }: { node: Node }) {
  editingNode.value = node
  editForm.value = {
    id: node.id,
    next: node.data.stepData?.next ?? '',
    condition: '',
    conditionTarget: '',
  }
  showEditModal.value = true
}

function saveNodeEdit() {
  if (!editingNode.value) return
  const node = editingNode.value
  node.data.stepData = {
    ...node.data.stepData,
    next: editForm.value.next,
  }
  showEditModal.value = false
}

// === 添加新节点 ===
function addNode(type: string) {
  const meta = nodeTypes[type] ?? nodeTypes.prompt
  const id = `step_${Date.now()}`
  const newNodes = [...nodes.value]
  const lastNode = newNodes[newNodes.length - 1]
  const x = lastNode ? lastNode.position.x + 250 : 100
  const y = lastNode ? lastNode.position.y : 80

  newNodes.push({
    id,
    type: 'workflowStep',
    position: { x, y },
    data: {
      label: meta.label,
      stepType: type,
      color: meta.color,
      borderColor: meta.borderColor,
      stepData: { id, type, next: '' },
    },
  })
  nodes.value = newNodes
}

// === 删除节点 ===
function deleteSelectedNodes() {
  const selected = getNodes.value.filter(n => n.selected)
  if (selected.length === 0) return
  const selectedIds = new Set(selected.map(n => n.id))
  nodes.value = nodes.value.filter(n => !selectedIds.has(n.id))
  edges.value = edges.value.filter(e => !selectedIds.has(e.source) && !selectedIds.has(e.target))
}

// 监听文件路径变化
watch(filePath, loadWorkflow, { immediate: true })
</script>

<template>
  <div class="workflow-editor">
    <!-- 工具栏 -->
    <div class="wf-toolbar">
      <span class="wf-title">🔄 工作流编辑器</span>
      <NSpace :size="4">
        <NButton size="tiny" @click="addNode('prompt')">+ Prompt</NButton>
        <NButton size="tiny" @click="addNode('llm_stream')">+ LLM</NButton>
        <NButton size="tiny" @click="addNode('parse')">+ Parse</NButton>
        <NButton size="tiny" @click="addNode('branch')">+ Branch</NButton>
        <NButton size="tiny" @click="addNode('execute')">+ Execute</NButton>
        <NButton size="tiny" @click="addNode('memory')">+ Memory</NButton>
        <NButton size="tiny" @click="addNode('end')">+ End</NButton>
        <div class="separator" />
        <NButton size="tiny" @click="deleteSelectedNodes">删除选中</NButton>
        <NButton size="tiny" type="primary" :loading="saving" @click="saveWorkflow">保存</NButton>
      </NSpace>
    </div>

    <NAlert v-if="error" type="error" closable style="margin: 4px 8px">{{ error }}</NAlert>

    <!-- Vue Flow 画布 -->
    <div class="wf-canvas">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :node-types="nodeTypesMap"
        :default-edge-options="{ animated: true }"
        :snap-to-grid="true"
        :snap-grid="[20, 20]"
        fit-view-on-init
        @node-double-click="onNodeDoubleClick"
        @keydown.delete="deleteSelectedNodes"
      >
        <Background :gap="20" />
        <Controls />

        <!-- 自定义节点渲染 -->
        <template #node-workflowStep="{ data }">
          <div
            class="wf-node"
            :style="{
              backgroundColor: data.color,
              border: `2px solid ${data.borderColor}`,
              borderRadius: '8px',
            }"
          >
            <div class="wf-node-label">{{ data.label }}</div>
            <div class="wf-node-id">{{ data.stepData?.id }}</div>
          </div>
        </template>
      </VueFlow>
    </div>

    <!-- 节点编辑弹窗 -->
    <NModal v-model:show="showEditModal" preset="dialog" title="编辑步骤">
      <NForm>
        <NFormItem label="步骤 ID">
          <NInput v-model:value="editForm.id" disabled />
        </NFormItem>
        <NFormItem label="下一步 (next)">
          <NInput v-model:value="editForm.next" placeholder="下一步骤 ID" />
        </NFormItem>
      </NForm>
      <template #action>
        <NButton @click="showEditModal = false">取消</NButton>
        <NButton type="primary" @click="saveNodeEdit">保存</NButton>
      </template>
    </NModal>
  </div>
</template>

<script lang="ts">
// Vue Flow 节点类型映射（必须在 setup 外定义）
const nodeTypesMap = {
  workflowStep: markRaw(defineComponent({
    name: 'WorkflowStepNode',
    props: ['data'],
    setup(props: any) {
      return () => h('div', {
        style: {
          backgroundColor: props.data?.color ?? '#fff',
          border: `2px solid ${props.data?.borderColor ?? '#999'}`,
          borderRadius: '8px',
          padding: '8px 16px',
          minWidth: '120px',
          textAlign: 'center',
        },
      }, [
        h('div', { style: { fontWeight: 600, fontSize: '13px' } }, props.data?.label ?? ''),
        h('div', { style: { fontSize: '11px', color: '#999', marginTop: '2px' } }, props.data?.stepData?.id ?? ''),
      ])
    },
  })),
}

import { defineComponent, markRaw, h } from 'vue'
</script>

<style scoped>
.workflow-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.wf-toolbar {
  padding: 6px 12px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.wf-title {
  font-size: 12px;
  font-weight: 600;
}

.separator {
  width: 1px;
  height: 20px;
  background: #e0e0e0;
}

.wf-canvas {
  flex: 1;
  min-height: 0;
}

.wf-node {
  padding: 8px 16px;
  min-width: 120px;
  text-align: center;
  cursor: pointer;
}

.wf-node-label {
  font-weight: 600;
  font-size: 13px;
}

.wf-node-id {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}
</style>
```

**注意**: 如果 Vue Flow 的自定义节点渲染方式有问题，可以简化为使用 Vue Flow 的默认节点 + 自定义颜色，不使用 `#node-workflowStep` 插槽。

**验收**: `npm run dev` 启动后，点击左侧 Workflow → main_loop.yaml，中间显示流程编辑器画布

---

### 步骤 5.3 - 集成到 EditorRouter

**执行**:
修改 `workbench/src/components/EditorRouter.vue`，在 `editorType` 计算属性中添加 workflow 类型：

在 `editorType` computed 中，在 `// YAML 文件` 判断之前添加：

```typescript
// Workflow 文件
if (path.includes('workflow/') && (path.endsWith('.yaml') || path.endsWith('.yml'))) return 'workflow'
```

然后在模板中添加：

```vue
<WorkflowEditor v-else-if="editorType === 'workflow'" />
```

并在 script setup 中导入：

```typescript
import WorkflowEditor from './editors/WorkflowEditor.vue'
```

**验收**: 点击 Workflow → main_loop.yaml，中间显示流程编辑器

---

## W6: 底部控制台（执行控制 + 轮次列表 + 指令注入）

### 步骤 6.1 - 重构 BottomConsole

**执行**:
重写 `workbench/src/components/BottomConsole.vue`：

```vue
<script setup lang="ts">
/**
 * 底部控制台
 * Tab 1: 执行控制 — 暂停/继续/单步 + 当前步骤高亮
 * Tab 2: 轮次列表 — 历史轮次，点击查看详情
 * Tab 3: 指令注入 — system/user 级别注入
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { NTabs, NTabPane, NButton, NSpace, NInput, NSelect, NTag, NDescriptions, NDescriptionsItem, NEmpty, NDataTable } from 'naive-ui'
import { useAppStore, type TurnRecord } from '../stores/app'

const store = useAppStore()

// === SSE 连接 ===
let eventSource: EventSource | null = null

function connectSSE() {
  if (eventSource) eventSource.close()
  eventSource = new EventSource('/api/agent/stream')

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      store.addSSEEvent(data.type ?? 'unknown', data)

      // 更新状态
      if (data.type === 'turn_start') {
        store.setExecutionState('RUNNING')
        store.currentTurn++
      } else if (data.type === 'turn_end') {
        store.setExecutionState('IDLE')
        const stats = data.data?.stats ?? {}
        store.totalTokens = stats.total_tokens ?? store.totalTokens
        store.currentLatency = stats.latency ?? 0
        store.addTurn({
          id: store.currentTurn,
          status: 'completed',
          narrative: '',
          commands: [],
          tokens: stats.tokens_used ?? 0,
          latency: stats.latency ?? 0,
          timestamp: new Date().toISOString(),
        })
      } else if (data.type === 'command') {
        // 指令事件
      } else if (data.type === 'error') {
        store.setExecutionState('IDLE')
      }
    } catch {
      // 忽略解析错误
    }
  }

  eventSource.onerror = () => {
    // 自动重连由 EventSource 处理
  }
}

onMounted(() => connectSSE())
onUnmounted(() => { if (eventSource) eventSource.close() })

// === 执行控制 ===
async function sendControl(action: string) {
  try {
    const res = await fetch('/api/agent/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    })
    const data = await res.json()
    store.setExecutionState(data.state)
  } catch (e) {
    console.error('控制失败:', e)
  }
}

// === 指令注入 ===
const injectLevel = ref('user')
const injectContent = ref('')
const injectSending = ref(false)

const levelOptions = [
  { label: 'system (插入 system prompt)', value: 'system' },
  { label: 'user (模拟玩家输入)', value: 'user' },
  { label: 'override (覆盖 Prompt)', value: 'override' },
]

async function sendInject() {
  if (!injectContent.value.trim()) return
  injectSending.value = true
  try {
    const res = await fetch('/api/agent/event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'player_action',
        data: {
          raw_text: injectContent.value,
          player_id: 'debug',
          inject_level: injectLevel.value,
        },
      }),
    })
    if (res.ok) {
      injectContent.value = ''
    }
  } catch (e) {
    console.error('注入失败:', e)
  } finally {
    injectSending.value = false
  }
}

// === 轮次详情 ===
const selectedTurnId = ref<number | null>(null)

const turnColumns = [
  { title: 'ID', key: 'id', width: 50 },
  { title: '状态', key: 'status', width: 80,
    render: (row: TurnRecord) => h(NTag, {
      type: row.status === 'completed' ? 'success' : row.status === 'failed' ? 'error' : 'warning',
      size: 'small',
    }, () => row.status)
  },
  { title: 'Token', key: 'tokens', width: 80 },
  { title: '延迟', key: 'latency', width: 80,
    render: (row: TurnRecord) => `${row.latency}ms`
  },
  { title: '时间', key: 'timestamp', width: 160 },
]

// === 工作流状态 ===
const workflowState = ref<any>(null)

async function loadWorkflowState() {
  try {
    const res = await fetch('/api/agent/workflow')
    if (res.ok) {
      workflowState.value = await res.json()
    }
  } catch {
    // 忽略
  }
}

// 定期刷新
let workflowTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  workflowTimer = setInterval(loadWorkflowState, 2000)
})
onUnmounted(() => {
  if (workflowTimer) clearInterval(workflowTimer)
})
</script>

<template>
  <div class="bottom-console-content">
    <NTabs type="card" size="small">
      <!-- Tab 1: 执行控制 -->
      <NTabPane name="control" tab="执行控制">
        <div class="control-panel">
          <div class="control-buttons">
            <NSpace :size="4">
              <NButton size="tiny" :disabled="store.isRunning" @click="sendControl('resume')">
                ▶ 运行
              </NButton>
              <NButton size="tiny" :disabled="!store.isRunning" @click="sendControl('pause')">
                ⏸ 暂停
              </NButton>
              <NButton size="tiny" :disabled="!store.isRunning && !store.isPaused" @click="sendControl('step')">
                ⏯ 单步
              </NButton>
            </NSpace>
            <div class="step-info">
              <span v-if="workflowState?.current_step" class="current-step">
                当前步骤: <NTag size="tiny" type="info">{{ workflowState.current_step }}</NTag>
              </span>
            </div>
          </div>
          <div class="event-log">
            <div v-for="(evt, i) in store.sseEvents.slice(-30).reverse()" :key="i" class="event-line">
              <span class="event-time">{{ evt.time }}</span>
              <NTag :type="evt.type === 'error' ? 'error' : evt.type === 'turn_start' ? 'success' : 'default'" size="tiny">
                {{ evt.type }}
              </NTag>
              <span class="event-data">{{ JSON.stringify(evt.data).slice(0, 80) }}</span>
            </div>
            <div v-if="store.sseEvents.length === 0" class="empty-hint">
              等待 Agent 运行...
            </div>
          </div>
        </div>
      </NTabPane>

      <!-- Tab 2: 轮次列表 -->
      <NTabPane name="turns" tab="轮次列表">
        <div class="turns-panel">
          <NDataTable
            :columns="turnColumns"
            :data="[...store.turnHistory].reverse()"
            :max-height="140"
            size="small"
            :row-props="(row: TurnRecord) => ({
              style: row.id === store.currentTurn ? 'background: #e3f2fd' : '',
              onClick: () => { selectedTurnId = row.id },
            })"
          />
          <NEmpty v-if="store.turnHistory.length === 0" description="暂无轮次记录" size="small" />
        </div>
      </NTabPane>

      <!-- Tab 3: 指令注入 -->
      <NTabPane name="inject" tab="指令注入">
        <div class="inject-panel">
          <NSpace align="center" :size="8">
            <NSelect v-model:value="injectLevel" :options="levelOptions" size="small" style="width: 200px" />
            <NInput
              v-model:value="injectContent"
              size="small"
              placeholder="输入注入内容..."
              style="flex: 1"
              @keyup.enter="sendInject"
            />
            <NButton size="small" type="primary" :loading="injectSending" @click="sendInject">
              发送
            </NButton>
          </NSpace>
          <div class="inject-hint">
            system: 插入 system prompt 末尾 | user: 模拟玩家输入 | override: 覆盖 Prompt
          </div>
        </div>
      </NTabPane>
    </NTabs>
  </div>
</template>

<style scoped>
.bottom-console-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.control-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.control-buttons {
  padding: 4px 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.step-info {
  font-size: 12px;
}

.current-step {
  display: flex;
  align-items: center;
  gap: 4px;
}

.event-log {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 11px;
}

.event-line {
  display: flex;
  gap: 6px;
  padding: 1px 0;
  align-items: center;
}

.event-time {
  color: #999;
  min-width: 60px;
  font-size: 10px;
}

.event-data {
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-hint {
  padding: 16px;
  color: #ccc;
  text-align: center;
  font-size: 12px;
}

.turns-panel {
  height: 100%;
  overflow-y: auto;
}

.inject-panel {
  padding: 8px;
}

.inject-hint {
  margin-top: 4px;
  font-size: 11px;
  color: #999;
}
</style>
```

**验收**: `npm run dev` 启动后，底部控制台显示 3 个 Tab，SSE 自动连接

---

### 步骤 6.2 - 添加后端指令注入端点

**执行**:
在 `src/api/routes/agent.py` 中确认 `/api/agent/event` 端点支持 `inject_level` 字段。

如果现有端点不支持，添加：

```python
@router.post("/inject")
async def inject_instruction(level: str = "user", content: str = ""):
    """
    注入指令到 Agent。
    level: system / user / override
    """
    if _game_master is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if not content.strip():
        raise HTTPException(status_code=400, detail="Content is required")

    # 构造注入事件
    from src.adapters.base import EngineEvent
    event = EngineEvent(
        event_id=f"inject_{_game_master.turn_count + 1}",
        timestamp=__import__("datetime").datetime.now().isoformat(),
        type="player_action",
        data={"raw_text": content, "player_id": "debug", "inject_level": level},
        context_hints=[],
        game_state={},
    )

    # 异步处理
    import asyncio
    response = await _event_handler.handle_event(event)

    return {
        "status": "injected",
        "level": level,
        "response_id": response.get("response_id"),
    }
```

**验收**: `uv run pytest tests/ -v --tb=short` 全部通过

---

## W7: agent-pack 导入/导出

### 步骤 7.1 - 添加后端 agent-pack 端点

**执行**:
创建 `src/api/routes/pack.py`：

```python
"""
agent-pack 导入/导出 API
"""
from __future__ import annotations

import io
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/pack", tags=["pack"])

# 项目根目录
PROJECT_ROOT = Path(".")


@router.get("/export")
async def export_pack():
    """
    导出 agent-pack.zip
    包含: system_prompt + skills + memory + config + workflow
    """
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. metadata.json
        metadata = {
            "name": "GameMaster Agent",
            "version": "2.0.0",
            "description": "RPG Game Master Agent 配置包",
            "exported_at": datetime.now().isoformat(),
        }
        zf.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))

        # 2. system_prompt.md
        sp_path = PROJECT_ROOT / "prompts" / "system_prompt.md"
        if sp_path.exists():
            zf.write(str(sp_path), "system_prompt.md")

        # 3. skills/
        skills_dir = PROJECT_ROOT / "skills"
        if skills_dir.exists():
            for f in skills_dir.rglob("*.md"):
                arcname = f"skills/" + str(f.relative_to(skills_dir))
                zf.write(str(f), arcname)

        # 4. memory/ (workspace/)
        workspace_dir = PROJECT_ROOT / "workspace"
        if workspace_dir.exists():
            for f in workspace_dir.rglob("*.md"):
                arcname = "memory/" + str(f.relative_to(workspace_dir))
                zf.write(str(f), arcname)

        # 5. workflow/
        workflow_dir = PROJECT_ROOT / "workflow"
        if workflow_dir.exists():
            for f in workflow_dir.rglob("*.yaml"):
                arcname = "workflow/" + str(f.relative_to(workflow_dir))
                zf.write(str(f), arcname)

        # 6. config/.env.template
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            # 移除敏感值
            lines = []
            for line in content.split('\n'):
                if 'API_KEY' in line or 'SECRET' in line or 'PASSWORD' in line:
                    key = line.split('=')[0] if '=' in line else line
                    lines.append(f"{key}=YOUR_VALUE_HERE")
                else:
                    lines.append(line)
            zf.writestr("config/.env.template", '\n'.join(lines))

    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=agent-pack.zip"},
    )


@router.post("/import")
async def import_pack(file: UploadFile):
    """
    导入 agent-pack.zip
    校验完整性 → 预览差异 → 合并
    """
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    content = await file.read()
    buf = io.BytesIO(content)

    try:
        with zipfile.ZipFile(buf, 'r') as zf:
            # 校验 metadata.json
            if "metadata.json" not in zf.namelist():
                raise HTTPException(status_code=400, detail="Invalid pack: missing metadata.json")

            metadata = json.loads(zf.read("metadata.json"))

            # 预览差异
            preview = []
            for name in zf.namelist():
                if name == "metadata.json":
                    continue

                # 映射到项目路径
                if name.startswith("system_prompt.md"):
                    target = PROJECT_ROOT / "prompts" / "system_prompt.md"
                elif name.startswith("skills/"):
                    target = PROJECT_ROOT / "skills" / name[len("skills/"):]
                elif name.startswith("memory/"):
                    target = PROJECT_ROOT / "workspace" / name[len("memory/"):]
                elif name.startswith("workflow/"):
                    target = PROJECT_ROOT / "workflow" / name[len("workflow/"):]
                elif name.startswith("config/"):
                    target = PROJECT_ROOT / name[len("config/"):]
                else:
                    continue

                exists = target.exists()
                action = "update" if exists else "create"
                preview.append({
                    "file": name,
                    "target": str(target),
                    "action": action,
                    "exists": exists,
                })

            # 执行合并（自动备份）
            backup_dir = PROJECT_ROOT / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
            for item in preview:
                target = Path(item["target"])
                if item["exists"]:
                    # 备份
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(target), str(backup_dir / target.name))

                # 提取文件
                target.parent.mkdir(parents=True, exist_ok=True)
                data = zf.read(item["file"])
                target.write_bytes(data)

            return {
                "status": "imported",
                "metadata": metadata,
                "files": preview,
                "backup": str(backup_dir) if backup_dir.exists() else None,
            }

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
```

在 `src/api/app.py` 中注册路由：

```python
from src.api.routes.pack import router as pack_router
app.include_router(pack_router)
```

**验收**: `python -c "from src.api.routes.pack import router; print('OK')"` 成功

---

### 步骤 7.2 - 前端导入/导出按钮

**执行**:
在 `workbench/src/components/TopBar.vue` 中添加导入/导出按钮。

在模板的 `status-area` 之前添加：

```vue
<div class="separator" />

<!-- agent-pack -->
<NButton size="small" @click="exportPack">📦 导出</NButton>
<NButton size="small" @click="triggerImport">📥 导入</NButton>
<input ref="fileInput" type="file" accept=".zip" style="display: none" @change="handleImport" />
```

在 script setup 中添加：

```typescript
import { ref } from 'vue'

const fileInput = ref<HTMLInputElement | null>(null)

async function exportPack() {
  window.open('/api/pack/export', '_blank')
}

function triggerImport() {
  fileInput.value?.click()
}

async function handleImport(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await fetch('/api/pack/import', { method: 'POST', body: formData })
    const data = await res.json()
    if (res.ok) {
      window.$message?.success(`导入成功: ${data.files?.length ?? 0} 个文件`)
    } else {
      window.$message?.error(`导入失败: ${data.detail}`)
    }
  } catch {
    window.$message?.error('导入失败')
  }

  // 重置 input
  input.value = ''
}
```

**验收**: `npm run dev` 启动后，顶部控制栏显示 📦 导出 和 📥 导入 按钮

---

### 步骤 7.3 - agent-pack 测试

**执行**:
创建 `tests/test_api/test_pack.py`：

```python
"""agent-pack 导入/导出测试"""
import pytest
import zipfile
import json
import io
from pathlib import Path


@pytest.fixture
def client(tmp_path):
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    from src.api.routes.pack import router

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestPackExport:
    def test_export_returns_zip(self, client):
        res = client.get("/api/pack/export")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/zip"

        # 验证是有效 zip
        buf = io.BytesIO(res.content)
        with zipfile.ZipFile(buf, 'r') as zf:
            names = zf.namelist()
            assert "metadata.json" in names

    def test_export_contains_metadata(self, client):
        res = client.get("/api/pack/export")
        buf = io.BytesIO(res.content)
        with zipfile.ZipFile(buf, 'r') as zf:
            metadata = json.loads(zf.read("metadata.json"))
            assert "name" in metadata
            assert "version" in metadata
            assert "exported_at" in metadata


class TestPackImport:
    def test_import_valid_pack(self, client, tmp_path):
        # 创建测试 zip
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr("metadata.json", json.dumps({
                "name": "test", "version": "1.0.0"
            }))
            zf.writestr("system_prompt.md", "# Test Prompt")
        buf.seek(0)

        res = client.post(
            "/api/pack/import",
            files={"file": ("test.zip", buf, "application/zip")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "imported"
        assert len(data["files"]) > 0

    def test_import_invalid_zip(self, client):
        res = client.post(
            "/api/pack/import",
            files={"file": ("bad.txt", b"not a zip", "text/plain")},
        )
        assert res.status_code == 400

    def test_import_missing_metadata(self, client):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr("readme.txt", "no metadata")
        buf.seek(0)

        res = client.post(
            "/api/pack/import",
            files={"file": ("no_meta.zip", buf, "application/zip")},
        )
        assert res.status_code == 400
```

**验收**: `pytest tests/test_api/test_pack.py -v` 全部通过（>=5 个测试）

---

## W5~W7 完成检查清单

- [ ] W5.1: Vue Flow 安装成功
- [ ] W5.2: WorkflowEditor 组件创建
- [ ] W5.3: EditorRouter 集成 workflow 类型
- [ ] 点击 Workflow 文件，中间显示流程编辑器画布
- [ ] 可以添加/删除节点，保存为 YAML
- [ ] W6.1: BottomConsole 重构（3 个 Tab）
- [ ] SSE 自动连接，实时显示事件
- [ ] 暂停/继续/单步按钮可用
- [ ] 指令注入面板可用
- [ ] W6.2: 后端 inject 端点添加
- [ ] W7.1: 后端 pack 端点创建
- [ ] W7.2: 前端导入/导出按钮
- [ ] W7.3: pack 测试通过（>=5 个）
- [ ] `npm run build` 前端构建成功
- [ ] **全部后端测试仍然通过**
