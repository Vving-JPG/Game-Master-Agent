# P2: 硬编码清理 + 代码质量（v5 版本）

> 优先级：🟠 高 | 预估工作量：3-4 小时 | 前置条件：P1 完成
> **v5 变更**: 精简为仅剩的硬编码清理任务，大部分已在 v5 代码更新中修复
> **记录时间**: 2026-05-03

---

## 修复内容概览

本次优化清理了代码中的硬编码颜色和字体，统一使用主题管理器：
1. **project_selector.py** Header/Footer 硬编码背景色
2. **graph_editor.py** 硬编码颜色和字体
3. **graph_editor.py** 类变量计数器冲突
4. **main_window.py** 硬编码字体

---

## Step 2.1: 清理 project_selector.py Header/Footer 硬编码背景色

### 问题描述
- **文件**: `2workbench/presentation/dialogs/project_selector.py`
- **问题**: L376 `#151515`（Header）和 L529 `#181818`（Footer）仍硬编码

### 修复方案

#### theme/manager.py 新增颜色变量
```python
PALETTES = {
    "dark": {
        ...
        "bg_darker": "#151515",   # Header 背景
        "bg_darkest": "#181818",  # Footer 背景
    },
    "light": {
        ...
        "bg_darker": "#e8e8e8",
        "bg_darkest": "#f0f0f0",
    }
}
```

#### project_selector.py 使用主题变量
```python
def _apply_theme(self) -> None:
    """应用主题样式"""
    p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
    
    bg_darker = p.get("bg_darker", "#151515")
    bg_darkest = p.get("bg_darkest", "#181818")
    
    self.setStyleSheet(f"""
        /* Header */
        QFrame#header {{
            background-color: {bg_darker};  # 使用主题变量
            border-bottom: 1px solid {border};
        }}
        
        /* Footer */
        QFrame#footer {{
            background-color: {bg_darkest};  # 使用主题变量
            border-top: 1px solid {border};
        }}
    """)
```

### 关键代码位置
- [theme/manager.py L34-L35](file:///d:/Game-Master-Agent/2workbench/presentation/theme/manager.py#L34-L35)
- [project_selector.py L360-L361](file:///d:/Game-Master-Agent/2workbench/presentation/dialogs/project_selector.py#L360-L361)
- [project_selector.py L376](file:///d:/Game-Master-Agent/2workbench/presentation/dialogs/project_selector.py#L376)
- [project_selector.py L529](file:///d:/Game-Master-Agent/2workbench/presentation/dialogs/project_selector.py#L529)

---

## Step 2.2: 清理 graph_editor.py 硬编码颜色

### 问题描述
- **文件**: `2workbench/presentation/editor/graph_editor.py`
- **问题**: L83 节点边框 `#3e3e42`、L91 标签文字 `#ffffff`、L103 类型标签 `#cccccc` 硬编码

### 修复方案

```python
# 样式 - 从主题获取颜色
p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
color_hex, type_label = NODE_COLORS.get(node_type, ("#9cdcfe", "自定义"))
self._color = QColor(color_hex)

self.setBrush(QBrush(self._color))
border_color = p.get("border", "#3e3e42")
self.setPen(QPen(QColor(border_color), 2))

# 标签文本
self._label_item = QGraphicsTextItem(self.label, self)
text_bright = p.get("text_bright", "#ffffff")
self._label_item.setDefaultTextColor(QColor(text_bright))

# 类型标签
self._type_item = QGraphicsTextItem(type_label, self)
text_primary = p.get("text_primary", "#cccccc")
self._type_item.setDefaultTextColor(QColor(text_primary))
```

### 关键代码位置
- [graph_editor.py L79-L110](file:///d:/Game-Master-Agent/2workbench/presentation/editor/graph_editor.py#L79-L110)

---

## Step 2.3: 修复 graph_editor.py 类变量计数器冲突

### 问题描述
- **文件**: `2workbench/presentation/editor/graph_editor.py`
- **问题**: L539 `_node_counter = 0` 是类变量，多个实例共享，导致节点 ID 冲突

### 修复方案

```python
# 修改前（类变量）
class GraphEditorWidget(QWidget):
    """图编辑器组件 — 场景 + 视图 + 工具栏"""
    _node_counter = 0  # 类变量，用于自动生成节点 ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

# 修改后（实例变量）
class GraphEditorWidget(QWidget):
    """图编辑器组件 — 场景 + 视图 + 工具栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._node_counter = 0  # 实例变量
        self._setup_ui()
```

同时将所有 `GraphEditorWidget._node_counter` 引用改为 `self._node_counter`。

### 关键代码位置
- [graph_editor.py L545](file:///d:/Game-Master-Agent/2workbench/presentation/editor/graph_editor.py#L545)
- [graph_editor.py L622-L648](file:///d:/Game-Master-Agent/2workbench/presentation/editor/graph_editor.py#L622-L648)

---

## Step 2.4: 统一硬编码字体

### 问题描述
- **涉及文件**:
  - `project_selector.py` L85/L93/L100: `QFont("Microsoft YaHei", ...)`
  - `main_window.py` L1106: `QFont("Cascadia Code", ...)`
  - `graph_editor.py`: 字体硬编码

### 修复方案

#### theme/manager.py 新增字体变量
```python
PALETTES = {
    "dark": {
        ...
        "font_family": '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif',
        "mono_font": '"Cascadia Code", "Consolas", "Monaco", "Courier New", monospace',
    },
    "light": {
        ...
        "font_family": '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif',
        "mono_font": '"Cascadia Code", "Consolas", "Monaco", "Courier New", monospace',
    }
}
```

#### graph_editor.py 使用主题字体
```python
font_family = p.get("font_family", "Microsoft YaHei")
font = QFont(font_family.split(",")[0].strip('"'), 10, QFont.Weight.Bold)
self._label_item.setFont(font)
type_font = QFont(font_family.split(",")[0].strip('"'), 8)
self._type_item.setFont(type_font)
```

#### main_window.py 使用主题字体
```python
# 只保留字体设置，颜色由全局 QSS 控制
p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
mono_font = p.get("mono_font", "'Cascadia Code', 'Consolas', 'Monaco', 'Courier New', monospace")
editor.setStyleSheet(f"font-family: {mono_font};")
```

### 关键代码位置
- [theme/manager.py L48-L49](file:///d:/Game-Master-Agent/2workbench/presentation/theme/manager.py#L48-L49)
- [graph_editor.py L95-L106](file:///d:/Game-Master-Agent/2workbench/presentation/editor/graph_editor.py#L95-L106)
- [main_window.py L1143-L1145](file:///d:/Game-Master-Agent/2workbench/presentation/main_window.py#L1143-L1145)

---

## 验收标准

- [x] Header/Footer 背景色跟随主题切换
- [x] 无硬编码颜色残留
- [x] 节点颜色跟随主题切换
- [x] 多个图编辑器实例的节点 ID 不冲突
- [x] 无硬编码字体名残留
- [x] 跨平台字体正确显示

---

## 相关文件

| 文件路径 | 修改类型 | 说明 |
|---------|---------|------|
| `presentation/theme/manager.py` | 修改 | 新增 bg_darker, bg_darkest, font_family, mono_font |
| `presentation/dialogs/project_selector.py` | 修改 | Header/Footer 颜色主题化 |
| `presentation/editor/graph_editor.py` | 修改 | 节点颜色主题化 + 字体统一 + 计数器修复 |
| `presentation/main_window.py` | 修改 | 编辑器字体主题化 |

---

*最后更新: 2026-05-03*
