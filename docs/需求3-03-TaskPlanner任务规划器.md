# 03 — TaskPlanner 任务规划器

> 目标执行者：Trae AI
> 依赖：01（AITool 基类）
> 产出：`feature/services/ai_assistant/planner.py` + `context.py` + `models.py`

---

## 1. 数据模型

**文件**：`feature/services/ai_assistant/models.py`

```python
"""
AI 助手数据模型
定义计划、步骤、结果、Diff、消息、会话等核心数据结构
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    """步骤执行状态"""
    PENDING = "pending"          # 待确认
    CONFIRMED = "confirmed"      # 用户已确认，等待执行
    EXECUTING = "executing"      # 执行中
    COMPLETED = "completed"      # 执行完成
    SKIPPED = "skipped"          # 用户跳过
    FAILED = "failed"            # 执行失败
    REJECTED = "rejected"        # 用户拒绝变更


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class PlanStep:
    """执行计划的单个步骤"""
    step_id: int                          # 步骤编号（从 1 开始）
    tool_name: str                        # 要调用的工具名称
    description: str                      # 步骤描述（给用户看的）
    parameters: dict[str, Any]            # 工具参数
    status: StepStatus = StepStatus.PENDING
    result: dict[str, Any] | None = None  # 执行结果
    diff: str = ""                        # 文件变更的 diff
    error: str = ""                       # 错误信息

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "description": self.description,
            "parameters": self.parameters,
            "status": self.status.value,
            "result": self.result,
            "diff": self.diff,
            "error": self.error,
        }


@dataclass
class ExecutionPlan:
    """执行计划"""
    goal: str                             # 用户的目标描述
    steps: list[PlanStep] = field(default_factory=list)
    context_summary: str = ""             # AI 对项目现状的理解

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "context_summary": self.context_summary,
        }


@dataclass
class ChatMessage:
    """对话消息"""
    role: MessageRole
    content: str
    tool_calls: list[dict] | None = None  # LLM 的工具调用请求
    tool_results: list[dict] | None = None  # 工具执行结果
    timestamp: float = 0.0

    def to_llm_message(self) -> dict:
        """转换为 LLM API 格式"""
        msg = {"role": self.role.value, "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.tool_results:
            msg["tool_results"] = self.tool_results
        return msg


@dataclass
class SessionState:
    """会话状态"""
    session_id: str = ""
    messages: list[ChatMessage] = field(default_factory=list)
    current_plan: ExecutionPlan | None = None
    current_step_index: int = -1          # 当前正在执行的步骤索引
    is_planning: bool = False             # 是否正在规划中
    is_executing: bool = False            # 是否正在执行中
    total_steps_executed: int = 0         # 累计执行步骤数
    total_steps_succeeded: int = 0        # 累计成功步骤数
```

---

## 2. 项目上下文收集器

**文件**：`feature/services/ai_assistant/context.py`

```python
"""
项目上下文收集器
在 AI 规划前收集项目当前状态，作为 LLM 的背景信息
"""
import json
from pathlib import Path

from foundation.logger import get_logger

logger = get_logger(__name__)


class ProjectContextCollector:
    """收集项目上下文信息"""

    def __init__(self):
        self._context_cache: dict | None = None

    def collect(self) -> dict:
        """
        收集当前项目的完整上下文

        Returns:
            包含项目结构、提示词、技能、图定义、配置的字典
        """
        from feature.project import project_manager

        if not project_manager.is_open:
            return {"error": "没有打开的项目"}

        project_path = project_manager.project_path
        project_name = project_manager.current_project.name

        context = {
            "project_name": project_name,
            "project_path": str(project_path),
            "prompts": self._collect_prompts(project_path),
            "skills": self._collect_skills(project_path),
            "graph": self._collect_graph(project_path),
            "config": self._collect_config(),
        }

        self._context_cache = context
        logger.info(f"上下文收集完成: {project_name}")
        return context

    def _collect_prompts(self, project_path: Path) -> list[dict]:
        """收集提示词信息"""
        prompts = []
        prompts_dir = project_path / "prompts"
        if prompts_dir.exists():
            for f in sorted(prompts_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                prompts.append({
                    "name": f.stem,
                    "size": len(content),
                    "preview": content[:300].replace("\n", "\\n"),
                })
        return prompts

    def _collect_skills(self, project_path: Path) -> list[dict]:
        """收集技能信息"""
        skills = []
        skills_dir = project_path / "skills"
        if skills_dir.exists():
            for skill_dir in sorted(skills_dir.iterdir()):
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        content = skill_file.read_text(encoding="utf-8")
                        metadata = self._parse_yaml_frontmatter(content)
                        skills.append({
                            "name": skill_dir.name,
                            "description": metadata.get("description", ""),
                            "keywords": metadata.get("keywords", []),
                            "allowed_tools": metadata.get("allowed-tools", []),
                            "size": len(content),
                            "preview": content[:200].replace("\n", "\\n"),
                        })
        return skills

    def _collect_graph(self, project_path: Path) -> dict:
        """收集图定义信息"""
        graph_file = project_path / "graph.json"
        if not graph_file.exists():
            return {"exists": False}

        try:
            graph_data = json.loads(graph_file.read_text(encoding="utf-8"))
            return {
                "exists": True,
                "node_count": len(graph_data.get("nodes", [])),
                "edge_count": len(graph_data.get("edges", [])),
                "nodes": [
                    {
                        "id": n.get("id", ""),
                        "type": n.get("type", ""),
                        "label": n.get("data", {}).get("label", ""),
                    }
                    for n in graph_data.get("nodes", [])
                ],
                "edges": [
                    {
                        "source": e.get("source", ""),
                        "target": e.get("target", ""),
                        "label": e.get("label", ""),
                    }
                    for e in graph_data.get("edges", [])
                ],
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"图定义解析失败: {e}")
            return {"exists": True, "error": str(e)}

    def _collect_config(self) -> dict:
        """收集项目配置"""
        from feature.project import project_manager

        try:
            config = project_manager.load_project_config()
            return config or {}
        except Exception as e:
            logger.warning(f"配置加载失败: {e}")
            return {}

    def _parse_yaml_frontmatter(self, content: str) -> dict:
        """简易解析 YAML Front Matter（不依赖 PyYAML）"""
        metadata = {}
        if not content.startswith("---"):
            return metadata

        lines = content.split("\n")
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            line = lines[i]
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if value.startswith("[") and value.endswith("]"):
                    import ast
                    try:
                        metadata[key] = ast.literal_eval(value)
                    except (ValueError, SyntaxError):
                        metadata[key] = value
                else:
                    metadata[key] = value
            i += 1

        return metadata

    def invalidate_cache(self):
        """清除上下文缓存（项目切换时调用）"""
        self._context_cache = None

    def get_cached_context(self) -> dict | None:
        """获取缓存的上下文"""
        return self._context_cache


# 全局单例
context_collector = ProjectContextCollector()
```

---

## 3. TaskPlanner 任务规划器

**文件**：`feature/services/ai_assistant/planner.py`

```python
"""
AI 任务规划器
接收用户自然语言需求 → 收集项目上下文 → 调用 LLM 生成执行计划 → 解析为结构化 Plan
"""
import json
import re
from typing import Any

from foundation.logger import get_logger
from foundation.llm.model_router import model_router
from foundation.llm.base import LLMMessage
from .context import context_collector
from .models import ExecutionPlan, PlanStep, StepStatus
from .prompts import PLANNER_SYSTEM_PROMPT

logger = get_logger(__name__)


class PlanParseError(Exception):
    """计划解析失败"""
    pass


class TaskPlanner:
    """AI 任务规划器"""

    def __init__(self):
        self._context_collector = context_collector

    async def plan(self, user_request: str, session_messages: list[dict] | None = None) -> ExecutionPlan:
        """
        根据用户请求生成执行计划

        Args:
            user_request: 用户的自然语言需求
            session_messages: 当前会话的历史消息（用于多轮对话上下文）

        Returns:
            ExecutionPlan 结构化的执行计划

        Raises:
            PlanParseError: LLM 输出无法解析为有效计划
        """
        # 1. 收集项目上下文
        logger.info(f"开始规划: {user_request[:50]}...")
        context = self._context_collector.collect()
        if "error" in context:
            raise PlanParseError(context["error"])

        # 2. 构建 LLM 消息
        messages = self._build_messages(user_request, context, session_messages)

        # 3. 调用 LLM
        try:
            client, config = model_router.route(
                content=user_request,
                event_type="ai_assistant_plan",
            )
        except Exception as e:
            logger.error(f"模型路由失败: {e}")
            raise PlanParseError(f"无法获取 LLM 客户端: {e}")

        try:
            response = await client.chat_async(
                messages=messages,
                temperature=config.get("temperature", 0.3),
                max_tokens=config.get("max_tokens", 4096),
            )
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise PlanParseError(f"LLM 调用失败: {e}")

        # 4. 提取响应文本
        response_text = self._extract_response_text(response)
        logger.debug(f"LLM 规划响应:\n{response_text[:500]}")

        # 5. 解析为 ExecutionPlan
        plan = self._parse_plan(response_text, user_request, context)

        logger.info(f"计划生成完成: {len(plan.steps)} 个步骤")
        return plan

    def _build_messages(
        self,
        user_request: str,
        context: dict,
        session_messages: list[dict] | None,
    ) -> list[LLMMessage]:
        """构建 LLM 消息列表"""

        system_content = PLANNER_SYSTEM_PROMPT.format(
            project_context=json.dumps(context, ensure_ascii=False, indent=2),
        )

        messages = [LLMMessage(role="system", content=system_content)]

        if session_messages:
            for msg in session_messages[-10:]:
                if msg.get("role") in ("user", "assistant"):
                    messages.append(LLMMessage(
                        role=msg["role"],
                        content=msg.get("content", ""),
                    ))

        messages.append(LLMMessage(role="user", content=user_request))

        return messages

    def _extract_response_text(self, response: Any) -> str:
        """从 LLM 响应中提取文本"""
        if hasattr(response, "content"):
            return response.content
        elif isinstance(response, dict):
            return response.get("content", response.get("text", str(response)))
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    def _parse_plan(
        self,
        response_text: str,
        user_request: str,
        context: dict,
    ) -> ExecutionPlan:
        """解析 LLM 输出为 ExecutionPlan"""
        json_str = self._extract_json_block(response_text)

        if not json_str:
            raise PlanParseError(
                "LLM 输出中未找到有效的 JSON 计划。"
                f"\n原始输出:\n{response_text[:1000]}"
            )

        try:
            plan_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise PlanParseError(f"JSON 解析失败: {e}\n原始 JSON:\n{json_str[:500]}")

        thinking = plan_data.get("thinking", "")
        steps_data = plan_data.get("plan", [])

        if not steps_data:
            raise PlanParseError("计划中没有步骤")

        steps = []
        for i, step_data in enumerate(steps_data):
            step = PlanStep(
                step_id=step_data.get("step", i + 1),
                tool_name=step_data.get("tool", ""),
                description=step_data.get("description", ""),
                parameters=step_data.get("parameters", {}),
                status=StepStatus.PENDING,
            )
            steps.append(step)

        return ExecutionPlan(
            goal=user_request,
            steps=steps,
            context_summary=thinking,
        )

    def _extract_json_block(self, text: str) -> str | None:
        """从 LLM 输出中提取 JSON 块"""
        # 方式 1：```json 代码块
        json_block_match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
        if json_block_match:
            return json_block_match.group(1).strip()

        # 方式 2：``` 代码块（无语言标记）
        code_block_match = re.search(r"```\s*\n(.*?)\n```", text, re.DOTALL)
        if code_block_match:
            candidate = code_block_match.group(1).strip()
            if candidate.startswith("{"):
                return candidate

        # 方式 3：直接查找 JSON 对象
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        return None

    async def refine_plan(
        self,
        plan: ExecutionPlan,
        user_feedback: str,
        session_messages: list[dict] | None = None,
    ) -> ExecutionPlan:
        """根据用户反馈修改计划"""
        context = self._context_collector.get_cached_context()
        if not context:
            context = self._context_collector.collect()

        current_plan_json = json.dumps(
            plan.to_dict(),
            ensure_ascii=False,
            indent=2,
        )

        refine_request = (
            f"当前计划：\n```json\n{current_plan_json}\n```\n\n"
            f"用户反馈：{user_feedback}\n\n"
            f"请根据用户反馈修改计划，输出完整的修改后计划（JSON 格式）。"
        )

        messages = self._build_messages(refine_request, context, session_messages)

        try:
            client, config = model_router.route(
                content=refine_request,
                event_type="ai_assistant_plan",
            )
            response = await client.chat_async(
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
            )
            response_text = self._extract_response_text(response)
            new_plan = self._parse_plan(response_text, plan.goal, context)
            return new_plan
        except Exception as e:
            logger.error(f"计划修改失败: {e}")
            raise PlanParseError(f"计划修改失败: {e}")


# 全局单例
task_planner = TaskPlanner()
```

---

## 4. System Prompt 模板（占位，11 号文档完善）

**文件**：`feature/services/ai_assistant/prompts.py`

```python
"""
AI 助手 System Prompt 模板
详细版本见 需求3-11-系统提示词设计.md
"""

PLANNER_SYSTEM_PROMPT = """你是一个 TRPG Agent 配置助手。你的任务是帮助用户管理 TRPG Agent 的配置文件。

## 当前项目状态

{project_context}

## 可用工具

1. **read_project** - 读取项目信息（无参数）
2. **create_prompt** - 创建提示词（name, content, category?）
3. **edit_prompt** - 修改提示词（name, content）
4. **list_prompts** - 列出所有提示词（无参数）
5. **delete_prompt** - 删除提示词（name）
6. **create_skill** - 创建技能（name, description, keywords, allowed_tools, content, triggers?）
7. **edit_skill** - 修改技能（name, content）
8. **list_skills** - 列出所有技能（无参数）
9. **delete_skill** - 删除技能（name）
10. **read_graph** - 读取图定义（无参数）
11. **update_graph** - 修改图定义（graph_data）
12. **read_config** - 读取配置（无参数）
13. **update_config** - 修改配置（updates）
14. **test_prompt** - 测试提示词效果（prompt_name, test_message, max_tokens?）

## 输出格式

你必须输出一个 JSON 对象，格式如下：

```json
{{
  "thinking": "对项目现状的分析和你的规划思路...",
  "plan": [
    {{
      "step": 1,
      "tool": "工具名称",
      "description": "步骤描述（中文，给用户看）",
      "parameters": {{
        "参数名": "参数值"
      }}
    }}
  ]
}}
```

## 规则

1. 第一步通常是 read_project，了解项目现状
2. 每个步骤只调用一个工具
3. parameters 中的 content 字段必须是完整的文件内容
4. 提示词的 category 可选：system, scene, npc, item, quest, rule, custom
5. 技能的 keywords 和 allowed_tools 用逗号分隔的字符串
6. graph_data 是完整的 JSON 字符串
7. 如果用户的需求只需要一步操作，也要输出为 plan 数组格式
8. thinking 字段要体现你对项目现状的理解和规划逻辑
"""


# 对话模式的 System Prompt（用于非规划场景的闲聊/问答）
CHAT_SYSTEM_PROMPT = """你是一个 TRPG Agent 配置助手。你可以帮助用户：

1. 创建和修改提示词（场景、NPC、物品、任务等）
2. 创建和修改技能（陷阱检测、开锁、 persuasion 等）
3. 管理图定义和项目配置
4. 测试提示词效果
5. 解答 TRPG 相关的设计问题

当用户提出需要修改配置的需求时，你应该生成一个执行计划。
当用户只是提问时，直接回答即可。
"""
```

---

## 5. 验证

创建完成后，验证以下内容：

```python
# 1. 验证数据模型
from feature.services.ai_assistant.models import (
    PlanStep, ExecutionPlan, ChatMessage, SessionState, StepStatus
)

step = PlanStep(
    step_id=1,
    tool_name="create_prompt",
    description="创建测试提示词",
    parameters={"name": "test", "content": "hello"},
)
assert step.status == StepStatus.PENDING
assert step.to_dict()["tool_name"] == "create_prompt"

plan = ExecutionPlan(goal="测试", steps=[step])
assert len(plan.steps) == 1

# 2. 验证上下文收集器（需要先打开项目）
# from feature.services.ai_assistant.context import context_collector
# context = context_collector.collect()
# assert "prompts" in context
# assert "skills" in context

# 3. 验证规划器（需要 LLM 连接）
# from feature.services.ai_assistant.planner import task_planner
# plan = await task_planner.plan("创建一个暗黑风格的地下城探索场景")
# assert len(plan.steps) > 0
```

---

## 6. 与现有代码的关系

| 现有组件 | 本文档如何使用 |
|----------|---------------|
| `foundation/llm/model_router.py` | `model_router.route()` 获取 LLM 客户端 |
| `foundation/llm/base.py` | `LLMMessage` 构建消息 |
| `feature/project/manager.py` | `project_manager.is_open` / `project_path` / `load_*` / `save_*` |
| `foundation/logger.py` | `get_logger(__name__)` |
| `foundation/event_bus.py` | 04/05 文档中通过 EventBus 发送规划事件 |
