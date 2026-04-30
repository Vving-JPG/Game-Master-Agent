"""
V2 命令行入口 — MUD 文字游戏模式。
通过 TextAdapter 连接 SQLite 引擎，启动事件驱动的 Agent 循环。
"""
from __future__ import annotations

import asyncio
import logging
import sys

from src.adapters.text_adapter import TextAdapter
from src.adapters.base import EngineEvent
from src.agent.game_master import GameMaster
from src.agent.event_handler import EventHandler
from src.memory.manager import MemoryManager
from src.skills.loader import SkillLoader
from src.services.llm_client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 配置
WORLD_ID = "w1"
PLAYER_ID = "p1"
WORKSPACE_PATH = "./workspace"
SKILLS_PATH = "./skills"
SYSTEM_PROMPT_PATH = "./prompts/system_prompt.md"


async def run_text_mode():
    """启动 MUD 文字游戏模式"""

    # 1. 初始化 LLM
    logger.info("初始化 LLM 客户端...")
    llm_client = LLMClient()

    # 2. 初始化记忆和 Skill
    logger.info("初始化记忆系统...")
    memory_manager = MemoryManager(WORKSPACE_PATH)

    logger.info("初始化 Skill 系统...")
    skill_loader = SkillLoader(SKILLS_PATH)

    # 3. 初始化引擎适配器
    logger.info("连接游戏引擎...")
    adapter = TextAdapter.from_world_id(WORLD_ID)
    await adapter.connect()

    # 4. 初始化 GameMaster
    logger.info("初始化 Game Master Agent...")
    game_master = GameMaster(
        llm_client=llm_client,
        memory_manager=memory_manager,
        skill_loader=skill_loader,
        engine_adapter=adapter,
        system_prompt_path=SYSTEM_PROMPT_PATH,
    )

    # 5. 初始化 EventHandler
    event_handler = EventHandler(
        game_master=game_master,
        engine_adapter=adapter,
    )

    # 6. 注册 SSE 回调（命令行模式只打印关键事件）
    async def print_sse(event_name: str, data: dict):
        if event_name == "turn_start":
            print("\n--- 回合开始 ---")
        elif event_name == "command":
            intent = data.get("intent", "")
            if intent != "no_op":
                print(f"  [指令] {intent}")
        elif event_name == "turn_end":
            stats = data.get("stats", {})
            print(f"--- 回合结束 (tokens: {stats.get('tokens_used', 0)}) ---\n")

    event_handler.register_sse_callback(print_sse)

    # 7. 交互循环
    print("=" * 50)
    print("  Game Master Agent V2 — MUD 模式")
    print(f"  世界: {WORLD_ID} | 玩家: {PLAYER_ID}")
    print("  输入 'quit' 退出, 'status' 查看状态")
    print("=" * 50)

    # 获取初始游戏状态
    player = await adapter.query_state("player", {"player_id": PLAYER_ID})
    location = player.get("location", "未知") if player else "未知"
    print(f"\n你当前在: {location}\n")

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        if user_input.lower() == "status":
            status = {
                "回合": game_master.turn_count,
                "总 Token": game_master.total_tokens,
                "历史长度": len(game_master.history),
            }
            for k, v in status.items():
                print(f"  {k}: {v}")
            continue

        if user_input.lower() == "help":
            print("  可用命令:")
            print("  quit/exit — 退出")
            print("  status — 查看状态")
            print("  help — 帮助")
            print("  其他输入 — 作为玩家操作发送给 Agent")
            continue

        # 构造引擎事件
        event = EngineEvent(
            event_id=f"cli_{game_master.turn_count + 1}",
            timestamp=__import__("datetime").datetime.now().isoformat(),
            type="player_action",
            data={"raw_text": user_input, "player_id": PLAYER_ID},
            context_hints=[],
            game_state={},
        )

        # 处理事件
        try:
            response = await event_handler.handle_event(event)
            print(f"\n{response.get('narrative', '')}")
        except Exception as e:
            logger.error(f"处理事件失败: {e}", exc_info=True)
            print(f"\n[错误] {e}")


def main():
    """入口"""
    try:
        asyncio.run(run_text_mode())
    except KeyboardInterrupt:
        print("\n再见！")


if __name__ == "__main__":
    main()
