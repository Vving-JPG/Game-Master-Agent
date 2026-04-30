<script setup lang="ts">
/**
 * 多态编辑器路由
 * 根据选中资源的类型，渲染不同的编辑器
 */
import { computed } from 'vue'
import { useAppStore } from '../stores/app'
import MdEditor from './editors/MdEditor.vue'
import YamlEditor from './editors/YamlEditor.vue'
import KeyValueEditor from './editors/KeyValueEditor.vue'
import SkillEditor from './editors/SkillEditor.vue'
import ToolViewer from './editors/ToolViewer.vue'
import RuntimeViewer from './editors/RuntimeViewer.vue'
import WorkflowEditor from './editors/WorkflowEditor.vue'

const store = useAppStore()

const editorType = computed(() => {
  const resource = store.selectedResource
  if (!resource) return 'empty'

  const path = resource.path ?? ''
  const key = resource.key ?? ''

  // Skill 文件
  if (path.includes('SKILL.md')) return 'skill'

  // Workflow 文件
  if (path.includes('workflow/') && (path.endsWith('.yaml') || path.endsWith('.yml'))) return 'workflow'

  // Markdown 文件
  if (path.endsWith('.md')) return 'markdown'

  // YAML 文件
  if (path.endsWith('.yaml') || path.endsWith('.yml')) return 'yaml'

  // 配置文件
  if (path.endsWith('.env') || path.endsWith('.env.template')) return 'keyvalue'

  // 工具
  if (key.startsWith('tool:')) return 'tool'

  // 运行时
  if (key.startsWith('runtime:')) return 'runtime'

  return 'markdown'
})
</script>

<template>
  <div class="editor-router">
    <MdEditor v-if="editorType === 'markdown'" />
    <SkillEditor v-else-if="editorType === 'skill'" />
    <WorkflowEditor v-else-if="editorType === 'workflow'" />
    <YamlEditor v-else-if="editorType === 'yaml'" />
    <KeyValueEditor v-else-if="editorType === 'keyvalue'" />
    <ToolViewer v-else-if="editorType === 'tool'" />
    <RuntimeViewer v-else-if="editorType === 'runtime'" />
    <div v-else class="empty-state">
      <p>← 从左侧选择资源开始编辑</p>
    </div>
  </div>
</template>

<style scoped>
.editor-router {
  height: 100%;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
}
</style>
