# P6 结构化状态 API

> 让 GUI "告诉" AI 它的状态，而不是让 AI "看" GUI
> 创建时间: 2026-05-02

---

## 1. 核心思路

### 1.1 问题：截图方式的局限

```
# 截图方式（旧）
AI → 截图 → 看像素 → 猜"有个按钮叫运行" → 点击坐标
                 ↓
        [不可靠、慢、容易错]

# 结构化方式（新）
AI → GET /api/dom → {"buttons": [{"id": "run", "text": "▶ 运行"}]} → 点击 id=run
                 ↓
        [可靠、快、精确]
```

### 1.2 三层方案组合

```
┌─────────────────────────────────────────────┐
│           Trae AI 获取信息的方式              │
├─────────────────────────────────────────────┤
│                                             │
│  1️⃣ GET /api/state     ← 最快，获取业务状态  │
│     用途: "Agent 在运行吗？" "当前项目是？"    │
│                                             │
│  2️⃣ GET /api/dom       ← 结构化，获取 UI 状态│
│     用途: "有哪些标签页？" "控制台最后输出？"  │
│                                             │
│  3️⃣ GET /api/screenshot ← 兜底，视觉验证     │
│     用途: "布局对不对？" "主题切换效果？"      │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 2. 方案 1: Widget Tree API (/api/dom)

### 2.1 核心类

**位置**: `presentation/state_api.py` - `WidgetTreeSerializer`

```python
class WidgetTreeSerializer:
    """Widget 树序列化器"""

    def serialize(
        self,
        widget: QWidget,
        depth: int = 0,
        selector: str | None = None,   # CSS-like 选择器
        diff: bool = False              # 只返回变化部分
    ) -> dict | None:
```

### 2.2 输出格式

```json
{
  "class": "MainWindow",
  "id": "main_window",
  "text": "Game Master Agent IDE",
  "visible": true,
  "enabled": true,
  "geometry": {
    "x": 100, "y": 100,
    "width": 1920, "height": 1080
  },
  "properties": {
    // 类型特定属性
  },
  "children": [
    {
      "class": "QPushButton",
      "id": "run_button",
      "text": "▶ 运行",
      "properties": {
        "checked": false,
        "checkable": false,
        "flat": false
      }
    }
  ]
}
```

### 2.3 选择器语法

| 选择器 | 说明 | 示例 |
|--------|------|------|
| `#id` | 按 objectName | `#run_button` |
| `.class` | 按类名 | `.QPushButton` |
| `console` | 预定义：控制台 | `console` |
| `editor` | 预定义：编辑器 | `editor` |
| `sidebar` | 预定义：侧边栏 | `sidebar` |
| `toolbar` | 预定义：工具栏 | `toolbar` |

### 2.4 支持的控件类型

- **QTabWidget**: `tab_count`, `current_index`, `tabs`
- **QTextEdit**: `line_count`, `character_count`, `last_lines`
- **QTableWidget**: `row_count`, `column_count`
- **QPushButton**: `checked`, `checkable`, `flat`
- **QComboBox**: `item_count`, `editable`, `items`
- **QCheckBox**: `checked`, `tristate`
- **QSlider**: `minimum`, `maximum`, `value`, `orientation`
- **QProgressBar**: `minimum`, `maximum`, `value`
- **QTreeWidget**: `top_level_item_count`, `header_labels`
- **QSplitter**: `orientation`, `sizes`

---

## 3. 方案 2: 应用状态 API (/api/state)

### 3.1 核心类

**位置**: `presentation/state_api.py` - `ApplicationStateProvider`

```python
class ApplicationStateProvider:
    """应用状态提供者"""

    def get_state(self, use_cache: bool = True) -> dict:
        """获取完整应用状态"""
```

### 3.2 状态结构

```json
{
  "timestamp": 1714620000.123,
  "project": {
    "open": true,
    "name": "my_agent",
    "path": "data/my_agent.agent",
    "template": "trpg"
  },
  "agent": {
    "status": "idle",
    "turn": 5,
    "model": "deepseek-chat"
  },
  "features": {
    "battle": {"enabled": true, "description": "战斗系统"},
    "dialogue": {"enabled": true, "description": "对话系统"}
  },
  "editor": {
    "active_tab": "graph_editor",
    "modified": false,
    "open_files": ["graph_editor", "prompt_editor"]
  },
  "console": {
    "last_lines": ["玩家说: 攻击", "🤖 你挥剑砍向哥布林..."],
    "line_count": 42
  },
  "ui": {
    "theme": "dark",
    "window": {
      "title": "my_agent - Game Master Agent IDE",
      "size": {"width": 1920, "height": 1080}
    }
  },
  "metrics": {
    "tokens": 1500,
    "cost": 0.03,
    "errors": 0
  }
}
```

---

## 4. 方案 3: Windows UI Automation (/api/uia)

### 4.1 核心类

**位置**: `presentation/state_api.py` - `WindowsUIAutomationProvider`

```python
class WindowsUIAutomationProvider:
    """Windows UI Automation 提供者"""

    def get_ui_tree(self, hwnd: int | None = None) -> dict:
        """获取 UI 自动化树"""
```

### 4.2 依赖

```bash
pip install comtypes
```

### 4.3 输出格式

```json
{
  "control_type": "Window",
  "name": "Game Master Agent IDE",
  "class_name": "Qt662QWindowIcon",
  "automation_id": "",
  "enabled": true,
  "visible": true,
  "bounding_rectangle": {
    "left": 100, "top": 100,
    "right": 2020, "bottom": 1180
  },
  "children": [
    {
      "control_type": "Button",
      "name": "运行",
      "class_name": "QPushButton"
    }
  ]
}
```

---

## 5. 统一门面: StateAPI

### 5.1 核心类

**位置**: `presentation/state_api.py` - `StateAPI`

```python
class StateAPI:
    """结构化状态 API 门面"""

    def get_dom(self, selector: str | None = None, diff: bool = False) -> dict
    def get_state(self) -> dict
    def get_uia_tree(self, hwnd: int | None = None) -> dict
    def find_widget(self, query: dict) -> dict
    def get_widget_by_path(self, path: str) -> dict
```

### 5.2 初始化

```python
from presentation.state_api import init_state_api, get_state_api

# 在 MainWindow 初始化时
init_state_api(self)

# 在其他地方获取
api = get_state_api()
```

---

## 6. HTTP API 端点

### 6.1 新增端点

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/state` | GET | - | 获取应用状态 |
| `/api/dom` | GET | `selector`, `diff` | 获取 Widget DOM |
| `/api/uia` | GET | - | 获取 UIA 树 |
| `/api/find` | GET | `id`, `class`, `text` | 查找 Widget |

### 6.2 使用示例

```bash
# 获取应用状态
curl http://localhost:18080/api/state

# 获取完整 DOM
curl http://localhost:18080/api/dom

# 获取控制台区域
curl http://localhost:18080/api/dom?selector=console

# 获取 DOM 变化
curl http://localhost:18080/api/dom?diff=true

# 查找按钮
curl "http://localhost:18080/api/find?id=run_button"
```

---

## 7. CLI 工具

### 7.1 命令

```bash
# 获取应用状态
python gui_ctl.py state
python gui_ctl.py state --json

# 获取 Widget DOM
python gui_ctl.py dom
python gui_ctl.py dom --selector console
python gui_ctl.py dom --selector editor
python gui_ctl.py dom --diff

# 获取 UIA 树
python gui_ctl.py uia

# 查找 Widget
python gui_ctl.py find --id run_button
python gui_ctl.py find --class QPushButton --text "运行"
```

### 7.2 输出示例

```bash
$ python gui_ctl.py state
📁 项目: my_agent (已打开)
🤖 Agent: idle | 回合: 5 | 模型: deepseek-chat
⚡ Features (3 启用): battle, dialogue, quest
📝 编辑器: graph_editor
🎨 主题: dark | 窗口: 1920x1080
```

---

## 8. 文件位置

```
2workbench/
├── presentation/
│   ├── state_api.py          # 核心实现 (新)
│   └── server.py             # HTTP 端点 (已更新)
└── ...

.trae/
├── skills/
│   └── workbench-gui/
│       └── gui_ctl.py        # CLI 工具 (已更新)
└── 记忆/
    ├── p6_state_api.md       # 本文档 (新)
    └── memory-guide.md       # 导航 (需更新)
```

---

## 9. 使用场景

### 9.1 AI 自动化测试

```python
# 不需要截图，直接获取状态
state = requests.get("http://localhost:18080/api/state").json()

if state["agent"]["status"] == "idle":
    # 点击运行按钮
    requests.post("http://localhost:18080/api/run", json={"event": "开始"})
```

### 9.2 精确查找控件

```python
# 查找特定按钮
dom = requests.get("http://localhost:18080/api/find?id=save_btn").json()

for widget in dom["results"]:
    print(f"找到按钮: {widget['text']} at ({widget['geometry']['x']}, {widget['geometry']['y']})")
```

### 9.3 监控变化

```python
# 只获取变化部分
diff = requests.get("http://localhost:18080/api/dom?diff=true").json()

for change in diff["tree"]["changed"]:
    print(f"{change['id']}.{change['field']}: {change['old']} → {change['new']}")
```

---

## 10. 与旧 API 对比

| 场景 | 旧方式 | 新方式 | 优势 |
|------|--------|--------|------|
| 检查 Agent 状态 | 截图 → OCR → 识别 | `GET /api/state` | 100% 准确 |
| 查找按钮 | 截图 → 视觉定位 | `GET /api/find?id=xxx` | 精确、快速 |
| 获取控制台输出 | 截图 → OCR | `GET /api/dom?selector=console` | 完整文本 |
| 验证布局 | 截图 → 视觉对比 | `GET /api/dom` | 结构化对比 |

---

*文档版本: 1.0*
*关联: workbench_w5w7.md, p5_gui_ops.md*
