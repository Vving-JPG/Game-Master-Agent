"""Feature 层服务模块

提供各种业务服务，如 API 测试、模型管理、打包、知识库、多 Agent 编排、安全护栏等。
"""
from feature.services.api_tester import ApiTester, ApiTestWorker, TestResult
from feature.services.model_manager import ModelManager, ModelConfig

# 导入并初始化打包服务（自动订阅 EventBus）
from feature.services.packaging_service import packaging_service

# 导入并初始化知识库服务（自动订阅 EventBus）
from feature.services.knowledge_service import (
    knowledge_service,
    NPCData, LocationData, ItemData, QuestData, WorldSettingData,
)

# 导入并初始化多 Agent 编排服务（自动订阅 EventBus）
from feature.services.multi_agent_service import (
    multi_agent_service,
    AgentInstance, ChainStep, AgentRole, StepType,
)

# 导入并初始化安全护栏服务（自动订阅 EventBus）
from feature.services.safety_service import (
    safety_service,
    FilterRule, SafetyLevel,
)

__all__ = [
    "ApiTester",
    "ApiTestWorker",
    "TestResult",
    "ModelManager",
    "ModelConfig",
    "packaging_service",
    "knowledge_service",
    "NPCData", "LocationData", "ItemData", "QuestData", "WorldSettingData",
    "multi_agent_service",
    "AgentInstance", "ChainStep", "AgentRole", "StepType",
    "safety_service",
    "FilterRule", "SafetyLevel",
]
