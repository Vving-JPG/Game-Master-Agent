"""存档管理模块 - 保存/加载游戏进度"""
import sqlite3
import os
import shutil
from datetime import datetime
from .core.utils.logger import get_logger

logger = get_logger(__name__)

SAVE_DIR = "saves"


def _ensure_save_dir():
    """确保存档目录存在"""
    os.makedirs(SAVE_DIR, exist_ok=True)


def save_game(world_id: int, slot_name: str, db_path: str | None = None) -> str:
    """保存游戏进度

    Args:
        world_id: 世界ID
        slot_name: 存档槽名称
        db_path: 数据库路径

    Returns:
        存档文件路径
    """
    _ensure_save_dir()
    source = db_path or "./data/game.db"
    if not os.path.exists(source):
        raise FileNotFoundError(f"数据库文件不存在: {source}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_filename = f"world_{world_id}_{slot_name}_{timestamp}.db"
    save_path = os.path.join(SAVE_DIR, save_filename)

    shutil.copy2(source, save_path)
    logger.info(f"游戏已保存: {save_path}")
    return save_path


def load_game(world_id: int, slot_name: str, db_path: str | None = None) -> str:
    """加载游戏进度

    Args:
        world_id: 世界ID
        slot_name: 存档槽名称
        db_path: 目标数据库路径

    Returns:
        存档文件路径
    """
    _ensure_save_dir()
    target = db_path or "./data/game.db"

    # 查找匹配的存档文件（最新的）
    matches = [
        f for f in os.listdir(SAVE_DIR)
        if f.startswith(f"world_{world_id}_{slot_name}_") and f.endswith(".db")
    ]
    if not matches:
        raise FileNotFoundError(f"未找到存档: world_{world_id}_{slot_name}")

    matches.sort(reverse=True)  # 最新的在前
    save_path = os.path.join(SAVE_DIR, matches[0])
    shutil.copy2(save_path, target)
    logger.info(f"游戏已加载: {save_path} -> {target}")
    return save_path


def list_saves(world_id: int | None = None) -> list[dict]:
    """列出所有存档

    Args:
        world_id: 可选，筛选特定世界的存档
    """
    _ensure_save_dir()
    saves = []
    for f in os.listdir(SAVE_DIR):
        if not f.endswith(".db"):
            continue
        parts = f.replace(".db", "").split("_")
        if len(parts) >= 4:
            wid = int(parts[1])
            if world_id and wid != world_id:
                continue
            saves.append({
                "filename": f,
                "world_id": wid,
                "slot_name": parts[2],
                "timestamp": parts[3],
                "path": os.path.join(SAVE_DIR, f),
            })
    saves.sort(key=lambda x: x["timestamp"], reverse=True)
    return saves


def delete_save(world_id: int, slot_name: str) -> bool:
    """删除存档"""
    _ensure_save_dir()
    matches = [
        f for f in os.listdir(SAVE_DIR)
        if f.startswith(f"world_{world_id}_{slot_name}_") and f.endswith(".db")
    ]
    for f in matches:
        os.remove(os.path.join(SAVE_DIR, f))
        logger.info(f"存档已删除: {f}")
    return len(matches) > 0
