"""
简单 Agent 演示 — 使用 GMAgent 进行对话

这个脚本演示如何:
1. 创建世界和玩家
2. 初始化 GMAgent
3. 运行对话回合
"""
from __future__ import annotations

import sys
from pathlib import Path

# 确保项目路径
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from foundation.database import init_db, get_db
from foundation.logger import get_logger
from core.models import WorldRepo, PlayerRepo, NPCRepo
from feature.ai import GMAgent

logger = get_logger(__name__)


def create_simple_agent_demo():
    """创建并运行简单 Agent 演示"""
    
    # 1. 初始化数据库
    db_path = PROJECT_ROOT / "data" / "demo.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    init_db(db_path=str(db_path))
    
    print("=" * 60)
    print("🎮 简单 Agent 演示")
    print("=" * 60)
    
    # 2. 创建世界
    world_repo = WorldRepo()
    world = world_repo.create(
        name="新手村",
        setting="fantasy",
        description="一个宁静的新手村庄，适合冒险者开始他们的旅程。",
        db_path=str(db_path)
    )
    print(f"✅ 创建世界: {world.name} (ID: {world.id})")
    
    # 3. 创建地点
    from core.models import LocationRepo
    location_repo = LocationRepo()
    location = location_repo.create(
        world_id=world.id,
        name="村庄广场",
        description="村庄的中心广场，村民们经常在这里聚集交流。",
        db_path=str(db_path)
    )
    print(f"✅ 创建地点: {location.name} (ID: {location.id})")
    
    # 4. 创建 NPC
    npc_repo = NPCRepo()
    npc = npc_repo.create(
        world_id=world.id,
        location_id=location.id,
        name="老村长",
        backstory="村庄的长者，经验丰富，乐于助人。",
        personality='{"kindness": 0.8, "wisdom": 0.9, "patience": 0.7}',
        speech_style="慈祥而睿智，经常使用谚语和故事来教导年轻人。",
        db_path=str(db_path)
    )
    print(f"✅ 创建 NPC: {npc.name} (ID: {npc.id})")
    
    # 4. 初始化 GMAgent
    print("\n🤖 初始化 GMAgent...")
    agent = GMAgent(world_id=world.id, db_path=str(db_path))
    print("✅ Agent 初始化完成")
    
    # 5. 运行对话
    print("\n" + "=" * 60)
    print("💬 开始对话")
    print("=" * 60)
    
    # 模拟玩家输入
    player_inputs = [
        "你好，我是新来的冒险者。",
        "我想了解一下这个村庄。",
        "有什么任务可以给我吗？"
    ]
    
    for i, player_input in enumerate(player_inputs, 1):
        print(f"\n--- 回合 {i} ---")
        print(f"👤 玩家: {player_input}")
        
        # 这里我们只是演示结构，实际运行需要配置 LLM API
        # result = agent.run_sync(f"玩家说: {player_input}")
        # print(f"🤖 Agent: {result}")
        
        # 模拟响应
        print(f"🤖 Agent: [需要配置 LLM API 才能生成真实响应]")
        print(f"   事件已发送: feature.ai.turn_start")
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")
    print("=" * 60)
    print(f"\n数据库保存位置: {db_path}")
    print("\n要运行真实的 Agent 对话，请:")
    print("1. 配置 LLM API Key (DeepSeek/OpenAI/Anthropic)")
    print("2. 在 .env 文件中设置 API Key")
    print("3. 取消注释 agent.run_sync() 调用")
    print("\n示例 .env 配置:")
    print("  DEEPSEEK_API_KEY=sk-xxx")
    print("  DEEPSEEK_BASE_URL=https://api.deepseek.com")


if __name__ == "__main__":
    create_simple_agent_demo()
