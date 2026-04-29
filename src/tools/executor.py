"""工具注册表和执行器"""
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 工具注册表: {name: {"func": callable, "schema": dict}}
TOOL_REGISTRY: dict[str, dict] = {}


def register_tool(name: str, func: callable, schema: dict) -> None:
    """注册工具

    Args:
        name: 工具名称（必须与schema中的function.name一致）
        func: 工具执行函数
        schema: OpenAI function calling格式的schema
    """
    TOOL_REGISTRY[name] = {"func": func, "schema": schema}
    logger.debug(f"注册工具: {name}")


def execute_tool(name: str, args: dict, **kwargs) -> str:
    """执行工具

    Args:
        name: 工具名称
        args: 工具参数（从LLM的tool_calls中提取）

    Returns:
        工具执行结果（字符串）

    Raises:
        KeyError: 工具不存在
    """
    if name not in TOOL_REGISTRY:
        logger.error(f"未知工具: {name}")
        raise KeyError(f"未知工具: {name}，可用工具: {list(TOOL_REGISTRY.keys())}")

    tool = TOOL_REGISTRY[name]
    func = tool["func"]
    logger.info(f"执行工具: {name}({args})")
    try:
        result = func(**args, **kwargs)
        return str(result) if not isinstance(result, str) else result
    except Exception as e:
        logger.error(f"工具 {name} 执行失败: {e}")
        return f"[工具执行失败: {name} - {str(e)}。GM将用文字描述代替。]"


def get_all_schemas() -> list[dict]:
    """获取所有已注册工具的schema列表"""
    return [tool["schema"] for tool in TOOL_REGISTRY.values()]


def get_tool_names() -> list[str]:
    """获取所有已注册工具的名称"""
    return list(TOOL_REGISTRY.keys())
