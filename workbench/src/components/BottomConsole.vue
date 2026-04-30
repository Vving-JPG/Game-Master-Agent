<script setup lang="ts">
/**
 * 底部控制台
 * Tab 1: 执行控制 — 暂停/继续/单步 + 当前步骤高亮
 * Tab 2: 轮次列表 — 历史轮次，点击查看详情
 * Tab 3: 指令注入 — system/user 级别注入
 */
import { ref, onMounted, onUnmounted, h } from 'vue'
import { NTabs, NTabPane, NButton, NSpace, NInput, NSelect, NTag, NEmpty, NDataTable } from 'naive-ui'
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
    const res = await fetch('/api/agent/inject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        level: injectLevel.value,
        content: injectContent.value,
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
let workflowAbortController: AbortController | null = null

async function loadWorkflowState() {
  // 取消之前的请求
  if (workflowAbortController) {
    workflowAbortController.abort()
  }
  workflowAbortController = new AbortController()

  try {
    const res = await fetch('/api/agent/workflow', {
      signal: workflowAbortController.signal
    })
    if (res.ok) {
      workflowState.value = await res.json()
    }
  } catch (e) {
    // 忽略 AbortError（组件卸载时取消请求）
    if ((e as Error).name !== 'AbortError') {
      console.error('加载工作流状态失败:', e)
    }
  }
}

// 定期刷新
let workflowTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  workflowTimer = setInterval(loadWorkflowState, 2000)
  loadWorkflowState() // 立即执行一次
})
onUnmounted(() => {
  if (workflowTimer) clearInterval(workflowTimer)
  if (workflowAbortController) {
    workflowAbortController.abort()
  }
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
