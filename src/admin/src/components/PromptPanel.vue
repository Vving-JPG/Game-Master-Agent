<template>
  <n-card title="System Prompt">
    <n-input v-model:value="promptContent" type="textarea" :rows="20" placeholder="输入 GM System Prompt..." />
    <template #action>
      <n-space>
        <n-button type="primary" @click="savePrompt" :loading="saving">应用</n-button>
        <n-button @click="loadHistory">版本历史</n-button>
      </n-space>
    </template>
  </n-card>
  <n-card v-if="showHistory" title="版本历史" style="margin-top: 16px;">
    <n-timeline>
      <n-timeline-item v-for="h in history" :key="h.id"
        :type="h.is_active ? 'success' : 'default'">
        版本 {{ h.version }} - {{ h.created_at }}
        <n-button size="small" @click="rollback(h.version)" :disabled="h.is_active">回滚</n-button>
      </n-timeline-item>
    </n-timeline>
  </n-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'

const API = '/api/admin/prompts/game_master_system'
const promptContent = ref('')
const saving = ref(false)
const showHistory = ref(false)
const history = ref([])
const message = useMessage()

onMounted(async () => {
  const resp = await fetch(API)
  const data = await resp.json()
  promptContent.value = data.content || ''
})

async function savePrompt() {
  saving.value = true
  await fetch('/api/admin/prompts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt_key: 'game_master_system', content: promptContent.value }),
  })
  saving.value = false
  message.success('Prompt 已更新，立即生效！')
}

async function loadHistory() {
  const resp = await fetch(`${API}/history`)
  history.value = await resp.json()
  showHistory.value = true
}

async function rollback(version) {
  await fetch('/api/admin/prompts/rollback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt_key: 'game_master_system', version }),
  })
  message.success(`已回滚到版本 ${version}`)
  loadHistory()
  // 重新加载当前版本
  const resp = await fetch(API)
  const data = await resp.json()
  promptContent.value = data.content || ''
}
</script>
