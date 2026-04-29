"""GameMaster 核心测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.services.llm_client import LLMClient
from src.agent.game_master import GameMaster
from src.tools.executor import TOOL_REGISTRY

# 确保工具注册表已填充（导入tools包会触发注册）
import src.tools  # noqa: F401

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


def test_init():
    """GameMaster能正常初始化"""
    llm = LLMClient()
    gm = GameMaster(WORLD_ID, PLAYER_ID, llm, DB_PATH)
    assert gm.world_id is not None
    assert gm.tools is not None
    assert len(gm.tools) >= 10  # 至少10个工具（可能被其他测试添加了更多）


def test_process_simple():
    """简单对话测试"""
    llm = LLMClient()
    gm = GameMaster(WORLD_ID, PLAYER_ID, llm, DB_PATH)
    response = gm.process("你好")
    assert response is not None
    assert len(response) > 0
    print(f"\nGM回复: {response[:200]}")


def test_process_look_around():
    """环顾四周测试（应该触发工具调用）"""
    llm = LLMClient()
    gm = GameMaster(WORLD_ID, PLAYER_ID, llm, DB_PATH)
    response = gm.process("环顾四周")
    assert response is not None
    assert len(response) > 0
    print(f"\nGM回复: {response[:200]}")


def test_history_persistence():
    """对话历史被正确保存"""
    llm = LLMClient()
    gm = GameMaster(WORLD_ID, PLAYER_ID, llm, DB_PATH)
    gm.process("测试消息")
    # 检查数据库中有记录
    from src.services.database import get_db
    with get_db(DB_PATH) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM game_messages WHERE world_id = ?",
            (gm.world_id,)
        ).fetchone()[0]
    assert count >= 2  # 至少: user + assistant


def test_process_stream():
    """流式输出测试"""
    llm = LLMClient()
    gm = GameMaster(WORLD_ID, PLAYER_ID, llm, DB_PATH)
    chunks = list(gm.process_stream("说一句话"))
    full_text = "".join(chunks)
    assert len(full_text) > 0
    print(f"\n流式回复: {full_text[:200]}")
