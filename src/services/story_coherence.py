"""剧情连贯性管理 - 确保剧情逻辑一致"""
from src.models import quest_repo, npc_repo
from src.utils.logger import get_logger

logger = get_logger(__name__)


def check_prerequisites(quest_id: int, player_id: int, db_path: str | None = None) -> tuple[bool, str]:
    """检查任务前置条件是否满足

    Returns:
        (是否满足, 原因)
    """
    quest = quest_repo.get_quest(quest_id, db_path)
    if not quest:
        return False, f"任务{quest_id}不存在"

    prerequisites = quest.get("prerequisites") or []
    if not prerequisites:
        return True, "无前置条件"

    # 检查每个前置条件
    for prereq in prerequisites:
        ptype = prereq.get("type")
        if ptype == "quest_completed":
            # 检查是否完成了指定任务
            required_quest_id = prereq.get("quest_id")
            # 获取该任务状态
            required_quest = quest_repo.get_quest(required_quest_id, db_path)
            if not required_quest or required_quest.get("status") != "completed":
                return False, f"需要先完成任务: {required_quest.get('title', required_quest_id) if required_quest else required_quest_id}"

        elif ptype == "level":
            # 检查等级
            from src.models import player_repo
            player = player_repo.get_player(player_id, db_path)
            if not player or player.get("level", 0) < prereq.get("level", 1):
                return False, f"需要等级{prereq.get('level')}"

        elif ptype == "npc_relationship":
            # 检查NPC关系
            npc_id = prereq.get("npc_id")
            min_rel = prereq.get("min_relationship", 0)
            npc = npc_repo.get_npc(npc_id, db_path)
            if npc:
                rels = npc.get("relationships") or {}
                if rels.get(str(player_id), 0) < min_rel:
                    return False, f"与{npc['name']}的关系需要达到{min_rel}"

    return True, "所有前置条件满足"


def validate_choice(quest_id: int, choice_id: str, db_path: str | None = None) -> tuple[bool, str]:
    """验证分支选择是否合法"""
    quest = quest_repo.get_quest(quest_id, db_path)
    if not quest:
        return False, f"任务{quest_id}不存在"

    branches = quest.get("branches") or []
    valid_ids = [b["id"] for b in branches]

    if choice_id not in valid_ids:
        return False, f"无效选择'{choice_id}'，可选: {valid_ids}"

    return True, "选择有效"


def get_story_summary(world_id: int, player_id: int, db_path: str | None = None) -> dict:
    """获取剧情摘要，用于GM了解当前剧情状态"""
    # 获取玩家任务
    quests = quest_repo.get_quests_by_player(player_id, db_path)

    summary = {
        "active_quests": [],
        "completed_quests": [],
        "failed_quests": [],
    }

    for q in quests:
        if q.get("status") == "active":
            summary["active_quests"].append({
                "id": q["id"],
                "title": q["title"],
                "description": q["description"][:50] + "..." if len(q["description"]) > 50 else q["description"],
            })
        elif q.get("status") == "completed":
            summary["completed_quests"].append({"id": q["id"], "title": q["title"]})
        elif q.get("status") == "failed":
            summary["failed_quests"].append({"id": q["id"], "title": q["title"]})

    return summary


def format_story_context(world_id: int, player_id: int, db_path: str | None = None) -> str:
    """格式化剧情上下文，用于GM Prompt"""
    summary = get_story_summary(world_id, player_id, db_path)

    lines = ["## 当前剧情状态"]

    if summary["active_quests"]:
        lines.append("### 进行中的任务")
        for q in summary["active_quests"]:
            lines.append(f"- {q['title']}: {q['description']}")

    if summary["completed_quests"]:
        lines.append("### 已完成的任务")
        for q in summary["completed_quests"]:
            lines.append(f"- ✓ {q['title']}")

    return "\n".join(lines)
