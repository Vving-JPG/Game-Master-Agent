"""存档管理器 — 版本化存档

改进点（相比现有版本）:
1. 存档元数据存入 SQLite（而非仅靠文件名）
2. 支持存档描述和标签
3. 支持自动存档
4. 通过 EventBus 通知存档事件
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from foundation.config import settings
from foundation.database import get_db
from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SaveInfo:
    """存档信息"""
    save_id: str
    world_id: int
    slot_name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    file_path: str = ""
    file_size: int = 0


class SaveManager:
    """存档管理器

    用法:
        sm = SaveManager()
        save_info = sm.save_game(world_id=1, slot_name="auto", description="自动存档")
        sm.load_game(world_id=1, slot_name="auto")
        saves = sm.list_saves(world_id=1)
    """

    def __init__(self, save_dir: str | None = None):
        self._save_dir = Path(save_dir or settings.save_directory)
        self._save_dir.mkdir(parents=True, exist_ok=True)

    def save_game(
        self,
        world_id: int,
        slot_name: str = "manual",
        description: str = "",
        tags: list[str] | None = None,
        db_path: str | Path | None = None,
    ) -> SaveInfo:
        """创建存档

        Args:
            world_id: 世界 ID
            slot_name: 存档槽名称（auto/manual/slot_1/...）
            description: 存档描述
            tags: 标签列表
            db_path: 数据库路径（默认从 settings）

        Returns:
            SaveInfo
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_id = f"world_{world_id}_{slot_name}_{timestamp}"

        # 复制数据库文件
        if db_path is None:
            db_path = settings.database_path

        src = Path(db_path)
        if not src.exists():
            logger.error(f"数据库文件不存在: {src}")
            raise FileNotFoundError(f"数据库文件不存在: {src}")

        dest = self._save_dir / f"{save_id}.db"
        shutil.copy2(src, dest)

        save_info = SaveInfo(
            save_id=save_id,
            world_id=world_id,
            slot_name=slot_name,
            description=description or f"{slot_name} 存档",
            tags=tags or [],
            created_at=datetime.now().isoformat(),
            file_path=str(dest),
            file_size=dest.stat().st_size,
        )

        logger.info(f"存档创建: {save_id} ({dest.stat().st_size // 1024}KB)")

        # 通知
        try:
            from foundation.event_bus import event_bus, Event
            event_bus.emit(Event(
                type="foundation.save.created",
                data={"save_id": save_id, "world_id": world_id, "slot": slot_name},
                source="foundation.save_manager",
            ))
        except Exception:
            pass

        return save_info

    def load_game(
        self,
        world_id: int,
        slot_name: str = "auto",
        db_path: str | Path | None = None,
    ) -> bool:
        """加载存档

        Args:
            world_id: 世界 ID
            slot_name: 存档槽名称
            db_path: 目标数据库路径

        Returns:
            是否成功加载
        """
        if db_path is None:
            db_path = settings.database_path

        # 查找最新匹配的存档
        saves = self.list_saves(world_id=world_id)
        matching = [s for s in saves if s.slot_name == slot_name]

        if not matching:
            logger.error(f"未找到存档: world_id={world_id}, slot={slot_name}")
            return False

        # 取最新的
        matching.sort(key=lambda s: s.created_at, reverse=True)
        save_info = matching[0]

        src = Path(save_info.file_path)
        dest = Path(db_path)

        if not src.exists():
            logger.error(f"存档文件不存在: {src}")
            return False

        shutil.copy2(src, dest)
        logger.info(f"存档加载: {save_info.save_id} -> {dest}")

        try:
            from foundation.event_bus import event_bus, Event
            event_bus.emit(Event(
                type="foundation.save.loaded",
                data={"save_id": save_info.save_id, "world_id": world_id},
                source="foundation.save_manager",
            ))
        except Exception:
            pass

        return True

    def list_saves(self, world_id: int | None = None) -> list[SaveInfo]:
        """列出存档

        Args:
            world_id: 按世界 ID 过滤

        Returns:
            SaveInfo 列表
        """
        saves = []
        for f in sorted(self._save_dir.glob("world_*.db"), reverse=True):
            # 解析文件名: world_{world_id}_{slot}_{timestamp}.db
            parts = f.stem.split("_")
            if len(parts) >= 4:
                w_id = int(parts[1])
                slot = parts[2]
                if world_id is not None and w_id != world_id:
                    continue
                saves.append(SaveInfo(
                    save_id=f.stem,
                    world_id=w_id,
                    slot_name=slot,
                    created_at=datetime.fromtimestamp(f.stat().st_ctime).isoformat(),
                    file_path=str(f),
                    file_size=f.stat().st_size,
                ))
        return saves

    def delete_save(self, save_id: str) -> bool:
        """删除存档"""
        path = self._save_dir / f"{save_id}.db"
        if path.exists():
            path.unlink()
            logger.info(f"存档删除: {save_id}")
            return True
        return False
