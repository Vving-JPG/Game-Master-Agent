"""数据库模块测试"""
import os
import tempfile
import sqlite3
from src.services.database import get_connection, get_db, init_db


def test_init_db():
    """测试数据库初始化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        tables = [t[0] for t in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "worlds" in tables
        assert "players" in tables
        assert "npcs" in tables
        assert "items" in tables
        assert "quests" in tables
        assert "game_logs" in tables


def test_get_connection():
    """测试获取连接"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        conn = get_connection(db_path)
        assert conn is not None
        conn.close()


def test_get_db_context_manager():
    """测试上下文管理器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        with get_db(db_path) as conn:
            conn.execute("INSERT INTO worlds (name, setting) VALUES ('测试世界', 'fantasy')")
        # 验证数据已提交
        conn2 = sqlite3.connect(db_path)
        count = conn2.execute("SELECT COUNT(*) FROM worlds").fetchone()[0]
        conn2.close()
        assert count == 1


def test_get_db_rollback():
    """测试异常时回滚"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        try:
            with get_db(db_path) as conn:
                conn.execute("INSERT INTO worlds (name, setting) VALUES ('回滚测试', 'fantasy')")
                raise ValueError("模拟错误")
        except ValueError:
            pass
        conn2 = sqlite3.connect(db_path)
        count = conn2.execute("SELECT COUNT(*) FROM worlds").fetchone()[0]
        conn2.close()
        assert count == 0  # 回滚了
