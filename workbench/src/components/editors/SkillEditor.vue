<script setup lang="ts">
/**
 * Skill 编辑器
 * 表单编辑 YAML Front Matter + Markdown 正文
 */
import { ref, watch, computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NButton, NAlert, NInput, NFormItem, NCard, NDynamicTags } from 'naive-ui'

const store = useAppStore()
const loading = ref(false)
const saving = ref(false)
const error = ref('')

// YAML Front Matter 字段
const name = ref('')
const description = ref('')
const version = ref('1.0.0')
const tags = ref<string[]>([])
const allowedTools = ref<string[]>([])

// Markdown Body
const body = ref('')

const filePath = computed(() => store.selectedResource?.path ?? '')

async function loadFile() {
  if (!filePath.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    const raw = data.content ?? ''

    // 解析 YAML Front Matter
    const fmMatch = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/)
    if (fmMatch) {
      const fm = fmMatch[1]
      body.value = fmMatch[2]
      name.value = extractField(fm, 'name') ?? ''
      description.value = extractField(fm, 'description') ?? ''
      version.value = extractField(fm, 'version') ?? '1.0.0'
      tags.value = extractList(fm, 'tags')
      allowedTools.value = extractList(fm, 'allowed-tools')
    } else {
      body.value = raw
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function extractField(yaml: string, field: string): string | null {
  const match = yaml.match(new RegExp(`^${field}:\\s*(.+)$`, 'm'))
  return match ? match[1].trim() : null
}

function extractList(yaml: string, field: string): string[] {
  const match = yaml.match(new RegExp(`^${field}:\\s*\\[([\\s\\S]*?)\\]`, 'm'))
  if (!match) return []
  return match[1]
    .split(',')
    .map(s => s.trim().replace(/['"]/g, ''))
    .filter(Boolean)
}

function toFileContent(): string {
  const toolsStr = allowedTools.value.length > 0
    ? '\nallowed-tools:\n' + allowedTools.value.map(t => `  - ${t}`).join('\n')
    : ''
  const tagsStr = tags.value.length > 0
    ? '\ntags:\n' + tags.value.map(t => `  - ${t}`).join('\n')
    : ''
  return `---\nname: ${name.value}\ndescription: ${description.value}\nversion: ${version.value}${tagsStr}${toolsStr}\n---\n\n${body.value}`
}

async function saveFile() {
  if (!filePath.value) return
  saving.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: toFileContent() }),
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
  <div class="skill-editor-wrapper">
    <div class="editor-toolbar">
      <span class="file-path">{{ filePath }}</span>
      <NButton size="tiny" :loading="saving" @click="saveFile">保存</NButton>
    </div>
    <NAlert v-if="error" type="error" closable style="margin: 8px">{{ error }}</NAlert>
    <div v-if="loading" class="loading-hint">加载中...</div>
    <div v-else class="skill-content">
      <NCard title="Skill 元数据" size="small" style="margin: 8px">
        <NFormItem label="名称" label-placement="left">
          <NInput v-model:value="name" size="small" />
        </NFormItem>
        <NFormItem label="描述" label-placement="left">
          <NInput v-model:value="description" size="small" type="textarea" :rows="2" />
        </NFormItem>
        <NFormItem label="版本" label-placement="left">
          <NInput v-model:value="version" size="small" style="width: 120px" />
        </NFormItem>
        <NFormItem label="标签">
          <NDynamicTags v-model:value="tags" />
        </NFormItem>
        <NFormItem label="允许的指令">
          <NDynamicTags v-model:value="allowedTools" />
        </NFormItem>
      </NCard>
      <NCard title="Skill 正文 (Markdown)" size="small" style="margin: 8px">
        <textarea
          v-model="body"
          class="skill-body"
          placeholder="Skill 的 Markdown 正文..."
          spellcheck="false"
        />
      </NCard>
    </div>
  </div>
</template>

<style scoped>
.skill-editor-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
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

.skill-content {
  flex: 1;
  overflow-y: auto;
}

.skill-body {
  width: 100%;
  min-height: 200px;
  padding: 8px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
}

.loading-hint {
  padding: 20px;
  text-align: center;
  color: #999;
}
</style>
