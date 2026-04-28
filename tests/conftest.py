"""pytest 公共 fixture"""
import pytest
from src.config import settings


@pytest.fixture
def app_settings():
    """提供应用配置"""
    return settings
