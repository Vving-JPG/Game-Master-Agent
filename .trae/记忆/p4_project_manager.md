# P4-03: ProjectManager 项目管理

> 模块: `presentation.project.manager`
> 文件: `2workbench/presentation/project/manager.py`
> 全局单例: `project_manager`

---

## 核心类

```python
class ProjectManager:
    """项目管理器"""
    
    # 属性
    current_project: ProjectConfig | None
    project_path: Path | None
    is_open: bool
    
    # 方法
    def create_project(
        self,
        name: str,
        template: str = "default",
        directory: str = ""
    ) -> Path
    
    def open_project(self, path: Path) -> ProjectConfig
    def save_project(self) -> bool
    def close_project(self)
    
    # 图相关
    def load_graph(self) -> dict
    def save_graph(self, graph_data: dict)
    
    # Prompt 相关
    def list_prompts(self) -> list[str]
    def load_prompt(self, name: str) -> str
    def save_prompt(self, name: str, content: str)
```

---

## 使用示例

```python
from presentation.project.manager import project_manager

# 创建项目
path = project_manager.create_project(
    name="我的冒险",
    template="fantasy",
    directory="./projects"
)

# 打开项目
config = project_manager.open_project(path)
print(f"项目: {config.name}")

# 保存图
graph_data = {"nodes": [...], "edges": [...]}
project_manager.save_graph(graph_data)

# 保存 Prompt
project_manager.save_prompt("narrative", "你是一个GM...")

# 列出所有 Prompts
prompts = project_manager.list_prompts()
```

---

## 项目配置

```python
@dataclass
class ProjectConfig:
    name: str
    template: str
    version: str
    created_at: datetime
    updated_at: datetime
```

---

## 项目结构

```
my_project/
├── project.json          # 项目配置
├── graph.json            # 图定义
├── prompts/              # Prompt 模板
│   ├── narrative.txt
│   ├── combat.txt
│   └── dialogue.txt
├── npcs/                 # NPC 定义
├── quests/               # 任务定义
└── saves/                # 存档
```
