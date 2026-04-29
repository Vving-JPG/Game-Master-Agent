"""种子数据测试"""
import tempfile
import os
from src.services.database import init_db
from src.data.seed_data import seed_world
from src.models import world_repo, location_repo, npc_repo, item_repo, quest_repo

DB_PATH = None

def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")

def test_seed():
    result = seed_world(DB_PATH)
    wid = result["world_id"]
    # 验证世界
    worlds = world_repo.list_worlds(DB_PATH)
    assert len(worlds) >= 1
    # 验证地点
    locs = location_repo.get_locations_by_world(wid, DB_PATH)
    assert len(locs) >= 5
    # 验证NPC
    npcs = npc_repo.get_npcs_by_location(result["locations"]["村长宅邸"], DB_PATH)
    assert len(npcs) >= 1
    # 验证道具
    items = item_repo.search_items("药水", DB_PATH)
    assert len(items) >= 2
    # 验证任务
    quests = quest_repo.get_quests_by_player(None, DB_PATH)
    assert len(quests) >= 2
