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
