<script setup lang="ts">
/**
 * 运行时查看器（只读）
 * 显示当前轮次详情
 */
// import { computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NDescriptions, NDescriptionsItem, NTag, NEmpty } from 'naive-ui'

const store = useAppStore()
</script>

<template>
  <div class="runtime-viewer">
    <NDescriptions bordered :column="1" size="small">
      <NDescriptionsItem label="执行状态">
        <NTag :type="store.isRunning ? 'success' : store.isPaused ? 'warning' : 'default'">
          {{ store.executionState }}
        </NTag>
      </NDescriptionsItem>
      <NDescriptionsItem label="当前回合">{{ store.currentTurn }}</NDescriptionsItem>
      <NDescriptionsItem label="总 Token">{{ store.totalTokens }}</NDescriptionsItem>
      <NDescriptionsItem label="本轮延迟">{{ store.currentLatency }}ms</NDescriptionsItem>
      <NDescriptionsItem label="历史轮次">{{ store.turnHistory.length }}</NDescriptionsItem>
    </NDescriptions>
    <div v-if="store.turnHistory.length === 0" style="padding: 20px">
      <NEmpty description="暂无运行记录" />
    </div>
  </div>
</template>

<style scoped>
.runtime-viewer {
  padding: 16px;
}
</style>
