# P4 Presentation - ProjectSelector & NewProjectDialog

> 项目选择器和新建项目对话框的细粒度记忆
> 涉及文件:
> - `presentation/dialogs/project_selector.py`
> - `presentation/project/new_dialog.py`

---

## 架构定位

属于 **P4 Presentation 层**，是应用的入口界面组件。

```
P4 Presentation 层
├── main_window.py          # 主窗口
├── project/manager.py      # 项目管理器
├── project/new_dialog.py   # 新建项目对话框 ⭐
└── dialogs/
    └── project_selector.py # 项目选择器 ⭐
```

---

## ProjectSelector 项目选择器

### 核心功能

仿 Godot 4.6 项目管理器的启动界面，提供项目列表展示、筛选、排序和操作功能。

### UI 结构 (4层布局)

```
┌──────────────────────────────────────────────────────────────┐
│ 🎲 Game Master Agent    [📋 项目] [📦 资产库]                │  Header (64px)
├──────────────────────────────────────────────────────────────┤
│ [➕ 新建] [📂 导入] [🔍 扫描]  [筛选...]    排序: [最近编辑▼] │  Toolbar (40px)
├────────────────────────────────────────────────┬─────────────┤
│                                                │  ✏️ 编辑    │
│  📄 [🟦] 项目名称                              │  ▶ 运行    │
│      📁 /path/to/project        2026-05-03    │  📝 重命名  │
│                                                │  📄 创建副本│
│  🎲 [🟩] TRPG Game                             │  🏷️ 管理标签│
│      📁 /path/to/trpg           2026-05-02    │  🗑️ 移除    │
│                                                │  🔗 移除缺失│
│                                                │  ─────────  │
│                                                │  ℹ️ 关于    │
├────────────────────────────────────────────────┴─────────────┤
│                                          v2.0.0              │  Footer (28px)
└──────────────────────────────────────────────────────────────┘
```

### 关键类

#### ProjectItemDelegate (自定义绘制)

```python
class ProjectItemDelegate(QStyledItemDelegate):
    """自定义项目列表项绘制"""
    
    def paint(self, painter, option, index):
        # 绘制逻辑:
        # 1. 背景 (选中/悬停/默认)
        # 2. 底部分割线
        # 3. 48x48 图标区域 (圆角矩形 + emoji)
        # 4. 项目名称 (14px, 白色)
        # 5. 项目路径 (11px, 灰色, 📁 前缀)
        # 6. 修改时间 (右侧, 11px, 灰色)
    
    def sizeHint(self, option, index):
        return QSize(0, 72)  # 固定行高 72px
```

#### ProjectSelector (主对话框)

```python
class ProjectSelector(QDialog):
    # 信号定义
    project_selected = pyqtSignal(str)      # 发射选中的项目路径
    new_project_requested = pyqtSignal()     # 请求创建新项目
    
    # 核心方法
    def _setup_ui(self) -> None              # 初始化 4 层布局
    def _load_projects(self) -> None         # 扫描并加载项目
    def _apply_filter_and_sort(self) -> None # 筛选 + 排序
    def _refresh_list(self) -> None          # 刷新列表显示
    def refresh_theme(self) -> None          # 外部主题切换时调用
```

### 项目数据结构

```python
{
    "name": "项目名称",
    "path": "/path/to/project.agent",
    "template": "blank",  # blank | trpg | chatbot
    "modified": "2026-05-03",
    "created": "2026-05-01"
}
```

### 颜色映射 (模板图标)

| 模板 | 颜色 | Hex |
|------|------|-----|
| blank | 蓝色 | `#569cd6` |
| trpg | 绿色 | `#4ec9b0` |
| chatbot | 紫色 | `#c586c0` |

### 主题颜色变量

从 `theme_manager.PALETTES` 获取:
- `bg_primary`: 主背景 (#1e1e1e)
- `bg_secondary`: 次背景 (#252526)
- `bg_hover`: 悬停背景 (#3e3e42)
- `accent`: 强调色 (#007acc)
- `text_bright`: 亮色文字 (#ffffff)
- `text_secondary`: 次色文字 (#858585)
- `border`: 边框色 (#3e3e42)
- `error`: 错误色 (#f44747)

---

## NewProjectDialog 新建项目对话框

### 核心功能

创建新项目时弹出的对话框，支持选择模板和设置项目路径。

### UI 结构

```
┌─────────────────────────────────────────┐
│  创建新项目                             │
│                                         │
│  项目名称                               │
│  ┌─────────────────────────────────┐    │
│  │ my_agent                        │    │
│  └─────────────────────────────────┘    │
│                                         │
│  项目路径                               │
│  ┌────────────────────────────┐ ┌────┐  │
│  │ /path/to/data              │ │浏览│  │
│  └────────────────────────────┘ └────┘  │
│                                         │
│  选择模板                               │
│  ┌────────┐  ┌────────┐  ┌────────┐    │
│  │  📄    │  │  🎲    │  │  🤖    │    │
│  │空白项目│  │TRPG游戏│  │对话机器│    │
│  │        │  │        │  │  人    │    │
│  └────────┘  └────────┘  └────────┘    │
│                                         │
│  <b>模板名</b> — 描述<br>               │
│  节点数: X | 边数: Y | Prompt: ...      │
│                                         │
│       ┌────┐              ┌────────┐    │
│       │取消│              │创建并运│    │
│       └────┘              │行      │    │
│                           └────────┘    │
└─────────────────────────────────────────┘
```

### 关键类

#### TemplateCard (模板卡片)

```python
class TemplateCard(QFrame):
    """模板选择卡片"""
    
    def __init__(self, icon: str, name: str, template_key: str, color: str):
        # icon: emoji 图标 (📄 🎲 🤖)
        # name: 显示名称
        # template_key: 模板键 (blank/trpg/chatbot)
        # color: 边框高亮色
```

#### NewProjectDialog (主对话框)

```python
class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        self._project_dir: Path          # 项目保存目录
        self._selected_template: str      # 当前选中模板
        self._template_cards: dict       # 模板卡片字典
    
    def on_template_selected(self, template_key: str) -> None:
        """模板被选中时调用"""
    
    def _on_browse_path(self) -> None:
        """浏览选择项目保存位置"""
    
    def get_project_data(self) -> dict:
        """获取用户输入的项目数据"""
        return {
            "name": self._name_edit.text().strip(),
            "template": self._selected_template,
            "description": "",
            "directory": str(self._project_dir),  # 新增字段
        }
```

### 模板颜色

| 模板 | 颜色 | Hex |
|------|------|-----|
| blank | 蓝色 | `#569cd6` |
| trpg | 绿色 | `#4ec9b0` |
| chatbot | 紫色 | `#c586c0` |

---

## 调用关系

### 启动流程

```
app.py
  └── 显示 ProjectSelector
       ├── 用户选择项目 → project_selected.emit(path) → 打开项目
       └── 用户点击新建 → new_project_requested.emit() → 显示 NewProjectDialog
                                                       └── get_project_data()
                                                           └── 创建项目
```

### 菜单调用

```
main_window.py
  └── _on_new_project()
       └── NewProjectDialog
            └── get_project_data()
                └── create_project_requested.emit(name, template, directory, "")
```

---

## 注意事项

1. **颜色来源**: 所有颜色从 `theme_manager.PALETTES` 获取，禁止硬编码
2. **日志使用**: 使用模块级 `logger`，禁止 `print`
3. **信号接口**: 保持向后兼容
   - `project_selected(str)`: 项目路径
   - `new_project_requested()`: 无参数
4. **主题刷新**: `refresh_theme()` 方法供外部调用
5. **项目扫描**: 扫描 `.agent` 后缀目录，读取 `project.json`

---

## 相关文件

- `presentation/dialogs/project_selector.py` - 项目选择器
- `presentation/project/new_dialog.py` - 新建项目对话框
- `presentation/project/manager.py` - 项目管理器
- `presentation/theme/manager.py` - 主题管理器
