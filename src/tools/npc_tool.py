"""NPC信息工具"""
import json
from src.models import npc_repo
from src.tools import world_tool
from src.data.npc_templates import apply_template
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_npc(name: str, location_id: int, personality_type: str | None = None,
               mood: str | None = None, speech_style: str | None = None,
               backstory: str | None = None, db_path: str | None = None) -> str:
    """创建NPC"""
    wid = world_tool._active_world_id

    # 获取模板属性
    if personality_type:
        overrides = {}
        if mood:
            overrides["mood"] = mood
        if speech_style:
            overrides["speech_style"] = speech_style
        attrs = apply_template(personality_type, name, overrides or None)
    else:
        attrs = {
            "personality": json.dumps({}),
            "mood": mood or "neutral",
            "goals": json.dumps([]),
            "speech_style": speech_style or "",
        }

    npc_id = npc_repo.create_npc(
        wid, name, location_id,
        backstory=backstory or "",
        db_path=db_path,
        **attrs,
    )
    template_info = f"（模板: {personality_type}）" if personality_type else ""
    return f"已创建NPC: {name} (ID:{npc_id}) 在地点{location_id} {template_info}"


def get_npc_info(npc_id: int, db_path: str | None = None) -> str:
    """获取NPC详细信息"""
    npc = npc_repo.get_npc(npc_id, db_path)
    if not npc:
        return f"未找到ID为{npc_id}的NPC"
    lines = [
        f"【{npc['name']}】",
        f"心情: {npc.get('mood', 'neutral')}",
    ]
    if npc.get("backstory"):
        lines.append(f"背景: {npc['backstory']}")
    if npc.get("speech_style"):
        lines.append(f"说话风格: {npc['speech_style']}")
    if npc.get("goals"):
        lines.append(f"目标: {npc['goals']}")
    return "\n".join(lines)


def search_npc(name: str, db_path: str | None = None) -> str:
    """按名字模糊搜索NPC"""
    wid = world_tool._active_world_id
    # 简单搜索：遍历所有地点的NPC
    from src.models import location_repo
    results = []
    for loc in location_repo.get_locations_by_world(wid, db_path):
        for npc in npc_repo.get_npcs_by_location(loc["id"], db_path):
            if name.lower() in npc["name"].lower():
                results.append(f"- {npc['name']} (位于{loc['name']}, ID:{npc['id']})")
    if not results:
        return f"未找到名字包含'{name}'的NPC"
    return "搜索结果:\n" + "\n".join(results)


def npc_dialog(npc_id: int, player_message: str, db_path: str | None = None) -> str:
    """让NPC与玩家对话"""
    from src.services.npc_dialog import generate_npc_dialog
    return generate_npc_dialog(npc_id, player_message, db_path=db_path)


def update_relationship(npc_id: int, target_id: int, change: int, db_path: str | None = None) -> str:
    """更新NPC关系"""
    npc = npc_repo.get_npc(npc_id, db_path)
    if not npc:
        return f"未找到ID为{npc_id}的NPC"

    relationships = npc.get("relationships") or {}
    current = relationships.get(str(target_id), 0)
    new_value = max(-100, min(100, current + change))
    relationships[str(target_id)] = new_value

    npc_repo.update_npc(npc_id, relationships=relationships, db_path=db_path)

    direction = "提升" if change > 0 else "下降"
    return f"NPC {npc['name']} 对目标{target_id}的关系{direction}了{abs(change)}点，当前: {new_value}"


def get_relationship_graph(npc_id: int | None = None, db_path: str | None = None) -> str:
    """获取关系网络"""
    from src.models import location_repo
    wid = world_tool._active_world_id

    nodes = []
    edges = []

    for loc in location_repo.get_locations_by_world(wid, db_path):
        for npc in npc_repo.get_npcs_by_location(loc["id"], db_path):
            nodes.append({"id": npc["id"], "name": npc["name"], "location": loc["name"]})
            rels = npc.get("relationships") or {}
            for target_id, value in rels.items():
                if abs(value) >= 10:  # 只显示有意义的关系
                    edges.append({"from": npc["id"], "to": int(target_id), "value": value})

    if npc_id:
        edges = [e for e in edges if e["from"] == npc_id or e["to"] == npc_id]

    if not edges:
        return "暂无显著关系"

    lines = ["关系网络:"]
    for e in edges:
        from_name = next((n["name"] for n in nodes if n["id"] == e["from"]), f"ID:{e['from']}")
        to_name = next((n["name"] for n in nodes if n["id"] == e["to"]), f"ID:{e['to']}")
        sign = "❤️" if e["value"] > 0 else "💔"
        lines.append(f"  {from_name} {sign} {to_name} ({e['value']:+d})")
    return "\n".join(lines)
