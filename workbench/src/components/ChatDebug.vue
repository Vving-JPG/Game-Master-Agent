<template>
  <div class="chat-debug">
    <n-card title="对话调试" size="small" :bordered="false">
      <!-- 消息列表 -->
      <div class="message-list" ref="msgListRef">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', `message-${msg.role}`]"
        >
          <div class="message-role">{{ msg.role === 'user' ? '玩家' : 'Agent' }}</div>
          <div class="message-content">{{ msg.content }}</div>
          <div v-if="msg.commands?.length" class="message-commands">
            <n-tag v-for="cmd in msg.commands" :key="cmd.intent" size="tiny" type="info">
              {{ cmd.intent }}
            </n-tag>
          </div>
          <div v-if="msg.error" class="message-error">
            <n-text type="error">{{ msg.error }}</n-text>
          </div>
        </div>
        <div v-if="loading" class="message message-agent">
          <div class="message-role">Agent</div>
          <div class="message-content">
            <n-spin size="small" /> 思考中...
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <n-select
          v-model:value="eventType"
          :options="eventOptions"
          size="small"
          style="margin-bottom: 8px"
          placeholder="选择事件类型"
        />
        <n-input-group>
          <n-input
            v-model:value="inputText"
            placeholder="输入玩家操作 (如: 和铁匠聊聊)"
            @keyup.enter="sendMessage"
            :disabled="loading"
          />
          <n-button
            type="primary"
            @click="sendMessage"
            :loading="loading"
            :disabled="!inputText.trim()"
          >
            发送
          </n-button>
        </n-input-group>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NCard, NSelect, NInput, NInputGroup, NButton, NSpin, NTag, NText } from 'naive-ui'
import { sendEvent } from '@/api/agent'
const inputText = ref('')
const eventType = ref('player_action')
const loading = ref(false)
const messages = ref<any[]>([])
const msgListRef = ref<HTMLElement | null>(null)

const eventOptions = [
  { label: 'player_action (玩家操作)', value: 'player_action' },
  { label: 'player_move (玩家移动)', value: 'player_move' },
  { label: 'combat_start (战斗开始)', value: 'combat_start' },
  { label: 'system_event (系统事件)', value: 'system_event' },
]

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true

  try {
    const data = await sendEvent({
      event_id: `debug_${Date.now()}`,
      timestamp: new Date().toISOString(),
      type: eventType.value,
      data: { raw_text: text, player_id: 'debug_player' },
      context_hints: [],
      game_state: {},
    })

    messages.value.push({
      role: 'agent',
      content: data.narrative || '(无叙事)',
      commands: data.commands || [],
    })
  } catch (e: any) {
    messages.value.push({
      role: 'agent',
      content: '',
      error: e.response?.data?.detail || e.message,
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    if (msgListRef.value) {
      msgListRef.value.scrollTop = msgListRef.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.message-list {
  height: 350px;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 8px;
}
.message {
  margin-bottom: 12px;
}
.message-role {
  font-size: 12px;
  font-weight: bold;
  margin-bottom: 4px;
}
.message-user .message-role { color: #1890ff; }
.message-agent .message-role { color: #52c41a; }
.message-content {
  padding: 8px 12px;
  border-radius: 4px;
  background: #f5f5f5;
  white-space: pre-wrap;
  word-break: break-word;
}
.message-user .message-content { background: #e6f7ff; }
.message-commands {
  margin-top: 4px;
}
.message-error {
  margin-top: 4px;
  padding: 4px 8px;
  background: #fff2f0;
  border-radius: 4px;
}
.input-area {
  margin-top: 4px;
}
</style>