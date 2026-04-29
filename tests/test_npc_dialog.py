"""NPC对话测试"""
import tempfile
import os
import json
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.tools import world_tool
from src.services.npc_dialog import build_npc_context, generate_npc_dialog
from src.models import npc_repo

DB_PATH = None
WORLD_ID = None


def setup_module():
    global DB_PATH, WORLD_ID
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    WORLD_ID = result["world_id"]
    world_tool.set_active(result["world_id"], result["player_id"])


def test_build_npc_context():
    """构建NPC上下文"""
    npc_id = npc_repo.create_npc(
        WORLD_ID,
        "测试法师", 1,
        personality={"openness": 0.9, "conscientiousness": 0.6, "extraversion": 0.2, "agreeableness": 0.4, "neuroticism": 0.5},
        mood="contemplative",
        speech_style="说话隐晦...",
        db_path=DB_PATH,
    )
    ctx = build_npc_context(npc_id, DB_PATH)
    assert ctx["name"] == "测试法师"
    assert ctx["mood"] == "contemplative"
    assert "开放性" in ctx["personality_desc"]


def test_generate_dialog():
    """生成NPC对话（真实LLM调用）"""
    npc_id = npc_repo.create_npc(
        WORLD_ID, "对话测试NPC", 1,
        personality={"openness": 0.3, "conscientiousness": 0.8, "extraversion": 0.7, "agreeableness": 0.5, "neuroticism": 0.2},
        mood="confident",
        speech_style="直率豪爽！",
        db_path=DB_PATH,
    )
    reply = generate_npc_dialog(npc_id, "你好，你是谁？", db_path=DB_PATH)
    assert reply is not None
    assert len(reply) > 0
    print(f"\nNPC回复: {reply}")
