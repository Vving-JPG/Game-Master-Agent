# P0-03: Logger 日志系统

> 模块: `foundation.logger`
> 文件: `2workbench/foundation/logger.py`

---

## 核心函数

```python
def setup_logging(level: str = "INFO", log_file: str | None = None)
def get_logger(name: str) -> logging.Logger
```

---

## 特性

- 🎨 控制台彩色输出
- 📁 文件结构化日志 + 轮转
- 🔍 支持 `extra` 字段传递上下文
- 📊 结构化 JSON 格式

---

## 使用示例

```python
from foundation.logger import get_logger, setup_logging

# 初始化（通常在应用启动时）
setup_logging("DEBUG")

# 获取 logger
logger = get_logger(__name__)

# 基本日志
logger.info("Agent 启动")
logger.debug("调试信息")
logger.warning("警告信息")
logger.error("错误信息")

# 带上下文的日志
logger.info(
    "NPC 对话生成完成",
    extra={"world_id": "1", "npc_id": "123", "turn": 5}
)

# 异常日志
logger.error("LLM 调用失败", exc_info=True)
```

---

## 日志格式

**控制台输出** (彩色):
```
[2024-05-01 10:30:45] [INFO] [feature.ai.gm_agent] Agent 启动
```

**文件输出** (JSON):
```json
{
  "timestamp": "2024-05-01T10:30:45",
  "level": "INFO",
  "logger": "feature.ai.gm_agent",
  "message": "Agent 启动",
  "extra": {"world_id": "1", "turn": 5}
}
```

---

## 日志级别

| 级别 | 使用场景 |
|------|---------|
| DEBUG | 详细调试信息 |
| INFO | 正常流程信息 |
| WARNING | 警告，非致命问题 |
| ERROR | 错误，需要处理 |
| CRITICAL | 严重错误，程序可能崩溃 |
