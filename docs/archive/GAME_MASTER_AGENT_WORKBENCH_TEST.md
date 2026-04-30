# Game Master Agent V2 — WorkBench 浏览器测试

> 阶段: WB-TEST
> 前置: W1-W7 全部完成 (P0-P4 后端完成)
> 目标: 启动前端 dev server，用浏览器逐项测试 WorkBench 全部功能，记录结果

---

## 项目上下文

**项目**: 通用游戏驱动 Agent 服务 — Agent 不是游戏本身，是独立服务层。
**前端**: Vue 3 + Naive UI + Vue Flow + Vite + TypeScript + Pinia
**后端**: Python 3.11+ / FastAPI / DeepSeek API
**前端目录**: `workbench/`
**后端目录**: `src/`

### 核心架构
```
游戏引擎 (Text/Godot) ◄──► Agent Service (Python) ◄──► WorkBench (Vue 3)
                                │
                          EngineAdapter (适配层)
                          Agent Workspace (.md 记忆文件)
```

---

## 踩坑记录 (必须遵守)

1. PowerShell `&&` 语法: 用 `;` 分隔
2. 中文括号: 代码和测试中用英文括号
3. 原子写入: 所有 `.md` 文件写入必须用 `atomic_write()`
4. YAML Front Matter: 引擎写 FM，Agent 写 Body，不要混淆
5. DeepSeek `reasoning_content`: `getattr(delta, 'reasoning_content', None)`
6. `tool_call_id`: tool 消息必须包含
7. `tool_calls` 增量拼接: dict 按 index 累积
8. 测试隔离: 每个测试模块用 `teardown_module` 清理全局状态
9. SQLite `datetime('now')`: 同一秒内时间戳相同，测试用 `>=` 而非 `==`
10. `llm_client.py`: V1 是同步 `OpenAI`，P1 已转为 `AsyncOpenAI`

---

## 前端已知问题 (测试时重点验证)

1. **LeftPanel.vue**: `loadSkillResources` 被注释掉了，可能需要启用
2. **WorkflowEditor.vue**: 使用 `type: 'default'` 节点 + 内联样式，而非自定义节点类型
3. **SSEEventLog.vue**: 有自己独立的 EventSource 连接，与 BottomConsole 的 SSE 可能重复

---

## 测试步骤 (共 10 步)

### 步骤 1: 环境检查

**目的**: 确认前后端依赖和配置就绪

**操作**:
1. 检查 `workbench/package.json` 存在，确认依赖列表包含: `vue`, `naive-ui`, `@vue-flow/core`, `pinia`, `vite`
2. 检查 `workbench/vite.config.ts`，确认:
   - dev server 端口 (默认 5173 或自定义)
   - 是否配置了 API 代理到后端 (如 `/api` → `http://localhost:8000`)
3. 检查 `workbench/tsconfig.json` 存在
4. 确认 Node.js 版本 >= 18

**验收**:
- [ ] `package.json` 包含核心依赖
- [ ] `vite.config.ts` 端口和代理配置正确
- [ ] Node.js 版本满足要求

---

### 步骤 2: 安装依赖 + 启动前端

**目的**: 安装前端依赖并启动 dev server

**操作**:
1. 进入 `workbench/` 目录
2. 执行 `npm install` (如已安装可跳过)
3. 执行 `npm run dev` 启动开发服务器
4. 等待编译完成，记录 dev server 输出的 URL (如 `http://localhost:5173`)

**验收**:
- [ ] `npm install` 无报错
- [ ] `npm run dev` 启动成功，无编译错误
- [ ] 终端输出 dev server URL

---

### 步骤 3: 页面加载 + 整体布局

**目的**: 验证页面能正常加载，四区布局正确

**操作**:
1. 用浏览器打开 dev server URL
2. 等待页面完全加载
3. 截图记录初始状态
4. 检查四区布局:
   - **TopBar** (顶部): 应显示项目名称/导航
   - **LeftPanel** (左侧): 应显示七层资源导航树
   - **MainEditor** (中央): 应显示编辑区域 (初始可能为空或欢迎页)
   - **BottomConsole** (底部): 应显示控制台/SSE 日志区域
   - **RightPanel** (右侧): 如有，检查内容

**验收**:
- [ ] 页面无白屏，无 JS 报错 (打开浏览器 Console 检查)
- [ ] 四区布局可见，无重叠/错位
- [ ] Naive UI 组件样式正常加载 (非裸 HTML)

---

### 步骤 4: LeftPanel — 七层资源导航

**目的**: 验证左侧面板的七层资源模型导航

**七层资源模型**:
1. 模型层 — 模型选择、参数配置
2. 提示词层 — system_prompt.md、Skill 提示词
3. 记忆层 — workspace/ 下的 .md 记忆文件
4. 工具层 — Skill 文件管理
5. 配置层 — Agent 参数
6. 工作流层 — YAML 定义的步骤执行流程
7. 状态层 — 运行时状态查看 (不可编辑)

**操作**:
1. 观察 LeftPanel 中的资源树结构
2. 逐层展开，确认每层有对应的节点/条目
3. 点击各层节点，观察 MainEditor 是否切换到对应编辑器
4. 特别检查 **loadSkillResources** 是否被注释 (已知问题 #1):
   - 打开 `workbench/src/components/LeftPanel.vue`
   - 搜索 `loadSkillResources`
   - 如果被注释，记录下来，测试时观察工具层是否为空

**验收**:
- [ ] 七层资源树结构可见
- [ ] 点击各层节点，MainEditor 正确切换
- [ ] 记录 loadSkillResources 注释状态

---

### 步骤 5: EditorRouter — 多态编辑器路由

**目的**: 验证 EditorRouter 根据文件路径/key 路由到正确的编辑器

**路由规则**:
| 路径/协议 | 目标编辑器 |
|-----------|-----------|
| `.md` 文件 | MdEditor |
| `skill://` | SkillEditor |
| `workflow://` | WorkflowEditor (Vue Flow) |
| `.yaml` 文件 | YamlEditor |
| `config://` | KeyValueEditor |
| `tool://` | ToolViewer |
| `runtime://` | RuntimeViewer |

**操作**:
1. 在 LeftPanel 中依次点击不同类型的资源
2. 每次点击后，确认 MainEditor 区域:
   - 切换到了正确的编辑器组件
   - 编辑器 UI 与预期匹配 (如 MdEditor 有 Markdown 工具栏，WorkflowEditor 有 Vue Flow 画布)
3. 尝试点击 `config://` 类型的资源，确认 KeyValueEditor 显示键值对表单
4. 尝试点击 `runtime://` 类型的资源，确认 RuntimeViewer 显示且不可编辑

**验收**:
- [ ] 7 种编辑器都能正确路由
- [ ] 每种编辑器的 UI 符合预期
- [ ] RuntimeViewer 和 ToolViewer 为只读状态

---

### 步骤 6: MdEditor + YamlEditor — 内容编辑

**目的**: 验证 Markdown 和 YAML 编辑器的基本功能

**操作**:
1. 导航到一个 `.md` 文件 (如 `prompts/system_prompt.md`)
2. 测试 MdEditor:
   - 内容是否正确加载显示
   - 能否编辑内容
   - 能否保存 (如有保存按钮)
3. 导航到一个 `.yaml` 文件 (如工作流定义文件)
4. 测试 YamlEditor:
   - YAML 内容是否正确渲染
   - 能否编辑
   - 能否保存

**验收**:
- [ ] MdEditor 正确加载和显示 .md 内容
- [ ] YamlEditor 正确加载和显示 .yaml 内容
- [ ] 编辑功能可用 (至少能输入文字)

---

### 步骤 7: WorkflowEditor — Vue Flow 可视化编排

**目的**: 验证工作流编辑器的 Vue Flow 画布和节点

**WorkflowEngine 设计**:
- ExecutionState 状态机: `IDLE → RUNNING → PAUSED → STEP_WAITING`
- YAML 定义步骤，支持 pause/resume/step 控制
- Vue Flow 可视化: 7 种固定节点类型 (Start/End/LLM/Tool/Condition/Parallel/Loop)

**操作**:
1. 在 LeftPanel 中导航到工作流层，点击一个 workflow 资源
2. 确认 WorkflowEditor 加载:
   - Vue Flow 画布可见
   - 有节点和连线渲染
3. 检查节点类型:
   - 是否能看到 Start/End/LLM/Tool 等节点
   - 节点样式是否正常 (已知问题 #2: 使用 `type: 'default'` + 内联样式)
4. 测试画布交互:
   - 能否拖拽节点
   - 能否缩放/平移画布
   - 能否点击节点查看详情

**验收**:
- [ ] Vue Flow 画布正常渲染
- [ ] 节点和连线可见
- [ ] 画布交互 (拖拽/缩放) 可用
- [ ] 记录节点样式实现方式 (default + inline vs custom)

---

### 步骤 8: BottomConsole — SSE + 日志

**目的**: 验证底部控制台的 SSE 连接和日志显示

**操作**:
1. 观察 BottomConsole 区域
2. 检查是否有 SSE 连接状态指示器
3. 检查日志输出区域是否可见
4. **SSE 重复连接检查** (已知问题 #3):
   - 打开浏览器 DevTools → Network 标签
   - 筛选 EventStream 类型的请求
   - 检查是否有多个 SSE 连接同时存在 (SSEEventLog 和 BottomConsole 各一个)
   - 记录连接数量
5. 如果后端也在运行，观察是否有 SSE 事件推送

**验收**:
- [ ] BottomConsole 区域可见
- [ ] 日志/事件区域可显示内容
- [ ] 记录 SSE 连接数量 (是否重复)

---

### 步骤 9: AgentStatus + ChatDebug

**目的**: 验证 Agent 状态面板和调试聊天功能

**操作**:
1. 检查 AgentStatus 面板:
   - 是否显示 Agent 当前状态 (IDLE/RUNNING 等)
   - 状态信息是否正确
2. 检查 ChatDebug 面板:
   - 是否有输入框
   - 是否能输入消息
   - 如果后端运行中，尝试发送一条测试消息，观察响应

**验收**:
- [ ] AgentStatus 面板可见，显示状态信息
- [ ] ChatDebug 面板可见，输入框可用
- [ ] 记录后端未运行时的表现 (如显示 "未连接" 等)

---

### 步骤 10: agent-pack 导入导出

**目的**: 验证 agent-pack.zip 的导入导出功能 (W7 实现)

**操作**:
1. 在 TopBar 或相关位置查找导入/导出按钮
2. 测试导出:
   - 点击导出按钮
   - 确认生成了 `agent-pack.zip` 文件
3. 测试导入:
   - 准备一个 agent-pack.zip (可用刚导出的)
   - 点击导入按钮
   - 选择文件，确认导入流程启动
4. 检查导入后资源是否正确加载

**验收**:
- [ ] 导出功能可用，生成 zip 文件
- [ ] 导入功能可用，能选择并加载 zip
- [ ] 导入后资源正确显示

---

## 测试结果汇总模板

测试完成后，按以下格式汇总:

```
## 测试结果

| 步骤 | 测试项 | 结果 | 备注 |
|------|--------|------|------|
| 1 | 环境检查 | ✅/❌ | |
| 2 | 安装依赖+启动 | ✅/❌ | |
| 3 | 页面加载+布局 | ✅/❌ | |
| 4 | 七层资源导航 | ✅/❌ | |
| 5 | 多态编辑器路由 | ✅/❌ | |
| 6 | MdEditor+YamlEditor | ✅/❌ | |
| 7 | WorkflowEditor | ✅/❌ | |
| 8 | BottomConsole+SSE | ✅/❌ | |
| 9 | AgentStatus+ChatDebug | ✅/❌ | |
| 10 | agent-pack导入导出 | ✅/❌ | |

### 已知问题验证
- loadSkillResources 注释状态: [是/否]
- SSE 重复连接: [是/否，几个连接]
- WorkflowEditor 节点样式: [default+inline / custom]

### 发现的新问题
1. ...
2. ...

### 浏览器 Console 错误
1. ...
2. ...
```

---

## 注意事项

1. **后端可选**: 步骤 3-7 不依赖后端运行，步骤 8-9 的 SSE 和 ChatDebug 需要后端。如果后端未启动，记录"后端未运行，跳过"即可
2. **截图**: 每个步骤建议截图，便于问题排查
3. **Console 错误**: 全程保持浏览器 DevTools Console 打开，记录所有红色错误
4. **不要修改代码**: 本次测试只验证，不修复。发现问题记录下来，后续单独修复
5. **Vite HMR**: 如果修改了任何文件，Vite 会热更新，注意观察是否有 HMR 报错
