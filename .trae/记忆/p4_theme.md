# P4-02: Theme 主题管理

> 模块: `presentation.theme.manager`
> 文件: `2workbench/presentation/theme/manager.py`
> 全局单例: `theme_manager`

---

## 核心类

```python
class ThemeManager:
    """主题管理器"""
    
    def apply(self, theme_name: str) -> bool
    def get_current_theme(self) -> str
    def get_available_themes(self) -> list[str]
    def get_stylesheet(self, theme_name: str) -> str
```

---

## 使用示例

```python
from presentation.theme.manager import theme_manager

# 应用主题
theme_manager.apply("dark")
theme_manager.apply("light")

# 获取当前主题
current = theme_manager.get_current_theme()

# 列出可用主题
themes = theme_manager.get_available_themes()
# ['dark', 'light']
```

---

## 内置主题

### Dark 主题

```python
DARK_THEME = {
    "background": "#1e1e1e",
    "foreground": "#d4d4d4",
    "accent": "#4ec9b0",
    "secondary": "#252526",
    "border": "#3e3e42",
    "error": "#f44336",
    "warning": "#ff9800",
    "success": "#4caf50",
}
```

### Light 主题

```python
LIGHT_THEME = {
    "background": "#ffffff",
    "foreground": "#333333",
    "accent": "#007acc",
    "secondary": "#f3f3f3",
    "border": "#e0e0e0",
    "error": "#d32f2f",
    "warning": "#f57c00",
    "success": "#388e3c",
}
```

---

## QSS 样式表

```python
# 获取完整 QSS
stylesheet = theme_manager.get_stylesheet("dark")

# 应用到应用
app.setStyleSheet(stylesheet)
```

---

## 自定义主题

```python
# 注册自定义主题
theme_manager.register_theme("custom", {
    "background": "#2d2d2d",
    "foreground": "#f0f0f0",
    # ...
})

# 应用自定义主题
theme_manager.apply("custom")
```
