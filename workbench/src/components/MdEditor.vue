<template>
  <div class="md-editor-container">
    <n-space v-if="filePath" align="center" justify="space-between" style="margin-bottom: 8px">
      <n-text strong>{{ filePath }}</n-text>
      <n-space>
        <n-button size="small" @click="toggleMode">
          {{ mode === 'edit' ? '预览' : '编辑' }}
        </n-button>
        <n-button size="small" @click="handleSave" :loading="saving" type="primary">
          保存
        </n-button>
        <n-button size="small" @click="handleReload">
          刷新
        </n-button>
      </n-space>
    </n-space>

    <div v-if="!filePath" class="empty-state">
      <n-text depth="3">选择一个文件开始编辑</n-text>
    </div>

    <div v-else class="editor-wrapper">
      <MdEditor
        v-if="mode === 'edit'"
        v-model="content"
        :theme="theme"
        language="zh-CN"
        :style="{ height: 'calc(100vh - 280px)' }"
        @on-save="handleSave"
      />

      <MdPreview
        v-else
        :id="previewId"
        :modelValue="content"
        :theme="theme"
        language="zh-CN"
        :style="{ height: 'calc(100vh - 280px)', overflow: 'auto' }"
      />
    </div>

    <!-- YAML Front Matter 编辑面板 -->
    <n-collapse v-if="frontmatter && Object.keys(frontmatter).length > 0" style="margin-top: 8px">
      <n-collapse-item title="YAML Front Matter" name="fm">
        <n-form label-placement="left" label-width="120" size="small">
          <n-form-item v-for="(_value, key) in frontmatter" :key="key" :label="String(key)">
            <n-input
              :value="String(frontmatter[key])"
              size="small"
              @update:value="updateFrontmatter(String(key), $event)"
            />
          </n-form-item>
        </n-form>
      </n-collapse-item>
    </n-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useMessage, NSpace, NText, NButton, NCollapse, NCollapseItem, NForm, NFormItem, NInput } from 'naive-ui'
import { MdEditor, MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { getFile, updateFile } from '@/api/workspace'

const props = defineProps<{
  filePath: string | null
}>()

const message = useMessage()
const content = ref('')
const frontmatter = ref<Record<string, any> | null>(null)
const saving = ref(false)
const dirty = ref(false)
const mode = ref<'edit' | 'preview'>('edit')
const theme = ref<'light' | 'dark'>('light')
const previewId = computed(() => `preview-${props.filePath}`)

async function loadFile(path: string) {
  try {
    const data = await getFile(path)
    content.value = data.content || ''
    frontmatter.value = data.frontmatter || null
    dirty.value = false
  } catch (e) {
    message.error('加载文件失败')
  }
}

async function handleSave() {
  if (!props.filePath) return
  saving.value = true
  try {
    await updateFile(props.filePath, {
      content: content.value,
      frontmatter: frontmatter.value || undefined,
    })
    dirty.value = false
    message.success('保存成功')
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleReload() {
  if (props.filePath) {
    await loadFile(props.filePath)
    message.info('已刷新')
  }
}

function toggleMode() {
  mode.value = mode.value === 'edit' ? 'preview' : 'edit'
}

function updateFrontmatter(key: string, _value: string) {
  if (frontmatter.value) {
    frontmatter.value[key] = _value
    dirty.value = true
  }
}

watch(() => props.filePath, (newPath) => {
  if (newPath) {
    loadFile(newPath)
  } else {
    content.value = ''
    frontmatter.value = null
  }
}, { immediate: true })
</script>

<style scoped>
.md-editor-container {
  height: 100%;
  padding: 8px;
}
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.editor-wrapper {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}
</style>