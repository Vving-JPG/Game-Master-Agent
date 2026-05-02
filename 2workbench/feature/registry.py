"""Feature 注册表 — 统一管理所有 Feature 模块

使用方式:
    from feature.registry import feature_registry

    # 注册
    feature_registry.register(BattleSystem())
    feature_registry.register(DialogueSystem())

    # 启用全部
    feature_registry.enable_all()

    # 获取某个系统
    battle = feature_registry.get("battle")

    # 获取所有状态
    states = feature_registry.get_all_states()
"""
from __future__ import annotations

from typing import Any

from foundation.logger import get_logger
from feature.base import BaseFeature

logger = get_logger(__name__)


class FeatureRegistry:
    """Feature 注册表"""

    def __init__(self):
        self._features: dict[str, BaseFeature] = {}

    def register(self, feature: BaseFeature) -> None:
        """注册 Feature 模块"""
        name = feature.name
        if name in self._features:
            logger.warning(f"Feature 已存在，将被覆盖: {name}")
        self._features[name] = feature
        logger.debug(f"Feature 注册: {name}")

    def unregister(self, name: str) -> None:
        """注销 Feature 模块"""
        if name in self._features:
            self._features[name].on_disable()
            del self._features[name]
            logger.debug(f"Feature 注销: {name}")

    def get(self, name: str) -> BaseFeature | None:
        """获取 Feature 模块"""
        return self._features.get(name)

    def enable(self, name: str) -> bool:
        """启用指定 Feature"""
        feature = self._features.get(name)
        if feature:
            feature.on_enable()
            return True
        return False

    def disable(self, name: str) -> bool:
        """禁用指定 Feature"""
        feature = self._features.get(name)
        if feature:
            feature.on_disable()
            return True
        return False

    def enable_all(self) -> None:
        """启用所有 Feature"""
        for name, feature in self._features.items():
            feature.on_enable()
        logger.info(f"已启用 {len(self._features)} 个 Feature")

    def disable_all(self) -> None:
        """禁用所有 Feature"""
        for name, feature in self._features.items():
            feature.on_disable()
        logger.info(f"已禁用 {len(self._features)} 个 Feature")

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """获取所有 Feature 的状态"""
        return {
            name: feature.get_state()
            for name, feature in self._features.items()
        }

    def list_features(self) -> list[str]:
        """列出所有已注册的 Feature"""
        return list(self._features.keys())


# 全局单例
feature_registry = FeatureRegistry()
