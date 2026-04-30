<script setup lang="ts">
/**
 * 工作流可视化编辑器
 * 基于 Vue Flow 的状态机编辑器，类似 Godot StateMachine
 */
import { ref, watch, computed } from 'vue'
import { VueFlow, useVueFlow, type Node, type Edge } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { NButton, NModal, NForm, NFormItem, NInput, NSpace, NAlert } from 'naive-ui'
import { useAppStore } from '../../stores/app'

const store = useAppStore()
const filePath = computed(() => store.selectedResource?.path ?? 'workflow/main_loop.yaml')

// Vue Flow 实例
const { onConnect, addEdges, getNodes, fitView } = useVueFlow({
  defaultViewport: { x: 0, y: 0, zoom: 0.8 },
})

// 节点和边
const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')

// 节点编辑弹窗
const editingNode = ref<Node | null>(null)
const showEditModal = ref(false)
const editForm = ref({ id: '', next: '', condition: '', conditionTarget: '' })

// === 节点类型定义 ===
const nodeTypes: Record<string, { label: string; color: string; borderColor: string }> = {
  prompt: { label: '📝 Prompt', color: '#e3f2fd', borderColor: '#1976d2' },
  llm_stream: { label: '🤖 LLM', color: '#f3e5f5', borderColor: '#7b1fa2' },
  parse: { label: '📋 Parse', color: '#e8f5e9', borderColor: '#388e3c' },
  branch: { label: '🔀 Branch', color: '#fff3e0', borderColor: '#f57c00' },
  execute: { label: '⚡ Execute', color: '#fce4ec', borderColor: '#c62828' },
  memory: { label: '💾 Memory', color: '#e0f2f1', borderColor: '#00796b' },
  end: { label: '✅ End', color: '#f5f5f5', borderColor: '#757575' },
}

// === 从 YAML 加载工作流 ===
async function loadWorkflow() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    const content = data.content ?? ''

    // 解析 YAML（简单解析，不依赖 js-yaml）
    const parsed = parseSimpleYaml(content)
    const steps = parsed.steps ?? []

    // 转换为 Vue Flow 节点
    const newNodes: Node[] = steps.map((step: any, i: number) => {
      const type = step.type ?? 'prompt'
      const meta = nodeTypes[type] ?? nodeTypes.prompt
      const x = 100 + (i % 4) * 250
      const y = 80 + Math.floor(i / 4) * 150
      return {
        id: step.id,
        type: 'default',
        position: { x, y },
        data: {
          label: `${meta.label}\n${step.id}`,
          stepType: type,
          color: meta.color,
          borderColor: meta.borderColor,
          stepData: step,
        },
        style: {
          backgroundColor: meta.color,
          border: `2px solid ${meta.borderColor}`,
          borderRadius: '8px',
          padding: '8px 16px',
          minWidth: '120px',
          textAlign: 'center',
        },
      }
    })

    // 转换为 Vue Flow 边
    const newEdges: Edge[] = []
    for (const step of steps) {
      if (step.next && step.next !== 'done') {
        newEdges.push({
          id: `e-${step.id}-${step.next}`,
          source: step.id,
          target: step.next,
          animated: true,
          style: { stroke: '#666', strokeWidth: 2 },
        })
      }
      // branch 条件边
      if (step.conditions) {
        for (const [, target] of Object.entries(step.conditions)) {
          if (Array.isArray(target) && target.length > 0) {
            const t = target[0] as any
            if (typeof t === 'object' && t.if && t.next) {
              newEdges.push({
                id: `e-${step.id}-${t.next}`,
                source: step.id,
                target: t.next,
                label: t.if,
                animated: true,
                style: { stroke: '#f57c00', strokeWidth: 2 },
              })
            }
          }
        }
      }
    }

    nodes.value = newNodes
    edges.value = newEdges

    // 延迟 fitView
    setTimeout(() => fitView(), 100)
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

/** 简单 YAML 解析（不依赖外部库） */
function parseSimpleYaml(text: string): any {
  const result: any = { steps: [] }
  const lines = text.split('\n')
  let currentStep: any = null
  let inSteps = false

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue

    if (trimmed.startsWith('steps:')) {
      inSteps = true
      continue
    }

    if (inSteps && trimmed.startsWith('- id:')) {
      if (currentStep) result.steps.push(currentStep)
      currentStep = { id: trimmed.replace('- id:', '').trim() }
      continue
    }

    if (currentStep && trimmed.startsWith('- ')) {
      // 条件列表项
      const match = trimmed.match(/- if:\s*"(.+?)"\s*$/)
      if (match) {
        currentStep.conditions = currentStep.conditions ?? []
        currentStep.conditions.push(match[1])
      }
      continue
    }

    if (currentStep && trimmed.includes(':')) {
      const idx = trimmed.indexOf(':')
      const key = trimmed.slice(0, idx).trim()
      const val = trimmed.slice(idx + 1).trim().replace(/^["']|["']$/g, '')
      if (key === 'type' || key === 'next' || key === 'default') {
        currentStep[key] = val
      }
    }
  }
  if (currentStep) result.steps.push(currentStep)
  return result
}

// === 保存为 YAML ===
async function saveWorkflow() {
  saving.value = true
  error.value = ''
  try {
    // @ts-ignore - 避免复杂的类型推断问题
    const yamlContent = nodesToYaml(nodes.value, edges.value)
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath.value)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: yamlContent }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

function nodesToYaml(nodeList: Node[], edgeList: Edge[]): string {
  let yaml = 'name: main_loop\nstart: ' + (nodeList[0]?.id ?? 'step_1') + '\nsteps:\n'

  for (const node of nodeList) {
    const data = node.data as Record<string, any>
    yaml += `  - id: ${node.id}\n`
    yaml += `    type: ${data.stepType}\n`

    // 找到从这个节点出发的边
    const outEdges = edgeList.filter(e => e.source === node.id)
    if (data.stepType === 'branch') {
      yaml += '    conditions:\n'
      for (const edge of outEdges) {
        yaml += `      - if: "${edge.label || 'true'}"\n`
        yaml += `        next: ${edge.target}\n`
      }
      yaml += '    default: done\n'
    } else if (outEdges.length > 0) {
      yaml += `    next: ${outEdges[0].target}\n`
    } else {
      yaml += '    next: done\n'
    }
  }

  return yaml
}

// === 连线处理 ===
onConnect((params) => {
  addEdges([{
    ...params,
    animated: true,
    style: { stroke: '#666', strokeWidth: 2 },
  }])
})

// === 双击编辑节点 ===
function onNodeDoubleClick({ node }: { node: Node }) {
  editingNode.value = node
  editForm.value = {
    id: node.id,
    next: (node.data as any).stepData?.next ?? '',
    condition: '',
    conditionTarget: '',
  }
  showEditModal.value = true
}

function saveNodeEdit() {
  if (!editingNode.value) return
  const node = editingNode.value
  const data = node.data as any
  data.stepData = {
    ...data.stepData,
    next: editForm.value.next,
  }
  // 更新标签
  const meta = nodeTypes[data.stepType] ?? nodeTypes.prompt
  data.label = `${meta.label}\n${node.id}`
  showEditModal.value = false
}

// === 添加新节点 ===
function addNode(type: string) {
  const meta = nodeTypes[type] ?? nodeTypes.prompt
  const id = `step_${Date.now()}`
  const newNodes = [...nodes.value]
  const lastNode = newNodes[newNodes.length - 1]
  const x = lastNode ? lastNode.position.x + 250 : 100
  const y = lastNode ? lastNode.position.y : 80

  newNodes.push({
    id,
    type: 'default',
    position: { x, y },
    data: {
      label: `${meta.label}\n${id}`,
      stepType: type,
      color: meta.color,
      borderColor: meta.borderColor,
      stepData: { id, type, next: '' },
    },
    style: {
      backgroundColor: meta.color,
      border: `2px solid ${meta.borderColor}`,
      borderRadius: '8px',
      padding: '8px 16px',
      minWidth: '120px',
      textAlign: 'center',
    },
  })
  nodes.value = newNodes
}

// === 删除节点 ===
function deleteSelectedNodes() {
  const selected = getNodes.value.filter(n => n.selected)
  if (selected.length === 0) return
  const selectedIds = new Set(selected.map(n => n.id))
  nodes.value = nodes.value.filter(n => !selectedIds.has(n.id))
  edges.value = edges.value.filter(e => !selectedIds.has(e.source) && !selectedIds.has(e.target))
}

// 监听文件路径变化
watch(filePath, loadWorkflow, { immediate: true })
</script>

<template>
  <div class="workflow-editor">
    <!-- 工具栏 -->
    <div class="wf-toolbar">
      <span class="wf-title">🔄 工作流编辑器</span>
      <NSpace :size="4">
        <NButton size="tiny" @click="addNode('prompt')">+ Prompt</NButton>
        <NButton size="tiny" @click="addNode('llm_stream')">+ LLM</NButton>
        <NButton size="tiny" @click="addNode('parse')">+ Parse</NButton>
        <NButton size="tiny" @click="addNode('branch')">+ Branch</NButton>
        <NButton size="tiny" @click="addNode('execute')">+ Execute</NButton>
        <NButton size="tiny" @click="addNode('memory')">+ Memory</NButton>
        <NButton size="tiny" @click="addNode('end')">+ End</NButton>
        <div class="separator" />
        <NButton size="tiny" @click="deleteSelectedNodes">删除选中</NButton>
        <NButton size="tiny" type="primary" :loading="saving" @click="saveWorkflow">保存</NButton>
      </NSpace>
    </div>

    <NAlert v-if="error" type="error" closable style="margin: 4px 8px">{{ error }}</NAlert>

    <!-- Vue Flow 画布 -->
    <div class="wf-canvas">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :default-edge-options="{ animated: true }"
        :snap-to-grid="true"
        :snap-grid="[20, 20]"
        fit-view-on-init
        @node-double-click="onNodeDoubleClick"
        @keydown.delete="deleteSelectedNodes"
      >
        <Background :gap="20" />
        <Controls />
      </VueFlow>
    </div>

    <!-- 节点编辑弹窗 -->
    <NModal v-model:show="showEditModal" preset="dialog" title="编辑步骤">
      <NForm>
        <NFormItem label="步骤 ID">
          <NInput v-model:value="editForm.id" disabled />
        </NFormItem>
        <NFormItem label="下一步 (next)">
          <NInput v-model:value="editForm.next" placeholder="下一步骤 ID" />
        </NFormItem>
      </NForm>
      <template #action>
        <NButton @click="showEditModal = false">取消</NButton>
        <NButton type="primary" @click="saveNodeEdit">保存</NButton>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.workflow-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.wf-toolbar {
  padding: 6px 12px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.wf-title {
  font-size: 12px;
  font-weight: 600;
}

.separator {
  width: 1px;
  height: 20px;
  background: #e0e0e0;
}

.wf-canvas {
  flex: 1;
  min-height: 0;
}
</style>
