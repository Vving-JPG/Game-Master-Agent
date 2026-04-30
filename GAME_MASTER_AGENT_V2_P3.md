# Game Master Agent V2 - P3: WorkBench (Vue 前端)

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户将 V1 的 Game Master Agent **重构为 V2 通用游戏驱动 Agent**。
- **后端技术栈**: Python 3.11+ / DeepSeek API / FastAPI / SQLite / python-frontmatter
- **前端技术栈**: Vue 3 + TypeScript + Naive UI + Vite + md-editor-v3
- **包管理器**: uv (后端) / npm (前端)
- **开发IDE**: Trae

### 前置条件

**P2 已完成**。以下后端端点已就绪：
- `GET /api/workspace/tree` — 文件树
- `GET/PUT/POST/DELETE /api/workspace/file` — 文件 CRUD
- `GET /api/skills` — Skill 列表
- `GET/PUT /api/skills/{name}` — Skill 读取/更新
- `POST /api/skills` — Skill 创建
- `DELETE /api/skills/{name}` — Skill 删除
- `POST /api/agent/event` — 发送事件
- `GET /api/agent/status` — Agent 状态
- `GET /api/agent/context` — 当前上下文
- `POST /api/agent/reset` — 重置会话
- `GET /api/agent/stream` — SSE 实时事件流
- P0 + P1 + P2 全部测试通过（基线 **188+** 个）

### P3 阶段目标

1. **初始化 Vue 项目** — Vite + Vue3 + TS + Naive UI
2. **实现文件浏览器** — Naive UI Tree + 异步加载
3. **实现 MD 编辑器** — md-editor-v3 + YAML Front Matter 面板
4. **实现 Agent 监控面板** — 轮询状态 + token 用量
5. **实现 SSE 事件流** — EventSource 实时日志
6. **实现对话调试** — 手动发送事件 + 查看回复
7. **整体布局** — 三栏式 NLayout
8. **前后端联调** — Vite proxy → FastAPI

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行，每完成一步都验证通过后再进行下一步
2. **先验证再继续**：每个步骤都有"验收标准"，必须验证通过才能继续
3. **主动执行**：用户说"开始"后，你应该主动执行每一步，不需要用户反复催促
4. **遇到错误先尝试解决**：如果某步出错，先尝试自行排查修复，3次失败后再询问用户
5. **每步完成后汇报**：完成一步后，简要汇报结果和下一步计划
6. **代码规范**：
   - TypeScript 严格模式
   - Vue 3 Composition API (`<script setup>`)
   - 组件文件使用 PascalCase 命名
   - 样式使用 `<style scoped>`
   - 所有 UI 文本使用中文
7. **不要跳步**：即使用户让你跳过，也要提醒风险后再决定
8. **不修改后端代码**：P3 只创建前端项目，不修改后端 Python 代码

## 参考设计文档

| 文档 | 内容 |
|------|------|
| `docs/workspace_design.md` | WorkBench UI 设计、组件代码参考、API 接口定义 |
| `docs/communication_protocol.md` | SSE 事件格式、API 端点定义 |

## V1 经验教训（必须遵守）

1. **npm 命令在 PowerShell 中正常使用**：`npm install`, `npm run dev` 等都可用
2. **Vite proxy 配置**：前端开发服务器需要代理 `/api` 到后端 `http://localhost:8000`
3. **Naive UI Tree 异步加载**：使用 `on-load` prop，不要一次性加载全部节点
4. **md-editor-v3 样式**：必须 `import 'md-editor-v3/lib/style.css'`
5. **SSE 重连**：EventSource 浏览器原生支持自动重连，但需要处理错误状态
6. **中文文件名**：workspace 中的 .md 文件可能包含中文名，API 请求和响应都需要正确处理 UTF-8

---

## P3: WorkBench（共 8 步）

### 步骤 3.1 - 初始化 Vue 项目

**目的**: 搭建前端框架

**执行**:
1. 在项目根目录下创建 `workbench/` 目录
2. 初始化 Vite + Vue3 + TypeScript 项目
3. 安装依赖

**命令**:

```powershell
# 创建 workbench 目录
New-Item -ItemType Directory -Force -Path d:\worldSim-master\workbench

# 初始化 Vue 项目（在 workbench 目录内）
cd d:\worldSim-master\workbench
npm create vite@latest . -- --template vue-ts

# 安装依赖
npm install

# 安装 UI 库和工具
npm install naive-ui @vicons/ionicons5 axios md-editor-v3
npm install -D @types/node
```

**配置 Vite 代理**:

创建/替换 `workbench/vite.config.ts`：

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

**配置 tsconfig 路径别名**:

在 `workbench/tsconfig.json` 的 `compilerOptions` 中添加：

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

**验收**: `cd workbench ; npm run dev` 启动成功，浏览器访问 `http://localhost:5173` 看到 Vue 欢迎页

---

### 步骤 3.2 - 实现文件浏览器 FileTree.vue

**目的**: 浏览 workspace 目录，点击打开文件

**设计参考**: `docs/workspace_design.md` 第 4.1 节

**执行**:
1. 创建 `workbench/src/components/FileTree.vue`
2. 创建 `workbench/src/api/workspace.ts`

**workspace.ts 完整代码**:

```typescript
/**
 * Workspace 文件 API
 */
import axios from 'axios'

export interface TreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  size: number | null
}

export interface FileContent {
  frontmatter: Record<string, any>
  content: string
  raw: string
}

export async function getTree(path: string = ''): Promise<TreeNode[]> {
  const { data } = await axios.get('/api/workspace/tree', { params: { path } })
  return data.children
}

export async function getFile(path: string): Promise<FileContent> {
  const { data } = await axios.get('/api/workspace/file', { params: { path } })
  return data
}

export async function updateFile(path: string, body: {
  frontmatter?: Record<string, any>
  content?: string
  raw?: string
}): Promise<void> {
  await axios.put('/api/workspace/file', { path, ...body })
}

export async function createFile(path: string, content: string): Promise<void> {
  await axios.post('/api/workspace/file', { path, content })
}

export async function deleteFile(path: string): Promise<void> {
  await axios.delete('/api/workspace/file', { params: { path } })
}
```

**FileTree.vue 完整代码**:

```vue
<template>
  <div class="file-tree">
    <n-input
      v-model:value="searchPattern"
      placeholder="搜索文件..."
      clearable
      size="small"
      style="margin-bottom: 8px"
    >
      <template #prefix>
        <n-icon size="14"><SearchOutline /></n-icon>
      </template>
    </n-input>

    <n-tree
      ref="treeRef"
      block-line
      :data="treeData"
      :pattern="searchPattern"
      :on-load="handleLoad"
      :expanded-keys="expandedKeys"
      :selected-keys="selectedKeys"
      virtual-scroll
      :render-label="renderLabel"
      :render-prefix="renderPrefix"
      selectable
      style="height: calc(100vh - 160px)"
      @update:selected-keys="handleSelect"
      @update:expanded-keys="handleExpandedKeysChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NIcon, useMessage } from 'naive-ui'
import {
  SearchOutline,
  FolderOutline,
  FolderOpenOutline,
  DocumentTextOutline,
} from '@vicons/ionicons5'
import type { TreeOption } from 'naive-ui'
import { getTree, type TreeNode } from '@/api/workspace'

const emit = defineEmits<{
  (e: 'file-selected', path: string): void
}>()

const treeRef = ref<any>(null)
const searchPattern = ref('')
const expandedKeys = ref<string[]>(['workspace'])
const selectedKeys = ref<string[]>([])
const treeData = ref<TreeOption[]>([])
const message = useMessage()

// 初始化根节点
onMounted(async () => {
  try {
    const children = await getTree()
    treeData.value = children.map((item: TreeNode) => ({
      label: item.name,
      key: item.path,
      isLeaf: item.type === 'file',
    }))
  } catch (e) {
    message.error('加载文件树失败')
  }
})

// 异步加载子目录
async function handleLoad(node: TreeOption) {
  const path = node.key as string
  try {
    const children = await getTree(path)
    node.children = children.map((item: TreeNode) => ({
      label: item.name,
      key: item.path,
      isLeaf: item.type === 'file',
    }))
  } catch (e) {
    message.error(`加载 ${path} 失败`)
  }
}

function renderLabel({ option }: { option: TreeOption }) {
  return option.label as string
}

function renderPrefix({ option }: { option: TreeOption }) {
  const isDir = !option.isLeaf
  const isExpanded = expandedKeys.value.includes(option.key as string)
  const IconComp = isDir
    ? (isExpanded ? FolderOpenOutline : FolderOutline)
    : DocumentTextOutline
  return h(NIcon, { size: 16, style: 'margin-right: 4px' }, {
    default: () => h(IconComp)
  })
}

function handleSelect(keys: string[]) {
  selectedKeys.value = keys
  if (keys.length > 0) {
    emit('file-selected', keys[0])
  }
}

function handleExpandedKeysChange(keys: string[]) {
  expandedKeys.value = keys
}
</script>

<style scoped>
.file-tree {
  padding: 8px;
}
</style>
```

**验收**: 组件可编译，`npm run build` 无错误

---

### 步骤 3.3 - 实现 MD 编辑器 MdEditor.vue

**目的**: 查看/编辑 .md 文件，支持 YAML Front Matter 编辑

**设计参考**: `docs/workspace_design.md` 第 5.1 节

**执行**:
创建 `workbench/src/components/MdEditor.vue`：

**完整代码**:

```vue
<template>
  <div class="md-editor-container">
    <n-space v-if="filePath" align="center" justify="space-between" style="margin-bottom: 8px">
      <n-text strong>{{ filePath }}</n-text>
      <n-space>
        <n-button size="small" @click="toggleMode">
          {{ mode === 'edit' ? '预览' : '编辑' }}
        </n-button>
        <n-button size="small" @click="handleSave" :loading="saving" type="primary">
          保存
        </n-button>
        <n-button size="small" @click="handleReload">
          刷新
        </n-button>
      </n-space>
    </n-space>

    <div v-if="!filePath" class="empty-state">
      <n-text depth="3">选择一个文件开始编辑</n-text>
    </div>

    <div v-else class="editor-wrapper">
      <MdEditor
        v-if="mode === 'edit'"
        v-model="content"
        :theme="theme"
        language="zh-CN"
        :style="{ height: 'calc(100vh - 280px)' }"
        @on-save="handleSave"
      />

      <MdPreview
        v-else
        :id="previewId"
        :modelValue="content"
        :theme="theme"
        language="zh-CN"
        :style="{ height: 'calc(100vh - 280px)', overflow: 'auto' }"
      />
    </div>

    <!-- YAML Front Matter 编辑面板 -->
    <n-collapse v-if="frontmatter && Object.keys(frontmatter).length > 0" style="margin-top: 8px">
      <n-collapse-item title="YAML Front Matter" name="fm">
        <n-form label-placement="left" label-width="120" size="small">
          <n-form-item v-for="(value, key) in frontmatter" :key="key" :label="String(key)">
            <n-input
              :value="String(frontmatter[key])"
              size="small"
              @update:value="updateFrontmatter(String(key), $event)"
            />
          </n-form-item>
        </n-form>
      </n-collapse-item>
    </n-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { MdEditor, MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { getFile, updateFile } from '@/api/workspace'

const props = defineProps<{
  filePath: string | null
}>()

const message = useMessage()
const content = ref('')
const frontmatter = ref<Record<string, any> | null>(null)
const saving = ref(false)
const dirty = ref(false)
const mode = ref<'edit' | 'preview'>('edit')
const theme = ref<'light' | 'dark'>('light')
const previewId = computed(() => `preview-${props.filePath}`)

async function loadFile(path: string) {
  try {
    const data = await getFile(path)
    content.value = data.content || ''
    frontmatter.value = data.frontmatter || null
    dirty.value = false
  } catch (e) {
    message.error('加载文件失败')
  }
}

async function handleSave() {
  if (!props.filePath) return
  saving.value = true
  try {
    await updateFile(props.filePath, {
      content: content.value,
      frontmatter: frontmatter.value || undefined,
    })
    dirty.value = false
    message.success('保存成功')
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleReload() {
  if (props.filePath) {
    await loadFile(props.filePath)
    message.info('已刷新')
  }
}

function toggleMode() {
  mode.value = mode.value === 'edit' ? 'preview' : 'edit'
}

function updateFrontmatter(key: string, value: string) {
  if (frontmatter.value) {
    frontmatter.value[key] = value
    dirty.value = true
  }
}

watch(() => props.filePath, (newPath) => {
  if (newPath) {
    loadFile(newPath)
  } else {
    content.value = ''
    frontmatter.value = null
  }
}, { immediate: true })
</script>

<style scoped>
.md-editor-container {
  height: 100%;
  padding: 8px;
}
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.editor-wrapper {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}
</style>
```

**验收**: 组件可编译，`npm run build` 无错误

---

### 步骤 3.4 - 实现 Agent 监控面板 AgentStatus.vue

**目的**: 显示 Agent 状态、token 用量、活跃 Skill

**设计参考**: `docs/workspace_design.md` 第 6.1 节

**执行**:
1. 创建 `workbench/src/api/agent.ts`
2. 创建 `workbench/src/components/AgentStatus.vue`

**agent.ts 完整代码**:

```typescript
/**
 * Agent 交互 API
 */
import axios from 'axios'

export interface AgentStatus {
  state: 'idle' | 'processing'
  turn_count: number
  total_tokens: number
  history_length: number
  current_event: string | null
}

export interface AgentContext {
  system_prompt: string
  system_prompt_length: number
  history_length: number
  active_skills: string[]
}

export async function getStatus(): Promise<AgentStatus> {
  const { data } = await axios.get('/api/agent/status')
  return data
}

export async function getContext(): Promise<AgentContext> {
  const { data } = await axios.get('/api/agent/context')
  return data
}

export async function resetSession(): Promise<void> {
  await axios.post('/api/agent/reset')
}

export async function sendEvent(event: {
  event_id: string
  timestamp: string
  type: string
  data: Record<string, any>
  context_hints?: string[]
  game_state?: Record<string, any>
}): Promise<any> {
  const { data } = await axios.post('/api/agent/event', event)
  return data
}
```

**AgentStatus.vue 完整代码**:

```vue
<template>
  <div class="agent-status">
    <n-card title="Agent 状态" size="small" :bordered="false">
      <n-space align="center" :size="8">
        <n-badge :type="statusColor" dot />
        <n-text>{{ statusText }}</n-text>
      </n-space>

      <n-descriptions :column="1" size="small" style="margin-top: 12px">
        <n-descriptions-item label="当前回合">
          {{ status.turn_count || 0 }}
        </n-descriptions-item>
        <n-descriptions-item label="Token 用量">
          {{ formatNumber(status.total_tokens || 0) }}
        </n-descriptions-item>
        <n-descriptions-item label="对话历史">
          {{ status.history_length || 0 }} 轮
        </n-descriptions-item>
        <n-descriptions-item label="当前事件">
          <n-text v-if="status.current_event" code>{{ status.current_event }}</n-text>
          <n-text v-else depth="3">无</n-text>
        </n-descriptions-item>
      </n-descriptions>
    </n-card>

    <n-space vertical style="margin-top: 8px">
      <n-button
        block
        size="small"
        @click="handleReset"
        type="warning"
      >
        重置会话
      </n-button>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import { getStatus, resetSession, type AgentStatus as AgentStatusType } from '@/api/agent'

const message = useMessage()
const status = ref<AgentStatusType>({
  state: 'idle',
  turn_count: 0,
  total_tokens: 0,
  history_length: 0,
  current_event: null,
})
let pollTimer: ReturnType<typeof setInterval> | null = null

const statusColor = computed(() => {
  return status.value.state === 'processing' ? 'success' : 'default'
})

const statusText = computed(() => {
  return status.value.state === 'processing' ? '处理中' : '空闲'
})

function formatNumber(n: number): string {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(n)
}

async function fetchStatus() {
  try {
    status.value = await getStatus()
  } catch {
    // 静默失败
  }
}

async function handleReset() {
  try {
    await resetSession()
    message.success('会话已重置')
    fetchStatus()
  } catch {
    message.error('重置失败')
  }
}

onMounted(() => {
  fetchStatus()
  pollTimer = setInterval(fetchStatus, 2000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.agent-status {
  padding: 4px;
}
</style>
```

**验收**: 组件可编译，`npm run build` 无错误

---

### 步骤 3.5 - 实现 SSE 事件流 SSEEventLog.vue

**目的**: 实时显示 Agent 的 token/command/turn 事件

**设计参考**: `docs/workspace_design.md` 第 6.2 节

**执行**:
创建 `workbench/src/components/SSEEventLog.vue`：

**完整代码**:

```vue
<template>
  <div class="sse-event-log">
    <n-card title="实时事件流" size="small" :bordered="false">
      <template #header-extra>
        <n-space align="center" :size="8">
          <n-tag :type="connected ? 'success' : 'error'" size="small">
            {{ connected ? '已连接' : '未连接' }}
          </n-tag>
          <n-button size="tiny" @click="clearEvents">清空</n-button>
        </n-space>
      </template>

      <div class="event-list" ref="listRef">
        <div
          v-for="(event, index) in events"
          :key="index"
          :class="['event-item', `event-${event.type}`]"
        >
          <span class="event-time">{{ event.time }}</span>
          <span class="event-type">{{ event.type }}</span>
          <span class="event-data">{{ formatData(event.data) }}</span>
        </div>
        <div v-if="events.length === 0" class="empty-hint">
          等待事件...
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface SSEEvent {
  type: string
  data: any
  time: string
}

const events = ref<SSEEvent[]>([])
const listRef = ref<HTMLElement | null>(null)
const connected = ref(false)
let eventSource: EventSource | null = null

function formatData(data: any): string {
  if (typeof data === 'string') return data
  if (data?.text) return data.text
  if (data?.intent) return `${data.intent}(${JSON.stringify(data.params || {}).slice(0, 50)})`
  if (data?.event_id) return `event_id: ${data.event_id}`
  if (data?.response_id) return `resp: ${data.response_id}`
  if (data?.stats) return `stats: ${data.stats.tokens_used || 0} tokens`
  return JSON.stringify(data).slice(0, 80)
}

function clearEvents() {
  events.value = []
}

function addEvent(type: string, data: any) {
  events.value.push({
    type,
    data,
    time: new Date().toLocaleTimeString(),
  })
  // 最多保留 200 条
  if (events.value.length > 200) {
    events.value = events.value.slice(-200)
  }
  scrollToBottom()
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

function connectSSE() {
  eventSource = new EventSource('/api/agent/stream?session_id=workbench')

  eventSource.onopen = () => {
    connected.value = true
  }

  eventSource.addEventListener('turn_start', (e) => {
    addEvent('turn_start', JSON.parse(e.data))
  })

  eventSource.addEventListener('token', (e) => {
    const data = JSON.parse(e.data)
    // 合并连续的 token 事件
    const last = events.value[events.value.length - 1]
    if (last?.type === 'token') {
      last.data.text += data.text
    } else {
      addEvent('token', data)
    }
  })

  eventSource.addEventListener('reasoning', (e) => {
    addEvent('reasoning', JSON.parse(e.data))
  })

  eventSource.addEventListener('command', (e) => {
    addEvent('command', JSON.parse(e.data))
  })

  eventSource.addEventListener('memory_update', (e) => {
    addEvent('memory_update', JSON.parse(e.data))
  })

  eventSource.addEventListener('command_rejected', (e) => {
    addEvent('rejected', JSON.parse(e.data))
  })

  eventSource.addEventListener('turn_end', (e) => {
    addEvent('turn_end', JSON.parse(e.data))
  })

  eventSource.addEventListener('error', (e) => {
    connected.value = false
    addEvent('error', { message: 'SSE 连接错误' })
  })
}

onMounted(() => {
  connectSSE()
})

onUnmounted(() => {
  eventSource?.close()
})
</script>

<style scoped>
.event-list {
  height: 250px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 4px;
  padding: 8px;
}
.event-item {
  padding: 2px 0;
  border-bottom: 1px solid #333;
}
.event-time {
  color: #6a9955;
  margin-right: 8px;
}
.event-type {
  color: #569cd6;
  margin-right: 8px;
  font-weight: bold;
  min-width: 80px;
  display: inline-block;
}
.event-token .event-data { color: #d4d4d4; }
.event-command .event-data { color: #dcdcaa; }
.event-turn_start .event-data,
.event-turn_end .event-data { color: #4ec9b0; }
.event-reasoning .event-data { color: #c586c0; }
.event-rejected .event-data { color: #f44747; }
.event-error .event-data { color: #f44747; }
.event-memory_update .event-data { color: #9cdcfe; }
.empty-hint {
  color: #666;
  text-align: center;
  padding: 20px;
}
</style>
```

**验收**: 组件可编译，`npm run build` 无错误

---

### 步骤 3.6 - 实现对话调试 ChatDebug.vue

**目的**: 手动发送事件，查看 Agent 回复

**设计参考**: `docs/workspace_design.md` 第 7.1 节

**执行**:
创建 `workbench/src/components/ChatDebug.vue`：

**完整代码**:

```vue
<template>
  <div class="chat-debug">
    <n-card title="对话调试" size="small" :bordered="false">
      <!-- 消息列表 -->
      <div class="message-list" ref="msgListRef">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', `message-${msg.role}`]"
        >
          <div class="message-role">{{ msg.role === 'user' ? '玩家' : 'Agent' }}</div>
          <div class="message-content">{{ msg.content }}</div>
          <div v-if="msg.commands?.length" class="message-commands">
            <n-tag v-for="cmd in msg.commands" :key="cmd.intent" size="tiny" type="info">
              {{ cmd.intent }}
            </n-tag>
          </div>
          <div v-if="msg.error" class="message-error">
            <n-text type="error">{{ msg.error }}</n-text>
          </div>
        </div>
        <div v-if="loading" class="message message-agent">
          <div class="message-role">Agent</div>
          <div class="message-content">
            <n-spin size="small" /> 思考中...
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <n-select
          v-model:value="eventType"
          :options="eventOptions"
          size="small"
          style="margin-bottom: 8px"
          placeholder="选择事件类型"
        />
        <n-input-group>
          <n-input
            v-model:value="inputText"
            placeholder="输入玩家操作 (如: 和铁匠聊聊)"
            @keyup.enter="sendMessage"
            :disabled="loading"
          />
          <n-button
            type="primary"
            @click="sendMessage"
            :loading="loading"
            :disabled="!inputText.trim()"
          >
            发送
          </n-button>
        </n-input-group>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import { sendEvent } from '@/api/agent'

const message = useMessage()
const inputText = ref('')
const eventType = ref('player_action')
const loading = ref(false)
const messages = ref<any[]>([])
const msgListRef = ref<HTMLElement | null>(null)

const eventOptions = [
  { label: 'player_action (玩家操作)', value: 'player_action' },
  { label: 'player_move (玩家移动)', value: 'player_move' },
  { label: 'combat_start (战斗开始)', value: 'combat_start' },
  { label: 'system_event (系统事件)', value: 'system_event' },
]

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true

  try {
    const data = await sendEvent({
      event_id: `debug_${Date.now()}`,
      timestamp: new Date().toISOString(),
      type: eventType.value,
      data: { raw_text: text, player_id: 'debug_player' },
      context_hints: [],
      game_state: {},
    })

    messages.value.push({
      role: 'agent',
      content: data.narrative || '(无叙事)',
      commands: data.commands || [],
    })
  } catch (e: any) {
    messages.value.push({
      role: 'agent',
      content: '',
      error: e.response?.data?.detail || e.message,
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    if (msgListRef.value) {
      msgListRef.value.scrollTop = msgListRef.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.message-list {
  height: 350px;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 8px;
}
.message {
  margin-bottom: 12px;
}
.message-role {
  font-size: 12px;
  font-weight: bold;
  margin-bottom: 4px;
}
.message-user .message-role { color: #1890ff; }
.message-agent .message-role { color: #52c41a; }
.message-content {
  padding: 8px 12px;
  border-radius: 4px;
  background: #f5f5f5;
  white-space: pre-wrap;
  word-break: break-word;
}
.message-user .message-content { background: #e6f7ff; }
.message-commands {
  margin-top: 4px;
}
.message-error {
  margin-top: 4px;
  padding: 4px 8px;
  background: #fff2f0;
  border-radius: 4px;
}
.input-area {
  margin-top: 4px;
}
</style>
```

**验收**: 组件可编译，`npm run build` 无错误

---

### 步骤 3.7 - 整体布局 App.vue

**目的**: 三栏式布局，整合所有组件

**设计参考**: `docs/workspace_design.md` 第 3 节

**执行**:
1. 替换 `workbench/src/App.vue`
2. 替换 `workbench/src/main.ts`（注册 Naive UI）
3. 删除默认的 `HelloWorld.vue` 等模板文件

**main.ts 完整代码**:

```typescript
import { createApp } from 'vue'
import { createDiscreteApi } from 'naive-ui'
import App from './App.vue'

const { message, notification, dialog } = createDiscreteApi(
  ['message', 'notification', 'dialog'],
  {
    configProviderProps: {
      // 全局配置
    },
  }
)

const app = createApp(App)
app.mount('#app')
```

**App.vue 完整代码**:

```vue
<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-layout has-sider style="height: 100vh">
            <!-- 左侧面板: 文件浏览器 -->
            <n-layout-sider
              :width="240"
              :collapsed-width="0"
              :collapsed="leftCollapsed"
              show-trigger="bar"
              collapse-mode="width"
              bordered
              :native-scrollbar="false"
              style="height: 100vh"
            >
              <div class="sider-header">
                <n-text strong>文件浏览器</n-text>
              </div>
              <FileTree @file-selected="handleFileSelected" />
            </n-layout-sider>

            <!-- 主内容区 -->
            <n-layout>
              <n-tabs v-model:value="activeTab" type="card" style="height: 100%">
                <!-- 编辑器 Tab -->
                <n-tab-pane name="editor" tab="编辑器">
                  <MdEditor :file-path="selectedFile" />
                </n-tab-pane>

                <!-- 对话调试 Tab -->
                <n-tab-pane name="chat" tab="对话调试">
                  <ChatDebug />
                </n-tab-pane>
              </n-tabs>
            </n-layout>

            <!-- 右侧面板: Agent 监控 -->
            <n-layout-sider
              :width="300"
              :collapsed-width="0"
              :collapsed="rightCollapsed"
              show-trigger="bar"
              collapse-mode="width"
              bordered
              position="right"
              :native-scrollbar="false"
              style="height: 100vh"
            >
              <n-scrollbar style="height: 100vh">
                <AgentStatus />
                <SSEEventLog />
              </n-scrollbar>
            </n-layout-sider>
          </n-layout>

          <!-- 底部状态栏 -->
          <n-layout-footer bordered style="height: 28px; line-height: 28px; padding: 0 16px; font-size: 12px">
            <n-space :size="16">
              <n-text depth="3">Game Master Agent WorkBench</n-text>
              <n-text depth="3">|</n-text>
              <n-text depth="3">后端: {{ backendStatus }}</n-text>
            </n-space>
          </n-layout-footer>
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NConfigProvider,
  NLayout,
  NLayoutSider,
  NLayoutFooter,
  NTabs,
  NTabPane,
  NScrollbar,
  NText,
  NSpace,
} from 'naive-ui'
import FileTree from '@/components/FileTree.vue'
import MdEditor from '@/components/MdEditor.vue'
import AgentStatus from '@/components/AgentStatus.vue'
import SSEEventLog from '@/components/SSEEventLog.vue'
import ChatDebug from '@/components/ChatDebug.vue'
import axios from 'axios'

const leftCollapsed = ref(false)
const rightCollapsed = ref(false)
const activeTab = ref('editor')
const selectedFile = ref<string | null>(null)
const backendStatus = ref('检测中...')

const themeOverrides = {
  common: {
    fontSize: '14px',
  },
}

function handleFileSelected(path: string) {
  selectedFile.value = path
  activeTab.value = 'editor'
}

onMounted(async () => {
  try {
    await axios.get('/api/agent/status', { timeout: 3000 })
    backendStatus.value = '已连接'
  } catch {
    backendStatus.value = '未连接'
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
html, body, #app {
  height: 100%;
  overflow: hidden;
}
.sider-header {
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
}
</style>
```

**清理默认模板文件**:

```powershell
# 删除 Vite 默认模板文件
Remove-Item -Force d:\worldSim-master\workbench\src\components\HelloWorld.vue -ErrorAction SilentlyContinue
Remove-Item -Force d:\worldSim-master\workbench\src\assets\vue.svg -ErrorAction SilentlyContinue
Remove-Item -Force d:\worldSim-master\workbench\src\style.css -ErrorAction SilentlyContinue
```

**验收**: `npm run dev` 启动成功，浏览器看到三栏布局，左侧文件树、中间编辑器/调试、右侧状态面板

---

### 步骤 3.8 - 前后端联调

**目的**: 验证前后端完整流程

**执行**:
1. 启动后端: `cd d:\worldSim-master ; uvicorn src.api.app:app --reload --port 8000`
2. 启动前端: `cd d:\worldSim-master\workbench ; npm run dev`
3. 验证以下流程：

**验证清单**:

- [ ] **文件浏览器**: 左侧面板显示 workspace 目录树，点击可展开子目录
- [ ] **文件编辑**: 点击 .md 文件，中间面板显示内容，可编辑并保存
- [ ] **YAML FM**: 编辑器下方显示 YAML Front Matter 字段，可修改
- [ ] **Agent 状态**: 右侧面板显示 Agent 状态（回合数、token 用量）
- [ ] **SSE 事件流**: 右侧面板显示实时事件日志（连接状态为"已连接"）
- [ ] **对话调试**: 切换到"对话调试"标签，输入文本发送，看到 Agent 回复
- [ ] **状态栏**: 底部显示"后端: 已连接"
- [ ] **`npm run build`**: 生产构建无错误

**常见问题排查**:

| 问题 | 原因 | 解决 |
|------|------|------|
| 文件树为空 | 后端未启动或路径错误 | 确认后端运行在 8000 端口 |
| SSE 显示"未连接" | 后端 Agent 未初始化 | 检查后端日志，确认 set_agent_refs 已调用 |
| 保存文件 404 | workspace 路径未设置 | 确认后端 set_workspace_path 已调用 |
| 中文乱码 | 编码问题 | 确认文件使用 UTF-8 编码 |

**验收**: 所有验证清单项通过，`npm run build` 无错误

---

## P3 完成检查清单

- [ ] Step 3.1: Vue 项目初始化 + 依赖安装 + Vite 代理配置
- [ ] Step 3.2: FileTree.vue 组件实现
- [ ] Step 3.3: MdEditor.vue 组件实现
- [ ] Step 3.4: AgentStatus.vue 组件实现
- [ ] Step 3.5: SSEEventLog.vue 组件实现
- [ ] Step 3.6: ChatDebug.vue 组件实现
- [ ] Step 3.7: App.vue 三栏布局 + main.ts 配置
- [ ] Step 3.8: 前后端联调全部通过
- [ ] `npm run build` 生产构建无错误
- [ ] 后端测试不受影响（188+ 个测试通过）
