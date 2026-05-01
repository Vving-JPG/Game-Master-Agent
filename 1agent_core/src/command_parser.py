"""
Agent 输出解析器。
将 LLM 的文本输出解析为标准 JSON 命令流。

容错策略:
1. 直接 JSON 解析
2. 提取 ```json ... ``` 代码块
3. 提取 { ... } JSON 对象
4. 兜底: 将整个文本作为 narrative
"""
from __future__ import annotations

import json
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CommandParser:
    """LLM 输出解析器"""

    def parse(self, raw_text: str) -> dict:
        """
        解析 LLM 输出为标准 JSON 命令流。

        返回格式:
        {
            "narrative": str,
            "commands": list[dict],
            "memory_updates": list[dict]
        }
        """
        text = raw_text.strip()
        if not text:
            return self._empty_response()

        # 策略 1: 直接 JSON 解析
        result = self._try_direct_parse(text)
        if result:
            return result

        # 策略 2: 提取 ```json ... ``` 代码块
        result = self._try_json_block(text)
        if result:
            return result

        # 策略 3: 提取最外层 { ... }
        result = self._try_brace_extract(text)
        if result:
            return result

        # 策略 4: 兜底 — 整个文本作为 narrative
        logger.warning("无法解析 LLM 输出为 JSON，将整个文本作为 narrative")
        return {"narrative": text, "commands": [], "memory_updates": []}

    def _try_direct_parse(self, text: str) -> Optional[dict]:
        """策略 1: 直接 JSON 解析"""
        try:
            result = json.loads(text)
            if isinstance(result, dict) and "narrative" in result:
                return self._normalize(result)
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def _try_json_block(self, text: str) -> Optional[dict]:
        """策略 2: 提取 ```json ... ``` 代码块"""
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if not match:
            return None
        try:
            result = json.loads(match.group(1))
            if isinstance(result, dict) and "narrative" in result:
                return self._normalize(result)
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def _try_brace_extract(self, text: str) -> Optional[dict]:
        """策略 3: 提取最外层 { ... }"""
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, dict) and "narrative" in result:
                return self._normalize(result)
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def _normalize(self, result: dict) -> dict:
        """确保响应包含所有必需字段"""
        return {
            "narrative": result.get("narrative", ""),
            "commands": self._normalize_commands(result.get("commands", [])),
            "memory_updates": self._normalize_memory_updates(
                result.get("memory_updates", [])
            ),
        }

    def _normalize_commands(self, commands: list) -> list[dict]:
        """规范化 commands 列表"""
        normalized = []
        for cmd in commands:
            if isinstance(cmd, dict) and "intent" in cmd:
                normalized.append({
                    "intent": cmd["intent"],
                    "params": cmd.get("params", {}),
                })
        return normalized

    def _normalize_memory_updates(self, updates: list) -> list[dict]:
        """规范化 memory_updates 列表"""
        normalized = []
        for upd in updates:
            if isinstance(upd, dict) and "file" in upd and "action" in upd:
                entry = {"file": upd["file"], "action": upd["action"]}
                if "content" in upd:
                    entry["content"] = upd["content"]
                if "frontmatter" in upd:
                    entry["frontmatter"] = upd["frontmatter"]
                normalized.append(entry)
        return normalized

    def _empty_response(self) -> dict:
        """空响应"""
        return {"narrative": "", "commands": [], "memory_updates": []}
