"""日志模块测试"""
from src.utils.logger import get_logger


def test_logger():
    """测试日志模块能正常输出"""
    logger = get_logger("test")
    logger.info("这是一条测试日志")
    assert logger.handlers  # 应该有handler
