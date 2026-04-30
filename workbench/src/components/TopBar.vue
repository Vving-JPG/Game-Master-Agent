<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NSelect, NSlider, NInputGroup, NTag, NSpace, useMessage } from 'naive-ui'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const message = useMessage()

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

// === agent-pack 导入/导出 ===
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
      message.success(`导入成功: ${data.files?.length ?? 0} 个文件`)
    } else {
      message.error(`导入失败: ${data.detail}`)
    }
  } catch {
    message.error('导入失败')
  }

  // 重置 input
  input.value = ''
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

    <div class="separator" />

    <!-- agent-pack -->
    <NButton size="small" @click="exportPack">📦 导出</NButton>
    <NButton size="small" @click="triggerImport">📥 导入</NButton>
    <input ref="fileInput" type="file" accept=".zip" style="display: none" @change="handleImport" />

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
