<template>
  <div class="file-tree">
    <n-input
      v-model:value="searchPattern"
      placeholder="搜索文件..."
      clearable
      size="small"
      style="margin-bottom: 8px"
    >
      <template #prefix>
        <n-icon size="14"><SearchOutline /></n-icon>
      </template>
    </n-input>

    <n-tree
      ref="treeRef"
      block-line
      :data="treeData"
      :pattern="searchPattern"
      :on-load="handleLoad"
      :expanded-keys="expandedKeys"
      :selected-keys="selectedKeys"
      virtual-scroll
      :render-label="renderLabel"
      :render-prefix="renderPrefix"
      selectable
      style="height: calc(100vh - 160px)"
      @update:selected-keys="(keys: string[], option: any[]) => handleSelect(keys, option)"
      @update:expanded-keys="handleExpandedKeysChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NIcon, useMessage, NInput, NTree } from 'naive-ui'
import {
  SearchOutline,
  FolderOutline,
  FolderOpenOutline,
  DocumentTextOutline,
} from '@vicons/ionicons5'
import type { TreeOption } from 'naive-ui'
import { getTree, type TreeNode } from '@/api/workspace'

const emit = defineEmits<{
  (e: 'file-selected', path: string): void
}>()

const searchPattern = ref('')
const expandedKeys = ref<string[]>(['workspace'])
const selectedKeys = ref<string[]>([])
const treeData = ref<TreeOption[]>([])
const message = useMessage()

// 初始化根节点
onMounted(async () => {
  try {
    const children = await getTree()
    treeData.value = children.map((item: TreeNode) => ({
      label: item.name,
      key: item.path,
      isLeaf: item.type === 'file',
    }))
  } catch (e) {
    message.error('加载文件树失败')
  }
})

// 异步加载子目录
async function handleLoad(node: TreeOption) {
  const path = node.key as string
  try {
    const children = await getTree(path)
    node.children = children.map((item: TreeNode) => ({
      label: item.name,
      key: item.path,
      isLeaf: item.type === 'file',
    }))
  } catch (e) {
    message.error(`加载 ${path} 失败`)
  }
}

function renderLabel({ option }: { option: TreeOption }) {
  return option.label as string
}

function renderPrefix({ option }: { option: TreeOption }) {
  const isDir = !option.isLeaf
  const isExpanded = expandedKeys.value.includes(option.key as string)
  const IconComp = isDir
    ? (isExpanded ? FolderOpenOutline : FolderOutline)
    : DocumentTextOutline
  return h(NIcon, { size: 16, style: 'margin-right: 4px' }, {
    default: () => h(IconComp)
  })
}

function handleSelect(keys: string[], option: TreeOption[]) {
  selectedKeys.value = keys
  if (keys.length > 0 && option.length > 0) {
    // 只选择文件，不选择文件夹
    const firstOption = option[0]
    if (firstOption && firstOption.isLeaf) {
      emit('file-selected', keys[0])
    }
  }
}

function handleExpandedKeysChange(keys: string[]) {
  expandedKeys.value = keys
}
</script>

<style scoped>
.file-tree {
  padding: 8px;
}
</style>