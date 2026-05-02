# 2workbench/feature/ai/command_parser.py
"""命令解析器 — 将 LLM 输出解析为结构化命令

4 级容错策略:
1. 直接 JSON 解析
2. 提取 ```json ... ``` 代码块
3. 提取最外层 { ... }
4. 兜底: 整个文本作为 narrative

从 1agent_core/src/command_parser.py 重构而来。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedCommand:
    """解析后的命令"""
    intent: str           # 命令意图（如 update_hp, move_to, give_item）
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedOutput:
    """解析后的完整输出"""
    narrative: str = ""                     # 叙事文本
    commands: list[ParsedCommand] = field(default_factory=list)
    memory_updates: list[dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""                      # 原始文本
    parse_method: str = ""                  # 使用的解析方法


def parse_llm_output(text: str) -> ParsedOutput:
    """解析 LLM 输出（4 级容错）

    Args:
        text: LLM 的原始文本输出

    Returns:
        ParsedOutput
    """
    if not text or not text.strip():
        return ParsedOutput(narrative="", raw_text=text, parse_method="empty")

    text = text.strip()
    result = ParsedOutput(raw_text=text)

    # 第 1 级: 直接 JSON 解析
    data = _try_parse_json(text)
    if data and "narrative" in data:
        result.parse_method = "direct_json"
        _fill_result(result, data)
        return result

    # 第 2 级: 提取 ```json ... ``` 代码块
    json_block = _extract_json_block(text)
    if json_block:
        data = _try_parse_json(json_block)
        if data and "narrative" in data:
            result.parse_method = "json_block"
            _fill_result(result, data)
            return result

    # 第 3 级: 提取最外层 { ... }
    json_outer = _extract_outer_braces(text)
    if json_outer:
        data = _try_parse_json(json_outer)
        if data and "narrative" in data:
            result.parse_method = "outer_braces"
            _fill_result(result, data)
            return result

    # 第 4 级: 兜底 — 整个文本作为 narrative
    result.parse_method = "fallback"
    result.narrative = text
    logger.debug(f"命令解析使用兜底策略（无法解析为 JSON）")

    return result


def _try_parse_json(text: str) -> dict | None:
    """尝试 JSON 解析"""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def _extract_json_block(text: str) -> str | None:
    """提取 ```json ... ``` 代码块"""
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None


def _extract_outer_braces(text: str) -> str | None:
    """提取最外层 { ... }"""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return None


def _fill_result(result: ParsedOutput, data: dict) -> None:
    """从 JSON 数据填充解析结果"""
    result.narrative = data.get("narrative", "")

    # 解析命令
    for cmd in data.get("commands", []):
        if isinstance(cmd, dict) and "intent" in cmd:
            result.commands.append(ParsedCommand(
                intent=cmd["intent"],
                params=cmd.get("params", {}),
            ))

    # 解析记忆更新
    for mem in data.get("memory_updates", []):
        if isinstance(mem, dict) and "action" in mem:
            result.memory_updates.append(mem)
