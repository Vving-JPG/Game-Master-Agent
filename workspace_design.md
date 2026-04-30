# V2 Agent Workspace 与 WorkBench 设计

> **版本**: v2.0-draft
> **日期**: 2026-04-28
> **前置文档**: `architecture_v2.md`, `memory_system.md`
> **关联文档**: `skill_system.md`, `communication_protocol.md`
> **参考**: Trae Workspace, 腾讯 WorkBuddy, Cursor Agent Window

---

## 1. Workspace 概述

### 1.1 什么是 Agent Workspace？

Agent Workspace 是 Agent 的**工作空间**——一个磁盘目录，存放 Agent 的所有记忆文件、Skill 文件和配置。类似 Trae 的 workspace，人类可以直接浏览和编辑。

```
workspace/                    ← Agent Workspace 根目录
├── index.md                  ← 全局记忆索引
├── npcs/                     ← NPC 记忆
├── locations/                ← 地点记忆
├── story/                    ← 剧情记忆
├── quests/                   ← 任务记忆
├── items/                    ← 物品记忆
├── player/                   ← 玩家记忆
└── session/                  ← 会话记忆
```

### 1.2 Workspace vs SQLite

| 维度 | SQLite (引擎侧) | Workspace (Agent 侧) |
|------|----------------|---------------------|
| 用途 | 结构化数据存储 | Agent 认知和记忆 |
| 谁写入 | 引擎 (代码) | Agent (LLM) + 引擎 (YAML FM) |
| 谁读取 | 引擎 (代码) | Agent (LLM) + 人类 (WorkBench) |
| 格式 | 关系表 | .md 文件 |
| 可见性 | 需要 API | 直接打开文件 |

---

## 2. WorkBench 概述

### 2.1 什么是 WorkBench？

WorkBench 是一个 Vue 3 + Naive UI 的 Web 应用，用于**管理和监控 Agent**。参考 Trae Workspace + 腾讯 WorkBuddy 的设计。

### 2.2 核心功能

| 面板 | 功能 | 优先级 |
|------|------|--------|
| **文件浏览器** | 浏览 workspace 目录，查看/编辑 .md 文件 | P0 |
| **Agent 监控** | 实时查看 Agent 状态、上下文、token 用量 | P0 |
| **对话调试** | 手动发送事件，查看 Agent 响应 | P0 |
| **系统提示词** | 编辑 Agent 的 system prompt | P1 |
| **Skill 管理** | 查看/编辑/创建 Skill 文件 | P1 |
| **会话管理** | 查看/重置会话历史 | P2 |

### 2.3 技术选型

| 技术 | 选择 | 说明 |
|------|------|------|
| 框架 | Vue 3 + Composition API | 用户指定 |
| UI 库 | Naive UI | 用户指定 |
| 文件树 | Naive UI `<n-tree>` | 原生支持异步加载 + 虚拟滚动 |
| MD 编辑器 | md-editor-v3 | 2.2k stars，功能全面 |
| HTTP 客户端 | axios | 标准 |
| SSE 客户端 | EventSource API | 浏览器原生 |
| 构建工具 | Vite | Vue 3 标配 |
| 语言 | TypeScript | 类型安全 |

---

## 3. UI 布局设计

### 3.1 整体布局

参考 Trae 的三栏式布局：

```
┌─────────────────────────────────────────────────────────────────────┐
│  WorkBench - 通用游戏驱动 Agent 管理端                               │
├──────────┬──────────────────────────────────┬───────────────────────┤
│          │                                  │                       │
│  文件    │        主内容区                   │    Agent 监控面板      │
│  浏览器  │                                  │                       │
│          │  ┌──────────────────────────┐    │  ┌─────────────────┐  │
│  ┌────┐  │  │                          │    │  │ Agent 状态      │  │
│  │npcs│  │  │    MD 编辑器 / 预览      │    │  │ ● 运行中        │  │
│  │locs│  │  │                          │    │  │ 回合: 42        │  │
│  │stry│  │  │  (显示选中的 .md 文件)    │    │  │ Token: 15,230   │  │
│  │qst │  │  │                          │    │  └─────────────────┘  │
│  │itm │  │  │                          │    │                       │
│  │plr │  │  └──────────────────────────┘    │  ┌─────────────────┐  │
│  │ses │  │                                  │  │ 当前上下文       │  │
│  └────┘  │  ┌──────────────────────────┐    │  │ Skills: combat  │  │
│          │  │    对话调试面板           │    │  │ Memory: 3 files │  │
│  ┌────┐  │  │                          │    │  │ History: 10轮   │  │
│  │skl │  │  │  > 玩家说: 和铁匠聊聊     │    │  └─────────────────┘  │
│  │prm │  │  │  Agent: 铁匠擦了擦汗...   │    │                       │
│  └────┘  │  │                          │    │  ┌─────────────────┐  │
│          │  └──────────────────────────┘    │  │ SSE 事件流      │  │
│          │                                  │  │ token: 铁匠...  │  │
│          │                                  │  │ cmd: update_rel │  │
│          │                                  │  └─────────────────┘  │
├──────────┴──────────────────────────────────┴───────────────────────┤
│  状态栏: 连接状态 | 适配器: text | 世界: world_001 | 玩家: player_001 │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 布局组件结构

```
App.vue
├── NLayout (has-sider)
│   ├── NLayoutSider (左侧面板, width: 240px)
│   │   ├── FileTree.vue        (文件浏览器)
│   │   └── SideNav.vue         (侧边导航: workspace/skills/prompts)
│   │
│   ├── NLayout (主内容区)
│   │   ├── NTabs
│   │   │   ├── Tab: Editor     → MdEditor.vue    (MD 编辑/预览)
│   │   │   └── Tab: Chat       → ChatDebug.vue   (对话调试)
│   │   │
│   │   └── (底部可选: 终端输出)
│   │
│   └── NLayoutSider (右侧面板, width: 300px)
│       ├── AgentStatus.vue     (Agent 状态卡片)
│       ├── ContextInfo.vue     (当前上下文信息)
│       ├── SSEEventLog.vue     (SSE 事件流)
│       └── TokenCounter.vue    (Token 用量)
│
└── NLayoutFooter (状态栏)
```

---

## 4. 文件浏览器组件

### 4.1 FileTree.vue

使用 Naive UI `<n-tree>` 组件，支持异步加载和虚拟滚动：

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
import axios from 'axios'

const emit = defineEmits<{
  (e: 'file-selected', path: string): void
}>()

const treeRef = ref<any>(null)
const searchPattern = ref('')
const expandedKeys = ref<string[]>(['workspace'])
const selectedKeys = ref<string[]>([])
const treeData = ref<TreeOption[]>([])
const message = useMessage()

// API 基础路径
const API_BASE = '/api/workspace'

// 初始化根节点
onMounted(async () => {
  try {
    const { data } = await axios.get(`${API_BASE}/tree`)
    treeData.value = data.children.map((item: any) => ({
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
    const { data } = await axios.get(`${API_BASE}/tree`, { params: { path } })
    node.children = data.children.map((item: any) => ({
      label: item.name,
      key: item.path,
      isLeaf: item.type === 'file',
    }))
  } catch (e) {
    message.error(`加载 ${path} 失败`)
  }
}

// 自定义标签渲染
function renderLabel({ option }: { option: TreeOption }) {
  return option.label as string
}

// 自定义前缀图标
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

// 文件选择
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

### 4.2 后端 API 支持

```python
# FastAPI 路由: workspace.py
from fastapi import APIRouter, Query
from pathlib import Path
import os

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

WORKSPACE_PATH = Path("./workspace")


@router.get("/tree")
async def get_tree(path: str = Query("", description="目录路径，空为根目录")):
    """获取目录结构"""
    target = WORKSPACE_PATH / path if path else WORKSPACE_PATH

    if not target.exists() or not target.is_dir():
        return {"children": []}

    children = []
    for item in sorted(target.iterdir()):
        # 跳过隐藏文件和临时文件
        if item.name.startswith(".") or item.name.startswith("~"):
            continue

        rel_path = str(item.relative_to(WORKSPACE_PATH))
        children.append({
            "name": item.name,
            "path": rel_path,
            "type": "file" if item.is_file() else "directory",
            "size": item.stat().st_size if item.is_file() else None,
        })

    return {"children": children}


@router.get("/file")
async def get_file(path: str = Query(..., description="文件相对路径")):
    """读取文件内容 (YAML + MD 分离返回)"""
    import frontmatter

    file_path = WORKSPACE_PATH / path
    if not file_path.exists():
        return {"error": "File not found"}

    post = frontmatter.load(str(file_path))
    return {
        "frontmatter": dict(post.metadata),
        "content": post.content,
        "raw": frontmatter.dumps(post)
    }


@router.put("/file")
async def update_file(body: dict):
    """更新文件"""
    import frontmatter
    from memory.file_io import atomic_write

    path = body["path"]
    file_path = WORKSPACE_PATH / path

    if "raw" in body:
        # 直接写入原始内容
        atomic_write(str(file_path), body["raw"])
    else:
        # 分别更新 YAML 和 MD
        if file_path.exists():
            post = frontmatter.load(str(file_path))
        else:
            post = frontmatter.Post(content="")

        if "frontmatter" in body:
            for key, value in body["frontmatter"].items():
                post[key] = value

        if "content" in body:
            post.content = body["content"]

        atomic_write(str(file_path), frontmatter.dumps(post))

    return {"status": "ok"}


@router.post("/file")
async def create_file(body: dict):
    """创建新文件"""
    from memory.file_io import atomic_write

    path = body["path"]
    file_path = WORKSPACE_PATH / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(str(file_path), body.get("content", ""))
    return {"status": "ok", "path": path}


@router.delete("/file")
async def delete_file(path: str = Query(...)):
    """删除文件"""
    file_path = WORKSPACE_PATH / path
    if file_path.exists():
        file_path.unlink()
    return {"status": "ok"}
```

---

## 5. MD 编辑器组件

### 5.1 MdEditor.vue

使用 md-editor-v3 组件，支持编辑和预览模式：

```vue
<template>
  <div class="md-editor-container">
    <n-space v-if="filePath" align="center" justify="space-between" style="margin-bottom: 8px">
      <n-text strong>{{ filePath }}</n-text>
      <n-space>
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
      <!-- 编辑模式 -->
      <MdEditor
        v-if="mode === 'edit'"
        v-model="content"
        :theme="theme"
        language="zh-CN"
        :style="{ height: 'calc(100vh - 240px)' }"
        @on-save="handleSave"
      />

      <!-- 预览模式 -->
      <MdPreview
        v-else
        :id="previewId"
        :modelValue="content"
        :theme="theme"
        language="zh-CN"
        :style="{ height: 'calc(100vh - 240px)', overflow: 'auto' }"
      />
    </div>

    <!-- YAML Front Matter 编辑面板 -->
    <n-collapse v-if="frontmatter" style="margin-top: 8px">
      <n-collapse-item title="YAML Front Matter" name="fm">
        <n-form label-placement="left" label-width="120" size="small">
          <n-form-item v-for="(value, key) in frontmatter" :key="key" :label="String(key)">
            <n-input
              v-model:value="frontmatter[key]"
              size="small"
              @update:value="markDirty"
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
import axios from 'axios'

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

// 加载文件
async function loadFile(path: string) {
  try {
    const { data } = await axios.get('/api/workspace/file', { params: { path } })
    content.value = data.content || ''
    frontmatter.value = data.frontmatter || null
    dirty.value = false
  } catch (e) {
    message.error('加载文件失败')
  }
}

// 保存文件
async function handleSave() {
  if (!props.filePath) return
  saving.value = true
  try {
    await axios.put('/api/workspace/file', {
      path: props.filePath,
      content: content.value,
      frontmatter: frontmatter.value,
    })
    dirty.value = false
    message.success('保存成功')
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 刷新
async function handleReload() {
  if (props.filePath) {
    await loadFile(props.filePath)
    message.info('已刷新')
  }
}

function markDirty() {
  dirty.value = true
}

// 监听文件路径变化
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
  border: 1px solid var(--n-border-color, #e0e0e0);
  border-radius: 4px;
  overflow: hidden;
}
</style>
```

---

## 6. Agent 监控面板

### 6.1 AgentStatus.vue

```vue
<template>
  <div class="agent-status">
    <n-card title="Agent 状态" size="small" :bordered="false">
      <!-- 状态指示器 -->
      <n-space align="center" :size="8">
        <n-badge :type="statusColor" dot />
        <n-text>{{ statusText }}</n-text>
      </n-space>

      <!-- 关键指标 -->
      <n-descriptions :column="1" size="small" style="margin-top: 12px">
        <n-descriptions-item label="当前回合">
          {{ status.turn_count || 0 }}
        </n-descriptions-item>
        <n-descriptions-item label="Token 用量">
          {{ formatNumber(status.total_tokens || 0) }}
        </n-descriptions-item>
        <n-descriptions-item label="活跃 Skill">
          <n-tag v-for="skill in status.active_skills" :key="skill" size="small" style="margin: 2px">
            {{ skill }}
          </n-tag>
          <n-text v-if="!status.active_skills?.length" depth="3">无</n-text>
        </n-descriptions-item>
        <n-descriptions-item label="加载记忆">
          {{ status.loaded_memories?.length || 0 }} 个文件
        </n-descriptions-item>
        <n-descriptions-item label="对话历史">
          {{ status.history_length || 0 }} 轮
        </n-descriptions-item>
      </n-descriptions>
    </n-card>

    <!-- 操作按钮 -->
    <n-space vertical style="margin-top: 8px">
      <n-button block size="small" @click="interruptAgent" :disabled="status.state !== 'processing'">
        中断当前回合
      </n-button>
      <n-button block size="small" @click="resetSession" type="warning">
        重置会话
      </n-button>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const status = ref<any>({})
let pollTimer: number | null = null

const statusColor = computed(() => {
  switch (status.value.state) {
    case 'idle': return 'default'
    case 'processing': return 'success'
    case 'error': return 'error'
    default: return 'default'
  }
})

const statusText = computed(() => {
  switch (status.value.state) {
    case 'idle': return '空闲'
    case 'processing': return '处理中'
    case 'error': return '错误'
    default: return '未知'
  }
})

function formatNumber(n: number): string {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(n)
}

async function fetchStatus() {
  try {
    const { data } = await axios.get('/api/agent/status')
    status.value = data
  } catch (e) {
    // 静默失败
  }
}

async function interruptAgent() {
  try {
    await axios.post('/api/agent/interrupt')
    message.success('已中断')
  } catch (e) {
    message.error('中断失败')
  }
}

async function resetSession() {
  try {
    await axios.post('/api/agent/reset')
    message.success('会话已重置')
    fetchStatus()
  } catch (e) {
    message.error('重置失败')
  }
}

onMounted(() => {
  fetchStatus()
  pollTimer = window.setInterval(fetchStatus, 2000)  // 每 2 秒刷新
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
```

### 6.2 SSEEventLog.vue

```vue
<template>
  <div class="sse-event-log">
    <n-card title="实时事件流" size="small" :bordered="false">
      <n-space align="center" justify="space-between" style="margin-bottom: 8px">
        <n-text depth="3" style="font-size: 12px">{{ events.length }} 条事件</n-text>
        <n-button size="tiny" @click="clearEvents">清空</n-button>
      </n-space>

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
let eventSource: EventSource | null = null

function formatData(data: any): string {
  if (typeof data === 'string') return data
  if (data?.text) return data.text
  if (data?.intent) return `${data.intent}(${JSON.stringify(data.params || {}).slice(0, 50)})`
  return JSON.stringify(data).slice(0, 80)
}

function clearEvents() {
  events.value = []
}

onMounted(() => {
  eventSource = new EventSource('/api/agent/stream')

  eventSource.addEventListener('turn_start', (e) => {
    events.value.push({ type: 'turn_start', data: JSON.parse(e.data), time: new Date().toLocaleTimeString() })
    scrollToBottom()
  })

  eventSource.addEventListener('token', (e) => {
    const data = JSON.parse(e.data)
    // 合并连续的 token 事件
    const last = events.value[events.value.length - 1]
    if (last?.type === 'token') {
      last.data.text += data.text
    } else {
      events.value.push({ type: 'token', data, time: new Date().toLocaleTimeString() })
    }
    scrollToBottom()
  })

  eventSource.addEventListener('command', (e) => {
    events.value.push({ type: 'command', data: JSON.parse(e.data), time: new Date().toLocaleTimeString() })
    scrollToBottom()
  })

  eventSource.addEventListener('turn_end', (e) => {
    events.value.push({ type: 'turn_end', data: JSON.parse(e.data), time: new Date().toLocaleTimeString() })
    scrollToBottom()
  })

  eventSource.addEventListener('error', (e) => {
    events.value.push({ type: 'error', data: { message: 'SSE 连接错误' }, time: new Date().toLocaleTimeString() })
  })
})

onUnmounted(() => {
  eventSource?.close()
})

function scrollToBottom() {
  requestAnimationFrame(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.event-list {
  height: 300px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 12px;
  background: var(--n-color-modal, #1e1e1e);
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
}
.event-token .event-data {
  color: #d4d4d4;
}
.event-command .event-data {
  color: #dcdcaa;
}
.event-turn_start .event-data,
.event-turn_end .event-data {
  color: #4ec9b0;
}
.event-error .event-data {
  color: #f44747;
}
</style>
```

---

## 7. 对话调试面板

### 7.1 ChatDebug.vue

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
        </div>
        <div v-if="loading" class="message message-agent">
          <div class="message-role">Agent</div>
          <div class="message-content">
            <n-spin size="small" /> 思考中...
          </div>
        </div>
      </div>

      <!-- 输入框 -->
      <n-input-group style="margin-top: 8px">
        <n-input
          v-model:value="inputText"
          placeholder="输入玩家操作 (如: 和铁匠聊聊)"
          @keyup.enter="sendMessage"
          :disabled="loading"
        />
        <n-button type="primary" @click="sendMessage" :loading="loading" :disabled="!inputText.trim()">
          发送
        </n-button>
      </n-input-group>

      <!-- 事件类型选择 -->
      <n-select
        v-model:value="eventType"
        :options="eventOptions"
        size="small"
        style="margin-top: 8px"
        placeholder="选择事件类型"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'

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
    const { data } = await axios.post('/api/agent/event', {
      event_id: `debug_${Date.now()}`,
      timestamp: new Date().toISOString(),
      type: eventType.value,
      data: { raw_text: text, player_id: 'debug_player' },
      context_hints: [],
      game_state: {}
    })

    messages.value.push({
      role: 'agent',
      content: data.narrative || '(无叙事)',
      commands: data.commands || []
    })
  } catch (e: any) {
    messages.value.push({
      role: 'agent',
      content: `[错误] ${e.response?.data?.detail || e.message}`
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
  height: 400px;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px;
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
}
.message-user .message-content { background: #e6f7ff; }
.message-commands {
  margin-top: 4px;
}
</style>
```

---

## 8. 项目初始化

### 8.1 创建 Vue 项目

```bash
cd workbench
npm create vite@latest . -- --template vue-ts
npm install
npm install naive-ui @vicons/ionicons5 axios md-editor-v3
npm install -D @types/node
```

### 8.2 Vite 配置 (代理 API)

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

### 8.3 开发模式启动

```bash
# 终端 1: 启动 Agent 后端
cd worldSim-master
uvicorn src.api.app:app --reload --port 8000

# 终端 2: 启动 WorkBench 前端
cd workbench
npm run dev
```

访问 `http://localhost:5173` 即可使用 WorkBench。

---

## 9. WorkBench 功能优先级

| 优先级 | 功能 | 说明 |
|--------|------|------|
| **P0** | 文件浏览器 | 浏览 workspace 目录，点击打开文件 |
| **P0** | MD 编辑器 | 查看/编辑 .md 文件，保存到后端 |
| **P0** | Agent 监控 | 显示 Agent 状态、token 用量 |
| **P0** | 对话调试 | 手动发送事件，查看响应 |
| **P1** | SSE 事件流 | 实时显示 Agent 的 token/command 事件 |
| **P1** | Skill 管理 | 查看/编辑 Skill 文件 |
| **P1** | 系统提示词编辑 | 编辑 Agent 的 system prompt |
| **P2** | 文件搜索 | 全文搜索 workspace 中的 .md 文件 |
| **P2** | 版本对比 | 查看文件修改历史 |
| **P2** | 会话管理 | 查看/导出/重置会话 |
