"""剧情数据模型测试"""
import tempfile
import os
import json
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.models import quest_repo

DB_PATH = None
WORLD_ID = None


def setup_module():
    global DB_PATH, WORLD_ID
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    WORLD_ID = result["world_id"]


def test_create_quest_with_branches():
    """创建带分支的任务"""
    branches = [
        {"id": "help", "text": "帮助村民", "next_step": 3},
        {"id": "ignore", "text": "无视请求", "next_step": 4},
    ]
    rewards = {"exp": 100, "gold": 50}
    qid = quest_repo.create_quest(
        WORLD_ID, "拯救村庄", "哥布林正在攻击村庄！",
        quest_type="main",
        branches=branches,
        rewards=rewards,
        db_path=DB_PATH,
    )
    quest = quest_repo.get_quest(qid, DB_PATH)
    assert quest["quest_type"] == "main"
    assert len(quest["branches"]) == 2


def test_quest_steps():
    """创建任务步骤"""
    qid = quest_repo.create_quest(WORLD_ID, "收集草药", "村长需要草药", db_path=DB_PATH)
    quest_repo.create_quest_step(qid, 1, "去森林采集草药", step_type="collect", target="草药", required_count=5, db_path=DB_PATH)
    quest_repo.create_quest_step(qid, 2, "把草药交给村长", step_type="talk", target="村长", db_path=DB_PATH)
    steps = quest_repo.get_quest_steps(qid, DB_PATH)
    assert len(steps) == 2
    assert steps[0]["step_type"] == "collect"


def test_update_step_progress():
    """更新步骤进度"""
    qid = quest_repo.create_quest(WORLD_ID, "杀怪", "消灭哥布林", db_path=DB_PATH)
    sid = quest_repo.create_quest_step(qid, 1, "消灭5个哥布林", step_type="kill", target="哥布林", required_count=5, db_path=DB_PATH)
    quest_repo.update_quest_step(sid, current_count=3, db_path=DB_PATH)
    steps = quest_repo.get_quest_steps(qid, DB_PATH)
    assert steps[0]["current_count"] == 3
