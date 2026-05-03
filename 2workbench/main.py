# 2workbench/main.py
"""备用入口 — 不使用 qasync（用于简单测试）"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from foundation.logger import get_logger


def main() -> None:
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("Game Master Agent IDE")

    # === 初始化 Feature 系统 ===
    from feature.registry import feature_registry
    from feature.battle.system import BattleSystem
    from feature.dialogue.system import DialogueSystem
    from feature.quest.system import QuestSystem
    from feature.item.system import ItemSystem
    from feature.exploration.system import ExplorationSystem
    from feature.narration.system import NarrationSystem
    from foundation.config import settings

    db_path = settings.database_path
    features = [
        BattleSystem(db_path=db_path),
        DialogueSystem(db_path=db_path),
        QuestSystem(db_path=db_path),
        ItemSystem(db_path=db_path),
        ExplorationSystem(db_path=db_path),
        NarrationSystem(db_path=db_path),
    ]
    for f in features:
        feature_registry.register(f)
    feature_registry.enable_all()
    logger = get_logger(__name__)
    logger.info(f"Feature 系统初始化完成: {len(features)} 个系统已注册")

    from presentation.theme.manager import theme_manager
    theme_manager.apply("dark")

    from presentation.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
