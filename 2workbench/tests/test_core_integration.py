"""Core 层集成测试"""
import sys, os, tempfile, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

random.seed(42)


def test_full_game_state_flow():
    """测试完整的游戏状态流程"""
    from foundation.database import init_db
    from core.models import (
        WorldRepo, PlayerRepo, NPCRepo, LocationRepo, ItemRepo,
        MemoryRepo, QuestRepo, LogRepo,
    )
    from core.state import create_initial_state

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        tmp_db = f.name

    try:
        init_db(db_path=tmp_db)

        # 创建世界
        world_repo = WorldRepo()
        world = world_repo.create(name='测试世界', setting='fantasy', db_path=tmp_db)

        # 创建地点
        loc_repo = LocationRepo()
        village = loc_repo.create(world_id=world.id, name='宁静村', connections={'north': 0}, db_path=tmp_db)
        forest = loc_repo.create(world_id=world.id, name='幽暗森林', connections={'south': village.id}, db_path=tmp_db)

        # 创建玩家
        player_repo = PlayerRepo()
        player = player_repo.create(world_id=world.id, name='冒险者', location_id=village.id, db_path=tmp_db)

        # 创建 NPC
        npc_repo = NPCRepo()
        elder = npc_repo.create(world_id=world.id, name='老村长', location_id=village.id, db_path=tmp_db)

        # 创建道具
        item_repo = ItemRepo()
        sword = item_repo.create(name='木剑', item_type='weapon', stats={'attack': 5}, db_path=tmp_db)
        potion = item_repo.create(name='治疗药水', item_type='consumable', usable=True, stackable=True, db_path=tmp_db)

        # 给玩家添加物品
        player_repo.add_item(player.id, sword.id, db_path=tmp_db)
        player_repo.add_item(player.id, potion.id, quantity=3, db_path=tmp_db)
        inventory = player_repo.get_inventory(player.id, db_path=tmp_db)
        assert len(inventory) == 2

        # 创建任务
        quest_repo = QuestRepo()
        quest = quest_repo.create(world_id=world.id, title='消灭哥布林', quest_type='main', db_path=tmp_db)
        quest_repo.update_status(quest.id, 'active', db_path=tmp_db)

        # 存储记忆
        mem_repo = MemoryRepo()
        mem_repo.store(world_id=world.id, category='session', source='system',
                      content='冒险者来到了宁静村', importance=0.9, turn=0, db_path=tmp_db)
        mem_repo.store(world_id=world.id, category='npc', source='npc:老村长',
                      content='老村长请求冒险者消灭哥布林', importance=0.8, turn=1, db_path=tmp_db)

        # 记录日志
        log_repo = LogRepo()
        log_repo.log(world.id, 'quest', '任务开始: 消灭哥布林', db_path=tmp_db)

        # 创建 Agent State
        state = create_initial_state(world_id=str(world.id), player_name=player.name)
        state['player']['id'] = player.id
        state['current_location'] = {'id': village.id, 'name': village.name}
        state['active_npcs'] = [{'id': elder.id, 'name': elder.name}]
        state['turn_count'] = 1

        # 检索记忆
        memories = mem_repo.recall(world_id=world.id, limit=10, db_path=tmp_db)
        assert len(memories) == 2

        # 验证 State
        assert state['world_id'] == str(world.id)
        assert state['turn_count'] == 1
        assert len(state['active_npcs']) == 1

        print('✅ test_full_game_state_flow')

    finally:
        os.unlink(tmp_db)


def test_calculators_with_state():
    """测试计算器与 State 的配合"""
    from core.calculators.combat import Combatant, combat_round, is_combat_over, calculate_rewards
    from core.calculators.ending import calculate_ending_score, determine_ending

    player = Combatant(name='冒险者', hp=100, max_hp=100, attack_bonus=3, damage_dice='1d8', ac=15)
    enemies = [
        Combatant(name='哥布林A', hp=15, max_hp=15, attack_bonus=1, damage_dice='1d4', ac=10),
        Combatant(name='哥布林B', hp=15, max_hp=15, attack_bonus=1, damage_dice='1d4', ac=10),
    ]

    round_num = 0
    while not is_combat_over(player, enemies) and round_num < 20:
        combat_round(player, enemies)
        round_num += 1

    rewards = calculate_rewards(enemies)
    assert rewards['defeated_count'] >= 0

    # 结局计算
    scores = calculate_ending_score(main_quests_completed=3, total_main_quests=5, player_hp=player.hp)
    ending = determine_ending(scores)
    assert ending in ('hero', 'villain', 'neutral', 'tragic', 'secret')

    print(f'✅ test_calculators_with_state (战斗 {round_num} 轮, 结局: {ending})')


def test_templates_with_repo():
    """测试模板与 Repository 的配合"""
    from core.constants.npc_templates import apply_template
    from core.constants.story_templates import generate_quest_from_template

    # NPC 模板
    npc_data = apply_template('wise_elder', overrides={'name': '自定义长者'})
    assert npc_data['name'] == '自定义长者'
    assert npc_data['personality'].openness == 0.8

    # 剧情模板
    quest = generate_quest_from_template('collect', npc='铁匠', item='铁矿石', count=5)
    assert '铁矿石' in quest['description']
    assert len(quest['steps']) == 3

    print('✅ test_templates_with_repo')


if __name__ == "__main__":
    test_full_game_state_flow()
    test_calculators_with_state()
    test_templates_with_repo()
    print("\n🎉 Core 层集成测试全部通过!")