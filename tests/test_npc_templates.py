"""NPC性格模板测试"""
from src.data.npc_templates import get_template, list_templates, apply_template
import json


def test_list_templates():
    """至少有5个模板"""
    templates = list_templates()
    assert len(templates) >= 5
    assert "brave_warrior" in templates


def test_get_template():
    """获取模板内容正确"""
    t = get_template("brave_warrior")
    assert t["name"] == "勇敢战士"
    assert t["personality"]["extraversion"] > 0.5
    assert "战斗" in t["common_topics"]


def test_apply_template():
    """应用模板生成属性"""
    attrs = apply_template("mysterious_mage", "甘道夫")
    personality = json.loads(attrs["personality"])
    assert personality["openness"] > 0.8
    assert attrs["mood"] == "contemplative"


def test_apply_template_with_overrides():
    """自定义覆盖"""
    attrs = apply_template("friendly_merchant", "商人", {"mood": "angry"})
    assert attrs["mood"] == "angry"


def test_unknown_template():
    """未知模板抛异常"""
    try:
        apply_template("nonexistent", "测试")
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "未知模板" in str(e)
