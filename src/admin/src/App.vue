<template>
  <n-config-provider :theme="darkTheme">
    <n-message-provider>
      <n-dialog-provider>
        <n-layout has-sider style="height: 100vh;">
          <n-layout-sider bordered :width="220">
            <div class="logo">GM Admin</div>
            <n-menu :options="menuOptions" @update:value="handleMenuSelect" />
          </n-layout-sider>
          <n-layout>
            <n-layout-header bordered style="height: 50px; display: flex; align-items: center; padding: 0 20px;">
              <span style="font-weight: bold;">{{ currentPageTitle }}</span>
            </n-layout-header>
            <n-layout-content content-style="padding: 20px;">
              <component :is="currentComponent" />
            </n-layout-content>
          </n-layout>
        </n-layout>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { ref, computed, markRaw } from 'vue'
import { darkTheme, NConfigProvider, NLayout, NLayoutSider, NLayoutHeader, NLayoutContent, NMenu, NMessageProvider, NDialogProvider } from 'naive-ui'
import PromptPanel from './components/PromptPanel.vue'
import MonitorPanel from './components/MonitorPanel.vue'
import DataPanel from './components/DataPanel.vue'
import LogsPanel from './components/LogsPanel.vue'
import ControlPanel from './components/ControlPanel.vue'

const API_BASE = '/api/admin'

const components = {
  prompt: markRaw(PromptPanel),
  monitor: markRaw(MonitorPanel),
  data: markRaw(DataPanel),
  logs: markRaw(LogsPanel),
  control: markRaw(ControlPanel),
}

const currentPage = ref('prompt')
const currentComponent = computed(() => components[currentPage.value])

const menuOptions = [
  { label: 'Prompt 管理', key: 'prompt' },
  { label: 'AI 监控', key: 'monitor' },
  { label: '游戏数据', key: 'data' },
  { label: '日志记录', key: 'logs' },
  { label: 'GM 控制', key: 'control' },
]

const currentPageTitle = computed(() => {
  return menuOptions.find(o => o.key === currentPage.value)?.label || ''
})

function handleMenuSelect(key) {
  currentPage.value = key
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
.logo { padding: 16px; font-size: 18px; font-weight: bold; color: #63e2b7; text-align: center; }
</style>
