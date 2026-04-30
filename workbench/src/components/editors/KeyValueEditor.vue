<script setup lang="ts">
/**
 * 键值对编辑器
 * 用于编辑 .env 文件
 */
import { ref, watch, computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NButton, NAlert, NInput, NSpace } from 'naive-ui'

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
