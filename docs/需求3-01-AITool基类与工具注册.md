# 01 — AITool 基类与工具注册

> 目标执行者：Trae AI
> 依赖：无
> 产出：`feature/services/ai_assistant/tools/base.py` + `registry.py` + `__init__.py`

---

## 1. AITool 抽象基类

**文件**：`feature/services/ai_assistant/tools/base.py`

```python
"""
AI 工具抽象基类
所有 AI 助手可调用的工具都必须继承此类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str  # "string", "integer", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None  # 枚举值限制


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    message: str = ""
    data: dict = field(default_factory=dict)
    diff: str = ""  # 文件变更的 diff 文本
    file_path: str = ""  # 被修改的文件路径（如果有）


class AITool(ABC):
    """AI 工具抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识符）"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（LLM 看到的说明）"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> list[ToolParameter]:
        """工具参数列表"""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        ...

    def to_llm_schema(self) -> dict:
        """转换为 LLM function calling 格式的 JSON Schema"""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def __repr__(self) -> str:
        return f"<AITool: {self.name}>"
```

---

## 2. ToolRegistry 工具注册中心

**文件**：`feature/services/ai_assistant/tools/registry.py`

```python
"""
工具注册中心
管理所有 AI 工具的注册、查询和分发
"""
from typing import Any

from foundation.logger import get_logger
from .base import AITool, ToolResult

logger = get_logger(__name__)


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: dict[str, AITool] = {}

    def register(self, tool: AITool):
        """注册工具"""
        if tool.name in self._tools:
            logger.warning(f"工具 '{tool.name}' 已存在，将被覆盖")
        self._tools[tool.name] = tool
        logger.debug(f"注册工具: {tool.name}")

    def get(self, name: str) -> AITool | None:
        """获取工具"""
        return self._tools.get(name)

    def get_all(self) -> dict[str, AITool]:
        """获取所有工具"""
        return dict(self._tools)

    def get_names(self) -> list[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())

    def to_llm_tools(self) -> list[dict]:
        """生成 LLM function calling 格式的工具列表"""
        return [tool.to_llm_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """执行指定工具"""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                message=f"未知工具: {tool_name}",
            )

        logger.info(f"执行工具: {tool_name}({kwargs})")
        try:
            result = await tool.execute(**kwargs)
            logger.info(f"工具执行完成: {tool_name} -> success={result.success}")
            return result
        except Exception as e:
            logger.error(f"工具执行失败: {tool_name} -> {e}")
            return ToolResult(
                success=False,
                message=f"工具执行异常: {e}",
            )


# 全局单例
tool_registry = ToolRegistry()
```

---

## 3. __init__.py

**文件**：`feature/services/ai_assistant/tools/__init__.py`

```python
from .base import AITool, ToolParameter, ToolResult
from .registry import ToolRegistry, tool_registry

__all__ = [
    "AITool",
    "ToolParameter",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
]
```

---

## 4. 验证

创建完成后，在 Python 中验证：

```python
from feature.services.ai_assistant.tools import tool_registry, AITool

# 检查注册中心
assert isinstance(tool_registry, ToolRegistry)
assert tool_registry.get_names() == []  # 尚未注册工具

# 检查 LLM Schema 生成
class DummyTool(AITool):
    @property
    def name(self): return "dummy"
    @property
    def description(self): return "测试工具"
    @property
    def parameters(self):
        return [ToolParameter("input", "string", "输入内容")]
    async def execute(self, **kw): return ToolResult(success=True)

schema = DummyTool().to_llm_schema()
assert schema["type"] == "function"
assert schema["function"]["name"] == "dummy"
```
