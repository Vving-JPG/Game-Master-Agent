"""上下文管理器 - 对话历史管理"""
import json
from src.services.llm_client import LLMClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_CONTEXT_TOKENS = 80000  # DeepSeek 上下文窗口约 128K，留余量
SUMMARY_TRIGGER_TOKENS = 60000  # 超过此值触发压缩


def estimate_tokens(text: str) -> int:
    """粗略估算 Token 数（中文约1.5字/token，英文约4字符/token）"""
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4)


def compress_history(history: list[dict], llm: LLMClient | None = None) -> list[dict]:
    """压缩对话历史

    策略:
    1. 保留 System Prompt（第一条）
    2. 保留最近 10 轮完整对话
    3. 将更早的对话用 LLM 做摘要
    4. 摘要作为一条 assistant 消息插入

    Args:
        history: 对话历史列表
        llm: LLM 客户端

    Returns:
        压缩后的对话历史
    """
    if len(history) <= 20:
        return history

    # 分离 system、要压缩的、保留的
    system_msgs = [m for m in history if m.get("role") == "system"]
    non_system = [m for m in history if m.get("role") != "system"]

    # 保留最近 10 轮（20条消息）
    keep_count = 20
    to_compress = non_system[:-keep_count]
    to_keep = non_system[-keep_count:]

    if not to_compress:
        return history

    # 构建摘要请求
    compress_content = "\n".join(
        f"[{m.get('role', '?')}]: {m.get('content', '')[:200]}"
        for m in to_compress
    )

    summary_prompt = f"""请将以下游戏对话历史压缩为简洁的摘要，保留关键信息：
- 玩家去过的地点
- 遇到的NPC和重要互动
- 获得的物品
- 做出的重要选择
- 当前任务进度

对话历史:
{compress_content}

请用2-4句话概括，格式如：
[世界摘要] 玩家从XX村出发，在YY森林遇到了ZZ。获得了AA物品，接受了BB任务。当前正在CC地点。"""

    try:
        llm = llm or LLMClient()
        summary = llm.chat([
            {"role": "system", "content": "你是一个游戏历史摘要生成器。只输出摘要，不要其他内容。"},
            {"role": "user", "content": summary_prompt},
        ])

        # 构建压缩后的历史
        compressed = system_msgs.copy()
        compressed.append({"role": "assistant", "content": f"[历史摘要] {summary}"})
        compressed.extend(to_keep)

        old_tokens = sum(estimate_tokens(m.get("content", "")) for m in history)
        new_tokens = sum(estimate_tokens(m.get("content", "")) for m in compressed)
        logger.info(f"历史压缩: {len(history)}条 → {len(compressed)}条, 约{old_tokens} → {new_tokens} tokens")

        return compressed
    except Exception as e:
        logger.error(f"压缩失败，使用截断: {e}")
        # 降级：简单截断
        return system_msgs + to_keep


def trim_history(history: list[dict], max_tokens: int = MAX_CONTEXT_TOKENS) -> list[dict]:
    """裁剪历史，确保不超过 Token 上限"""
    total = sum(estimate_tokens(m.get("content", "")) for m in history)
    if total <= max_tokens:
        return history

    # 从最早的非 system 消息开始删除
    result = []
    system_msgs = [m for m in history if m.get("role") == "system"]
    non_system = [m for m in history if m.get("role") != "system"]

    for msg in reversed(non_system):
        result.insert(0, msg)
        if sum(estimate_tokens(m.get("content", "")) for m in system_msgs + result) > max_tokens:
            result.pop(0)
            break

    return system_msgs + result
