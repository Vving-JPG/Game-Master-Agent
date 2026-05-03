# P1: 回归 Bug 紧急修复

> 优先级: 🔴 最高 | 状态: ✅ 已完成
> 修复本次更新引入的 3 个崩溃级回归 BUG

---

## BUG-014: prompt_editor.py self._logger 不存在

**文件**: `2workbench/presentation/editor/prompt_editor.py` L234

**问题**: 模块级别定义的是 `logger`，但代码使用了 `self._logger`

**修复**:
```python
# 修改前
self._logger.info(f"Prompt 保存: {self._current_prompt} ({len(content)} 字符)")

# 修改后
logger.info(f"Prompt 保存: {self._current_prompt} ({len(content)} 字符)")
```

---

## BUG-015: runtime_panel.py QLabel 整数运算

**文件**: `2workbench/presentation/ops/debugger/runtime_panel.py` L113

**问题**: `self._line_count` 是 QLabel 对象，不能直接 `+=` 整数

**修复**:
```python
# __init__ 中添加
self._line_count_int = 0  # 行数统计（整数）

# 修改 append_stream_token
if '\n' in token:
    self._line_count_int += token.count('\n')  # 使用整数变量
```

---

## BUG-016: runtime_panel.py _update_stats() 不存在

**文件**: `2workbench/presentation/ops/debugger/runtime_panel.py` L114

**问题**: `ConsoleOutput` 类中没有定义 `_update_stats()` 方法

**修复**:
```python
def _update_stats(self) -> None:
    """更新统计显示"""
    self._count_label.setText(f"字符: {self._count}")
    self._line_count.setText(f"行数: {self._line_count_int}")
```

同时更新 `clear()` 方法:
```python
def clear(self) -> None:
    """清空输出"""
    self._output.clear()
    self._count = 0
    self._line_count_int = 0  # 重置整数计数
    self._line_count.setText("行数: 0")
```

---

## 验证方法

```bash
cd 2workbench
python -m py_compile presentation/editor/prompt_editor.py
python -m py_compile presentation/ops/debugger/runtime_panel.py
```

---

## 相关文件

- `presentation/editor/prompt_editor.py`
- `presentation/ops/debugger/runtime_panel.py`
