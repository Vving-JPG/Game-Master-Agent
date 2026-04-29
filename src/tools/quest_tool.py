"""任务工具集"""
import json
from src.models import quest_repo
from src.tools import world_tool
from src.data.story_templates import generate_quest_from_template
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_quest(title: str, description: str, quest_type: str = "side",
                 template_name: str | None = None, template_vars: str | None = None,
                 db_path: str | None = None) -> str:
    """创建任务"""
    wid = world_tool._active_world_id
    pid = world_tool._active_player_id

    branches = None
    rewards = None

    if template_name and template_vars:
        try:
            vars_dict = json.loads(template_vars)
            quest_data = generate_quest_from_template(template_name, vars_dict, quest_type)
            title = quest_data["title"]
            description = quest_data["description"]
            rewards = quest_data["rewards"]
            branches = quest_data["branches"]
        except Exception as e:
            return f"模板生成失败: {e}"

    qid = quest_repo.create_quest(
        wid, title, description,
        quest_type=quest_type,
        branches=branches,
        rewards=rewards,
        db_path=db_path,
    )

    # 分配给玩家
    if pid:
        quest_repo.assign_quest(qid, pid, db_path=db_path)

    # 如果有模板步骤，自动创建
    if template_name and template_vars:
        try:
            vars_dict = json.loads(template_vars)
            quest_data = generate_quest_from_template(template_name, vars_dict)
            for step in quest_data["steps"]:
                quest_repo.create_quest_step(
                    qid, step["step_order"], step["description"],
                    step_type=step.get("step_type", "goto"),
                    target=step.get("target", ""),
                    required_count=step.get("required_count", 1),
                    db_path=db_path,
                )
        except Exception:
            pass

    return f"已创建任务: {title} (ID:{qid}, 类型:{quest_type})"


def update_quest_progress(quest_id: int, step_index: int, progress: int,
                         db_path: str | None = None) -> str:
    """更新任务进度"""
    steps = quest_repo.get_quest_steps(quest_id, db_path)
    if not steps:
        return f"未找到任务{quest_id}的步骤"
    if step_index >= len(steps):
        return f"步骤序号{step_index}超出范围（共{len(steps)}步）"

    step = steps[step_index]
    quest_repo.update_quest_step(step["id"], current_count=progress, db_path=db_path)

    # 检查是否完成
    if progress >= step["required_count"]:
        quest_repo.update_quest_step(step["id"], completed=1, db_path=db_path)
        if step_index + 1 < len(steps):
            return f"步骤完成！下一步: {steps[step_index + 1]['description']}"
        else:
            quest_repo.update_quest(quest_id, status="completed", db_path=db_path)
            return f"🎉 任务完成！所有步骤已完成。"

    return f"进度更新: {step['description']} ({progress}/{step['required_count']})"


def handle_choice(quest_id: int, choice_id: str, db_path: str | None = None) -> str:
    """处理分支选择"""
    quest = quest_repo.get_quest(quest_id, db_path)
    if not quest:
        return f"未找到任务{quest_id}"

    branches = quest.get("branches") or []
    chosen = next((b for b in branches if b["id"] == choice_id), None)
    if not chosen:
        return f"无效的选择: {choice_id}，可选: {[b['id'] for b in branches]}"

    logger.info(f"任务{quest_id}分支选择: {choice_id} → {chosen['text']}")
    return f"你选择了: {chosen['text']}"
