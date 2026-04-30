<script setup lang="ts">
import { NConfigProvider, NLayout, NLayoutHeader, NLayoutContent, NLayoutFooter, NLayoutSider } from 'naive-ui'
import { NMessageProvider } from 'naive-ui'
import TopBar from './components/TopBar.vue'
import LeftPanel from './components/LeftPanel.vue'
import MainEditor from './components/MainEditor.vue'
import RightPanel from './components/RightPanel.vue'
import BottomConsole from './components/BottomConsole.vue'
</script>

<template>
  <NConfigProvider>
    <NMessageProvider>
      <NLayout class="app-layout" has-sider>
        <!-- 顶部控制栏 -->
        <NLayoutHeader class="top-bar" bordered>
          <TopBar />
        </NLayoutHeader>

        <NLayout has-sider class="main-area">
          <!-- 左侧资源导航 18% -->
          <NLayoutSider
            class="left-panel"
            :width="260"
            :min-width="200"
            :max-width="400"
            bordered
            collapse-mode="width"
          >
            <LeftPanel />
          </NLayoutSider>

          <!-- 中间 + 右侧 -->
          <NLayout class="center-right-area">
            <NLayout has-sider class="center-right-inner">
              <!-- 中间主工作区 -->
              <NLayoutContent class="main-editor">
                <MainEditor />
              </NLayoutContent>

              <!-- 右侧辅助面板 30% -->
              <NLayoutSider
                class="right-panel"
                :width="360"
                :min-width="280"
                :max-width="500"
                bordered
                collapse-mode="width"
              >
                <RightPanel />
              </NLayoutSider>
            </NLayout>

            <!-- 底部控制台 -->
            <NLayoutFooter class="bottom-console" bordered>
              <BottomConsole />
            </NLayoutFooter>
          </NLayout>
        </NLayout>
      </NLayout>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-layout {
  height: 100vh;
}

.top-bar {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-area {
  height: calc(100vh - 48px);
}

.left-panel {
  height: 100%;
  overflow-y: auto;
}

.center-right-area {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.center-right-inner {
  flex: 1;
  min-height: 0;
}

.main-editor {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.right-panel {
  height: 100%;
  overflow-y: auto;
}

.bottom-console {
  height: 200px;
  min-height: 100px;
  max-height: 400px;
  overflow: hidden;
}
</style>
