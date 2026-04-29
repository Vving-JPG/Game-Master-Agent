"""Location Repository 测试"""
import tempfile
import os
from src.services.database import init_db
from src.models import world_repo, location_repo

DB_PATH = None

def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    init_db(DB_PATH)

def test_create_and_get():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    lid = location_repo.create_location(wid, "村庄", "一个宁静的小村庄", {"north": 0}, DB_PATH)
    loc = location_repo.get_location(lid, DB_PATH)
    assert loc["name"] == "村庄"
    assert loc["connections"] == {"north": 0}

def test_list_by_world():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    location_repo.create_location(wid, "地点A", db_path=DB_PATH)
    location_repo.create_location(wid, "地点B", db_path=DB_PATH)
    locs = location_repo.get_locations_by_world(wid, DB_PATH)
    assert len(locs) >= 2

def test_update_connections():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    lid = location_repo.create_location(wid, "十字路口", db_path=DB_PATH)
    location_repo.update_location(lid, connections={"north": 2, "south": 3}, db_path=DB_PATH)
    loc = location_repo.get_location(lid, DB_PATH)
    assert loc["connections"]["north"] == 2
    assert loc["connections"]["south"] == 3
