<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-layout has-sider style="height: 100vh">
            <!-- 左侧面板: 文件浏览器 -->
            <n-layout-sider
              :width="240"
              :collapsed-width="0"
              :collapsed="leftCollapsed"
              show-trigger="bar"
              collapse-mode="width"
              bordered
              :native-scrollbar="false"
              style="height: 100vh"
            >
              <div class="sider-header">
                <n-text strong>文件浏览器</n-text>
              </div>
              <FileTree @file-selected="handleFileSelected" />
            </n-layout-sider>

            <!-- 主内容区 -->
            <n-layout>
              <n-tabs v-model:value="activeTab" type="card" style="height: 100%">
                <!-- 编辑器 Tab -->
                <n-tab-pane name="editor" tab="编辑器">
                  <MdEditor :file-path="selectedFile" />
                </n-tab-pane>

                <!-- 对话调试 Tab -->
                <n-tab-pane name="chat" tab="对话调试">
                  <ChatDebug />
                </n-tab-pane>
              </n-tabs>
            </n-layout>

            <!-- 右侧面板: Agent 监控 -->
            <n-layout-sider
              :width="300"
              :collapsed-width="0"
              :collapsed="rightCollapsed"
              show-trigger="bar"
              collapse-mode="width"
              bordered
              :native-scrollbar="false"
              style="height: 100vh"
            >
              <n-scrollbar style="height: 100vh">
                <AgentStatus />
                <SSEEventLog />
              </n-scrollbar>
            </n-layout-sider>
          </n-layout>

          <!-- 底部状态栏 -->
          <n-layout-footer bordered style="height: 28px; line-height: 28px; padding: 0 16px; font-size: 12px">
            <n-space :size="16">
              <n-text depth="3">Game Master Agent WorkBench</n-text>
              <n-text depth="3">|</n-text>
              <n-text depth="3">后端: {{ backendStatus }}</n-text>
            </n-space>
          </n-layout-footer>
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NConfigProvider,
  NLayout,
  NLayoutSider,
  NLayoutFooter,
  NTabs,
  NTabPane,
  NScrollbar,
  NText,
  NSpace,
  NMessageProvider,
  NDialogProvider,
  NNotificationProvider,
} from 'naive-ui'
import FileTree from '@/components/FileTree.vue'
import MdEditor from '@/components/MdEditor.vue'
import AgentStatus from '@/components/AgentStatus.vue'
import SSEEventLog from '@/components/SSEEventLog.vue'
import ChatDebug from '@/components/ChatDebug.vue'
import axios from 'axios'

const leftCollapsed = ref(false)
const rightCollapsed = ref(false)
const activeTab = ref('editor')
const selectedFile = ref<string | null>(null)
const backendStatus = ref('检测中...')

const themeOverrides = {
  common: {
    fontSize: '14px',
  },
}

function handleFileSelected(path: string) {
  selectedFile.value = path
  activeTab.value = 'editor'
}

onMounted(async () => {
  try {
    await axios.get('/api/agent/status', { timeout: 3000 })
    backendStatus.value = '已连接'
  } catch {
    backendStatus.value = '未连接'
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
html, body, #app {
  height: 100%;
  overflow: hidden;
}
.sider-header {
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
}
</style>