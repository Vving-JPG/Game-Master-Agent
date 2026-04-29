"""多模型路由 - 不同任务用不同模型"""
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 模型配置
MODEL_CONFIG = {
    "deepseek-chat": {
        "name": "deepseek-chat",
        "description": "日常对话，速度快，成本低",
        "use_cases": ["日常对话", "简单描述", "NPC闲聊"],
    },
    "deepseek-reasoner": {
        "name": "deepseek-reasoner",
        "description": "关键剧情，质量高，速度慢",
        "use_cases": ["关键剧情", "重要选择", "Boss战", "结局"],
    },
}

# 关键词路由规则
CRITICAL_KEYWORDS = [
    "战斗", "boss", "决战", "死亡", "结局", "选择", "命运",
    "重要", "秘密", "真相", "最终", "关键",
]


def route_model(user_input: str, history: list[dict] | None = None) -> str:
    """根据输入内容路由到合适的模型

    Args:
        user_input: 玩家输入
        history: 对话历史（可选，用于判断上下文重要性）

    Returns:
        模型名称
    """
    # 检查是否包含关键词
    input_lower = user_input.lower()
    for keyword in CRITICAL_KEYWORDS:
        if keyword in input_lower:
            logger.info(f"路由到 deepseek-reasoner (关键词: {keyword})")
            return "deepseek-reasoner"

    # 检查对话轮次（长对话可能涉及重要剧情）
    if history:
        user_count = sum(1 for m in history if m.get("role") == "user")
        if user_count > 20:
            logger.info(f"路由到 deepseek-reasoner (长对话: {user_count}轮)")
            return "deepseek-reasoner"

    # 默认用快速模型
    return "deepseek-chat"


def get_model_config(model_name: str) -> dict:
    """获取模型配置"""
    return MODEL_CONFIG.get(model_name, MODEL_CONFIG["deepseek-chat"])
