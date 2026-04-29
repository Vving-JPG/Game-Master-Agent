"""多结局系统测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.services.ending_system import calculate_ending_score, determine_ending, format_ending_narrative, ENDING_TYPES
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


def test_calculate_ending_score():
    """计算结局分数"""
    scores = calculate_ending_score(WORLD_ID, PLAYER_ID, DB_PATH)
    assert "hero" in scores
    assert "neutral" in scores


def test_determine_ending():
    """确定结局"""
    # 完成一些主线任务
    qid = quest_repo.create_quest(WORLD_ID, "主线任务", "测试", quest_type="main", player_id=PLAYER_ID, db_path=DB_PATH)
    quest_repo.update_quest(qid, status="completed", db_path=DB_PATH)

    ending = determine_ending(WORLD_ID, PLAYER_ID, DB_PATH)
    assert "name" in ending
    assert "description" in ending
    assert ending["score"] > 0


def test_format_ending_narrative():
    """格式化结局"""
    ending = ENDING_TYPES["hero"].copy()
    ending["score"] = 100
    ending["all_scores"] = {}
    text = format_ending_narrative(ending)
    assert "英雄结局" in text
    assert "100" in text
