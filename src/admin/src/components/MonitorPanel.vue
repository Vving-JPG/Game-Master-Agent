<template>
  <n-grid :cols="4" :x-gap="12">
    <n-gi><n-statistic label="总调用次数" :value="stats.total_calls" /></n-gi>
    <n-gi><n-statistic label="总 Token" :value="stats.total_tokens" /></n-gi>
    <n-gi><n-statistic label="平均延迟(ms)" :value="Math.round(stats.avg_latency)" /></n-gi>
    <n-gi><n-statistic label="错误次数" :value="stats.error_count" /></n-gi>
  </n-grid>
  <n-card title="最近调用" style="margin-top: 16px;">
    <n-data-table :columns="columns" :data="calls" :max-height="400" />
  </n-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const stats = ref({})
const calls = ref([])
const columns = [
  { title: '时间', key: 'created_at', width: 180 },
  { title: '类型', key: 'call_type', width: 120 },
  { title: 'Prompt Tokens', key: 'prompt_tokens', width: 120 },
  { title: 'Completion Tokens', key: 'completion_tokens', width: 140 },
  { title: '延迟(ms)', key: 'latency_ms', width: 100 },
  { title: '工具调用', key: 'tool_names', width: 200 },
  { title: '错误', key: 'error', width: 200 },
]

onMounted(async () => {
  const [statsResp, callsResp] = await Promise.all([
    fetch('/api/admin/monitor/stats'),
    fetch('/api/admin/monitor/calls?limit=50'),
  ])
  stats.value = await statsResp.json()
  calls.value = await callsResp.json()
})
</script>
