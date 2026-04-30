# 项目记忆导航

> 本文件引导 AI 渐进式加载 `d:\worldSim-master\.trae\记忆\` 中的项目上下文。
> 遵循 3 层披露：**Index（查表）→ Activation（关键字段）→ Execution（完整加载）**。

---

## Layer 1: 记忆索引（始终加载）

| 文件 | 阶段 | 测试数 | 一句话 |
|------|------|--------|--------|
| `记忆/1.md` | V1 P0 - 项目初始化 | 12 | 技术栈选定、环境搭建、LLMClient封装 |
| `记忆/2.md` | V1 P1 - 持久化骨架 | 36 | SQLite建表(11表)、Repository层、种子数据 |
| `记忆/3.md` | V1 P2 - Agent循环 | 68 | 工具系统(10工具)、GameMaster推理循环、CLI |
| `记忆/4.md` | V1 P3' - 三大游戏系统 | 116 | NPC系统、剧情任务、战斗系统 |
| `记忆/5.md` | V1 P4' - 通信与前端 | 156 | FastAPI+WebSocket、Vue3管理端、Prompt版本管理 |
| `记忆/6.md` | V1 P5' - 优化与发布 | 179 | Prompt优化、缓存、降级、插件、多模型路由 |
| `记忆/v2.1.md` | **V2 P0 - 清理重构** | 175 | 砍掉tools/plugins/context_manager，新增memory/skills/adapters三模块 |
| `记忆/v2.2.md` | **V2 P1 - 核心重构** | 189 | 事件驱动GameMaster、CommandParser、PromptBuilder、EventHandler、LLMClient异步化 |
| `记忆/v2.3.md` | **V2 P2 - API扩展** | 216 | Workspace/Skills/Agent API、SSE流式推送、28个新测试 |
| `记忆/v2.4.md` | **V2 P3 - WorkBench前端** | 216+ | Vue3+TS+Vite+Naive UI、文件浏览器、MD编辑器、Agent监控、SSE事件流 |
| `记忆/v2.5.md` | **V2 P4 - 集成与清理** | 226 | 清理V1遗留、cli_v2.py、集成测试、性能测试、文档更新 |
| `记忆/workbench_w1w4.md` | **W1~W4 - WorkBench重构** | 6+ | 新布局、七层导航、多态编辑器、YAML工作流引擎 |
| `记忆/workbench_w5w7.md` | **W5~W7 - 流程与Pack** | 7+ | Vue Flow编辑器、底部控制台、Agent-Pack导入导出 |

### 阶段依赖图

```
V1: 1 → 2 → 3 → 4 → 5 → 6
                              ↘
V2:                         v2.1 → v2.2 → v2.3 → v2.4 → v2.5 ✅
                                      ↘
WorkBench:                         W1~W4 → W5~W7 ✅
```

---

## Layer 2: 激活规则（按需加载）

**当用户/任务涉及以下主题时，加载对应文件：**

| 触发关键词 | 加载文件 | 加载层级 |
|-----------|----------|----------|
| 数据库、表结构、Repository、SQLite、schema | `记忆/2.md` §2 + §4 | Activation |
| 工具调用、function calling、tool、骰子、dice | `记忆/3.md` §1 | Activation |
| NPC、对话、好感度、关系、性格模板 | `记忆/4.md` §1 | Activation |
| 任务、剧情、quest、分支、结局 | `记忆/4.md` §2 | Activation |
| 战斗、combat、伤害、HP、攻击 | `记忆/4.md` §3 | Activation |
| API、FastAPI、路由、WebSocket、REST | `记忆/5.md` §1-§4 + `记忆/v2.2.md` §5 | Activation |
| 管理端、admin、Vue、Naive UI、Prompt管理、页面空白 | `记忆/5.md` §7-§11 + `0.md` | Activation |
| 缓存、降级、重试、性能、模型路由 | `记忆/6.md` §2 | Activation |
| 记忆系统、memory、workspace、.md文件、atomic_write | `记忆/v2.1.md` §4 | Activation |
| Skill、SKILL.md、技能、能力定义 | `记忆/v2.1.md` §5 | Activation |
| 适配器、adapter、引擎、engine、TextAdapter | `记忆/v2.1.md` §6 | Activation |
| CommandParser、命令解析、JSON解析、容错解析 | `记忆/v2.2.md` §1.1 | Activation |
| PromptBuilder、Prompt组装、system_prompt.md | `记忆/v2.2.md` §1.2+§1.3 | Activation |
| EventHandler、SSE推送、事件分发 | `记忆/v2.2.md` §1.4 + `记忆/v2.3.md` §2.4 | Activation |
| LLMClient、stream、异步化、AsyncOpenAI、chat | `记忆/v2.2.md` §2.1 | Activation |
| GameMaster、handle_event、事件驱动、game_master | `记忆/v2.2.md` §2.3 | Activation |
| game_master 旧接口、ws.py、action.py、API适配 | `记忆/v2.5.md` §2.1 | Activation |
| Workspace API、文件树、文件CRUD | `记忆/v2.3.md` §2.1 + `记忆/v2.4.md` §4.1 | Activation |
| Skills API、Skill管理、builtin/agent_created | `记忆/v2.3.md` §2.2 | Activation |
| Agent API、状态查询、事件发送 | `记忆/v2.3.md` §2.3 + `记忆/v2.4.md` §4.2 | Activation |
| SSE端点、流式推送、实时事件 | `记忆/v2.3.md` §2.4 + `记忆/v2.4.md` §3.5 | Activation |
| WorkBench、Vue3、前端、Vite、Naive UI | `记忆/v2.4.md` 全文 | Execution |
| 文件浏览器、FileTree、MdEditor | `记忆/v2.4.md` §3.2 + §3.3 | Activation |
| Agent监控面板、AgentStatus、状态轮询 | `记忆/v2.4.md` §3.4 | Activation |
| 对话调试、ChatDebug、手动发送事件 | `记忆/v2.4.md` §3.6 | Activation |
| CLI、cli_v2.py、命令行、MUD模式 | `记忆/v2.5.md` §2.2 | Activation |
| 集成测试、test_integration、端到端 | `记忆/v2.5.md` §2.3 | Activation |
| 性能测试、benchmark、延迟测试 | `记忆/v2.5.md` §2.4 | Activation |
| V2、重构、新架构、清理冗余 | `记忆/v2.1.md` 全文 | Execution |
| P1、核心重构、Agent循环重写 | `记忆/v2.2.md` 全文 | Execution |
| P2、API扩展、REST端点 | `记忆/v2.3.md` 全文 | Execution |
| P3、WorkBench、Vue前端 | `记忆/v2.4.md` 全文 | Execution |
| P4、集成清理、测试完善 | `记忆/v2.5.md` 全文 | Execution |
| 项目整体理解、全貌 | `记忆/v2.5.md` + `记忆/v2.4.md` + `记忆/v2.3.md` + `记忆/v2.2.md` + `记忆/v2.1.md` | Execution |
| 配置、.env、API Key、DeepSeek | `记忆/1.md` §11 | Activation |
| WorkBench重构、W1、W2、W3、W4 | `记忆/workbench_w1w4.md` | Execution |
| WorkBench W5、W6、W7 | `记忆/workbench_w5w7.md` | Execution |
| 流程编辑器、Vue Flow、WorkflowEditor | `记忆/workbench_w5w7.md` §W5 | Activation |
| 底部控制台、BottomConsole、SSE | `记忆/workbench_w5w7.md` §W6 | Activation |
| Agent-Pack、导入导出、pack | `记忆/workbench_w5w7.md` §W7 | Activation |
| 工作流引擎、WorkflowEngine、YAML | `记忆/workbench_w1w4.md` §W4 | Activation |
| 多态编辑器、EditorRouter、SkillEditor | `记忆/workbench_w1w4.md` §W3 | Activation |
| 七层导航、ResourceTree、LeftPanel | `记忆/workbench_w1w4.md` §W2 | Activation |
| Pinia、app.ts、全局状态 | `记忆/workbench_w1w4.md` §W1 | Activation |

---

## Layer 3: 执行规则（完整加载）

**以下情况加载完整文件（不只是摘要）：**

1. **用户说"重启/恢复/继续开发"** → 加载 `记忆/v2.5.md` 全文（当前最新状态）
2. **需要修改 V1 保留代码**（如 combat.py, database.py）→ 加载对应阶段记忆文件全文
3. **需要修改 P1 代码**（game_master.py, command_parser.py, prompt_builder.py, event_handler.py）→ 加载 `记忆/v2.2.md` 全文
4. **需要修改 P2 代码**（workspace.py, skills.py, agent.py, sse.py）→ 加载 `记忆/v2.3.md` 全文
5. **需要修改 P3 代码**（FileTree.vue, MdEditor.vue, AgentStatus.vue 等前端组件）→ 加载 `记忆/v2.4.md` 全文
6. **需要修改 P4 代码**（cli_v2.py, 集成测试, ws.py/action.py）→ 加载 `记忆/v2.5.md` 全文
7. **需要修改 LLMClient** → 加载 `记忆/v2.2.md` §2.1（异步化细节）
8. **用户提到具体表名/函数名找不到** → 加载 `记忆/2.md`（数据库）+ `记忆/3.md`（工具）
9. **需要理解某个设计决策的来龙去脉** → 加载该阶段记忆文件的 §6（关键设计决策）
10. **需要继续 WorkBench W5~W7 开发** → 加载 `记忆/workbench_w5w7.md` 全文
11. **需要理解 WorkBench 完整架构** → 加载 `记忆/workbench_w1w4.md` + `记忆/workbench_w5w7.md`

---

## 快速上下文恢复命令

```
# 新对话开始时，AI 应执行：
1. 读取本文件（已内置在 rules 中，自动加载）
2. 如果用户提到了具体功能，按 Layer 2 激活对应文件
3. 如果用户说"继续开发/恢复上下文"，加载 v2.5.md 全文
```

---

*最后更新: 2026-04-30*  
*关联目录: d:\worldSim-master\.trae\记忆\*  
*当前阶段: **W1~W7 全部完成** ✅*
