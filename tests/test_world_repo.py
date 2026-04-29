"""World Repository 测试"""
import tempfile
import os
from src.services.database import init_db
from src.models import world_repo


DB_PATH = None


def setup_module():
    global DB_PATH
    tmpdir = tempfile.mkdtemp()
    DB_PATH = os.path.join(tmpdir, "test.db")
    init_db(DB_PATH)


def test_create_and_get():
    """创建后能查询到"""
    wid = world_repo.create_world("测试世界", "fantasy", DB_PATH)
    world = world_repo.get_world(wid, DB_PATH)
    assert world is not None
    assert world["name"] == "测试世界"
    assert world["setting"] == "fantasy"


def test_list_worlds():
    """能列出所有世界"""
    world_repo.create_world("世界A", db_path=DB_PATH)
    world_repo.create_world("世界B", db_path=DB_PATH)
    worlds = world_repo.list_worlds(DB_PATH)
    assert len(worlds) >= 2


def test_update():
    """修改后能查到新值"""
    wid = world_repo.create_world("原名", db_path=DB_PATH)
    world_repo.update_world(wid, name="新名", db_path=DB_PATH)
    world = world_repo.get_world(wid, DB_PATH)
    assert world["name"] == "新名"


def test_delete():
    """删除后查不到"""
    wid = world_repo.create_world("待删除", db_path=DB_PATH)
    world_repo.delete_world(wid, DB_PATH)
    world = world_repo.get_world(wid, DB_PATH)
    assert world is None
