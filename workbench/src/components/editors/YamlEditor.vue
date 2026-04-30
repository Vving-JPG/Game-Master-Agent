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
