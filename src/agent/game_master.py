"""Game Master Agent - 核心推理循环"""
import json
import time
from src.services.llm_client import LLMClient
from src.prompts.gm_system import get_system_prompt
from src.tools.executor import execute_tool, get_all_schemas
from src.tools import world_tool
from src.services.database import init_db, get_db
from src.models import player_repo, location_repo, world_repo, metrics_repo
from src.services.context_manager import trim_history
from src.utils.logger import get_logger

logger = get_logger(__name__)

# DeepSeek工具调用的最大循环次数（防止无限循环）
MAX_TOOL_ROUNDS = 10


class GameMaster:
    """Game Master Agent

    核心循环:
    1. 接收玩家输入
    2. 组装上下文（System Prompt + 对话历史）
    3. 调用DeepSeek（带工具）
    4. 如果有工具调用 → 执行工具 → 结果反馈给LLM → 继续推理
    5. 如果没有工具调用 → 返回叙事文本
    """

    def __init__(self, world_id: int, player_id: int, llm_client: LLMClient | None = None, db_path: str | None = None):
        self.world_id = world_id
        self.player_id = player_id
        self.llm = llm_client or LLMClient()
        self.db_path = db_path
        self.tools = get_all_schemas()
        self.history: list[dict] = []

        # 设置工具的活跃世界和玩家
        world_tool.set_active(world_id, player_id)

        # 加载历史对话
        self._load_history()

    def _load_history(self):
        """从数据库加载历史对话"""
        with get_db(self.db_path) as conn:
            rows = conn.execute(
                "SELECT role, content FROM game_messages WHERE world_id = ? ORDER BY timestamp ASC LIMIT 50",
                (self.world_id,),
            ).fetchall()
        self.history = [{"role": r["role"], "content": r["content"]} for r in rows]
        if self.history:
            logger.info(f"加载了 {len(self.history)} 条历史消息")

    def _save_message(self, role: str, content: str):
        """保存消息到数据库"""
        with get_db(self.db_path) as conn:
            conn.execute(
                "INSERT INTO game_messages (world_id, role, content) VALUES (?, ?, ?)",
                (self.world_id, role, content),
            )

    def _build_context(self) -> list[dict]:
        """构建完整的消息上下文"""
        # 系统消息
        system_prompt = get_system_prompt(self._get_world_context())
        messages = [{"role": "system", "content": system_prompt}]
        # 对话历史（裁剪后）
        trimmed = trim_history(self.history)
        messages.extend(trimmed)
        return messages

    def _get_world_context(self) -> str:
        """获取当前世界状态的文本摘要"""
        try:
            return world_tool.query_world_state("overview", self.db_path)
        except Exception as e:
            logger.warning(f"获取世界上下文失败: {e}")
            return ""

    def process(self, user_input: str) -> str:
        """处理玩家输入，返回GM叙事回复

        这是核心方法。循环:
        用户输入 → LLM推理 → (有工具调用? → 执行 → 反馈) → 返回文本
        """
        # 1. 记录玩家输入
        self.history.append({"role": "user", "content": user_input})
        self._save_message("user", user_input)

        # 2. 推理循环
        tool_round = 0
        while tool_round < MAX_TOOL_ROUNDS:
            tool_round += 1
            messages = self._build_context()

            # 记录调用开始时间
            start_time = time.time()
            response = self.llm.chat_with_tools(messages, self.tools)
            latency_ms = int((time.time() - start_time) * 1000)
            
            choice = response.choices[0]
            message = choice.message
            
            # 记录 LLM 调用
            usage = response.usage
            tool_calls_count = len(message.tool_calls) if message.tool_calls else 0
            tool_names = []
            if message.tool_calls:
                tool_names = [tc.function.name for tc in message.tool_calls]
            
            try:
                metrics_repo.record_llm_call(
                    world_id=self.world_id,
                    call_type="chat_with_tools",
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    latency_ms=latency_ms,
                    tool_calls_count=tool_calls_count,
                    tool_names=tool_names,
                    error="",
                    db_path=self.db_path
                )
            except Exception as e:
                logger.warning(f"记录 LLM 调用失败: {e}")

            # 3. 检查是否有工具调用
            if message.tool_calls:
                logger.info(f"LLM请求调用 {len(message.tool_calls)} 个工具 (第{tool_round}轮)")

                # 首先添加assistant消息（包含tool_calls）到历史
                assistant_msg = {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                }
                # DeepSeek: 如果有reasoning_content，需要保留
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    assistant_msg["reasoning_content"] = message.reasoning_content
                self.history.append(assistant_msg)

                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = {}
                    try:
                        func_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        func_args = {}

                    # 执行工具
                    result = execute_tool(func_name, func_args, db_path=self.db_path)
                    logger.info(f"工具 {func_name} 返回: {result[:100]}...")

                    # 将工具结果加入历史
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
                # 继续推理（让LLM看到工具结果后继续）
                continue

            # 4. 没有工具调用，返回文本回复
            reply = message.content or ""
            self.history.append({"role": "assistant", "content": reply})
            self._save_message("assistant", reply)

            # 显示Token统计
            stats = self.llm.get_usage_stats()
            logger.info(f"回复完成 | Token统计: {stats}")

            return reply

        # 超过最大工具轮次
        logger.warning(f"工具调用超过{MAX_TOOL_ROUNDS}轮，强制返回")
        return "（系统提示：GM处理过于复杂，请简化你的请求。）"

    def process_stream(self, user_input: str):
        """流式处理玩家输入，逐字yield回复

        Yields:
            str: 每个文本片段
        """
        self.history.append({"role": "user", "content": user_input})
        self._save_message("user", user_input)

        tool_round = 0
        while tool_round < MAX_TOOL_ROUNDS:
            tool_round += 1
            messages = self._build_context()

            # 记录调用开始时间
            start_time = time.time()
            # 流式调用（带工具时不能用流式，需要完整响应来解析tool_calls）
            response = self.llm.chat_with_tools(messages, self.tools)
            latency_ms = int((time.time() - start_time) * 1000)
            
            choice = response.choices[0]
            message = choice.message
            
            # 记录 LLM 调用
            usage = response.usage
            tool_calls_count = len(message.tool_calls) if message.tool_calls else 0
            tool_names = []
            if message.tool_calls:
                tool_names = [tc.function.name for tc in message.tool_calls]
            
            try:
                metrics_repo.record_llm_call(
                    world_id=self.world_id,
                    call_type="chat_with_tools",
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    latency_ms=latency_ms,
                    tool_calls_count=tool_calls_count,
                    tool_names=tool_names,
                    error="",
                    db_path=self.db_path
                )
            except Exception as e:
                logger.warning(f"记录 LLM 调用失败: {e}")

            if message.tool_calls:
                # 首先添加assistant消息（包含tool_calls）到历史
                assistant_msg = {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                }
                # DeepSeek: 如果有reasoning_content，需要保留
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    assistant_msg["reasoning_content"] = message.reasoning_content
                self.history.append(assistant_msg)

                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = {}
                    try:
                        func_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        func_args = {}
                    result = execute_tool(func_name, func_args, db_path=self.db_path)
                    self.history.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
                continue

            # 没有工具调用时，用流式输出
            reply = message.content or ""
            self.history.append({"role": "assistant", "content": reply})
            self._save_message("assistant", reply)

            # 逐字yield
            for char in reply:
                yield char

            stats = self.llm.get_usage_stats()
            logger.info(f"流式回复完成 | Token统计: {stats}")
            return
