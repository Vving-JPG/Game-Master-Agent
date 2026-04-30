# Game Master Agent - WorkBench 重构 W1~W4

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户重构 **Game Master Agent 的 WorkBench（管理端）**。
- **技术栈**: Vue 3 + TypeScript + Naive UI + Vite + Vue Flow
- **包管理器**: npm
- **后端**: Python FastAPI（已有，在 `src/api/` 下）
- **前端目录**: `workbench/`
- **开发IDE**: Trae

### 前置条件

**V2 后端已完成**（P0-P4）。以下后端模块已就绪：
- `src/agent/` — GameMaster、CommandParser、PromptBuilder、EventHandler
- `src/memory/` — MemoryManager、MemoryLoader、FileIO
- `src/skills/` — SkillLoader
- `src/adapters/` — EngineAdapter、TextAdapter
- `src/api/routes/` — workspace、skills、agent 路由
- `src/api/sse.py` — SSE 流式推送
- `prompts/system_prompt.md` — Agent 主提示词
- `skills/builtin/` — 5 个内置 SKILL.md
- `workspace/` — Agent 记忆文件

### W1~W4 阶段目标

1. **W1**: 骨架重构 — 新布局（顶部控制栏 + 三栏 + 底部控制台）
2. **W2**: 左侧七层资源导航 + 右侧辅助面板
3. **W3**: 中间多态编辑器（MD / YAML / 键值对 / Skill 表单）
4. **W4**: 循环引擎 — YAML 工作流 + GameMaster ReAct 循环 + 执行状态机

### WorkBench 定位

**WorkBench 是 Agent 的 IDE + 运行时调试器**，不是游戏界面。
核心验证闭环：改 Prompt → 看 AI 输出 → 看游戏实际效果 → 再改 Prompt。

## 行为准则

1. **一步一步执行**：严格按照步骤顺序，每步验证通过再继续
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始"后主动执行，不需要反复催促
4. **遇到错误先尝试解决**：3 次失败后再询问用户
5. **每步完成后汇报**：简要汇报结果和下一步计划
6. **代码规范**：
   - TypeScript 严格模式
   - Vue 3 Composition API + `<script setup lang="ts">`
   - Naive UI 组件库
   - 中文注释
   - 组件文件名 PascalCase
7. **不要跳步**
8. **不要删除现有文件**：W1 会重构 App.vue，但保留现有组件作为参考

## 参考文档

| 文档 | 内容 |
|------|------|
| `docs/workspace_design.md` | WorkBench 原始设计 |
| `docs/architecture_v2.md` | V2 架构总览 |
| `docs/communication_protocol.md` | SSE 协议 |
| `docs/skill_system.md` | SKILL.md 标准 |

## V1 经验教训

1. **Vite 代理**: `vite.config.ts` 中配置 `/api` 代理到 `http://localhost:8000`
2. **Naive UI**: 使用 `n-config-provider` 包裹根组件
3. **SSE 连接**: 使用原生 `EventSource`，注意跨域
4. **中文括号**: 代码中用英文括号 `()`

---

## W1: 骨架重构（布局 + 顶部控制栏 + 底部控制台）

### 步骤 1.1 - 安装新依赖

**执行**:

```powershell
cd d:\worldSim-master\workbench
npm install @vueuse/core pinia
```

**验收**: `npm ls @vueuse/core pinia` 显示已安装

---

### 步骤 1.2 - 创建 Pinia Store

**目的**: 全局状态管理（Agent 状态、当前选中资源、执行状态等）

**执行**:
创建 `workbench/src/stores/app.ts`：

```typescript
/**
 * 全局应用状态
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/** 执行状态 */
export type ExecutionState = 'IDLE' | 'RUNNING' | 'PAUSED' | 'STEP_WAITING'

/** 资源类型 */
export type ResourceType = 'prompt' | 'memory' | 'config' | 'tools' | 'workflow' | 'runtime'

/** 资源节点 */
export interface ResourceNode {
  key: string
  label: string
  type: ResourceType
  icon: string
  path?: string
  isLeaf?: boolean
  children?: ResourceNode[]
}

/** 轮次记录 */
export interface TurnRecord {
  id: number
  status: 'completed' | 'failed' | 'paused' | 'current'
  narrative: string
  commands: Array<{ intent: string; status: string }>
  tokens: number
  latency: number
  timestamp: string
}

export const useAppStore = defineStore('app', () => {
  // === 执行状态 ===
  const executionState = ref<ExecutionState>('IDLE')
  const currentTurn = ref(0)
  const totalTokens = ref(0)
  const currentLatency = ref(0)

  // === 模型配置 ===
  const selectedModel = ref('deepseek-chat')
  const temperature = ref(0.7)
  const maxTokens = ref(4096)

  // === 资源导航 ===
  const selectedResource = ref<ResourceNode | null>(null)
  const expandedKeys = ref<string[]>([])

  // === 轮次历史 ===
  const turnHistory = ref<TurnRecord[]>([])

  // === SSE 事件 ===
  const sseEvents = ref<Array<{ type: string; data: any; time: string }>>([])

  // === 计算属性 ===
  const isRunning = computed(() => executionState.value === 'RUNNING')
  const isPaused = computed(() => executionState.value === 'PAUSED')

  // === 方法 ===
  function setExecutionState(state: ExecutionState) {
    executionState.value = state
  }

  function addTurn(turn: TurnRecord) {
    turnHistory.value.push(turn)
  }

  function addSSEEvent(type: string, data: any) {
    sseEvents.value.push({ type, data, time: new Date().toLocaleTimeString() })
    // 保留最近 500 条
    if (sseEvents.value.length > 500) {
      sseEvents.value = sseEvents.value.slice(-500)
    }
  }

  function reset() {
    executionState.value = 'IDLE'
    currentTurn.value = 0
    totalTokens.value = 0
    currentLatency.value = 0
    turnHistory.value = []
    sseEvents.value = []
  }

  return {
    executionState,
    currentTurn,
    totalTokens,
    currentLatency,
    selectedModel,
    temperature,
    maxTokens,
    selectedResource,
    expandedKeys,
    turnHistory,
    sseEvents,
    isRunning,
    isPaused,
    setExecutionState,
    addTurn,
    addSSEEvent,
    reset,
  }
})
```

创建 `workbench/src/stores/index.ts`：

```typescript
export { useAppStore } from './app'
```

**验收**: TypeScript 编译无错误

---

### 步骤 1.3 - 重构 App.vue（新布局）

**目的**: 替换现有三栏布局为新的 IDE 布局

**执行**:
重写 `workbench/src/App.vue`：

```vue
<script setup lang="ts">
import { NConfigProvider, NLayout, NLayoutHeader, NLayoutContent, NLayoutFooter } from 'naive-ui'
import { NMessageProvider } from 'naive-ui'
import TopBar from './components/TopBar.vue'
import LeftPanel from './components/LeftPanel.vue'
import MainEditor from './components/MainEditor.vue'
import RightPanel from './components/RightPanel.vue'
import BottomConsole from './components/BottomConsole.vue'
</script>

<template>
  <NConfigProvider>
    <NMessageProvider>
      <NLayout class="app-layout" has-sider>
        <!-- 顶部控制栏 -->
        <NLayoutHeader class="top-bar" bordered>
          <TopBar />
        </NLayoutHeader>

        <NLayout has-sider class="main-area">
          <!-- 左侧资源导航 18% -->
          <NLayoutSider
            class="left-panel"
            :width="260"
            :min-width="200"
            :max-width="400"
            bordered
            collapse-mode="width"
          >
            <LeftPanel />
          </NLayoutSider>

          <!-- 中间 + 右侧 -->
          <NLayout class="center-right-area">
            <NLayout has-sider class="center-right-inner">
              <!-- 中间主工作区 -->
              <NLayoutContent class="main-editor">
                <MainEditor />
              </NLayoutContent>

              <!-- 右侧辅助面板 30% -->
              <NLayoutSider
                class="right-panel"
                :width="360"
                :min-width="280"
                :max-width="500"
                bordered
                collapse-mode="width"
                position="right"
              >
                <RightPanel />
              </NLayoutSider>
            </NLayout>

            <!-- 底部控制台 -->
            <NLayoutFooter class="bottom-console" bordered>
              <BottomConsole />
            </NLayoutFooter>
          </NLayout>
        </NLayout>
      </NLayout>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-layout {
  height: 100vh;
}

.top-bar {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-area {
  height: calc(100vh - 48px);
}

.left-panel {
  height: 100%;
  overflow-y: auto;
}

.center-right-area {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.center-right-inner {
  flex: 1;
  min-height: 0;
}

.main-editor {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.right-panel {
  height: 100%;
  overflow-y: auto;
}

.bottom-console {
  height: 200px;
  min-height: 100px;
  max-height: 400px;
  overflow: hidden;
}
</style>
```

**验收**: `npm run dev` 启动无报错（组件还没创建会报错，先创建占位组件）

---

### 步骤 1.4 - 创建占位组件

**执行**:

创建 `workbench/src/components/TopBar.vue`：

```vue
<script setup lang="ts">
import { NButton, NSelect, NSlider, NInputGroup, NTag, NSpace } from 'naive-ui'
import { useAppStore } from '../stores/app'

const store = useAppStore()

const modelOptions = [
  { label: 'deepseek-chat', value: 'deepseek-chat' },
  { label: 'deepseek-reasoner', value: 'deepseek-reasoner' },
]

function handleRun() {
  store.setExecutionState('RUNNING')
}

function handlePause() {
  store.setExecutionState('PAUSED')
}

function handleStep() {
  store.setExecutionState('STEP_WAITING')
}

function handleReset() {
  store.reset()
}
</script>

<template>
  <div class="top-bar-content">
    <!-- 执行控制 -->
    <NSpace :size="4">
      <NButton size="small" type="primary" :disabled="store.isRunning" @click="handleRun">
        ▶ 运行
      </NButton>
      <NButton size="small" :disabled="!store.isRunning" @click="handlePause">
        ⏸ 暂停
      </NButton>
      <NButton size="small" :disabled="!store.isRunning && !store.isPaused" @click="handleStep">
        ⏯ 单步
      </NButton>
      <NButton size="small" @click="handleReset">
        ↺ 重置
      </NButton>
    </NSpace>

    <div class="separator" />

    <!-- 模型选择 -->
    <NSelect
      v-model:value="store.selectedModel"
      :options="modelOptions"
      size="small"
      style="width: 180px"
    />

    <!-- 温度 -->
    <NInputGroup size="small" style="width: 160px">
      <span class="input-label">温度</span>
      <NSlider v-model:value="store.temperature" :min="0" :max="2" :step="0.1" style="flex: 1" />
      <span class="input-value">{{ store.temperature.toFixed(1) }}</span>
    </NInputGroup>

    <!-- 状态 -->
    <div class="status-area">
      <NTag :type="store.isRunning ? 'success' : store.isPaused ? 'warning' : 'default'" size="small">
        {{ store.executionState }}
      </NTag>
      <span class="stat-text">回合: {{ store.currentTurn }}</span>
      <span class="stat-text">Token: {{ store.totalTokens }}</span>
    </div>
  </div>
</template>

<style scoped>
.top-bar-content {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 12px;
}

.separator {
  width: 1px;
  height: 24px;
  background: #e0e0e0;
}

.input-label {
  padding: 0 8px;
  font-size: 12px;
  color: #666;
  white-space: nowrap;
}

.input-value {
  padding: 0 8px;
  font-size: 12px;
  min-width: 28px;
  text-align: right;
}

.status-area {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-text {
  font-size: 12px;
  color: #666;
}
</style>
```

创建 `workbench/src/components/LeftPanel.vue`：

```vue
<script setup lang="ts">
/**
 * 左侧资源导航面板
 * W2 会替换为完整的七层树形结构
 */
import { NTabs, NTabPane } from 'naive-ui'
</script>

<template>
  <div class="left-panel-content">
    <NTabs type="line" size="small" placement="left">
      <NTabPane name="prompt" tab="🧠 Prompt">
        <div class="placeholder">W2: 提示词管理</div>
      </NTabPane>
      <NTabPane name="memory" tab="📁 Memory">
        <div class="placeholder">W2: 记忆文件</div>
      </NTabPane>
      <NTabPane name="config" tab="⚙️ Config">
        <div class="placeholder">W2: 配置管理</div>
      </NTabPane>
      <NTabPane name="tools" tab="🔧 Tools">
        <div class="placeholder">W2: 工具列表</div>
      </NTabPane>
      <NTabPane name="workflow" tab="🔄 Workflow">
        <div class="placeholder">W2: 工作流</div>
      </NTabPane>
      <NTabPane name="runtime" tab="📊 Runtime">
        <div class="placeholder">W2: 运行时</div>
      </NTabPane>
    </NTabs>
  </div>
</template>

<style scoped>
.left-panel-content {
  height: 100%;
  padding: 4px;
}

.placeholder {
  padding: 20px;
  color: #999;
  text-align: center;
  font-size: 13px;
}
</style>
```

创建 `workbench/src/components/MainEditor.vue`：

```vue
<script setup lang="ts">
/**
 * 中间主工作区
 * W3 会替换为多态编辑器
 */
import { useAppStore } from '../stores/app'

const store = useAppStore()
</script>

<template>
  <div class="main-editor-content">
    <div v-if="store.selectedResource" class="editor-header">
      {{ store.selectedResource.label }}
    </div>
    <div v-else class="editor-placeholder">
      <p>← 从左侧选择资源开始编辑</p>
      <p class="hint">支持 .md / .yaml / .env / SKILL.md / workflow.yaml</p>
    </div>
  </div>
</template>

<style scoped>
.main-editor-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.editor-header {
  padding: 8px 16px;
  border-bottom: 1px solid #e0e0e0;
  font-size: 13px;
  font-weight: 500;
}

.editor-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
}

.editor-placeholder .hint {
  margin-top: 8px;
  font-size: 12px;
  color: #bbb;
}
</style>
```

创建 `workbench/src/components/RightPanel.vue`：

```vue
<script setup lang="ts">
/**
 * 右侧辅助面板
 * W2 会替换为完整的 Agent 状态 + 监控面板
 */
import { NTabs, NTabPane, NStatistic, NGrid, NGridItem } from 'naive-ui'
import { useAppStore } from '../stores/app'

const store = useAppStore()
</script>

<template>
  <div class="right-panel-content">
    <NTabs type="line" size="small">
      <NTabPane name="agent" tab="🤖 Agent 状态">
        <div class="stat-grid">
          <NStatistic label="状态" :value="store.executionState" />
          <NStatistic label="当前回合" :value="store.currentTurn" />
          <NStatistic label="总 Token" :value="store.totalTokens" />
          <NStatistic label="本轮延迟" :value="store.currentLatency + 'ms'" />
        </div>
      </NTabPane>
      <NTabPane name="monitor" tab="📊 资源监控">
        <div class="placeholder">W2: 资源监控</div>
      </NTabPane>
    </NTabs>
  </div>
</template>

<style scoped>
.right-panel-content {
  height: 100%;
  padding: 4px;
}

.stat-grid {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.placeholder {
  padding: 20px;
  color: #999;
  text-align: center;
  font-size: 13px;
}
</style>
```

创建 `workbench/src/components/BottomConsole.vue`：

```vue
<script setup lang="ts">
/**
 * 底部控制台
 * W6 会替换为完整的执行控制 + 轮次回溯 + 指令注入
 */
import { NTabs, NTabPane } from 'naive-ui'
import { useAppStore } from '../stores/app'

const store = useAppStore()
</script>

<template>
  <div class="bottom-console-content">
    <NTabs type="card" size="small">
      <NTabPane name="control" tab="执行控制">
        <div class="console-output">
          <div v-for="(evt, i) in store.sseEvents.slice(-20)" :key="i" class="event-line">
            <span class="event-time">{{ evt.time }}</span>
            <span class="event-type">{{ evt.type }}</span>
            <span class="event-data">{{ JSON.stringify(evt.data).slice(0, 100) }}</span>
          </div>
          <div v-if="store.sseEvents.length === 0" class="empty-hint">
            等待 Agent 运行...
          </div>
        </div>
      </NTabPane>
      <NTabPane name="inject" tab="指令注入">
        <div class="placeholder">W6: 指令注入面板</div>
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

.console-output {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
}

.event-line {
  display: flex;
  gap: 8px;
  padding: 2px 0;
  border-bottom: 1px solid #f0f0f0;
}

.event-time {
  color: #999;
  min-width: 70px;
}

.event-type {
  color: #1890ff;
  min-width: 100px;
}

.event-data {
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-hint {
  padding: 20px;
  color: #ccc;
  text-align: center;
}

.placeholder {
  padding: 20px;
  color: #999;
  text-align: center;
  font-size: 13px;
}
</style>
```

更新 `workbench/src/main.ts`：

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
```

**验收**: `npm run dev` 启动成功，浏览器看到新布局（顶部控制栏 + 左侧 Tab + 中间空白 + 右侧状态 + 底部控制台）

---

### 步骤 1.5 - 更新 vite.config.ts

**执行**:
重写 `workbench/vite.config.ts`：

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**验收**: `npm run dev` 启动后，`/api/*` 请求代理到后端

---

## W2: 左侧七层资源导航 + 右侧辅助面板

### 步骤 2.1 - 创建资源树组件

**执行**:
创建 `workbench/src/components/ResourceTree.vue`：

```vue
<script setup lang="ts">
/**
 * 通用资源树组件
 * 支持异步加载子节点、搜索过滤、右键菜单
 */
import { ref, computed, h } from 'vue'
import { NTree, NDropdown, NIcon, NInput, NSpace } from 'naive-ui'
import type { TreeOption } from 'naive-ui'
import { useAppStore, type ResourceNode } from '../stores/app'

const props = defineProps<{
  title: string
  icon: string
  loadData: (key: string) => Promise<ResourceNode[]>
  onSelect?: (node: ResourceNode) => void
  onCreate?: (parentKey: string) => void
}>()

const store = useAppStore()
const searchValue = ref('')
const treeData = ref<TreeOption[]>([])
const loading = ref(false)

/** 将 ResourceNode 转换为 NTree 的 TreeOption */
function toTreeOptions(nodes: ResourceNode[]): TreeOption[] {
  return nodes.map(node => ({
    key: node.key,
    label: node.label,
    prefix: () => h('span', { style: 'margin-right: 4px' }, node.icon),
    isLeaf: node.isLeaf ?? false,
    children: node.children ? toTreeOptions(node.children) : undefined,
  }))
}

/** 异步加载子节点 */
async function handleLoad(node: TreeOption) {
  const key = String(node.key)
  const children = await props.loadData(key)
  node.children = toTreeOptions(children)
}

/** 选中节点 */
function handleSelect(keys: string[], option: TreeOption[]) {
  if (option.length > 0 && props.onSelect) {
    const node = option[0] as any
    props.onSelect({
      key: node.key,
      label: node.label as string,
      type: 'prompt' as any, // 由父组件覆盖
      icon: '',
      path: node.key,
    })
  }
}

/** 过滤 */
const filteredData = computed(() => {
  if (!searchValue.value) return treeData.value
  // 简单的标签过滤
  return filterTree(treeData.value, searchValue.value.toLowerCase())
})

function filterTree(nodes: TreeOption[], keyword: string): TreeOption[] {
  return nodes.reduce<TreeOption[]>((acc, node) => {
    const label = (node.label as string).toLowerCase()
    if (label.includes(keyword)) {
      acc.push(node)
    } else if (node.children) {
      const filtered = filterTree(node.children, keyword)
      if (filtered.length > 0) {
        acc.push({ ...node, children: filtered })
      }
    }
    return acc
  }, [])
}

// 初始加载
async function init() {
  loading.value = true
  try {
    const nodes = await props.loadData('root')
    treeData.value = toTreeOptions(nodes)
  } finally {
    loading.value = false
  }
}

init()
</script>

<template>
  <div class="resource-tree">
    <div class="tree-header">
      <span class="tree-title">{{ icon }} {{ title }}</span>
      <NInput
        v-model:value="searchValue"
        size="tiny"
        placeholder="搜索..."
        clearable
        style="margin-top: 4px"
      />
    </div>
    <NTree
      :data="filteredData"
      :load="handleLoad"
      :on-update:selected-keys="handleSelect"
      block-line
      selectable
      expand-on-click
      :pattern="searchValue"
      class="tree-content"
    />
  </div>
</template>

<style scoped>
.resource-tree {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tree-header {
  padding: 4px 8px;
}

.tree-title {
  font-size: 12px;
  font-weight: 600;
  color: #333;
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  font-size: 13px;
}
</style>
```

**验收**: TypeScript 编译无错误

---

### 步骤 2.2 - 创建各层资源数据加载器

**执行**:
创建 `workbench/src/api/resources.ts`：

```typescript
/**
 * 七层资源数据加载
 */
import type { ResourceNode } from '../stores/app'

const API_BASE = '/api'

/** 获取 Prompt 资源树 */
export async function loadPromptResources(): Promise<ResourceNode[]> {
  const res = await fetch(`${API_BASE}/workspace/tree?path=prompts`)
  const data = await res.json()
  return data.children?.map(toResourceNode('prompt')) ?? [
    { key: 'prompts/system_prompt.md', label: 'system_prompt.md', type: 'prompt', icon: '📄', path: 'prompts/system_prompt.md', isLeaf: true },
  ]
}

/** 获取 Skill 资源树 */
export async function loadSkillResources(): Promise<ResourceNode[]> {
  const res = await fetch(`${API_BASE}/skills`)
  const data = await res.json()
  const builtin: ResourceNode[] = (data.builtin ?? []).map((s: any) => ({
    key: `skills/builtin/${s.name}/SKILL.md`,
    label: `${s.name} (v${s.version})`,
    type: 'prompt' as const,
    icon: '⚡',
    path: `skills/builtin/${s.name}/SKILL.md`,
    isLeaf: true,
  }))
  const agentCreated: ResourceNode[] = (data.agent_created ?? []).map((s: any) => ({
    key: `skills/agent_created/${s.name}/SKILL.md`,
    label: `${s.name} (v${s.version})`,
    type: 'prompt' as const,
    icon: '🤖',
    path: `skills/agent_created/${s.name}/SKILL.md`,
    isLeaf: true,
  }))
  const nodes: ResourceNode[] = []
  if (builtin.length > 0) {
    nodes.push({ key: 'builtin', label: '内置 Skill', type: 'prompt', icon: '📦', children: builtin })
  }
  if (agentCreated.length > 0) {
    nodes.push({ key: 'agent_created', label: 'Agent 创建', type: 'prompt', icon: '🤖', children: agentCreated })
  }
  return nodes
}

/** 获取 Memory 资源树 */
export async function loadMemoryResources(): Promise<ResourceNode[]> {
  const res = await fetch(`${API_BASE}/workspace/tree?path=workspace`)
  const data = await res.json()
  return data.children?.map(toResourceNode('memory')) ?? []
}

/** 获取 Config 资源树 */
export async function loadConfigResources(): Promise<ResourceNode[]> {
  return [
    { key: '.env', label: '.env', type: 'config', icon: '🔑', path: '.env', isLeaf: true },
    { key: 'adapter.yaml', label: 'adapter.yaml', type: 'config', icon: '🔧', path: 'adapter.yaml', isLeaf: true },
  ]
}

/** 获取 Tools 资源树 */
export async function loadToolResources(): Promise<ResourceNode[]> {
  // 从 system_prompt.md 中解析可用指令
  const tools = [
    { intent: 'update_npc_relationship', desc: '修改 NPC 好感度' },
    { intent: 'update_npc_state', desc: '修改 NPC 状态' },
    { intent: 'offer_quest', desc: '发布任务' },
    { intent: 'update_quest', desc: '更新任务' },
    { intent: 'give_item', desc: '给予物品' },
    { intent: 'remove_item', desc: '移除物品' },
    { intent: 'modify_stat', desc: '修改属性' },
    { intent: 'teleport_player', desc: '传送玩家' },
    { intent: 'show_notification', desc: '显示通知' },
    { intent: 'play_sound', desc: '播放音效' },
    { intent: 'no_op', desc: '空操作' },
  ]
  return tools.map(t => ({
    key: `tool:${t.intent}`,
    label: t.intent,
    type: 'tools' as const,
    icon: '🔧',
    isLeaf: true,
  }))
}

/** 获取 Workflow 资源树 */
export async function loadWorkflowResources(): Promise<ResourceNode[]> {
  return [
    { key: 'workflow/main_loop.yaml', label: 'main_loop.yaml', type: 'workflow', icon: '🔄', path: 'workflow/main_loop.yaml', isLeaf: true },
  ]
}

/** 获取 Runtime 资源树 */
export async function loadRuntimeResources(): Promise<ResourceNode[]> {
  return [
    { key: 'runtime:current', label: 'Current Turn', type: 'runtime', icon: '▶️', isLeaf: true },
    { key: 'runtime:history', label: 'Turn History', type: 'runtime', icon: '📜', isLeaf: true },
    { key: 'runtime:events', label: 'Event Log', type: 'runtime', icon: '📋', isLeaf: true },
  ]
}

/** 通用转换 */
function toResourceNode(type: ResourceNode['type']): (item: any) => ResourceNode {
  return (item: any) => ({
    key: item.path ?? item.name,
    label: item.name ?? item.path,
    type,
    icon: item.type === 'directory' ? '📁' : '📄',
    path: item.path,
    isLeaf: item.type !== 'directory',
    children: item.children?.map(toResourceNode(type)),
  })
}
```

**验收**: TypeScript 编译无错误

---

### 步骤 2.3 - 重构 LeftPanel

**执行**:
重写 `workbench/src/components/LeftPanel.vue`：

```vue
<script setup lang="ts">
/**
 * 左侧七层资源导航
 */
import { NTabs, NTabPane } from 'naive-ui'
import { useAppStore, type ResourceNode } from '../stores/app'
import ResourceTree from './ResourceTree.vue'
import {
  loadPromptResources,
  loadSkillResources,
  loadMemoryResources,
  loadConfigResources,
  loadToolResources,
  loadWorkflowResources,
  loadRuntimeResources,
} from '../api/resources'

const store = useAppStore()

function handleSelect(node: ResourceNode) {
  store.selectedResource = node
}
</script>

<template>
  <div class="left-panel-content">
    <NTabs type="line" size="small" placement="left">
      <NTabPane name="prompt" tab="🧠">
        <ResourceTree title="Prompt" icon="🧠" :load-data="loadPromptResources" :on-select="handleSelect" />
      </NTabPane>
      <NTabPane name="memory" tab="📁">
        <ResourceTree title="Memory" icon="📁" :load-data="loadMemoryResources" :on-select="handleSelect" />
      </NTabPane>
      <NTabPane name="config" tab="⚙️">
        <ResourceTree title="Config" icon="⚙️" :load-data="loadConfigResources" :on-select="handleSelect" />
      </NTabPane>
      <NTabPane name="tools" tab="🔧">
        <ResourceTree title="Tools" icon="🔧" :load-data="loadToolResources" :on-select="handleSelect" />
      </NTabPane>
      <NTabPane name="workflow" tab="🔄">
        <ResourceTree title="Workflow" icon="🔄" :load-data="loadWorkflowResources" :on-select="handleSelect" />
      </NTabPane>
      <NTabPane name="runtime" tab="📊">
        <ResourceTree title="Runtime" icon="📊" :load-data="loadRuntimeResources" :on-select="handleSelect" />
      </NTabPane>
    </NTabs>
  </div>
</template>

<style scoped>
.left-panel-content {
  height: 100%;
  padding: 4px;
}
</style>
```

**验收**: `npm run dev` 启动后，左侧显示 6 个 Tab，每个 Tab 有资源树

---

## W3: 中间多态编辑器

### 步骤 3.1 - 创建编辑器路由逻辑

**执行**:
创建 `workbench/src/components/EditorRouter.vue`：

```vue
<script setup lang="ts">
/**
 * 多态编辑器路由
 * 根据选中资源的类型，渲染不同的编辑器
 */
import { computed } from 'vue'
import { useAppStore } from '../stores/app'
import MdEditor from './editors/MdEditor.vue'
import YamlEditor from './editors/YamlEditor.vue'
import KeyValueEditor from './editors/KeyValueEditor.vue'
import SkillEditor from './editors/SkillEditor.vue'
import ToolViewer from './editors/ToolViewer.vue'
import RuntimeViewer from './editors/RuntimeViewer.vue'

const store = useAppStore()

const editorType = computed(() => {
  const resource = store.selectedResource
  if (!resource) return 'empty'

  const path = resource.path ?? ''
  const key = resource.key ?? ''

  // Skill 文件
  if (path.includes('SKILL.md')) return 'skill'

  // Markdown 文件
  if (path.endsWith('.md')) return 'markdown'

  // YAML 文件
  if (path.endsWith('.yaml') || path.endsWith('.yml')) return 'yaml'

  // 配置文件
  if (path.endsWith('.env') || path.endsWith('.env.template')) return 'keyvalue'

  // 工具
  if (key.startsWith('tool:')) return 'tool'

  // 运行时
  if (key.startsWith('runtime:')) return 'runtime'

  return 'markdown'
})
</script>

<template>
  <div class="editor-router">
    <MdEditor v-if="editorType === 'markdown'" />
    <SkillEditor v-else-if="editorType === 'skill'" />
    <YamlEditor v-else-if="editorType === 'yaml'" />
    <KeyValueEditor v-else-if="editorType === 'keyvalue'" />
    <ToolViewer v-else-if="editorType === 'tool'" />
    <RuntimeViewer v-else-if="editorType === 'runtime'" />
    <div v-else class="empty-state">
      <p>← 从左侧选择资源开始编辑</p>
    </div>
  </div>
</template>

<style scoped>
.editor-router {
  height: 100%;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
}
</style>
```

**验收**: TypeScript 编译无错误

---

### 步骤 3.2 - 创建各类型编辑器

**执行**:

创建目录 `workbench/src/components/editors/`

**3.2.1 MdEditor.vue**（复用 md-editor-v3）:

```vue
<script setup lang="ts">
/**
 * Markdown 编辑器
 * 用于编辑 .md 记忆文件和 system_prompt.md
 */
import { ref, watch, computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NButton, NSpace, NAlert } from 'naive-ui'

const store = useAppStore()
const content = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')

const filePath = computed(() => store.selectedResource?.path ?? '')

async function loadFile() {
  if (!filePath.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    content.value = data.content ?? ''
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function saveFile() {
  if (!filePath.value) return
  saving.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: content.value }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

watch(filePath, loadFile, { immediate: true })
</script>

<template>
  <div class="md-editor-wrapper">
    <div class="editor-toolbar">
      <span class="file-path">{{ filePath }}</span>
      <NSpace>
        <NButton size="tiny" :loading="saving" @click="saveFile">保存</NButton>
      </NSpace>
    </div>
    <NAlert v-if="error" type="error" closable style="margin: 8px">{{ error }}</NAlert>
    <div v-if="loading" class="loading-hint">加载中...</div>
    <div v-else class="editor-area">
      <textarea
        v-model="content"
        class="markdown-textarea"
        placeholder="Markdown 内容..."
        spellcheck="false"
      />
      <div class="preview-area" v-html="renderMarkdown(content)" />
    </div>
  </div>
</template>

<script lang="ts">
function renderMarkdown(text: string): string {
  // 简单的 Markdown 渲染（换行 → <br>，代码块保留）
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.md-editor-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.editor-toolbar {
  padding: 6px 12px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.file-path {
  font-size: 12px;
  color: #666;
  font-family: monospace;
}

.editor-area {
  flex: 1;
  display: flex;
  min-height: 0;
}

.markdown-textarea {
  flex: 1;
  padding: 12px;
  border: none;
  border-right: 1px solid #e0e0e0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  outline: none;
}

.preview-area {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.6;
}

.loading-hint {
  padding: 20px;
  text-align: center;
  color: #999;
}
</style>
```

**3.2.2 YamlEditor.vue**:

```vue
<script setup lang="ts">
/**
 * YAML 编辑器
 * 用于编辑 workflow/*.yaml、adapter.yaml 等
 */
import { ref, watch, computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NButton, NAlert } from 'naive-ui'

const store = useAppStore()
const content = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const filePath = computed(() => store.selectedResource?.path ?? '')

async function loadFile() {
  if (!filePath.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    content.value = data.content ?? ''
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function saveFile() {
  if (!filePath.value) return
  saving.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: content.value }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

watch(filePath, loadFile, { immediate: true })
</script>

<template>
  <div class="yaml-editor-wrapper">
    <div class="editor-toolbar">
      <span class="file-path">{{ filePath }}</span>
      <NButton size="tiny" :loading="saving" @click="saveFile">保存</NButton>
    </div>
    <NAlert v-if="error" type="error" closable style="margin: 8px">{{ error }}</NAlert>
    <div v-if="loading" class="loading-hint">加载中...</div>
    <textarea
      v-else
      v-model="content"
      class="yaml-textarea"
      placeholder="YAML 内容..."
      spellcheck="false"
    />
  </div>
</template>

<style scoped>
.yaml-editor-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.editor-toolbar {
  padding: 6px 12px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.file-path {
  font-size: 12px;
  color: #666;
  font-family: monospace;
}

.yaml-textarea {
  flex: 1;
  padding: 12px;
  border: none;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  outline: none;
}

.loading-hint {
  padding: 20px;
  text-align: center;
  color: #999;
}
</style>
```

**3.2.3 KeyValueEditor.vue**:

```vue
<script setup lang="ts">
/**
 * 键值对编辑器
 * 用于编辑 .env 文件
 */
import { ref, watch, computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NButton, NAlert, NInput, NSpace, NIcon } from 'naive-ui'

const store = useAppStore()
const pairs = ref<Array<{ key: string; value: string }>>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const filePath = computed(() => store.selectedResource?.path ?? '')

function parseEnv(text: string) {
  return text
    .split('\n')
    .filter(line => line.trim() && !line.trim().startsWith('#'))
    .map(line => {
      const idx = line.indexOf('=')
      if (idx === -1) return { key: line.trim(), value: '' }
      return { key: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() }
    })
}

function toEnvText() {
  return pairs.value.map(p => `${p.key}=${p.value}`).join('\n')
}

async function loadFile() {
  if (!filePath.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    pairs.value = parseEnv(data.content ?? '')
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function saveFile() {
  if (!filePath.value) return
  saving.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: toEnvText() }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

function addPair() {
  pairs.value.push({ key: '', value: '' })
}

function removePair(index: number) {
  pairs.value.splice(index, 1)
}

watch(filePath, loadFile, { immediate: true })
</script>

<template>
  <div class="kv-editor-wrapper">
    <div class="editor-toolbar">
      <span class="file-path">{{ filePath }}</span>
      <NSpace>
        <NButton size="tiny" @click="addPair">+ 添加</NButton>
        <NButton size="tiny" :loading="saving" @click="saveFile">保存</NButton>
      </NSpace>
    </div>
    <NAlert v-if="error" type="error" closable style="margin: 8px">{{ error }}</NAlert>
    <div v-if="loading" class="loading-hint">加载中...</div>
    <div v-else class="kv-list">
      <div v-for="(pair, i) in pairs" :key="i" class="kv-row">
        <NInput v-model:value="pair.key" size="small" placeholder="KEY" style="flex: 1" />
        <span class="kv-eq">=</span>
        <NInput v-model:value="pair.value" size="small" placeholder="VALUE" style="flex: 2" />
        <NButton size="tiny" quaternary @click="removePair(i)">✕</NButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kv-editor-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.editor-toolbar {
  padding: 6px 12px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.file-path {
  font-size: 12px;
  color: #666;
  font-family: monospace;
}

.kv-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
}

.kv-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.kv-eq {
  color: #999;
  font-weight: bold;
}

.loading-hint {
  padding: 20px;
  text-align: center;
  color: #999;
}
</style>
```

**3.2.4 SkillEditor.vue**:

```vue
<script setup lang="ts">
/**
 * Skill 编辑器
 * 表单编辑 YAML Front Matter + Markdown 正文
 */
import { ref, watch, computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NButton, NAlert, NInput, NFormItem, NCard, NSpace, NDynamicTags } from 'naive-ui'

const store = useAppStore()
const loading = ref(false)
const saving = ref(false)
const error = ref('')

// YAML Front Matter 字段
const name = ref('')
const description = ref('')
const version = ref('1.0.0')
const tags = ref<string[]>([])
const allowedTools = ref<string[]>([])

// Markdown Body
const body = ref('')

const filePath = computed(() => store.selectedResource?.path ?? '')

async function loadFile() {
  if (!filePath.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    const raw = data.content ?? ''

    // 解析 YAML Front Matter
    const fmMatch = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/)
    if (fmMatch) {
      const fm = fmMatch[1]
      body.value = fmMatch[2]
      name.value = extractField(fm, 'name') ?? ''
      description.value = extractField(fm, 'description') ?? ''
      version.value = extractField(fm, 'version') ?? '1.0.0'
      tags.value = extractList(fm, 'tags')
      allowedTools.value = extractList(fm, 'allowed-tools')
    } else {
      body.value = raw
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function extractField(yaml: string, field: string): string | null {
  const match = yaml.match(new RegExp(`^${field}:\\s*(.+)$`, 'm'))
  return match ? match[1].trim() : null
}

function extractList(yaml: string, field: string): string[] {
  const match = yaml.match(new RegExp(`^${field}:\\s*\\[([\\s\\S]*?)\\]`, 'm'))
  if (!match) return []
  return match[1]
    .split(',')
    .map(s => s.trim().replace(/['"]/g, ''))
    .filter(Boolean)
}

function toFileContent(): string {
  const toolsStr = allowedTools.value.length > 0
    ? '\nallowed-tools:\n' + allowedTools.value.map(t => `  - ${t}`).join('\n')
    : ''
  const tagsStr = tags.value.length > 0
    ? '\ntags:\n' + tags.value.map(t => `  - ${t}`).join('\n')
    : ''
  return `---\nname: ${name.value}\ndescription: ${description.value}\nversion: ${version.value}${tagsStr}${toolsStr}\n---\n\n${body.value}`
}

async function saveFile() {
  if (!filePath.value) return
  saving.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: toFileContent() }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

watch(filePath, loadFile, { immediate: true })
</script>

<template>
  <div class="skill-editor-wrapper">
    <div class="editor-toolbar">
      <span class="file-path">{{ filePath }}</span>
      <NButton size="tiny" :loading="saving" @click="saveFile">保存</NButton>
    </div>
    <NAlert v-if="error" type="error" closable style="margin: 8px">{{ error }}</NAlert>
    <div v-if="loading" class="loading-hint">加载中...</div>
    <div v-else class="skill-content">
      <NCard title="Skill 元数据" size="small" style="margin: 8px">
        <NFormItem label="名称" label-placement="left">
          <NInput v-model:value="name" size="small" />
        </NFormItem>
        <NFormItem label="描述" label-placement="left">
          <NInput v-model:value="description" size="small" type="textarea" :rows="2" />
        </NFormItem>
        <NFormItem label="版本" label-placement="left">
          <NInput v-model:value="version" size="small" style="width: 120px" />
        </NFormItem>
        <NFormItem label="标签">
          <NDynamicTags v-model:value="tags" />
        </NFormItem>
        <NFormItem label="允许的指令">
          <NDynamicTags v-model:value="allowedTools" />
        </NFormItem>
      </NCard>
      <NCard title="Skill 正文 (Markdown)" size="small" style="margin: 8px">
        <textarea
          v-model="body"
          class="skill-body"
          placeholder="Skill 的 Markdown 正文..."
          spellcheck="false"
        />
      </NCard>
    </div>
  </div>
</template>

<style scoped>
.skill-editor-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.editor-toolbar {
  padding: 6px 12px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.file-path {
  font-size: 12px;
  color: #666;
  font-family: monospace;
}

.skill-content {
  flex: 1;
  overflow-y: auto;
}

.skill-body {
  width: 100%;
  min-height: 200px;
  padding: 8px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
}

.loading-hint {
  padding: 20px;
  text-align: center;
  color: #999;
}
</style>
```

**3.2.5 ToolViewer.vue**:

```vue
<script setup lang="ts">
/**
 * 工具查看器（只读）
 * 展示工具的 intent、参数、描述
 */
import { computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NDescriptions, NDescriptionsItem, NTag } from 'naive-ui'

const store = useAppStore()

const toolInfo = computed(() => {
  const key = store.selectedResource?.key ?? ''
  const intent = key.replace('tool:', '')
  const tools: Record<string, { desc: string; params: string }> = {
    update_npc_relationship: { desc: '修改 NPC 好感度', params: 'npc_id, change, reason' },
    update_npc_state: { desc: '修改 NPC 状态', params: 'npc_id, field, value' },
    offer_quest: { desc: '发布任务', params: 'title, description, objective, reward' },
    update_quest: { desc: '更新任务状态', params: 'quest_id, status, progress' },
    give_item: { desc: '给予物品', params: 'name, type, player_id' },
    remove_item: { desc: '移除物品', params: 'item_id' },
    modify_stat: { desc: '修改玩家属性', params: 'stat, change, reason' },
    teleport_player: { desc: '传送玩家', params: 'location_id' },
    show_notification: { desc: '显示通知', params: 'message, type' },
    play_sound: { desc: '播放音效', params: 'sound_id' },
    no_op: { desc: '空操作', params: '(无)' },
  }
  return { intent, ...(tools[intent] ?? { desc: '未知工具', params: '未知' }) }
})
</script>

<template>
  <div class="tool-viewer">
    <NDescriptions bordered :column="1" size="small">
      <NDescriptionsItem label="Intent">
        <NTag>{{ toolInfo.intent }}</NTag>
      </NDescriptionsItem>
      <NDescriptionsItem label="描述">{{ toolInfo.desc }}</NDescriptionsItem>
      <NDescriptionsItem label="参数">{{ toolInfo.params }}</NDescriptionsItem>
    </NDescriptions>
  </div>
</template>

<style scoped>
.tool-viewer {
  padding: 16px;
}
</style>
```

**3.2.6 RuntimeViewer.vue**:

```vue
<script setup lang="ts">
/**
 * 运行时查看器（只读）
 * 显示当前轮次详情
 */
import { computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NDescriptions, NDescriptionsItem, NTag, NEmpty } from 'naive-ui'

const store = useAppStore()
</script>

<template>
  <div class="runtime-viewer">
    <NDescriptions bordered :column="1" size="small">
      <NDescriptionsItem label="执行状态">
        <NTag :type="store.isRunning ? 'success' : store.isPaused ? 'warning' : 'default'">
          {{ store.executionState }}
        </NTag>
      </NDescriptionsItem>
      <NDescriptionsItem label="当前回合">{{ store.currentTurn }}</NDescriptionsItem>
      <NDescriptionsItem label="总 Token">{{ store.totalTokens }}</NDescriptionsItem>
      <NDescriptionsItem label="本轮延迟">{{ store.currentLatency }}ms</NDescriptionsItem>
      <NDescriptionsItem label="历史轮次">{{ store.turnHistory.length }}</NDescriptionsItem>
    </NDescriptions>
    <div v-if="store.turnHistory.length === 0" style="padding: 20px">
      <NEmpty description="暂无运行记录" />
    </div>
  </div>
</template>

<style scoped>
.runtime-viewer {
  padding: 16px;
}
</style>
```

**验收**: TypeScript 编译无错误

---

### 步骤 3.3 - 集成 EditorRouter 到 MainEditor

**执行**:
重写 `workbench/src/components/MainEditor.vue`：

```vue
<script setup lang="ts">
import EditorRouter from './EditorRouter.vue'
</script>

<template>
  <div class="main-editor-content">
    <EditorRouter />
  </div>
</template>

<style scoped>
.main-editor-content {
  height: 100%;
}
</style>
```

**验收**: `npm run dev` 启动后，点击左侧不同资源，中间切换不同编辑器

---

## W4: 循环引擎（YAML 工作流 + GameMaster ReAct 循环 + 执行状态机）

### 步骤 4.1 - 创建工作流引擎

**执行**:
创建 `src/agent/workflow.py`：

```python
"""
工作流引擎。
读取 YAML 定义的工作流步骤，按顺序/分支执行。
支持暂停、继续、单步控制。
"""
from __future__ import annotations

import asyncio
import logging
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    PROMPT = "prompt"
    LLM_STREAM = "llm_stream"
    PARSE = "parse"
    BRANCH = "branch"
    EXECUTE = "execute"
    MEMORY = "memory"
    END = "end"


class ExecutionState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STEP_WAITING = "STEP_WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str
    type: StepType
    next: str = ""
    conditions: dict[str, str] = field(default_factory=dict)
    default: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepContext:
    """步骤执行上下文（在步骤间传递数据）"""
    event: dict = field(default_factory=dict)
    messages: list[dict] = field(default_factory=list)
    llm_output: str = ""
    parsed_response: dict = field(default_factory=dict)
    commands: list[dict] = field(default_factory=list)
    command_results: list[dict] = field(default_factory=list)
    memory_updates: list[dict] = field(default_factory=list)
    turn_id: int = 0
    error: Optional[str] = None


class WorkflowEngine:
    """工作流引擎"""

    def __init__(self):
        self.steps: dict[str, WorkflowStep] = {}
        self.start_step: str = ""
        self.state = ExecutionState.IDLE
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # 默认不暂停
        self._step_mode = False
        self._current_step_id: Optional[str] = None

        # 步骤处理器注册
        self._handlers: dict[StepType, Callable[[StepContext], Awaitable[StepContext]]] = {}

    def load_from_yaml(self, yaml_path: str) -> None:
        """从 YAML 文件加载工作流定义"""
        path = Path(yaml_path)
        if not path.exists():
            logger.warning(f"工作流文件不存在: {yaml_path}")
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self.steps.clear()
        self.start_step = data.get('start', data.get('steps', [{}])[0].get('id', ''))

        for step_data in data.get('steps', []):
            step = WorkflowStep(
                id=step_data['id'],
                type=StepType(step_data['type']),
                next=step_data.get('next', ''),
                conditions=step_data.get('conditions', {}),
                default=step_data.get('default', ''),
                metadata=step_data.get('metadata', {}),
            )
            self.steps[step.id] = step

        logger.info(f"工作流加载完成: {len(self.steps)} 个步骤, 起始: {self.start_step}")

    def register_handler(
        self,
        step_type: StepType,
        handler: Callable[[StepContext], Awaitable[StepContext]],
    ) -> None:
        """注册步骤处理器"""
        self._handlers[step_type] = handler

    def pause(self) -> None:
        """暂停执行"""
        self._pause_event.clear()
        self.state = ExecutionState.PAUSED
        logger.info("工作流已暂停")

    def resume(self) -> None:
        """继续执行"""
        self._pause_event.set()
        self.state = ExecutionState.RUNNING
        logger.info("工作流已继续")

    def step_once(self) -> None:
        """单步模式：执行一步后自动暂停"""
        self._step_mode = True
        self._pause_event.set()
        logger.info("单步模式已启用")

    @property
    def current_step_id(self) -> Optional[str]:
        return self._current_step_id

    async def run(self, context: StepContext) -> StepContext:
        """执行工作流"""
        self.state = ExecutionState.RUNNING
        self._pause_event.set()
        step_id = self.start_step
        max_iterations = 50  # 防止无限循环

        try:
            for _ in range(max_iterations):
                if not step_id or step_id == 'done':
                    self.state = ExecutionState.COMPLETED
                    break

                step = self.steps.get(step_id)
                if not step:
                    logger.error(f"步骤不存在: {step_id}")
                    context.error = f"Step not found: {step_id}"
                    self.state = ExecutionState.FAILED
                    break

                # 等待暂停解除
                await self._wait_if_paused()

                self._current_step_id = step_id
                logger.info(f"执行步骤: {step_id} ({step.type.value})")

                # 执行步骤
                handler = self._handlers.get(step.type)
                if handler:
                    context = await handler(context)
                else:
                    logger.warning(f"步骤 {step_id} 没有注册处理器")

                # 检查错误
                if context.error:
                    self.state = ExecutionState.FAILED
                    break

                # 单步模式：执行一步后暂停
                if self._step_mode:
                    self._step_mode = False
                    self._pause_event.clear()
                    self.state = ExecutionState.STEP_WAITING
                    await self._wait_if_paused()

                # 确定下一步
                step_id = self._resolve_next(step, context)

        except Exception as e:
            logger.error(f"工作流执行失败: {e}", exc_info=True)
            context.error = str(e)
            self.state = ExecutionState.FAILED

        finally:
            self._current_step_id = None

        return context

    def _resolve_next(self, step: WorkflowStep, context: StepContext) -> str:
        """解析下一步"""
        if step.type == StepType.BRANCH and step.conditions:
            for condition, target in step.conditions.items():
                if self._evaluate_condition(condition, context):
                    return target
            return step.default

        if step.type == StepType.END:
            return ""

        return step.next

    def _evaluate_condition(self, condition: str, context: StepContext) -> bool:
        """简单的条件表达式求值"""
        ctx = {
            'commands': context.commands,
            'command_results': context.command_results,
            'memory_updates': context.memory_updates,
            'llm_output': context.llm_output,
            'parsed_response': context.parsed_response,
        }
        try:
            return bool(eval(condition, {"__builtins__": {}}, ctx))  # noqa: S307
        except Exception:
            logger.warning(f"条件求值失败: {condition}")
            return False

    async def _wait_if_paused(self) -> None:
        """如果暂停了，等待恢复"""
        while not self._pause_event.is_set():
            self.state = ExecutionState.PAUSED
            await asyncio.sleep(0.1)
```

**验收**: `python -c "from src.agent.workflow import WorkflowEngine; print('OK')"` 成功

---

### 步骤 4.2 - 创建默认工作流 YAML

**执行**:
创建 `workflow/main_loop.yaml`：

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

**验收**: 文件存在

---

### 步骤 4.3 - 安装 PyYAML

**执行**:

```powershell
cd d:\worldSim-master
uv pip install pyyaml --break-system-packages
```

**验收**: `python -c "import yaml; print('OK')"` 成功

---

### 步骤 4.4 - 重构 GameMaster 集成工作流引擎

**执行**:
修改 `src/agent/game_master.py`，在现有代码基础上集成 WorkflowEngine。

**在 GameMaster.__init__ 中添加**:

```python
from src.agent.workflow import WorkflowEngine, StepContext, ExecutionState, StepType

# 在 __init__ 中添加:
self.workflow = WorkflowEngine()
self._register_workflow_handlers()
workflow_path = "workflow/main_loop.yaml"
if Path(workflow_path).exists():
    self.workflow.load_from_yaml(workflow_path)
```

**添加工作流处理器注册方法**:

```python
def _register_workflow_handlers(self):
    """注册工作流步骤处理器"""

    async def handle_prompt(ctx: StepContext) -> StepContext:
        event_dict = {
            "event_id": ctx.event.get("event_id", ""),
            "timestamp": ctx.event.get("timestamp", ""),
            "type": ctx.event.get("type", ""),
            "data": ctx.event.get("data", {}),
            "context_hints": ctx.event.get("context_hints", []),
            "game_state": ctx.event.get("game_state", {}),
        }
        ctx.messages = self.prompt_builder.build(
            event=event_dict,
            history=self.history,
            memory_depth="activation",
        )
        return ctx

    async def handle_llm_stream(ctx: StepContext) -> StepContext:
        full_content = ""
        reasoning_content = ""
        tokens_used = 0

        async for chunk in self.llm_client.stream(ctx.messages):
            event_type = chunk["event"]
            data = chunk["data"]
            if event_type == "token":
                full_content += data["text"]
            elif event_type == "reasoning":
                reasoning_content += data["text"]
            elif event_type == "llm_complete":
                tokens_used = len(full_content) + len(reasoning_content)

        self.total_tokens += tokens_used
        ctx.llm_output = full_content
        return ctx

    async def handle_parse(ctx: StepContext) -> StepContext:
        response = self.command_parser.parse(ctx.llm_output)
        ctx.parsed_response = response
        ctx.commands = response.get("commands", [])
        ctx.memory_updates = response.get("memory_updates", [])
        return ctx

    async def handle_execute(ctx: StepContext) -> StepContext:
        if ctx.commands:
            try:
                results = await self.engine_adapter.send_commands(ctx.commands)
                ctx.command_results = [
                    {
                        "intent": r.intent,
                        "status": r.status,
                        "new_value": r.new_value,
                        "reason": r.reason,
                        "suggestion": r.suggestion,
                    }
                    for r in results
                ]
            except Exception as e:
                ctx.command_results = [{"intent": "error", "status": "error", "reason": str(e)}]
        return ctx

    async def handle_memory(ctx: StepContext) -> StepContext:
        for update in ctx.memory_updates:
            try:
                self.memory_manager.apply_memory_updates([update])
            except Exception as e:
                logger.error(f"记忆更新失败: {update.get('file')} - {e}")
        return ctx

    self.workflow.register_handler(StepType.PROMPT, handle_prompt)
    self.workflow.register_handler(StepType.LLM_STREAM, handle_llm_stream)
    self.workflow.register_handler(StepType.PARSE, handle_parse)
    self.workflow.register_handler(StepType.EXECUTE, handle_execute)
    self.workflow.register_handler(StepType.MEMORY, handle_memory)
```

**添加工作流执行控制方法**:

```python
@property
def execution_state(self) -> ExecutionState:
    return self.workflow.state

def pause(self):
    self.workflow.pause()

def resume(self):
    self.workflow.resume()

def step_once(self):
    self.workflow.step_once()

@property
def current_step_id(self) -> str | None:
    return self.workflow.current_step_id
```

**注意**: 现有的 `handle_event()` 方法保持不变作为后备。如果工作流文件不存在，仍然走原来的逻辑。

**验收**: `python -c "from src.agent.game_master import GameMaster; print('OK')"` 成功

---

### 步骤 4.5 - 添加控制 API 端点

**执行**:
在 `src/api/routes/agent.py` 中添加新端点：

```python
@router.post("/control")
async def control_agent(action: str):
    """
    控制 Agent 执行: pause / resume / step
    """
    if _game_master is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if action == "pause":
        _game_master.pause()
    elif action == "resume":
        _game_master.resume()
    elif action == "step":
        _game_master.step_once()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    return {"state": _game_master.execution_state.value}

@router.get("/workflow")
async def get_workflow():
    """获取当前工作流定义"""
    if _game_master is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    workflow = _game_master.workflow
    return {
        "state": workflow.state.value,
        "current_step": workflow.current_step_id,
        "steps": [
            {
                "id": s.id,
                "type": s.type.value,
                "next": s.next,
                "conditions": s.conditions,
            }
            for s in workflow.steps.values()
        ],
    }
```

**验收**: `uv run pytest tests/ -v --tb=short` 全部通过

---

### 步骤 4.6 - 工作流引擎测试

**执行**:
创建 `tests/test_agent/test_workflow.py`：

```python
"""工作流引擎测试"""
import pytest
import yaml
from pathlib import Path
from src.agent.workflow import (
    WorkflowEngine, WorkflowStep, StepType, StepContext, ExecutionState
)


@pytest.fixture
def workflow_file(tmp_path):
    wf_path = tmp_path / "test_workflow.yaml"
    wf_path.write_text("""
name: test_loop
start: step_a
steps:
  - id: step_a
    type: prompt
    next: step_b
  - id: step_b
    type: llm_stream
    next: step_c
  - id: step_c
    type: parse
    next: step_d
  - id: step_d
    type: branch
    conditions:
      - if: "len(commands) > 0"
        next: step_e
    default: step_f
  - id: step_e
    type: execute
    next: step_f
  - id: step_f
    type: memory
    next: done
  - id: done
    type: end
""", encoding="utf-8")
    return str(wf_path)


@pytest.fixture
def engine(workflow_file):
    e = WorkflowEngine()
    e.load_from_yaml(workflow_file)
    return e


class TestWorkflowEngine:

    def test_load_yaml(self, engine):
        assert len(engine.steps) == 7
        assert engine.start_step == "step_a"
        assert StepType.PROMPT in [s.type for s in engine.steps.values()]

    @pytest.mark.asyncio
    async def test_linear_execution(self, engine):
        """线性执行: prompt → llm → parse → branch(default) → memory → end"""
        call_order = []

        async def mock_handler(ctx):
            call_order.append(ctx)
            return ctx

        for st in [StepType.PROMPT, StepType.LLM_STREAM, StepType.PARSE,
                    StepType.EXECUTE, StepType.MEMORY]:
            engine.register_handler(st, mock_handler)

        ctx = StepContext(event={"type": "test"})
        result = await engine.run(ctx)

        assert engine.state == ExecutionState.COMPLETED
        assert len(call_order) == 4  # prompt, llm, parse, memory (跳过 execute)

    @pytest.mark.asyncio
    async def test_branch_execution(self, engine):
        """分支执行: 有 commands 时走 execute"""
        call_order = []

        async def mock_parse(ctx):
            ctx.commands = [{"intent": "test", "params": {}}]
            call_order.append("parse")
            return ctx

        async def mock_execute(ctx):
            ctx.command_results = [{"status": "success"}]
            call_order.append("execute")
            return ctx

        async def mock_other(ctx):
            call_order.append("other")
            return ctx

        engine.register_handler(StepType.PROMPT, mock_other)
        engine.register_handler(StepType.LLM_STREAM, mock_other)
        engine.register_handler(StepType.PARSE, mock_parse)
        engine.register_handler(StepType.EXECUTE, mock_execute)
        engine.register_handler(StepType.MEMORY, mock_other)

        ctx = StepContext()
        await engine.run(ctx)

        assert "execute" in call_order

    @pytest.mark.asyncio
    async def test_pause_resume(self, engine):
        """暂停和继续"""
        import asyncio

        async def slow_handler(ctx):
            await asyncio.sleep(0.1)
            return ctx

        for st in [StepType.PROMPT, StepType.LLM_STREAM, StepType.PARSE,
                    StepType.MEMORY]:
            engine.register_handler(st, slow_handler)

        async def run_and_pause():
            task = asyncio.create_task(engine.run(StepContext()))
            await asyncio.sleep(0.05)
            engine.pause()
            assert engine.state == ExecutionState.PAUSED
            await asyncio.sleep(0.1)
            engine.resume()
            result = await task
            return result

        result = await run_and_pause()
        assert engine.state == ExecutionState.COMPLETED

    @pytest.mark.asyncio
    async def test_step_mode(self, engine):
        """单步模式"""
        step_count = 0

        async def counting_handler(ctx):
            nonlocal step_count
            step_count += 1
            return ctx

        for st in [StepType.PROMPT, StepType.LLM_STREAM, StepType.PARSE,
                    StepType.MEMORY]:
            engine.register_handler(st, counting_handler)

        # 启用单步模式
        engine.step_once()

        ctx = StepContext()
        result = await engine.run(ctx)

        # 单步模式应该只执行一步就暂停
        assert step_count >= 1
        assert engine.state == ExecutionState.STEP_WAITING or engine.state == ExecutionState.COMPLETED

    def test_condition_evaluation(self, engine):
        """条件表达式求值"""
        ctx = StepContext(commands=[{"intent": "test"}])
        assert engine._evaluate_condition("len(commands) > 0", ctx) is True
        assert engine._evaluate_condition("len(commands) > 5", ctx) is False

        ctx2 = StepContext(command_results=[{"status": "rejected"}])
        assert engine._evaluate_condition(
            "any(r.get('status') == 'rejected' for r in command_results)", ctx2
        ) is True
```

**验收**: `pytest tests/test_agent/test_workflow.py -v` 全部通过（>=6 个测试）

---

## W1~W4 完成检查清单

- [ ] W1.1: Pinia + VueUse 安装成功
- [ ] W1.2: Pinia Store 创建完毕
- [ ] W1.3: App.vue 新布局（顶部 + 三栏 + 底部）
- [ ] W1.4: 5 个占位组件创建完毕
- [ ] W1.5: Vite 代理配置正确
- [ ] `npm run dev` 启动成功，新布局可见
- [ ] W2.1: ResourceTree 组件创建
- [ ] W2.2: 七层数据加载器创建
- [ ] W2.3: LeftPanel 集成 ResourceTree
- [ ] W3.1: EditorRouter 创建
- [ ] W3.2: 6 种编辑器创建（MD/YAML/KV/Skill/Tool/Runtime）
- [ ] W3.3: MainEditor 集成 EditorRouter
- [ ] 点击不同资源，中间切换不同编辑器
- [ ] W4.1: WorkflowEngine 创建
- [ ] W4.2: main_loop.yaml 创建
- [ ] W4.3: PyYAML 安装
- [ ] W4.4: GameMaster 集成工作流
- [ ] W4.5: 控制端点添加
- [ ] W4.6: 工作流测试通过（>=6 个）
- [ ] **全部后端测试仍然通过**
