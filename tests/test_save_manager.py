"""存档管理测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.services import save_manager

DB_PATH = None

def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    # 使用临时存档目录
    save_manager.SAVE_DIR = os.path.join(tmpdir, "saves")

def test_save_and_list():
    result = seed_world(DB_PATH)
    save_manager.save_game(result["world_id"], "slot1", DB_PATH)
    saves = save_manager.list_saves(result["world_id"])
    assert len(saves) == 1
    assert saves[0]["slot_name"] == "slot1"

def test_save_load_restore():
    result = seed_world(DB_PATH)
    # 保存
    save_manager.save_game(result["world_id"], "test", DB_PATH)
    # 修改数据
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO game_logs (world_id, event_type, content) VALUES (?, 'system', '修改后的数据')", (result["world_id"],))
    conn.commit()
    conn.close()
    # 加载（应该恢复到保存时的状态）
    save_manager.load_game(result["world_id"], "test", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM game_logs").fetchone()[0]
    conn.close()
    assert count == 0  # 修改的数据被恢复了

def test_delete_save():
    result = seed_world(DB_PATH)
    save_manager.save_game(result["world_id"], "temp", DB_PATH)
    save_manager.delete_save(result["world_id"], "temp")
    saves = save_manager.list_saves(result["world_id"])
    assert len(saves) == 0
