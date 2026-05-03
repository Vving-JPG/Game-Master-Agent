# P0-04: Database 数据库连接

> 模块: `foundation.database`
> 文件: `2workbench/foundation/database.py`

---

## 核心函数

```python
def get_db(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]
def get_connection(db_path: str | None = None) -> sqlite3.Connection
def init_db(db_path: str | None = None) -> None
```

---

## 特性

- 🚀 SQLite WAL 模式提升并发
- 📋 Row 工厂支持字典式访问
- 🔒 线程安全（每个线程独立连接）
- 📦 版本号管理支持迁移

---

## 使用示例

```python
from foundation.database import get_db, get_connection, init_db

# 上下文管理器（推荐）
# 自动 commit/rollback
with get_db() as db:
    db.execute("INSERT INTO worlds (name) VALUES (?)", ("幻想世界",))
    # 自动 commit

# 获取连接
conn = get_connection()
cursor = conn.execute("SELECT * FROM worlds")
rows = cursor.fetchall()

# 初始化数据库（执行 schema.sql）
init_db()
```

---

## 线程安全

```python
from foundation.database import get_thread_db

# 获取线程本地连接
conn = get_thread_db()
```

每个线程有独立的连接，避免并发冲突。

---

## Schema 迁移

数据库版本号存储在 `db_version` 表中，支持增量迁移。

```sql
-- schema.sql 示例
CREATE TABLE IF NOT EXISTS worlds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 版本号
CREATE TABLE IF NOT EXISTS db_version (
    version INTEGER PRIMARY KEY
);
```
