"""多模型路由器 — 配置驱动的智能模型选择

路由策略:
1. 显式指定 — 调用方直接指定 provider + model
2. 规则匹配 — 根据内容特征（关键词、长度、事件类型）评分选择
3. 默认回退 — 使用 settings.default_provider

规则配置示例:
    routing_rules:
      - name: critical_narrative
        provider: deepseek
        model: deepseek-reasoner
        conditions:
          keywords: [战斗, boss, 决战, 死亡, 结局, 命运, 秘密, 真相]
          min_turn_length: 20
        score: 10

      - name: creative_writing
        provider: openai
        model: gpt-4o
        conditions:
          keywords: [描写, 描述, 氛围, 场景, 情感]
        score: 5
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from foundation.config import Settings, settings
from foundation.event_bus import event_bus, Event
from foundation.llm.base import BaseLLMClient, LLMMessage
from foundation.llm.openai_client import OpenAICompatibleClient
from foundation.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RoutingRule:
    """路由规则"""
    name: str
    provider: str
    model: str
    keywords: list[str] = field(default_factory=list)
    event_types: list[str] = field(default_factory=list)
    min_turn_length: int = 0
    score: int = 0
    temperature: float | None = None
    max_tokens: int | None = None


# 默认路由规则
DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "name": "critical_narrative",
        "provider": "deepseek",
        "model": "deepseek-reasoner",
        "keywords": ["战斗", "boss", "决战", "死亡", "结局", "选择", "命运",
                      "重要", "秘密", "真相", "最终", "关键", "转折", "危机"],
        "min_turn_length": 20,
        "score": 10,
    },
    {
        "name": "npc_deep_dialogue",
        "provider": "deepseek",
        "model": "deepseek-reasoner",
        "keywords": ["关系", "信任", "背叛", "过去", "回忆", "秘密", "身世"],
        "score": 8,
    },
    {
        "name": "standard_narrative",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "score": 0,  # 默认规则
    },
]


class ModelRouter:
    """多模型路由器

    用法:
        router = ModelRouter(settings)

        # 自动路由
        client, config = router.route(content="战斗开始！")

        # 显式指定
        client, config = router.route(provider="openai", model="gpt-4o")
    """

    def __init__(self, settings_obj: Settings | None = None):
        self._settings = settings_obj or settings
        self._clients: dict[str, BaseLLMClient] = {}
        self._rules: list[RoutingRule] = []
        self._load_rules(DEFAULT_RULES)
        self._init_clients()

    def _load_rules(self, rules: list[dict[str, Any]]) -> None:
        """加载路由规则"""
        self._rules = [RoutingRule(**rule) for rule in rules]
        logger.info(f"已加载 {len(self._rules)} 条路由规则")

    def _init_clients(self) -> None:
        """初始化所有已配置的 LLM 客户端"""
        providers = self._settings.get_available_providers()
        for provider in providers:
            config = self._settings.get_provider_config(provider)
            if config.api_key:
                self._clients[provider] = OpenAICompatibleClient(
                    provider_name=provider,
                    api_key=config.api_key,
                    base_url=config.base_url,
                    model=config.model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                )
                logger.info(f"LLM 客户端已初始化: {provider}/{config.model}")

    def route(
        self,
        content: str = "",
        event_type: str = "",
        turn_length: int = 0,
        provider: str | None = None,
        model: str | None = None,
    ) -> tuple[BaseLLMClient, dict[str, Any]]:
        """路由到合适的 LLM 客户端

        Args:
            content: 输入内容（用于规则匹配）
            event_type: 事件类型
            turn_length: 当前对话轮数
            provider: 显式指定供应商（跳过路由）
            model: 显式指定模型（跳过路由）

        Returns:
            (client, config) 元组
            config 包含: provider, model, temperature, max_tokens
        """
        # 显式指定
        if provider:
            client = self._get_client(provider)
            config = self._settings.get_provider_config(provider)
            return client, {
                "provider": provider,
                "model": model or config.model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            }

        # 规则匹配
        best_rule = self._match_rules(content, event_type, turn_length)

        if best_rule:
            client = self._get_client(best_rule.provider)
            provider_config = self._settings.get_provider_config(best_rule.provider)
            logger.debug(
                f"路由匹配: {best_rule.name} -> "
                f"{best_rule.provider}/{best_rule.model} (score={best_rule.score})"
            )
            return client, {
                "provider": best_rule.provider,
                "model": best_rule.model,
                "temperature": best_rule.temperature or provider_config.temperature,
                "max_tokens": best_rule.max_tokens or provider_config.max_tokens,
            }

        # 默认回退
        default_provider = self._settings.default_provider
        client = self._get_client(default_provider)
        config = self._settings.get_provider_config(default_provider)
        return client, {
            "provider": default_provider,
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

    def _match_rules(
        self,
        content: str,
        event_type: str,
        turn_length: int,
    ) -> RoutingRule | None:
        """匹配最佳路由规则"""
        best: RoutingRule | None = None
        best_score = -1

        content_lower = content.lower()

        for rule in self._rules:
            score = 0

            # 关键词匹配
            for keyword in rule.keywords:
                if keyword.lower() in content_lower:
                    score += 1

            # 事件类型匹配
            if event_type and event_type in rule.event_types:
                score += 5

            # 对话长度匹配
            if rule.min_turn_length and turn_length >= rule.min_turn_length:
                score += 3

            # 加上基础分
            score += rule.score

            if score > best_score:
                best_score = score
                best = rule

        return best

    def _get_client(self, provider: str) -> BaseLLMClient:
        """获取或创建客户端"""
        if provider not in self._clients:
            # 尝试初始化
            try:
                config = self._settings.get_provider_config(provider)
                if config.api_key:
                    self._clients[provider] = OpenAICompatibleClient(
                        provider_name=provider,
                        api_key=config.api_key,
                        base_url=config.base_url,
                        model=config.model,
                        max_tokens=config.max_tokens,
                        temperature=config.temperature,
                    )
            except Exception as e:
                logger.error(f"无法初始化 LLM 客户端 ({provider}): {e}")

        if provider not in self._clients:
            raise ValueError(
                f"LLM 客户端未初始化: {provider}。"
                f"请在 .env 中配置 {provider.upper()}_API_KEY"
            )

        return self._clients[provider]

    def get_all_clients(self) -> dict[str, BaseLLMClient]:
        """获取所有已初始化的客户端"""
        return dict(self._clients)

    def add_rule(self, rule: dict[str, Any]) -> None:
        """动态添加路由规则"""
        self._rules.append(RoutingRule(**rule))
        logger.info(f"新增路由规则: {rule.get('name')}")

    def reload(self) -> None:
        """重新加载配置和客户端"""
        self._clients.clear()
        self._rules.clear()
        self._load_rules(DEFAULT_RULES)
        self._init_clients()
        logger.info("模型路由器已重新加载")


# 全局单例
model_router = ModelRouter()
