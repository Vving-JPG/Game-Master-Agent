# P1: 回归 Bug 紧急修复

> 优化阶段: P1 | 优先级: 🔴 最高 | 状态: ✅ 已完成
> 相关文档: [优化大纲](../优化大纲.md) | [优化步骤P1](../优化步骤P1.md)

---

## 问题概述

v4 版本引入的 2 个新回归 Bug（崩溃级），需要紧急修复。

---

## Step 1.1: BUG-017 - runtime_panel.py self._count_label 未定义

### 问题描述
- **文件**: `2workbench/presentation/ops/debugger/runtime_panel.py`
- **行号**: L130 (引用位置)
- **严重性**: 🔴 致命 — 流式输出时 AttributeError

### 根因分析
`_update_stats()` 方法引用了 `self._count_label`，但 `_setup_ui` 中从未创建该 QLabel。

### 修复方案
在 `_setup_ui` 的统计标签区域添加：

```python
# L73-77
self._count = 0
self._line_count_int = 0  # 行数统计（整数）
self._count_label = QLabel("字符: 0")  # 字符数标签
self._count_label.setStyleSheet(f"color: {text_secondary}; font-size: 11px;")
toolbar.addWidget(self._count_label)
```

### 使用位置
```python
# L137-139
def _update_stats(self) -> None:
    """更新统计显示"""
    self._count_label.setText(f"字符: {self._count}")
```

### 验证结果
✅ `_count_label` 在 L75 正确定义，L139 正确使用，无 AttributeError

---

## Step 1.2: BUG-018 - tool_manager.py self._logger 未定义

### 问题描述
- **文件**: `2workbench/presentation/editor/tool_manager.py`
- **行号**: L395, L415, L417
- **严重性**: 🔴 致命 — 添加自定义工具时 AttributeError

### 根因分析
代码中使用了 `self._logger`，但该变量未定义。应使用模块级 `logger`。

### 修复方案
使用模块级 logger：

```python
# L30
logger = get_logger(__name__)

# L394-416 使用方式
logger.info(f"自定义工具添加: {name}")
logger.info(f"工具已注册到 Agent: {tool.name}")
logger.error(f"工具注册到 Agent 失败: {e}")
```

### 验证结果
✅ 代码使用的是模块级 `logger`，非 `self._logger`，无问题

---

## 相关文件

| 文件 | 修改内容 |
|------|---------|
| [runtime_panel.py](../../2workbench/presentation/ops/debugger/runtime_panel.py) | 添加 `_count_label` 定义 |
| [tool_manager.py](../../2workbench/presentation/editor/tool_manager.py) | 使用模块级 logger |

---

## 验收标准

- [x] 全项目无 `self._logger` 残留
- [x] 所有日志正常输出
- [x] 流式输出时字符数正确更新
- [x] 不抛出 AttributeError

---

*创建时间: 2026-05-03*
*更新记录: 初始创建*
