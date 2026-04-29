"""Item Repository 测试"""
import tempfile
import os
from src.services.database import init_db
from src.models import item_repo

DB_PATH = None

def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    init_db(DB_PATH)

def test_create_and_get():
    iid = item_repo.create_item("铁剑", "weapon", "common", {"attack": 5}, "一把普通的铁剑", slot="weapon", db_path=DB_PATH)
    item = item_repo.get_item(iid, DB_PATH)
    assert item["name"] == "铁剑"
    assert item["stats"]["attack"] == 5
    assert item["slot"] == "weapon"

def test_search():
    item_repo.create_item("治疗药水", "potion", "common", {"hp": 30}, db_path=DB_PATH)
    item_repo.create_item("高级治疗药水", "potion", "rare", {"hp": 80}, db_path=DB_PATH)
    results = item_repo.search_items("药水", DB_PATH)
    assert len(results) >= 2

def test_update():
    iid = item_repo.create_item("木盾", "armor", db_path=DB_PATH)
    item_repo.update_item(iid, rarity="uncommon", db_path=DB_PATH)
    item = item_repo.get_item(iid, DB_PATH)
    assert item["rarity"] == "uncommon"
