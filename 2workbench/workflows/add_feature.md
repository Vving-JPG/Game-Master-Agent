# 工作流: 添加新 Feature 模块

## 步骤

1. **创建目录**:
```powershell
New-Item -ItemType Directory -Force -Path feature/<feature_name>
```

2. **创建 system.py**:
```python
# feature/<feature_name>/system.py
"""<中文名称>系统"""
from __future__ import annotations
from typing import Any
from foundation.logger import get_logger
from feature.base import BaseFeature

logger = get_logger(__name__)

class <ClassName>System(BaseFeature):
    name = "<feature_name>"
    description = "<功能描述>"

    def on_enable(self) -> None:
        super().on_enable()
        self.subscribe("feature.ai.command.executed", self._on_command)

    def _on_command(self, event) -> None:
        intent = event.get("intent", "")
        if intent == "<your_intent>":
            self.handle_<action>(event.get("params", {}))

    def handle_<action>(self, params: dict) -> None:
        """处理动作"""
        logger.info(f"执行动作: {params}")
        # 实现逻辑

    def get_state(self) -> dict[str, Any]:
        return super().get_state()
```

3. **创建 __init__.py**:
```python
from feature.<feature_name>.system import <ClassName>System
__all__ = ["<ClassName>System"]
```

4. **注册到 feature_registry**:
在 `feature/__init__.py` 中添加导入和导出。

5. **添加 EventBus 事件**:
在 `feature/ai/events.py` 中定义相关事件常量。

6. **测试**:
```powershell
cd 2workbench ; python -c "
from feature.<feature_name> import <ClassName>System
sys = <ClassName>System()
sys.on_enable()
assert sys.enabled
sys.on_disable()
print('OK: <ClassName>System 测试通过')
"
```
