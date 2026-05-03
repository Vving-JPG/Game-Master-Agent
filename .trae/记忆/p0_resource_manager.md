# P0-08: ResourceManager 资源管理

> 模块: `foundation.resource_manager`
> 文件: `2workbench/foundation/resource_manager.py`

---

## 核心类

```python
class ResourceManager:
    def __init__(self, base_path: str)
    
    # 文件操作
    def read_file(self, path: str) -> str
    def write_file(self, path: str, content: str)
    def delete_file(self, path: str) -> bool
    def exists(self, path: str) -> bool
    
    # 目录操作
    def scan_directory(self, sub_path: str = "") -> dict
    def ensure_dir(self, path: str)
    
    # 安全操作
    def safe_path(self, path: str) -> Path  # 防止目录遍历
```

---

## 使用示例

```python
from foundation.resource_manager import ResourceManager

rm = ResourceManager(base_path="./workspace")

# 扫描目录
tree = rm.scan_directory()

# 读写文件
rm.write_file("npcs/张三.md", "# 张三\n\n一个勇敢的战士。")
content = rm.read_file("npcs/张三.md")

# 确保目录存在
rm.ensure_dir("quests/main")

# 安全路径检查
safe = rm.safe_path("../../../etc/passwd")  # 会规范化并限制在 base_path 内
```

---

## 安全特性

- 🔒 防止目录遍历攻击
- ✅ 路径规范化
- 🚫 禁止访问 base_path 之外的文件

---

## 目录结构

```
workspace/
├── npcs/           # NPC 定义
├── quests/         # 任务定义
├── items/          # 物品定义
├── locations/      # 地点定义
├── prompts/        # Prompt 模板
└── saves/          # 存档文件
```
