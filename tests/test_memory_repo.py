"""NPC记忆系统测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.models import npc_repo, memory_repo

DB_PATH = None
NPC_ID = None


def setup_module():
    global DB_PATH, NPC_ID
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    result = seed_world(DB_PATH)
    NPC_ID = npc_repo.create_npc(result["world_id"], "记忆NPC", 1, db_path=DB_PATH)


def test_add_and_get_memory():
    """添加和查询记忆"""
    mid = memory_repo.add_memory(NPC_ID, "玩家给了我一把剑", importance=8, db_path=DB_PATH)
    assert mid > 0
    memories = memory_repo.get_memories(NPC_ID, db_path=DB_PATH)
    assert len(memories) == 1
    assert "剑" in memories[0]["content"]


def test_memory_ordering():
    """记忆按重要性排序"""
    memory_repo.add_memory(NPC_ID, "不重要的事", importance=2, db_path=DB_PATH)
    memory_repo.add_memory(NPC_ID, "非常重要的事", importance=9, db_path=DB_PATH)
    memories = memory_repo.get_memories(NPC_ID, db_path=DB_PATH)
    assert memories[0]["content"] == "非常重要的事"


def test_compress_memories():
    """压缩记忆"""
    for i in range(60):
        memory_repo.add_memory(NPC_ID, f"记忆{i}", importance=i % 10, db_path=DB_PATH)
    deleted = memory_repo.compress_memories(NPC_ID, keep_count=10, db_path=DB_PATH)
    assert deleted > 0
    remaining = memory_repo.get_memories(NPC_ID, limit=100, db_path=DB_PATH)
    assert len(remaining) <= 10


def test_delete_memory():
    """删除记忆"""
    mid = memory_repo.add_memory(NPC_ID, "要删除的记忆", db_path=DB_PATH)
    memory_repo.delete_memory(mid, DB_PATH)
    memories = memory_repo.get_memories(NPC_ID, db_path=DB_PATH)
    assert not any(m["id"] == mid for m in memories)
