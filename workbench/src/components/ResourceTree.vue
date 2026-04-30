<script setup lang="ts">
/**
 * 通用资源树组件
 * 支持异步加载子节点、搜索过滤、右键菜单
 */
import { ref, computed, h } from 'vue'
import { NTree, NInput } from 'naive-ui'
import type { TreeOption } from 'naive-ui'
import { useAppStore, type ResourceNode } from '../stores/app'

const props = defineProps<{
  title: string
  icon: string
  loadData: (key: string) => Promise<ResourceNode[]>
  onSelect?: (node: ResourceNode) => void
  onCreate?: (parentKey: string) => void
}>()

// store is used in template
// @ts-ignore
const _store = useAppStore()
const searchValue = ref('')
const treeData = ref<TreeOption[]>([])
const loading = ref(false)

/** 将 ResourceNode 转换为 NTree 的 TreeOption */
function toTreeOptions(nodes: ResourceNode[]): TreeOption[] {
  return nodes.map(node => ({
    key: node.key,
    label: node.label,
    prefix: () => h('span', { style: 'margin-right: 4px' }, node.icon),
    isLeaf: node.isLeaf ?? false,
    children: node.children ? toTreeOptions(node.children) : undefined,
  }))
}

/** 异步加载子节点 */
async function handleLoad(node: TreeOption) {
  const key = String(node.key)
  const children = await props.loadData(key)
  node.children = toTreeOptions(children)
}

/** 选中节点 */
function handleSelect(_keys: string[], option: TreeOption[]) {
  if (option.length > 0 && props.onSelect) {
    const node = option[0] as any
    props.onSelect({
      key: node.key,
      label: node.label as string,
      type: 'prompt' as any, // 由父组件覆盖
      icon: '',
      path: node.key,
    })
  }
}

/** 过滤 */
const filteredData = computed(() => {
  if (!searchValue.value) return treeData.value
  // 简单的标签过滤
  return filterTree(treeData.value, searchValue.value.toLowerCase())
})

function filterTree(nodes: TreeOption[], keyword: string): TreeOption[] {
  return nodes.reduce<TreeOption[]>((acc, node) => {
    const label = (node.label as string).toLowerCase()
    if (label.includes(keyword)) {
      acc.push(node)
    } else if (node.children) {
      const filtered = filterTree(node.children, keyword)
      if (filtered.length > 0) {
        acc.push({ ...node, children: filtered })
      }
    }
    return acc
  }, [])
}

// 初始加载
async function init() {
  loading.value = true
  try {
    const nodes = await props.loadData('root')
    treeData.value = toTreeOptions(nodes)
  } finally {
    loading.value = false
  }
}

init()
</script>

<template>
  <div class="resource-tree">
    <div class="tree-header">
      <span class="tree-title">{{ icon }} {{ title }}</span>
      <NInput
        v-model:value="searchValue"
        size="tiny"
        placeholder="搜索..."
        clearable
        style="margin-top: 4px"
      />
    </div>
    <NTree
      :data="filteredData"
      :load="handleLoad"
      :on-update:selected-keys="handleSelect as any"
      block-line
      selectable
      expand-on-click
      :pattern="searchValue"
      class="tree-content"
    />
  </div>
</template>

<style scoped>
.resource-tree {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tree-header {
  padding: 4px 8px;
}

.tree-title {
  font-size: 12px;
  font-weight: 600;
  color: #333;
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  font-size: 13px;
}
</style>
