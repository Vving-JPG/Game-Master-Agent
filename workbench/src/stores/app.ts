/**
 * 全局应用状态
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/** 执行状态 */
export type ExecutionState = 'IDLE' | 'RUNNING' | 'PAUSED' | 'STEP_WAITING'

/** 资源类型 */
export type ResourceType = 'prompt' | 'memory' | 'config' | 'tools' | 'workflow' | 'runtime'

/** 资源节点 */
export interface ResourceNode {
  key: string
  label: string
  type: ResourceType
  icon: string
  path?: string
  isLeaf?: boolean
  children?: ResourceNode[]
}

/** 轮次记录 */
export interface TurnRecord {
  id: number
  status: 'completed' | 'failed' | 'paused' | 'current'
  narrative: string
  commands: Array<{ intent: string; status: string }>
  tokens: number
  latency: number
  timestamp: string
}

export const useAppStore = defineStore('app', () => {
  // === 执行状态 ===
  const executionState = ref<ExecutionState>('IDLE')
  const currentTurn = ref(0)
  const totalTokens = ref(0)
  const currentLatency = ref(0)

  // === 模型配置 ===
  const selectedModel = ref('deepseek-chat')
  const temperature = ref(0.7)
  const maxTokens = ref(4096)

  // === 资源导航 ===
  const selectedResource = ref<ResourceNode | null>(null)
  const expandedKeys = ref<string[]>([])

  // === 轮次历史 ===
  const turnHistory = ref<TurnRecord[]>([])

  // === SSE 事件 ===
  const sseEvents = ref<Array<{ type: string; data: any; time: string }>>([])

  // === 计算属性 ===
  const isRunning = computed(() => executionState.value === 'RUNNING')
  const isPaused = computed(() => executionState.value === 'PAUSED')

  // === 方法 ===
  function setExecutionState(state: ExecutionState) {
    executionState.value = state
  }

  function addTurn(turn: TurnRecord) {
    turnHistory.value.push(turn)
  }

  function addSSEEvent(type: string, data: any) {
    sseEvents.value.push({ type, data, time: new Date().toLocaleTimeString() })
    // 保留最近 500 条
    if (sseEvents.value.length > 500) {
      sseEvents.value = sseEvents.value.slice(-500)
    }
  }

  function reset() {
    executionState.value = 'IDLE'
    currentTurn.value = 0
    totalTokens.value = 0
    currentLatency.value = 0
    turnHistory.value = []
    sseEvents.value = []
  }

  return {
    executionState,
    currentTurn,
    totalTokens,
    currentLatency,
    selectedModel,
    temperature,
    maxTokens,
    selectedResource,
    expandedKeys,
    turnHistory,
    sseEvents,
    isRunning,
    isPaused,
    setExecutionState,
    addTurn,
    addSSEEvent,
    reset,
  }
})
