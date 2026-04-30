<script setup lang="ts">
/**
 * Markdown 编辑器
 * 用于编辑 .md 记忆文件和 system_prompt.md
 */
import { ref, watch, computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NButton, NSpace, NAlert } from 'naive-ui'

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
  <div class="md-editor-wrapper">
    <div class="editor-toolbar">
      <span class="file-path">{{ filePath }}</span>
      <NSpace>
        <NButton size="tiny" :loading="saving" @click="saveFile">保存</NButton>
      </NSpace>
    </div>
    <NAlert v-if="error" type="error" closable style="margin: 8px">{{ error }}</NAlert>
    <div v-if="loading" class="loading-hint">加载中...</div>
    <div v-else class="editor-area">
      <textarea
        v-model="content"
        class="markdown-textarea"
        placeholder="Markdown 内容..."
        spellcheck="false"
      />
      <div class="preview-area" v-html="renderMarkdown(content)" />
    </div>
  </div>
</template>

<script lang="ts">
function renderMarkdown(text: string): string {
  // 简单的 Markdown 渲染（换行 → <br>，代码块保留）
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.md-editor-wrapper {
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

.editor-area {
  flex: 1;
  display: flex;
  min-height: 0;
}

.markdown-textarea {
  flex: 1;
  padding: 12px;
  border: none;
  border-right: 1px solid #e0e0e0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  outline: none;
}

.preview-area {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.6;
}

.loading-hint {
  padding: 20px;
  text-align: center;
  color: #999;
}
</style>
