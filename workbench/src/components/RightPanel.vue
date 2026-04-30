<script setup lang="ts">
/**
 * 右侧辅助面板
 * W2 会替换为完整的 Agent 状态 + 监控面板
 */
import { NTabs, NTabPane, NStatistic } from 'naive-ui'
import { useAppStore } from '../stores/app'

const store = useAppStore()
</script>

<template>
  <div class="right-panel-content">
    <NTabs type="line" size="small">
      <NTabPane name="agent" tab="🤖 Agent 状态">
        <div class="stat-grid">
          <NStatistic label="状态" :value="store.executionState" />
          <NStatistic label="当前回合" :value="store.currentTurn" />
          <NStatistic label="总 Token" :value="store.totalTokens" />
          <NStatistic label="本轮延迟" :value="store.currentLatency + 'ms'" />
        </div>
      </NTabPane>
      <NTabPane name="monitor" tab="📊 资源监控">
        <div class="placeholder">W2: 资源监控</div>
      </NTabPane>
    </NTabs>
  </div>
</template>

<style scoped>
.right-panel-content {
  height: 100%;
  padding: 4px;
}

.stat-grid {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.placeholder {
  padding: 20px;
  color: #999;
  text-align: center;
  font-size: 13px;
}
</style>
