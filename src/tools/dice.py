"""骰子工具 - 支持标准RPG骰子表达式"""
import re
import random
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 匹配骰子表达式: 2d6+3, 1d20, d100, 3d8-1
DICE_PATTERN = re.compile(r'^(\d*)d(\d+)([+-]\d+)?$')


def roll_dice(expression: str) -> dict:
    """掷骰子

    Args:
        expression: 骰子表达式，如 '2d6+3', '1d20', 'd100', '3d8-1'

    Returns:
        dict: {expression, rolls, modifier, total}

    Raises:
        ValueError: 表达式格式无效
    """
    expression = expression.strip().lower()
    match = DICE_PATTERN.match(expression)

    if not match:
        raise ValueError(f"无效的骰子表达式: '{expression}'。正确格式如: '2d6+3', '1d20', 'd100'")

    count = int(match.group(1)) if match.group(1) else 1
    sides = int(match.group(2))
    modifier_str = match.group(3) or ""
    modifier = int(modifier_str) if modifier_str else 0

    if count < 1 or count > 100:
        raise ValueError(f"骰子数量必须在1-100之间，当前: {count}")
    if sides < 1 or sides > 1000:
        raise ValueError(f"骰子面数必须在1-1000之间，当前: {sides}")

    rolls = [random.randint(1, sides) for _ in range(count)]
    subtotal = sum(rolls)
    total = subtotal + modifier

    result = {
        "expression": expression,
        "rolls": rolls,
        "modifier": modifier,
        "subtotal": subtotal,
        "total": total,
    }

    logger.info(f"掷骰子: {expression} → {rolls} (合计{subtotal}) {'+' if modifier >= 0 else ''}{modifier} = {total}")
    return result
