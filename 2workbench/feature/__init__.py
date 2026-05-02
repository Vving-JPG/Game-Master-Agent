"""Feature 层 — 业务功能集合"""
from feature.base import BaseFeature
from feature.registry import FeatureRegistry, feature_registry
from feature.battle import BattleSystem
from feature.dialogue import DialogueSystem
from feature.quest import QuestSystem
from feature.item import ItemSystem
from feature.exploration import ExplorationSystem
from feature.narration import NarrationSystem

__all__ = [
    "BaseFeature",
    "FeatureRegistry", "feature_registry",
    "BattleSystem",
    "DialogueSystem",
    "QuestSystem",
    "ItemSystem",
    "ExplorationSystem",
    "NarrationSystem",
]
