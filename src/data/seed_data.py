"""种子数据 - 默认游戏世界"""
from src.services.database import init_db, get_db
from src.models import (
    world_repo, location_repo, player_repo,
    npc_repo, item_repo, quest_repo,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def seed_world(db_path: str | None = None) -> dict:
    """创建默认游戏世界

    Returns:
        包含 world_id, player_id 等关键ID的字典
    """
    init_db(db_path)
    logger.info("开始加载种子数据...")

    # 1. 创建世界
    world_id = world_repo.create_world(
        "艾泽拉斯大陆",
        "fantasy",
        db_path=db_path,
    )

    # 2. 创建地点
    locations = {}
    loc_data = [
        ("宁静村", "一个位于大陆东部的宁静小村庄，周围是翠绿的农田和古老的石墙", {"east": 0}),
        ("幽暗森林", "村庄北方的茂密森林，阳光难以穿透树冠，传闻有野兽出没", {"south": 0}),
        ("矿洞入口", "村庄东边的废弃矿洞，深处传来奇怪的声音", {"west": 0}),
        ("流浪者酒馆", "宁静村中心的古老酒馆，冒险者们在此交换情报", None),
        ("村长宅邸", "村庄最古老的建筑，村长在此处理村务", None),
    ]
    for name, desc, conn in loc_data:
        lid = location_repo.create_location(world_id, name, desc, conn, db_path)
        locations[name] = lid

    # 设置双向连接
    location_repo.update_location(locations["宁静村"], connections={"east": locations["矿洞入口"], "north": locations["幽暗森林"]}, db_path=db_path)
    location_repo.update_location(locations["幽暗森林"], connections={"south": locations["宁静村"]}, db_path=db_path)
    location_repo.update_location(locations["矿洞入口"], connections={"west": locations["宁静村"]}, db_path=db_path)

    # 3. 创建NPC
    npc_data = [
        ("老村长", locations["村长宅邸"], {"openness": 0.6, "conscientiousness": 0.9}, "宁静村的村长，已经守护村庄三十年", "wise", "说话缓慢而庄重，经常引用古老的谚语"),
        ("酒馆老板 铁锤", locations["流浪者酒馆"], {"extraversion": 0.9, "agreeableness": 0.8}, "矮人酒馆老板，曾经是冒险者", "cheerful", "热情豪爽，喜欢讲当年的冒险故事"),
        ("铁匠 铁砧", locations["宁静村"], {"conscientiousness": 0.9, "neuroticism": 0.3}, "村庄的铁匠，手艺精湛但话不多", "neutral", "说话简短直接，专注于锻造"),
        ("神秘旅者", locations["流浪者酒馆"], {"openness": 0.95, "extraversion": 0.2}, "来历不明的旅者，似乎知道很多秘密", "mysterious", "说话隐晦，喜欢用谜语回答问题"),
    ]
    for name, loc, personality, backstory, mood, speech in npc_data:
        npc_repo.create_npc(
            world_id, name, loc,
            personality=personality, backstory=backstory,
            mood=mood, speech_style=speech,
            db_path=db_path,
        )

    # 4. 创建道具
    item_data = [
        ("木剑", "weapon", "common", {"attack": 3}, "一把简陋的木制训练剑", 1, False, False, "weapon"),
        ("铁剑", "weapon", "uncommon", {"attack": 8}, "标准的铁制长剑，冒险者的入门武器", 3, False, False, "weapon"),
        ("治疗药水", "potion", "common", {"hp": 30}, "红色的液体，饮用后恢复30点生命值", 1, True, True, None),
        ("大治疗药水", "potion", "rare", {"hp": 80}, "浓稠的红色液体，恢复80点生命值", 5, True, True, None),
        ("皮甲", "armor", "common", {"defense": 3}, "轻便的皮革护甲", 1, False, False, "chest"),
        ("铁盾", "armor", "uncommon", {"defense": 5}, "一面坚固的铁盾", 3, False, False, "shield"),
        ("魔法卷轴·火球", "scroll", "rare", {"damage": 40}, "释放一颗火球，造成40点伤害", 5, False, True, None),
        ("面包", "misc", "common", {}, "简单的面包，可以充饥", 1, True, True, None),
        ("火把", "misc", "common", {}, "照亮黑暗的火把", 1, True, False, None),
        ("经验宝石", "misc", "epic", {"exp": 200}, "蕴含魔力的宝石，使用后获得200经验值", 1, False, True, None),
    ]
    for name, itype, rarity, stats, desc, lvl, stack, use, slot in item_data:
        item_repo.create_item(name, itype, rarity, stats, desc, lvl, stack, use, slot, db_path)

    # 5. 创建初始任务
    quest_repo.create_quest(
        world_id, "哥布林的威胁",
        "村长告诉你，最近幽暗森林中的哥布林越来越猖獗，已经威胁到村庄的安全。请前往幽暗森林调查并消灭哥布林。",
        "main", rewards={"exp": 100, "gold": 50, "items": "铁剑"},
        db_path=db_path,
    )
    quest_repo.create_quest(
        world_id, "铁匠的请求",
        "铁匠铁砧需要从矿洞中获取一些稀有矿石来锻造新武器。请前往矿洞入口探索。",
        "side", rewards={"exp": 50, "gold": 30},
        db_path=db_path,
    )

    # 6. 创建默认玩家
    player_id = player_repo.create_player(world_id, "冒险者", db_path=db_path)
    # 设置玩家属性
    player_repo.update_player(
        player_id, db_path=db_path,
        hp=100, max_hp=100, mp=50, max_mp=50,
        level=1, exp=0, gold=10,
        location_id=locations["宁静村"],
    )
    logger.info(f"创建默认玩家: 冒险者 (id={player_id})")

    # 给玩家一些初始物品
    player_repo.add_item(player_id, 1, 1, db_path)  # 木剑
    player_repo.add_item(player_id, 3, 3, db_path)  # 治疗药水 x3
    player_repo.add_item(player_id, 8, 5, db_path)  # 面包 x5

    logger.info(f"种子数据加载完成！世界ID: {world_id}, 玩家ID: {player_id}")
    return {"world_id": world_id, "locations": locations, "player_id": player_id}
