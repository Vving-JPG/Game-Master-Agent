"""CLI 命令行界面 - 在终端中与Game Master对话"""
import sys
from src.services.database import init_db
from src.services.llm_client import LLMClient
from src.data.seed_data import seed_world
from src.agent.game_master import GameMaster
from src.utils.logger import get_logger

logger = get_logger(__name__)


def show_status(gm: GameMaster):
    """显示当前状态"""
    from src.tools import player_tool
    print("\n" + "=" * 40)
    print(player_tool.get_player_info(gm.db_path))
    print("=" * 40)


def show_help():
    """显示帮助"""
    print("""
=== 可用命令 ===
/status  - 查看玩家状态
/help    - 显示此帮助
/quit    - 退出游戏
/save    - 保存游戏
/history - 查看对话历史数量
/tokens  - 查看Token使用统计
==================
其他任何输入都会发送给Game Master
""")


def main():
    """CLI主入口"""
    db_path = None

    # 初始化数据库和种子数据
    print("=== Game Master Agent ===")
    print("正在初始化世界...")

    try:
        result = seed_world(db_path)
        world_id = result["world_id"]
    except Exception:
        # 如果世界已存在，使用现有世界
        from src.models import world_repo
        worlds = world_repo.list_worlds(db_path)
        if worlds:
            world_id = worlds[0]["id"]
            print(f"使用已有世界: {worlds[0]['name']}")
        else:
            print("错误: 无法初始化世界")
            sys.exit(1)

    # 创建玩家（如果不存在）
    from src.models import player_repo
    from src.services.database import get_db
    with get_db(db_path) as conn:
        existing = conn.execute("SELECT id FROM players WHERE world_id = ? LIMIT 1", (world_id,)).fetchone()
    if existing:
        player_id = existing["id"]
        print(f"欢迎回来，冒险者！")
    else:
        player_id = player_repo.create_player(world_id, "冒险者", db_path)
        print(f"欢迎，新的冒险者！")

    # 创建GM
    llm = LLMClient()
    gm = GameMaster(world_id, player_id, llm, db_path)

    print(f"世界: {world_id} | 玩家ID: {player_id}")
    print("输入 /help 查看命令，/quit 退出\n")

    # 主循环
    while True:
        try:
            user_input = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        # 特殊命令
        if user_input == "/quit":
            print("再见！")
            break
        elif user_input == "/help":
            show_help()
            continue
        elif user_input == "/status":
            show_status(gm)
            continue
        elif user_input == "/tokens":
            stats = llm.get_usage_stats()
            print(f"\nToken统计: {stats}")
            continue
        elif user_input == "/history":
            print(f"\n对话历史: {len(gm.history)} 条消息")
            continue
        elif user_input.startswith("/save"):
            slot = user_input.split()[1] if len(user_input.split()) > 1 else "auto"
            from src.services.save_manager import save_game
            path = save_game(world_id, slot, db_path)
            print(f"\n游戏已保存: {path}")
            continue

        # 发送给GM
        try:
            print()
            response = gm.process(user_input)
            print(f"\nGM> {response}")
        except Exception as e:
            logger.error(f"处理失败: {e}")
            print(f"\n[系统错误] {e}")


if __name__ == "__main__":
    main()
