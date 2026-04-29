"""任务工具测试"""
import tempfile
import os
import json
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.tools import world_tool, quest_tool
from src.models import quest_repo

DB_PATH = None


def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    world_tool.set_active(result["world_id"], result["player_id"])


def test_create_quest_basic():
    """基本创建任务"""
    result = quest_tool.create_quest("测试任务", "这是一个测试", db_path=DB_PATH)
    assert "测试任务" in result
    assert "ID:" in result


def test_create_quest_from_template():
    """用模板创建任务"""
    result = quest_tool.create_quest(
        "消灭哥布林", "清除威胁",
        template_name="exterminate",
        template_vars=json.dumps({"enemy": "哥布林", "count": "5", "location": "幽暗森林"}),
        db_path=DB_PATH,
    )
    assert "消灭" in result


def test_update_progress():
    """更新进度"""
    qid = quest_repo.create_quest(1, "进度测试", "测试", db_path=DB_PATH)
    quest_repo.create_quest_step(qid, 1, "杀3个怪", step_type="kill", target="怪", required_count=3, db_path=DB_PATH)
    result = quest_tool.update_quest_progress(qid, 0, 2, DB_PATH)
    assert "2/3" in result


def test_complete_quest():
    """完成任务"""
    qid = quest_repo.create_quest(1, "完成测试", "测试", db_path=DB_PATH)
    quest_repo.create_quest_step(qid, 1, "步骤1", required_count=1, db_path=DB_PATH)
    result = quest_tool.update_quest_progress(qid, 0, 1, DB_PATH)
    assert "完成" in result


def test_handle_choice():
    """分支选择"""
    branches = [{"id": "a", "text": "选项A"}, {"id": "b", "text": "选项B"}]
    qid = quest_repo.create_quest(1, "分支测试", "测试", branches=json.dumps(branches), db_path=DB_PATH)
    result = quest_tool.handle_choice(qid, "a", DB_PATH)
    assert "选项A" in result
