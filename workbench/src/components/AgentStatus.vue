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
import { useMessage, NCard, NSpace, NBadge, NText, NDescriptions, NDescriptionsItem, NButton } from 'naive-ui'
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