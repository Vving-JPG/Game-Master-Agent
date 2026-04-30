# WorkBench W5~W7 - 流程编辑器、控制台与 Agent-Pack

> 完成时间: 2026-04-30
> 测试数: 7+ (pack测试)
> 依赖: W1~W4 完成

---

## 一句话总结

Vue Flow 工作流可视化编辑器 + 三栏底部控制台 + Agent-Pack 导入导出系统。

---

## 已完成清单

### W5: 流程编辑器 (Vue Flow)
- [x] `@vue-flow/core` + background + controls 安装
- [x] `WorkflowEditor.vue` 组件 (7种节点类型)
- [x] `EditorRouter.vue` 集成 workflow 类型
- [x] YAML 解析与序列化
- [x] 节点增删改、连线编辑

### W6: 底部控制台重构
- [x] 三栏 Tab: 执行控制 / 轮次列表 / 指令注入
- [x] SSE 实时事件流 (`/api/agent/stream`)
- [x] 执行控制按钮: 运行/暂停/单步
- [x] 工作流状态轮询 (`/api/agent/workflow`)
- [x] `/api/agent/inject` 指令注入端点

### W7: Agent-Pack 导入/导出
- [x] `/api/pack/export` 导出 zip
- [x] `/api/pack/import` 导入 zip (自动备份)
- [x] 前端 TopBar 导入/导出按钮
- [x] 7 个 pack 测试 (30s 超时)

---

## 关键文件

### 后端
```
src/api/routes/pack.py          # pack 导入/导出 API
src/api/routes/agent.py         # +/inject 端点
src/api/app.py                  # 注册 pack 路由
tests/test_api/test_pack.py     # 7 个测试
```

### 前端
```
workbench/src/components/editors/WorkflowEditor.vue
workbench/src/components/EditorRouter.vue
workbench/src/components/BottomConsole.vue
workbench/src/components/TopBar.vue
```

### 配置
```
pyproject.toml                  # +timeout = 30
```

---

## 技术决策

1. **Vue Flow 使用默认节点**: 避免自定义节点类型的 TypeScript 复杂类型问题
2. **简单 YAML 解析器**: 不依赖 js-yaml，手动解析 workflow YAML
3. **全局测试超时**: pyproject.toml 配置 30s 默认超时
4. **Agent-Pack 结构**:
   ```
   metadata.json
   system_prompt.md
   skills/*.md
   memory/*.md
   workflow/*.yaml
   config/.env.template
   ```

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/pack/export` | GET | 下载 agent-pack.zip |
| `/api/pack/import` | POST | 上传并导入 zip |
| `/api/agent/inject` | POST | 指令注入 (system/user/override) |
| `/api/agent/workflow` | GET | 获取工作流状态 |

---

## 测试覆盖

- `test_pack.py`: 7 个测试 (导出/导入/异常/往返)
- 全局 30s 超时 (pytest-timeout)

---

## 遗留/注意事项

1. `WorkflowEditor.vue` 使用 `// @ts-ignore` 绕过复杂类型推断
2. 自定义节点渲染简化使用默认节点 + style 属性
3. `test_step_mode` 测试在 30s 超时 (可能需更长超时或异步处理)

---

## 下一步 (可选)

- W8: 运行时调试面板增强
- W9: 多 Agent 会话管理
- W10: 性能监控与优化
