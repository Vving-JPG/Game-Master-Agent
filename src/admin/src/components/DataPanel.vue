<template>
  <n-tabs type="line">
    <n-tab-pane name="npcs" tab="NPC">
      <n-data-table :columns="npcColumns" :data="npcs" />
    </n-tab-pane>
    <n-tab-pane name="quests" tab="任务">
      <n-data-table :columns="questColumns" :data="quests" />
    </n-tab-pane>
    <n-tab-pane name="players" tab="玩家">
      <n-data-table :columns="playerColumns" :data="players" />
    </n-tab-pane>
  </n-tabs>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const worldId = 1
const npcs = ref([])
const quests = ref([])
const players = ref([])

const npcColumns = [
  { title: 'ID', key: 'id' },
  { title: '名字', key: 'name' },
  { title: '心情', key: 'mood' },
]

const questColumns = [
  { title: 'ID', key: 'id' },
  { title: '标题', key: 'title' },
  { title: '状态', key: 'status' },
]

const playerColumns = [
  { title: 'ID', key: 'id' },
  { title: '名字', key: 'name' },
  { title: '等级', key: 'level' },
  { title: 'HP', key: 'hp' },
]

onMounted(async () => {
  const [npcResp, questResp, playerResp] = await Promise.all([
    fetch(`/api/admin/data/npcs?world_id=${worldId}`),
    fetch(`/api/admin/data/quests?world_id=${worldId}`),
    fetch(`/api/admin/data/players?world_id=${worldId}`),
  ])
  npcs.value = await npcResp.json()
  quests.value = await questResp.json()
  players.value = await playerResp.json()
})
</script>
