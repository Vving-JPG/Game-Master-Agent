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
import { NCard, NSpace, NTag, NButton } from 'naive-ui'

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

  eventSource.addEventListener('error', (_e) => {
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