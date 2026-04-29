"""剧情连贯性测试"""
import tempfile
import os
import json
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.services.story_coherence import check_prerequisites, validate_choice, get_story_summary
from src.models import quest_repo

DB_PATH = None
WORLD_ID = None
PLAYER_ID = None


def setup_module():
    global DB_PATH, WORLD_ID, PLAYER_ID
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    WORLD_ID = result["world_id"]
    PLAYER_ID = result["player_id"]


def test_check_prerequisites_no_prereq():
    """无前置条件"""
    qid = quest_repo.create_quest(WORLD_ID, "简单任务", "测试", db_path=DB_PATH)
    ok, reason = check_prerequisites(qid, PLAYER_ID, DB_PATH)
    assert ok is True


def test_check_prerequisites_quest_completed():
    """需要完成前置任务"""
    pre_qid = quest_repo.create_quest(WORLD_ID, "前置任务", "先完成我", db_path=DB_PATH)
    quest_repo.update_quest(pre_qid, status="completed", db_path=DB_PATH)

    qid = quest_repo.create_quest(
        WORLD_ID, "后续任务", "需要前置",
        prerequisites=json.dumps([{"type": "quest_completed", "quest_id": pre_qid}]),
        db_path=DB_PATH,
    )
    ok, reason = check_prerequisites(qid, PLAYER_ID, DB_PATH)
    assert ok is True


def test_validate_choice():
    """验证分支选择"""
    branches = [{"id": "help", "text": "帮助"}, {"id": "ignore", "text": "无视"}]
    qid = quest_repo.create_quest(WORLD_ID, "分支任务", "测试", branches=json.dumps(branches), db_path=DB_PATH)
    ok, reason = validate_choice(qid, "help", DB_PATH)
    assert ok is True


def test_get_story_summary():
    """获取剧情摘要"""
    quest_repo.create_quest(WORLD_ID, "活跃任务", "进行中", player_id=PLAYER_ID, db_path=DB_PATH)
    summary = get_story_summary(WORLD_ID, PLAYER_ID, DB_PATH)
    assert len(summary["active_quests"]) >= 1
