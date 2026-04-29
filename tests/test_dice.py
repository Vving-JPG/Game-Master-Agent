"""骰子工具测试"""
import pytest
from src.tools.dice import roll_dice


def test_d20():
    """d20结果在1-20之间"""
    for _ in range(20):
        result = roll_dice("1d20")
        assert 1 <= result["total"] <= 20
        assert len(result["rolls"]) == 1


def test_2d6_plus3():
    """2d6+3结果在5-15之间"""
    for _ in range(20):
        result = roll_dice("2d6+3")
        assert 5 <= result["total"] <= 15
        assert len(result["rolls"]) == 2
        assert result["modifier"] == 3


def test_3d8_minus1():
    """3d8-1结果在2-23之间"""
    for _ in range(20):
        result = roll_dice("3d8-1")
        assert 2 <= result["total"] <= 23
        assert result["modifier"] == -1


def test_d100():
    """d100（省略数量）"""
    for _ in range(10):
        result = roll_dice("d100")
        assert 1 <= result["total"] <= 100
        assert len(result["rolls"]) == 1


def test_expression_parse():
    """各种表达式解析正确"""
    r1 = roll_dice("1d6")
    assert r1["modifier"] == 0
    assert len(r1["rolls"]) == 1

    r2 = roll_dice("4d12+5")
    assert r2["modifier"] == 5
    assert len(r2["rolls"]) == 4


def test_invalid_expression():
    """无效表达式抛出异常"""
    with pytest.raises(ValueError):
        roll_dice("abc")
    with pytest.raises(ValueError):
        roll_dice("0d6")
    with pytest.raises(ValueError):
        roll_dice("1d0")


def test_result_structure():
    """返回值结构正确"""
    result = roll_dice("2d6+3")
    assert "expression" in result
    assert "rolls" in result
    assert "modifier" in result
    assert "subtotal" in result
    assert "total" in result
