"""Prompt 版本管理测试"""
import tempfile, os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.models import prompt_repo

DB_PATH = None

def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    seed_world(DB_PATH)

def test_save_and_get():
    """保存和获取 Prompt"""
    prompt_repo.save_prompt("test_key", "你是一个GM。", DB_PATH)
    result = prompt_repo.get_active_prompt("test_key", DB_PATH)
    assert result == "你是一个GM。"

def test_version_increment():
    """版本自动递增"""
    prompt_repo.save_prompt("ver_test", "v1", DB_PATH)
    prompt_repo.save_prompt("ver_test", "v2", DB_PATH)
    prompt_repo.save_prompt("ver_test", "v3", DB_PATH)
    history = prompt_repo.get_prompt_history("ver_test", db_path=DB_PATH)
    assert len(history) == 3
    assert history[0]["version"] == 3  # 最新的在前

def test_only_latest_active():
    """只有最新版本是活跃的"""
    prompt_repo.save_prompt("active_test", "old", DB_PATH)
    prompt_repo.save_prompt("active_test", "new", DB_PATH)
    result = prompt_repo.get_active_prompt("active_test", DB_PATH)
    assert result == "new"

def test_rollback():
    """回滚"""
    prompt_repo.save_prompt("rb_test", "v1", DB_PATH)
    prompt_repo.save_prompt("rb_test", "v2", DB_PATH)
    prompt_repo.rollback_prompt("rb_test", 1, DB_PATH)
    result = prompt_repo.get_active_prompt("rb_test", DB_PATH)
    assert result == "v1"
