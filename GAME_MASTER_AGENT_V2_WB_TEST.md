# Game Master Agent V2 - WB_TEST: WorkBench 测试验证

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户**测试验证** Game Master Agent V2 的 PyQt WorkBench 管理界面。

- **技术**: Python PyQt6
- **目标**: 逐项验证 WorkBench 各功能是否正常工作
- **包管理器**: uv
- **开发IDE**: Trae

### 前置条件

**后端 (P0-P4) 已完成**，**WorkBench (WB) 已完成**：
- `workbench/` — PyQt6 桌面管理界面
- `src/` — 后端源码 (226+ 测试通过)
- `workspace/`、`skills/`、`prompts/` — 运行时数据

### 测试目标

逐项验证 WorkBench 的 7 个核心功能，记录每项的通过/失败状态。

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行
2. **记录结果**：每项测试记录 ✅ 通过 或 ❌ 失败 + 错误信息
3. **遇到错误先尝试修复**：如果测试失败，先尝试修复代码，3次失败后再报告
4. **每步完成后汇报**：完成一步后，简要汇报结果

---

## 测试步骤

### Test 1: 环境检查

**目的**: 确认所有依赖已安装。

```bash
# 检查 PyQt6
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"

# 检查 python-frontmatter
python -c "import frontmatter; print('frontmatter OK')"

# 检查 yaml
python -c "import yaml; print('yaml OK')"

# 检查 workbench 模块
python -c "from workbench.app import main; print('workbench OK')"

# 检查后端模块
python -c "from src.memory.manager import MemoryManager; print('backend OK')"
```

**验收**: 所有 import 无报错。

---

### Test 2: 启动测试

**目的**: 确认 WorkBench 能正常启动。

```bash
cd workbench
python -m app
```

**检查项**:
- [ ] 窗口正常弹出（不是终端，是 GUI 窗口）
- [ ] 窗口标题: "Game Master Agent WorkBench"
- [ ] 窗口最小尺寸 1200x800
- [ ] 无报错、无崩溃

**验收**: 窗口正常显示，无报错。

---

### Test 3: 三栏布局测试

**目的**: 验证三栏布局正确。

**检查项**:
- [ ] 左侧有资源树（约 18% 宽度）
- [ ] 中间有编辑区（约 52% 宽度）
- [ ] 右侧有辅助面板（约 30% 宽度）
- [ ] 底部有控制台（Tab 面板）
- [ ] 顶部有工具栏
- [ ] 拖动分割线可以调整比例
- [ ] 关闭窗口后程序正常退出（无残留进程）

**验收**: 布局正确，可调整比例。

---

### Test 4: 暗色主题测试

**目的**: 验证暗色主题生效。

**检查项**:
- [ ] 背景色为深色（#1e1e1e 附近）
- [ ] 文字为浅色（#d4d4d4 附近）
- [ ] 工具栏背景深色
- [ ] 树控件背景深色
- [ ] 编辑器背景深色
- [ ] Tab 标签深色
- [ ] 按钮、输入框深色
- [ ] 状态栏蓝色背景

**验收**: 整体暗色主题一致。

---

### Test 5: 顶部工具栏测试

**目的**: 验证工具栏按钮和控件。

**检查项**:
- [ ] 显示 ▶ 运行 按钮
- [ ] 显示 ⏸ 暂停 按钮
- [ ] 显示 ⏯ 单步 按钮
- [ ] 显示 ↺ 重置 按钮
- [ ] 显示模型选择下拉框（deepseek-chat / deepseek-reasoner）
- [ ] 显示温度数值框（默认 0.7）
- [ ] F5 快捷键触发运行
- [ ] F6 快捷键触发暂停
- [ ] F10 快捷键触发单步

**验收**: 所有工具栏控件正常显示和响应。

---

### Test 6: 资源树测试

**目的**: 验证左侧七层资源树。

**前置**: 确保 `workspace/`、`skills/`、`prompts/` 目录下有测试文件。如果没有，先创建：

```bash
mkdir -p workspace/npcs workspace/locations workspace/story
echo "# 铁匠\n\n## 描述\n一个老铁匠。" > workspace/npcs/铁匠.md
echo "# 铁匠铺\n\n## 描述\n村口的铁匠铺。" > workspace/locations/铁匠铺.md
echo "# 系统提示词\n\n你是一个游戏世界的主宰者。" > prompts/system_prompt.md
mkdir -p skills/builtin/combat
echo "---\nname: combat\ntype: builtin\n---\n# 战斗技能" > skills/builtin/combat/SKILL.md
mkdir -p workflow
echo "nodes: []\nedges: []" > workflow/main_loop.yaml
```

**检查项**:
- [ ] 显示 🧠 Prompt 分类
- [ ] 显示 📁 Memory 分类
- [ ] 显示 ⚙️ Config 分类
- [ ] 显示 🔧 Tools 分类
- [ ] 显示 🔄 Workflow 分类
- [ ] 显示 📊 Runtime 分类
- [ ] Prompt 下有 system_prompt.md
- [ ] Memory 下有 npcs/、locations/ 目录
- [ ] npcs/ 下有 铁匠.md
- [ ] Workflow 下有 main_loop.yaml
- [ ] 目录可展开/折叠
- [ ] 文件名有颜色区分（.md 蓝色等）
- [ ] 右键点击文件弹出菜单（打开/重命名/删除/新建）

**验收**: 七层资源树正确显示真实文件。

---

### Test 7: 多态编辑器测试

**目的**: 验证中间编辑器根据文件类型切换。

**检查项**:

7.1 点击 `prompts/system_prompt.md`:
- [ ] 中间显示 Markdown 编辑器
- [ ] 内容为 "# 系统提示词\n\n你是一个游戏世界的主宰者。"
- [ ] 顶部显示 YAML Front Matter（如果有）

7.2 点击 `workspace/npcs/铁匠.md`:
- [ ] 中间切换到 Markdown 编辑器
- [ ] 内容为 "# 铁匠\n\n## 描述\n一个老铁匠。"

7.3 点击 `workflow/main_loop.yaml`:
- [ ] 中间切换到流程图编辑器
- [ ] 显示节点和连线

7.4 编辑保存测试:
- [ ] 在编辑器中修改内容
- [ ] 按 Ctrl+S 保存
- [ ] 重新打开文件，确认内容已保存

**验收**: 编辑器正确切换，保存功能正常。

---

### Test 8: 流程图编辑器测试

**目的**: 验证流程图编辑器功能。

**检查项**:
- [ ] 打开 workflow/main_loop.yaml 显示流程图
- [ ] 或直接在流程图编辑器中看到默认的 Agent 主循环
- [ ] 有节点显示（接收事件、构建 Prompt、LLM 推理等）
- [ ] 节点之间有连线
- [ ] 节点可拖拽移动
- [ ] 拖拽后连线自动跟随
- [ ] 点击节点高亮选中
- [ ] 下拉选择节点类型
- [ ] 点击"添加节点"按钮，新节点出现
- [ ] 点击"保存"按钮，YAML 文件更新

**验收**: 流程图编辑器基本功能正常。

---

### Test 9: 底部控制台测试

**目的**: 验证底部 5 个 Tab。

**检查项**:
- [ ] 显示 5 个 Tab: 执行控制 / 流程视图 / 轮次回溯 / 指令注入 / 强制工具
- [ ] Tab 切换正常
- [ ] 执行控制 Tab: 显示状态徽章 (IDLE) + 4 个按钮 + 日志区
- [ ] 轮次回溯 Tab: 左侧列表 + 右侧详情
- [ ] 指令注入 Tab: 级别选择 (system/user/override) + 输入框 + 发送按钮
- [ ] 强制工具 Tab: 工具选择 + 参数输入 + 执行按钮
- [ ] 底部控制台可拖动调整高度

**验收**: 底部控制台 5 个 Tab 正常。

---

### Test 10: Agent 交互测试

**目的**: 验证运行/暂停/单步/重置功能。

**前置**: 后端模块可用（src/ 存在且可 import）。

**检查项**:
- [ ] 启动时日志显示 "后端模块初始化成功"（或具体的初始化信息）
- [ ] 点击 ▶ 运行，状态徽章变为 RUNNING（蓝色）
- [ ] 日志区显示 Agent 处理信息
- [ ] 运行完成后状态回到 IDLE（绿色）
- [ ] 点击 ⏸ 暂停，状态变为 PAUSED（橙色）
- [ ] 点击 ↺ 重置，状态回到 IDLE
- [ ] 右侧 Agent 状态面板更新（状态、回合数等）

**注意**: 如果后端模块不可用（import 失败），Agent 交互测试可以跳过，但需要记录原因。

**验收**: Agent 交互基本流程正常（或记录跳过原因）。

---

### Test 11: 键盘快捷键测试

**目的**: 验证快捷键。

**检查项**:
- [ ] Ctrl+S 保存当前文件
- [ ] F5 运行
- [ ] F6 暂停
- [ ] F10 单步
- [ ] Q 退出（如果有绑定）

**验收**: 快捷键正常响应。

---

### Test 12: 文件操作测试

**目的**: 验证文件的增删改。

**检查项**:
- [ ] 右键 → 新建文件，在对应目录下创建新 .md 文件
- [ ] 新建文件出现在资源树中
- [ ] 打开新文件，编辑内容，保存
- [ ] 重新打开确认内容保存正确

**验收**: 文件操作正常。

---

## 测试结果汇总

测试完成后，输出以下格式的汇总：

```
## WorkBench 测试结果

| # | 测试项 | 结果 | 备注 |
|---|--------|------|------|
| 1 | 环境检查 | ✅/❌ | |
| 2 | 启动测试 | ✅/❌ | |
| 3 | 三栏布局 | ✅/❌ | |
| 4 | 暗色主题 | ✅/❌ | |
| 5 | 顶部工具栏 | ✅/❌ | |
| 6 | 资源树 | ✅/❌ | |
| 7 | 多态编辑器 | ✅/❌ | |
| 8 | 流程图编辑器 | ✅/❌ | |
| 9 | 底部控制台 | ✅/❌ | |
| 10 | Agent 交互 | ✅/❌/⏭️ | |
| 11 | 键盘快捷键 | ✅/❌ | |
| 12 | 文件操作 | ✅/❌ | |

总计: X/12 通过
```

## 注意事项

1. **GUI 测试需要显示环境**: Trae 可能无法直接显示 GUI 窗口。如果无法显示，改为**代码审查模式**：
   - 检查每个文件的代码是否正确
   - 检查 import 是否正确
   - 检查信号连接是否正确
   - 检查样式文件是否正确
   - 用 `python -c "from workbench.app import main; print('OK')"` 验证 import

2. **截图**: 如果能显示 GUI，截图保存测试结果。

3. **修复优先级**: 如果测试失败，按以下优先级修复：
   - P0: 启动崩溃 → 必须修复
   - P1: 布局错误 → 必须修复
   - P2: 功能不工作 → 尝试修复
   - P3: 样式问题 → 可以后修
