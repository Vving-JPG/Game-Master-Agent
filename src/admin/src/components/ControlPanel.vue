<template>
  <n-card title="GM 运行时参数">
    <n-form>
      <n-form-item label="Temperature">
        <n-slider v-model:value="config.temperature" :min="0" :max="2" :step="0.1" />
      </n-form-item>
      <n-form-item label="最大工具轮次">
        <n-input-number v-model:value="config.max_tool_rounds" :min="1" :max="20" />
      </n-form-item>
      <n-form-item label="最大上下文消息数">
        <n-input-number v-model:value="config.max_context_messages" :min="10" :max="200" />
      </n-form-item>
      <n-space>
        <n-button type="primary" @click="saveConfig">应用配置</n-button>
        <n-button type="warning" @click="pauseGM" v-if="!config.paused">暂停 GM</n-button>
        <n-button type="success" @click="resumeGM" v-else>恢复 GM</n-button>
      </n-space>
    </n-form>
  </n-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'

const config = ref({})
const message = useMessage()

onMounted(async () => {
  const resp = await fetch('/api/admin/control/config')
  config.value = await resp.json()
})

async function saveConfig() {
  await fetch('/api/admin/control/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config.value),
  })
  message.success('配置已更新')
}

async function pauseGM() {
  await fetch('/api/admin/control/pause', { method: 'POST' })
  config.value.paused = true
  message.warning('GM 已暂停')
}

async function resumeGM() {
  await fetch('/api/admin/control/resume', { method: 'POST' })
  config.value.paused = false
  message.success('GM 已恢复')
}
</script>
