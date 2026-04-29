"""Player Repository 测试"""
import tempfile
import os
from src.services.database import init_db
from src.models import world_repo, player_repo, item_repo

DB_PATH = None

def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    init_db(DB_PATH)

def test_create_and_get():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    pid = player_repo.create_player(wid, "勇者", db_path=DB_PATH)
    player = player_repo.get_player(pid, DB_PATH)
    assert player["name"] == "勇者"
    assert player["hp"] == 100
    assert player["level"] == 1

def test_update():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    pid = player_repo.create_player(wid, "勇者", db_path=DB_PATH)
    player_repo.update_player(pid, hp=80, gold=50, db_path=DB_PATH)
    player = player_repo.get_player(pid, DB_PATH)
    assert player["hp"] == 80
    assert player["gold"] == 50

def test_add_and_remove_item():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    pid = player_repo.create_player(wid, "勇者", db_path=DB_PATH)
    iid = item_repo.create_item("治疗药水", "potion", "common", db_path=DB_PATH)
    player_repo.add_item(pid, iid, 3, DB_PATH)
    inv = player_repo.get_inventory(pid, DB_PATH)
    assert len(inv) == 1
    assert inv[0]["quantity"] == 3
    player_repo.remove_item(pid, iid, 1, DB_PATH)
    inv = player_repo.get_inventory(pid, DB_PATH)
    assert inv[0]["quantity"] == 2
    player_repo.remove_item(pid, iid, 2, DB_PATH)
    inv = player_repo.get_inventory(pid, DB_PATH)
    assert len(inv) == 0
