/**
 * Workspace 文件 API
 */
import axios from 'axios'

export interface TreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  size: number | null
}

export interface FileContent {
  frontmatter: Record<string, any>
  content: string
  raw: string
}

export async function getTree(path: string = ''): Promise<TreeNode[]> {
  const { data } = await axios.get('/api/workspace/tree', { params: { path } })
  return data.children
}

export async function getFile(path: string): Promise<FileContent> {
  const { data } = await axios.get('/api/workspace/file', { params: { path } })
  return data
}

export async function updateFile(path: string, body: {
  frontmatter?: Record<string, any>
  content?: string
  raw?: string
}): Promise<void> {
  await axios.put('/api/workspace/file', { path, ...body })
}

export async function createFile(path: string, content: string): Promise<void> {
  await axios.post('/api/workspace/file', { path, content })
}

export async function deleteFile(path: string): Promise<void> {
  await axios.delete('/api/workspace/file', { params: { path } })
}