"""剧情模板测试"""
from src.data.story_templates import generate_quest_from_template, STORY_TEMPLATES


def test_rescue_template():
    """救援模板"""
    quest = generate_quest_from_template("rescue", {
        "victim": "公主", "enemy": "巨龙", "location": "龙穴"
    })
    assert "公主" in quest["title"]
    assert len(quest["steps"]) == 3
    assert quest["steps"][1]["step_type"] == "kill"
    assert quest["rewards"]["exp"] == 150


def test_collect_template():
    """收集模板"""
    quest = generate_quest_from_template("collect", {
        "item": "草药", "count": "5", "giver": "村长"
    })
    assert quest["steps"][0]["required_count"] == 5


def test_unknown_template():
    """未知模板"""
    try:
        generate_quest_from_template("nonexistent", {})
        assert False
    except ValueError:
        pass
