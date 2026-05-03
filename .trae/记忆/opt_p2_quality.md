# P2: 硬编码样式清理 + 代码质量

> 优化阶段: P2 | 优先级: 🟠 高 | 状态: ✅ 已完成 | 预估工作量: 4-6 小时
> 相关文档: [优化大纲](../优化大纲.md) | [优化步骤P2](../优化步骤P2.md)

---

## 问题概述

清理全项目硬编码颜色和样式，统一使用主题管理器；修复代码质量问题。

---

## Step 2.1: 全局修复 self._logger → logger

### 问题描述
`self._logger` 错误已反复出现 3 次（event_monitor、prompt_editor、tool_manager），需全局排查。

### 修复方案

```bash
# 在 2workbench/ 目录下搜索所有 self._logger
grep -rn "self\._logger" 2workbench/presentation/
```

### 验证结果
✅ 全局搜索显示只有 `base.py` 中定义了 `self._logger`，无其他文件错误使用。

---

## Step 2.2: 清理 main_window.py 硬编码颜色

### 问题描述
QUAL-002 — 工具栏状态标签、欢迎页、右侧面板等硬编码颜色。

### 涉及行号
L200, L328, L803-813, L840-849

### 修复方案
使用 `theme_manager.get_color()` 替换硬编码颜色：

```python
# 修改前
label.setStyleSheet("color: #858585;")

# 修改后
from presentation.theme.manager import theme_manager
text_secondary = theme_manager.get_color("text_secondary")
label.setStyleSheet(f"color: {text_secondary};")
```

### 修复的颜色映射

| 原硬编码值 | 主题变量 | 使用位置 |
|-----------|---------|---------|
| `#858585` | `text_secondary` | 工具栏状态标签、欢迎页 |
| `#cccccc` | `text_primary` | 节点/工具描述 |
| `#4ec9b0` | `success` | Agent 运行中状态 |
| `#dcdcaa` | `warning` | 工具名称 |
| `#f44336` | `error` | Agent 错误状态 |

### 验证结果
✅ 无硬编码颜色残留

---

## Step 2.3: 清理 Ops 面板硬编码颜色

### 涉及文件及行号

| 文件 | 行号 | 硬编码值 |
|------|------|---------|
| `event_monitor.py` | L57, L115-119 | `#858585`, `#cccccc`, `#f44747`, `#4ec9b0`, `#569cd6`, `#dcdcaa`, `#6e6e6e` |
| `runtime_panel.py` | L57, L66-68, L78, L248 | `#858585`, 字体样式 |
| `knowledge_editor.py` | L394, L400 | `#858585` |
| `eval_workbench.py` | L91 | `#858585` |
| `deploy_manager.py` | L46, L97 | 样式硬编码 |

### 修复方案
统一使用主题变量替换：

```python
from presentation.theme.manager import theme_manager

# 事件类型颜色映射
color_map = {
    "DEBUG": theme_manager.get_color("text_secondary"),
    "INFO": theme_manager.get_color("text_primary"),
    "WARNING": theme_manager.get_color("warning"),
    "ERROR": theme_manager.get_color("error"),
}
```

### 验证结果
✅ 所有 Ops 面板无硬编码颜色残留

---

## Step 2.4: 清理 project_selector.py 硬编码样式

### 问题描述
ProjectCard 和 ProjectSelector 对话框大量硬编码暗色样式。

### 涉及文件及行号
`project_selector.py` L37-60, L128-159

### 修复方案
使用 `theme_manager.get_color()` 替换所有硬编码颜色：

```python
# 修改前
bg_primary = p.get("bg_primary", "#1e1e1e")
icon_colors = {"blank": "#569cd6", "trpg": "#4ec9b0", "chatbot": "#c586c0"}

# 修改后
bg_primary = theme_manager.get_color("bg_primary")
icon_colors = {
    "blank": theme_manager.get_color("info"),
    "trpg": theme_manager.get_color("success"),
    "chatbot": theme_manager.get_color("warning")
}
```

### 验证结果
✅ 所有硬编码颜色已替换为主题变量

---

## Step 2.5: 清理 graph_editor.py 硬编码字体

### 问题描述
L92, L104, L275 字体硬编码 `Microsoft YaHei`

### 修复方案
跨平台字体检测：

```python
from PyQt6.QtGui import QFont, QFontDatabase

# 修改前
font = QFont("Microsoft YaHei", 9)

# 修改后
font = QFont("Microsoft YaHei", 10, QFont.Weight.Bold) if "Microsoft YaHei" in QFontDatabase.families() else QFont("Segoe UI", 10, QFont.Weight.Bold)
```

### 验证结果
✅ 3处字体已使用跨平台检测

---

## Step 2.6: 清理未使用的导入

### 问题描述
`tool_manager.py` L22 有未使用的 `QPushButton` 导入。

### 修复方案
```python
# 移除前
from PyQt6.QtWidgets import (
    ..., QPushButton,
)

# 移除后
from PyQt6.QtWidgets import (
    ...,  # 无 QPushButton
)
```

### 验证结果
✅ `QPushButton` 已移除

---

## Step 2.7: app.py print → logger

### 问题描述
`app.py` L75 使用 `print` 输出错误信息。

### 修复方案
```python
# 修改前
print(f"错误: 项目路径不存在: {args.project}")

# 修改后
logger.error(f"项目路径不存在: {args.project}")
```

### 验证结果
✅ `print` 已替换为 `logger.error`

---

## 相关文件

| 文件 | 修改内容 |
|------|---------|
| [main_window.py](../../2workbench/presentation/main_window.py) | 16处颜色替换 |
| [runtime_panel.py](../../2workbench/presentation/ops/debugger/runtime_panel.py) | 颜色主题化 |
| [event_monitor.py](../../2workbench/presentation/ops/debugger/event_monitor.py) | 颜色主题化 |
| [knowledge_editor.py](../../2workbench/presentation/ops/knowledge/knowledge_editor.py) | 颜色主题化 |
| [eval_workbench.py](../../2workbench/presentation/ops/evaluator/eval_workbench.py) | 颜色主题化 |
| [log_viewer.py](../../2workbench/presentation/ops/logger_panel/log_viewer.py) | 颜色主题化 |
| [safety_panel.py](../../2workbench/presentation/ops/safety/safety_panel.py) | 颜色主题化 |
| [project_selector.py](../../2workbench/presentation/dialogs/project_selector.py) | QSS模板化 |
| [graph_editor.py](../../2workbench/presentation/editor/graph_editor.py) | 跨平台字体 |
| [tool_manager.py](../../2workbench/presentation/editor/tool_manager.py) | 移除未使用导入 |
| [app.py](../../2workbench/app.py) | print→logger |

---

## 验收标准

- [x] 全项目无 `self._logger` 残留
- [x] 所有日志正常输出
- [x] Dark 主题下颜色正确
- [x] Light 主题下颜色正确
- [x] 切换主题后即时更新
- [x] 所有 Ops 面板跟随主题切换
- [x] 无硬编码颜色值残留
- [x] 跨平台字体正确显示
- [x] 无 IDE 警告

---

*创建时间: 2026-05-03*
*更新记录: 初始创建*
