"""日志工具测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.tools import world_tool, log_tool
from src.models import log_repo

DB_PATH = None
WORLD_ID = None


def setup_module():
    global DB_PATH, WORLD_ID
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    WORLD_ID = result["world_id"]
    world_tool.set_active(WORLD_ID, result["player_id"])


def test_log_event():
    result = log_tool.log_event("system", "测试日志记录", DB_PATH)
    assert "已记录" in result
    logs = log_repo.get_recent_logs(WORLD_ID, 10, DB_PATH)
    assert any("测试日志记录" in log["content"] for log in logs)
