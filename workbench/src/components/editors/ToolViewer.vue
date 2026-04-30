<script setup lang="ts">
/**
 * 工具查看器（只读）
 * 展示工具的 intent、参数、描述
 */
import { computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { NDescriptions, NDescriptionsItem, NTag } from 'naive-ui'

const store = useAppStore()

const toolInfo = computed(() => {
  const key = store.selectedResource?.key ?? ''
  const intent = key.replace('tool:', '')
  const tools: Record<string, { desc: string; params: string }> = {
    update_npc_relationship: { desc: '修改 NPC 好感度', params: 'npc_id, change, reason' },
    update_npc_state: { desc: '修改 NPC 状态', params: 'npc_id, field, value' },
    offer_quest: { desc: '发布任务', params: 'title, description, objective, reward' },
    update_quest: { desc: '更新任务状态', params: 'quest_id, status, progress' },
    give_item: { desc: '给予物品', params: 'name, type, player_id' },
    remove_item: { desc: '移除物品', params: 'item_id' },
    modify_stat: { desc: '修改玩家属性', params: 'stat, change, reason' },
    teleport_player: { desc: '传送玩家', params: 'location_id' },
    show_notification: { desc: '显示通知', params: 'message, type' },
    play_sound: { desc: '播放音效', params: 'sound_id' },
    no_op: { desc: '空操作', params: '(无)' },
  }
  return { intent, ...(tools[intent] ?? { desc: '未知工具', params: '未知' }) }
})
</script>

<template>
  <div class="tool-viewer">
    <NDescriptions bordered :column="1" size="small">
      <NDescriptionsItem label="Intent">
        <NTag>{{ toolInfo.intent }}</NTag>
      </NDescriptionsItem>
      <NDescriptionsItem label="描述">{{ toolInfo.desc }}</NDescriptionsItem>
      <NDescriptionsItem label="参数">{{ toolInfo.params }}</NDescriptionsItem>
    </NDescriptions>
  </div>
</template>

<style scoped>
.tool-viewer {
  padding: 16px;
}
</style>
