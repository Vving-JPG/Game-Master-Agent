"""AI 行为指标测试"""
import tempfile, os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.models import metrics_repo

DB_PATH = None

def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    seed_world(DB_PATH)

def test_record_and_get():
    metrics_repo.record_llm_call(1, prompt_tokens=100, completion_tokens=50, latency_ms=500, db_path=DB_PATH)
    calls = metrics_repo.get_recent_calls(1, db_path=DB_PATH)
    assert len(calls) == 1
    assert calls[0]["prompt_tokens"] == 100

def test_token_stats():
    metrics_repo.record_llm_call(1, prompt_tokens=100, completion_tokens=50, db_path=DB_PATH)
    metrics_repo.record_llm_call(1, prompt_tokens=200, completion_tokens=100, db_path=DB_PATH)
    stats = metrics_repo.get_token_stats(DB_PATH)
    assert stats["total_calls"] >= 2
    assert stats["total_tokens"] >= 450
