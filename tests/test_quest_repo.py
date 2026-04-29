"""Quest Repository 测试"""
import tempfile
import os
from src.services.database import init_db
from src.models import world_repo, player_repo, quest_repo

DB_PATH = None

def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    init_db(DB_PATH)

def test_create_and_get():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    qid = quest_repo.create_quest(wid, "拯救村长", "村长被哥布林抓走了", "main", rewards={"exp": 100, "gold": 50}, db_path=DB_PATH)
    quest = quest_repo.get_quest(qid, DB_PATH)
    assert quest["title"] == "拯救村长"
    assert quest["rewards"]["exp"] == 100

def test_update_status():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    qid = quest_repo.create_quest(wid, "测试任务", db_path=DB_PATH)
    quest_repo.update_quest_status(qid, "completed", DB_PATH)
    quest = quest_repo.get_quest(qid, DB_PATH)
    assert quest["status"] == "completed"

def test_invalid_status():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    qid = quest_repo.create_quest(wid, "测试", db_path=DB_PATH)
    result = quest_repo.update_quest_status(qid, "invalid_status", DB_PATH)
    assert result is False
