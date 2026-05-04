"""模型管理器 — 兼容层

⚠️ 已弃用: 此模块已移至 feature.services 模块。
请使用: from feature.services import ModelManager

保留此文件仅用于向后兼容，将在未来版本中移除。
"""
from __future__ import annotations

import warnings

# 从 Feature 层重新导出所有内容
from feature.services import ModelManager, ModelConfig

# 发出弃用警告
warnings.warn(
    "presentation.dialogs.model_manager 已弃用，请使用 feature.services 模块。",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ModelManager", "ModelConfig"]
