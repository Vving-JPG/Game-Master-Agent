<script setup lang="ts">
/**
 * 左侧七层资源导航
 */
import { NTabs, NTabPane } from 'naive-ui'
import { useAppStore, type ResourceNode } from '../stores/app'
import ResourceTree from './ResourceTree.vue'
import {
  loadPromptResources,
  // loadSkillResources,
  loadMemoryResources,
  loadConfigResources,
  loadToolResources,
  loadWorkflowResources,
  loadRuntimeResources,
} from '../api/resources'

const store = useAppStore()

function handleSelect(node: ResourceNode) {
  store.selectedResource = node
}
</script>

<template>
  <div class="left-panel-content">
    <NTabs type="line" size="small" placement="left">
      <NTabPane name="prompt" tab="🧠">
        <ResourceTree title="Prompt" icon="🧠" :load-data="loadPromptResources" :on-select="handleSelect" />
      </NTabPane>
      <NTabPane name="memory" tab="📁">
        <ResourceTree title="Memory" icon="📁" :load-data="loadMemoryResources" :on-select="handleSelect" />
      </NTabPane>
      <NTabPane name="config" tab="⚙️">
        <ResourceTree title="Config" icon="⚙️" :load-data="loadConfigResources" :on-select="handleSelect" />
      </NTabPane>
      <NTabPane name="tools" tab="🔧">
        <ResourceTree title="Tools" icon="🔧" :load-data="loadToolResources" :on-select="handleSelect" />
      </NTabPane>
      <NTabPane name="workflow" tab="🔄">
        <ResourceTree title="Workflow" icon="🔄" :load-data="loadWorkflowResources" :on-select="handleSelect" />
      </NTabPane>
      <NTabPane name="runtime" tab="📊">
        <ResourceTree title="Runtime" icon="📊" :load-data="loadRuntimeResources" :on-select="handleSelect" />
      </NTabPane>
    </NTabs>
  </div>
</template>

<style scoped>
.left-panel-content {
  height: 100%;
  padding: 4px;
}
</style>
