/**
 * Agent 交互 API
 */
import axios from 'axios'

export interface AgentStatus {
  state: 'idle' | 'processing'
  turn_count: number
  total_tokens: number
  history_length: number
  current_event: string | null
}

export interface AgentContext {
  system_prompt: string
  system_prompt_length: number
  history_length: number
  active_skills: string[]
}

export async function getStatus(): Promise<AgentStatus> {
  const { data } = await axios.get('/api/agent/status')
  return data
}

export async function getContext(): Promise<AgentContext> {
  const { data } = await axios.get('/api/agent/context')
  return data
}

export async function resetSession(): Promise<void> {
  await axios.post('/api/agent/reset')
}

export async function sendEvent(event: {
  event_id: string
  timestamp: string
  type: string
  data: Record<string, any>
  context_hints?: string[]
  game_state?: Record<string, any>
}): Promise<any> {
  const { data } = await axios.post('/api/agent/event', event)
  return data
}