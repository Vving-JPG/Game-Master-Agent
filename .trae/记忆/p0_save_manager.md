# P0-06: SaveManager 存档管理

> 模块: `foundation.save_manager`
> 文件: `2workbench/foundation/save_manager.py`

---

## 核心类

```python
class SaveManager:
    def save_game(
        self,
        world_id: int,
        slot_name: str,
        description: str = ""
    ) -> SaveInfo

    def load_game(self, world_id: int, slot_name: str) -> bool
    def list_saves(self, world_id: int) -> list[SaveInfo]
    def delete_save(self, world_id: int, slot_name: str) -> bool
```

---

## 使用示例

```python
from foundation.save_manager import SaveManager

sm = SaveManager()

# 创建存档
save_info = sm.save_game(
    world_id=1,
    slot_name="auto",
    description="自动存档"
)

# 加载存档
success = sm.load_game(world_id=1, slot_name="auto")

# 列出存档
saves = sm.list_saves(world_id=1)
for save in saves:
    print(f"{save.slot_name}: {save.description} ({save.created_at})")
```

---

## SaveInfo 数据结构

```python
@dataclass
class SaveInfo:
    world_id: int
    slot_name: str
    description: str
    created_at: datetime
    checksum: str  # 数据完整性校验
```

---

## 存档槽位

| 槽位名 | 用途 |
|--------|------|
| auto | 自动存档 |
| quick | 快速存档 |
| slot1~slot9 | 手动存档 |

---

## 版本化存档

存档数据包含版本号，支持跨版本兼容处理。
