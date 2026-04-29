"""GameLog Repository 测试"""
import tempfile
import os
from src.services.database import init_db
from src.models import world_repo, log_repo

DB_PATH = None

def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    init_db(DB_PATH)

def test_log_and_query():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    log_repo.log_event(wid, "dialog", "玩家与村长对话", DB_PATH)
    log_repo.log_event(wid, "combat", "玩家击败了哥布林", DB_PATH)
    log_repo.log_event(wid, "discovery", "玩家发现了隐藏宝箱", DB_PATH)
    logs = log_repo.get_recent_logs(wid, 10, DB_PATH)
    assert len(logs) == 3
    # 验证三种事件类型都存在（由于时间戳可能相同，不验证顺序）
    event_types = {log["event_type"] for log in logs}
    assert event_types == {"dialog", "combat", "discovery"}

def test_invalid_event_type():
    wid = world_repo.create_world("测试", db_path=DB_PATH)
    log_repo.log_event(wid, "invalid_type", "测试", DB_PATH)
    logs = log_repo.get_recent_logs(wid, 10, DB_PATH)
    assert logs[0]["event_type"] == "system"  # 被修正为system
