/**
 * 七层资源数据加载
 */
import type { ResourceNode } from '../stores/app'

const API_BASE = '/api'

/** 获取 Prompt 资源树 */
export async function loadPromptResources(): Promise<ResourceNode[]> {
  const res = await fetch(`${API_BASE}/workspace/tree?path=prompts`)
  const data = await res.json()
  return data.children?.map(toResourceNode('prompt')) ?? [
    { key: 'prompts/system_prompt.md', label: 'system_prompt.md', type: 'prompt', icon: '📄', path: 'prompts/system_prompt.md', isLeaf: true },
  ]
}

/** 获取 Skill 资源树 */
export async function loadSkillResources(): Promise<ResourceNode[]> {
  const res = await fetch(`${API_BASE}/skills`)
  const data = await res.json()
  const builtin: ResourceNode[] = (data.builtin ?? []).map((s: any) => ({
    key: `skills/builtin/${s.name}/SKILL.md`,
    label: `${s.name} (v${s.version})`,
    type: 'prompt' as const,
    icon: '⚡',
    path: `skills/builtin/${s.name}/SKILL.md`,
    isLeaf: true,
  }))
  const agentCreated: ResourceNode[] = (data.agent_created ?? []).map((s: any) => ({
    key: `skills/agent_created/${s.name}/SKILL.md`,
    label: `${s.name} (v${s.version})`,
    type: 'prompt' as const,
    icon: '🤖',
    path: `skills/agent_created/${s.name}/SKILL.md`,
    isLeaf: true,
  }))
  const nodes: ResourceNode[] = []
  if (builtin.length > 0) {
    nodes.push({ key: 'builtin', label: '内置 Skill', type: 'prompt', icon: '📦', children: builtin })
  }
  if (agentCreated.length > 0) {
    nodes.push({ key: 'agent_created', label: 'Agent 创建', type: 'prompt', icon: '🤖', children: agentCreated })
  }
  return nodes
}

/** 获取 Memory 资源树 */
export async function loadMemoryResources(): Promise<ResourceNode[]> {
  const res = await fetch(`${API_BASE}/workspace/tree?path=workspace`)
  const data = await res.json()
  return data.children?.map(toResourceNode('memory')) ?? []
}

/** 获取 Config 资源树 */
export async function loadConfigResources(): Promise<ResourceNode[]> {
  return [
    { key: '.env', label: '.env', type: 'config', icon: '🔑', path: '.env', isLeaf: true },
    { key: 'adapter.yaml', label: 'adapter.yaml', type: 'config', icon: '🔧', path: 'adapter.yaml', isLeaf: true },
  ]
}

/** 获取 Tools 资源树 */
export async function loadToolResources(): Promise<ResourceNode[]> {
  // 从 system_prompt.md 中解析可用指令
  const tools = [
    { intent: 'update_npc_relationship', desc: '修改 NPC 好感度' },
    { intent: 'update_npc_state', desc: '修改 NPC 状态' },
    { intent: 'offer_quest', desc: '发布任务' },
    { intent: 'update_quest', desc: '更新任务' },
    { intent: 'give_item', desc: '给予物品' },
    { intent: 'remove_item', desc: '移除物品' },
    { intent: 'modify_stat', desc: '修改属性' },
    { intent: 'teleport_player', desc: '传送玩家' },
    { intent: 'show_notification', desc: '显示通知' },
    { intent: 'play_sound', desc: '播放音效' },
    { intent: 'no_op', desc: '空操作' },
  ]
  return tools.map(t => ({
    key: `tool:${t.intent}`,
    label: t.intent,
    type: 'tools' as const,
    icon: '🔧',
    isLeaf: true,
  }))
}

/** 获取 Workflow 资源树 */
export async function loadWorkflowResources(): Promise<ResourceNode[]> {
  return [
    { key: 'workflow/main_loop.yaml', label: 'main_loop.yaml', type: 'workflow', icon: '🔄', path: 'workflow/main_loop.yaml', isLeaf: true },
  ]
}

/** 获取 Runtime 资源树 */
export async function loadRuntimeResources(): Promise<ResourceNode[]> {
  return [
    { key: 'runtime:current', label: 'Current Turn', type: 'runtime', icon: '▶️', isLeaf: true },
    { key: 'runtime:history', label: 'Turn History', type: 'runtime', icon: '📜', isLeaf: true },
    { key: 'runtime:events', label: 'Event Log', type: 'runtime', icon: '📋', isLeaf: true },
  ]
}

/** 通用转换 */
function toResourceNode(type: ResourceNode['type']): (item: any) => ResourceNode {
  return (item: any) => ({
    key: item.path ?? item.name,
    label: item.name ?? item.path,
    type,
    icon: item.type === 'directory' ? '📁' : '📄',
    path: item.path,
    isLeaf: item.type !== 'directory',
    children: item.children?.map(toResourceNode(type)),
  })
}
