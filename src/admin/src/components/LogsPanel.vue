<template>
  <n-tabs type="line">
    <n-tab-pane name="events" tab="游戏事件">
      <n-data-table :columns="eventColumns" :data="events" />
    </n-tab-pane>
    <n-tab-pane name="conversations" tab="对话记录">
      <n-data-table :columns="convColumns" :data="conversations" />
    </n-tab-pane>
  </n-tabs>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const worldId = 1
const events = ref([])
const conversations = ref([])

const eventColumns = [
  { title: '时间', key: 'timestamp' },
  { title: '类型', key: 'event_type' },
  { title: '内容', key: 'content' },
]

const convColumns = [
  { title: '时间', key: 'timestamp' },
  { title: '角色', key: 'role' },
  { title: '内容', key: 'content' },
]

onMounted(async () => {
  const [eventResp, convResp] = await Promise.all([
    fetch(`/api/admin/logs/game-events?world_id=${worldId}`),
    fetch(`/api/admin/logs/conversations?world_id=${worldId}`),
  ])
  events.value = await eventResp.json()
  conversations.value = await convResp.json()
})
</script>
