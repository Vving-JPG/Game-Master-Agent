"""安全护栏服务 — Feature 层

负责内容过滤规则的管理和过滤逻辑，通过 EventBus 与 Presentation 层通信。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any
from enum import Enum

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger

logger = get_logger(__name__)


class SafetyLevel(str, Enum):
    """安全级别"""
    STRICT = "strict"      # 严格: 所有规则启用
    STANDARD = "standard"  # 标准: 大部分规则启用
    RELAXED = "relaxed"    # 宽松: 仅关键规则启用


@dataclass
class FilterRule:
    """过滤规则"""
    id: str = ""
    name: str = ""
    pattern: str = ""       # 正则表达式
    category: str = "custom"  # violence / sexual / political / custom
    level: str = "standard"   # strict / standard / relaxed
    enabled: bool = True
    replacement: str = "***"  # 替换文本


# 默认过滤规则
DEFAULT_RULES = [
    FilterRule(id="r1", name="暴力内容", pattern=r"(杀|砍|斩|刺|血腥)", category="violence", level="strict"),
    FilterRule(id="r2", name="色情内容", pattern=r"(裸|性|色情)", category="sexual", level="strict"),
    FilterRule(id="r3", name="政治敏感", pattern=r"(政治|敏感|领导人)", category="political", level="standard"),
]


class SafetyService:
    """安全护栏服务

    管理内容过滤规则和过滤逻辑。
    """

    def __init__(self):
        self._rules: list[FilterRule] = list(DEFAULT_RULES)
        self._safety_level = SafetyLevel.STANDARD
        self._setup_listeners()

    def _setup_listeners(self):
        """设置 EventBus 监听器"""
        event_bus.subscribe("ui.safety.rules.load_requested", self._on_load_rules)
        event_bus.subscribe("ui.safety.rules.save_requested", self._on_save_rules)
        event_bus.subscribe("ui.safety.rule.add_requested", self._on_add_rule)
        event_bus.subscribe("ui.safety.rule.update_requested", self._on_update_rule)
        event_bus.subscribe("ui.safety.rule.delete_requested", self._on_delete_rule)
        event_bus.subscribe("ui.safety.level.change_requested", self._on_change_level)
        event_bus.subscribe("ui.safety.filter.requested", self._on_filter_content)
        event_bus.subscribe("ui.safety.preview.requested", self._on_preview_filter)
        event_bus.subscribe("ui.safety.export.requested", self._on_export_rules)
        event_bus.subscribe("ui.safety.import.requested", self._on_import_rules)

    def _get_active_rules(self) -> list[FilterRule]:
        """获取当前安全级别下启用的规则"""
        level_priority = {
            SafetyLevel.STRICT: ["strict", "standard", "relaxed"],
            SafetyLevel.STANDARD: ["standard", "relaxed"],
            SafetyLevel.RELAXED: ["relaxed"],
        }
        allowed_levels = level_priority.get(self._safety_level, ["standard"])
        return [rule for rule in self._rules if rule.enabled and rule.level in allowed_levels]

    def _on_load_rules(self, event: Event):
        """加载规则列表"""
        try:
            event_bus.emit(Event(
                type="feature.safety.rules.loaded",
                data={
                    "rules": [asdict(rule) for rule in self._rules],
                    "safety_level": self._safety_level.value,
                    "success": True
                }
            ))
        except Exception as e:
            logger.error(f"加载规则失败: {e}")
            event_bus.emit(Event(
                type="feature.safety.rules.load_failed",
                data={"error": str(e)}
            ))

    def _on_save_rules(self, event: Event):
        """保存规则列表"""
        try:
            rules_data = event.data.get("rules", [])
            self._rules = [FilterRule(**rule) for rule in rules_data]
            event_bus.emit(Event(
                type="feature.safety.rules.saved",
                data={"success": True, "count": len(self._rules)}
            ))
        except Exception as e:
            logger.error(f"保存规则失败: {e}")
            event_bus.emit(Event(
                type="feature.safety.rules.save_failed",
                data={"error": str(e)}
            ))

    def _on_add_rule(self, event: Event):
        """添加规则"""
        try:
            rule_data = event.data.get("rule", {})
            rule = FilterRule(**rule_data)
            self._rules.append(rule)
            event_bus.emit(Event(
                type="feature.safety.rule.added",
                data={"rule": asdict(rule), "success": True}
            ))
        except Exception as e:
            logger.error(f"添加规则失败: {e}")
            event_bus.emit(Event(
                type="feature.safety.rule.add_failed",
                data={"error": str(e)}
            ))

    def _on_update_rule(self, event: Event):
        """更新规则"""
        try:
            rule_id = event.data.get("id", "")
            rule_data = event.data.get("rule", {})
            for i, rule in enumerate(self._rules):
                if rule.id == rule_id:
                    self._rules[i] = FilterRule(**rule_data)
                    event_bus.emit(Event(
                        type="feature.safety.rule.updated",
                        data={"rule": rule_data, "success": True}
                    ))
                    return
            event_bus.emit(Event(
                type="feature.safety.rule.update_failed",
                data={"error": f"规则 {rule_id} 不存在"}
            ))
        except Exception as e:
            logger.error(f"更新规则失败: {e}")
            event_bus.emit(Event(
                type="feature.safety.rule.update_failed",
                data={"error": str(e)}
            ))

    def _on_delete_rule(self, event: Event):
        """删除规则"""
        try:
            rule_id = event.data.get("id", "")
            self._rules = [rule for rule in self._rules if rule.id != rule_id]
            event_bus.emit(Event(
                type="feature.safety.rule.deleted",
                data={"id": rule_id, "success": True}
            ))
        except Exception as e:
            logger.error(f"删除规则失败: {e}")
            event_bus.emit(Event(
                type="feature.safety.rule.delete_failed",
                data={"error": str(e)}
            ))

    def _on_change_level(self, event: Event):
        """更改安全级别"""
        try:
            level = event.data.get("level", "standard")
            self._safety_level = SafetyLevel(level)
            active_rules = self._get_active_rules()
            event_bus.emit(Event(
                type="feature.safety.level.changed",
                data={
                    "level": self._safety_level.value,
                    "active_rules_count": len(active_rules),
                    "success": True
                }
            ))
        except Exception as e:
            logger.error(f"更改安全级别失败: {e}")
            event_bus.emit(Event(
                type="feature.safety.level.change_failed",
                data={"error": str(e)}
            ))

    def _on_filter_content(self, event: Event):
        """过滤内容"""
        try:
            content = event.data.get("content", "")
            active_rules = self._get_active_rules()

            filtered_content = content
            matched_rules = []

            for rule in active_rules:
                try:
                    if re.search(rule.pattern, filtered_content):
                        filtered_content = re.sub(rule.pattern, rule.replacement, filtered_content)
                        matched_rules.append(asdict(rule))
                except re.error as e:
                    logger.warning(f"规则 {rule.id} 正则表达式错误: {e}")

            event_bus.emit(Event(
                type="feature.safety.filter.completed",
                data={
                    "original": content,
                    "filtered": filtered_content,
                    "matched_rules": matched_rules,
                    "is_filtered": len(matched_rules) > 0,
                }
            ))
        except Exception as e:
            logger.error(f"过滤内容失败: {e}")
            event_bus.emit(Event(
                type="feature.safety.filter.failed",
                data={"error": str(e)}
            ))

    def _on_preview_filter(self, event: Event):
        """预览过滤效果"""
        try:
            content = event.data.get("content", "")
            active_rules = self._get_active_rules()

            preview_lines = []
            for rule in active_rules:
                try:
                    matches = re.findall(rule.pattern, content)
                    if matches:
                        preview_lines.append(f"规则 '{rule.name}': 发现 {len(matches)} 处匹配")
                        for match in matches[:3]:  # 最多显示3个
                            preview_lines.append(f"  - {match}")
                except re.error as e:
                    preview_lines.append(f"规则 '{rule.name}': 正则错误 - {e}")

            if not preview_lines:
                preview_lines.append("没有发现敏感内容")

            event_bus.emit(Event(
                type="feature.safety.preview.completed",
                data={
                    "content": content,
                    "preview": "\n".join(preview_lines),
                    "rules_checked": len(active_rules),
                }
            ))
        except Exception as e:
            logger.error(f"预览过滤失败: {e}")
            event_bus.emit(Event(
                type="feature.safety.preview.failed",
                data={"error": str(e)}
            ))

    def _on_export_rules(self, event: Event):
        """导出规则"""
        try:
            file_path = event.data.get("file_path", "")
            export_data = {
                "rules": [asdict(rule) for rule in self._rules],
                "safety_level": self._safety_level.value,
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            event_bus.emit(Event(
                type="feature.safety.export.completed",
                data={"file_path": file_path, "success": True}
            ))
        except Exception as e:
            event_bus.emit(Event(
                type="feature.safety.export.failed",
                data={"error": str(e)}
            ))

    def _on_import_rules(self, event: Event):
        """导入规则"""
        try:
            file_path = event.data.get("file_path", "")
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            if "rules" in import_data:
                self._rules = [FilterRule(**rule) for rule in import_data["rules"]]
            if "safety_level" in import_data:
                self._safety_level = SafetyLevel(import_data["safety_level"])
            event_bus.emit(Event(
                type="feature.safety.import.completed",
                data={"file_path": file_path, "success": True}
            ))
        except Exception as e:
            event_bus.emit(Event(
                type="feature.safety.import.failed",
                data={"error": str(e)}
            ))


# 全局单例
safety_service = SafetyService()
