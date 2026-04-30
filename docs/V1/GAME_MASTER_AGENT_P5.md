# Game Master Agent - P5' 螺旋优化与发布

> 本文件是 Trae AI 助手执行 P5' 阶段的指引。P0-P4' 必须已全部完成。
> **本阶段是持续迭代优化，提升质量、性能、稳定性，并完成发布准备。**

## 前置条件

执行本阶段前，确认以下成果已就绪：
- [ ] P0-P4' 全部完成（146+个测试通过）
- [ ] `uv run pytest tests/ -v` 全部通过
- [ ] `uv run uvicorn src.api.app:app --reload --port 8000` 能正常启动
- [ ] CLI `uv run python src/cli.py` 能正常对话
- [ ] `src/prompts/gm_system.py` 存在（当前 System Prompt）
- [ ] `src/services/context_manager.py` 存在（`compress_history` 接口已预留）
- [ ] `docs/prompt-tuning-log.md` 存在（调优日志）
- [ ] 管理端 `/admin` 可访问（Prompt 管理面板）

## 行为准则

1. **一步一步执行**：严格按步骤顺序，每步验证通过后再继续
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始P5'"后，主动执行每一步
4. **遇到错误先尝试解决**：3次失败后再询问用户
5. **每步完成后汇报**：简要汇报结果和下一步
6. **代码规范**：UTF-8、中文注释、PEP 8、每个模块必须有 pytest 测试
7. **不要跳步**
8. **PowerShell 注意**：Windows PowerShell 不支持 `&&`，用 `;` 分隔命令

## 历史经验教训（必须遵守）

- **DeepSeek reasoning_content**：涉及 LLM 调用时注意传递
- **tool_call_id**：tool 消息必须包含此字段
- **全局状态隔离**：测试中不要污染 `TOOL_REGISTRY`
- **模块引用**：用 `from module import module; module.variable` 避免值拷贝
- **seed_world 返回值**：`seed_world()` 返回 `{"world_id": ..., "player_id": ...}`
- **llm.chat() 返回字符串**：P0 的 LLMClient.chat() 返回 `str`，不是 response 对象
- **get_npc 返回 dict**：已经是解析后的字典，不需要再 json.loads

---

## 步骤 5.1 - 基于调优日志迭代 Prompt

**目的**: 系统性提升 GM 叙事质量

**执行**:
1. 读取当前 System Prompt：
   ```bash
   # 查看当前 Prompt
   type src\prompts\gm_system.py
   # 查看调优日志
   type docs\prompt-tuning-log.md
   ```
2. 分析当前 Prompt 的常见问题，针对性修改。以下是需要重点检查和优化的方向：

   **A. 防止 GM 替玩家做决定**：
   ```
   在 System Prompt 中添加/强化：
   - 你是游戏主持人（Game Master），不是玩家
   - 绝对不要替玩家做决定、替玩家行动、替玩家说话
   - 每次回复末尾用提问或描述引导玩家做出选择
   - 玩家说"我做什么"时，描述结果并等待下一步指令
   ```

   **B. 提升叙事长度和丰富度**：
   ```
   在 System Prompt 中添加：
   - 每次回复至少3-5句话，包含环境描写、感官细节、NPC反应
   - 使用生动的形容词和比喻
   - 描述场景时要调动多种感官（视觉、听觉、嗅觉、触觉）
   - 战斗场景要有动作感和紧张感
   ```

   **C. 保持风格一致性**：
   ```
   在 System Prompt 中添加：
   - 始终用第二人称"你"称呼玩家
   - 保持奇幻RPG的叙事风格
   - NPC对话要有个性差异（根据性格模板）
   - 不要突然跳出角色或使用现代网络用语
   ```

   **D. 强化记忆和连贯性**：
   ```
   在 System Prompt 中添加：
   - 始终记住玩家之前做过的事、见过的人、去过的地点
   - 如果玩家提到之前的事件，正确引用
   - 不要引入与之前叙事矛盾的内容
   ```

3. 修改 `src/prompts/gm_system.py`，将优化后的 Prompt 写入。**保留原有结构，只做增量修改**。
4. 记录每次修改到 `docs/prompt-tuning-log.md`：
   ```markdown
   ## P5' 优化记录

   ### 优化1 - 防止替玩家做决定
   - **日期**: 2026-04-28
   - **问题**: GM 经常替玩家做决定
   - **修改**: 添加"绝不替玩家做决定"的约束
   - **效果**: 待验证
   ```

**验收**: 修改后的 Prompt 在管理端 `/admin` 中可见，CLI 对话测试叙事质量有提升

---

## 步骤 5.2 - 添加 Few-Shot 示例

**目的**: 给 GM 提供参考案例，稳定回复风格

**执行**:
1. 在 `src/prompts/gm_system.py` 的 System Prompt 末尾添加示例区块：
   ```python
   FEW_SHOT_EXAMPLES = """

   ## 回复示例

   ### 场景描述示例
   玩家: "环顾四周"
   GM: 你站在村庄广场的中央，脚下是磨损的石板路。一座古老的石井立在广场中央，井沿上刻满了岁月的痕迹。东边是铁匠铺，传来叮叮当当的锤击声和金属的灼热气息。西边的小酒馆门口，一个醉醺醺的矮人正靠在门框上打盹。北边的告示板上贴满了各种悬赏令，其中一张画着一只巨大的狼影。微风吹过，带来远处森林的松脂香和一丝不安的气息。

   ### NPC对话示例
   玩家: "你好，村长，我听说附近有哥布林出没？"
   GM: 村长抬起布满皱纹的脸，浑浊的眼睛中闪过一丝忧虑。他缓缓放下手中的烟斗，叹了口气。"年轻人，你说得没错。那些绿皮畜生最近越来越猖狂了，上周末它们甚至袭击了北边的农场。"他用拐杖敲了敲地面，"如果你愿意帮忙，我可以给你指个方向。不过……你确定自己准备好了吗？"

   ### 战斗叙事示例
   玩家: "我挥剑攻击哥布林"
   GM: 你握紧铁剑，向最近的哥布林冲去！剑刃划破空气，带着凛冽的风声——哥布林本能地侧身闪避，但你的剑尖还是划过了它的肩膀，鲜血飞溅。哥布林发出尖锐的嚎叫，愤怒地举起生锈的短刀向你反击！

   ### 任务发布示例
   玩家: "我接受这个任务"
   GM: 村长欣慰地点了点头，从怀里掏出一封泛黄的信件递给你。"这是我的老朋友——森林守卫林达写来的。她提到在迷雾森林深处发现了一座被遗忘的精灵遗迹，但最近那里出现了不明的黑暗力量。把这封信交给她，她会告诉你更多。"他停顿了一下，"路上小心，年轻人。迷雾森林……不是什么善地。"
   """
   ```
2. 在 `get_system_prompt()` 函数中将 `FEW_SHOT_EXAMPLES` 拼接到 Prompt 末尾。
3. 用 CLI 测试 4 个场景（环顾四周、NPC 对话、战斗、接受任务），对比优化前后回复质量。
4. 记录到调优日志。

**验收**: 4 个场景的回复质量明显提升，风格一致

---

## 步骤 5.3 - 实现 LLM 摘要压缩

**目的**: 解决长对话 Token 超限问题

**执行**:
1. 修改 `src/services/context_manager.py`，实现 `compress_history`：
   ```python
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
   ```
2. 修改 `src/agent/game_master.py`，在 `process()` 中使用压缩：
   ```python
   # 在 _build_context() 方法中添加:
   from src.services.context_manager import estimate_tokens, compress_history, SUMMARY_TRIGGER_TOKENS

   def _build_context(self):
       # 先检查是否需要压缩
       total_tokens = sum(estimate_tokens(m.get("content", "")) for m in self.history)
       if total_tokens > SUMMARY_TRIGGER_TOKENS:
           self.history = compress_history(self.history, self.llm)

       return [SYSTEM_PROMPT] + self.history
   ```
3. 创建 `tests/test_context_manager.py`：
   ```python
   """上下文管理测试"""
   from src.services.context_manager import estimate_tokens, compress_history, trim_history


   def test_estimate_tokens():
       """Token 估算"""
       t1 = estimate_tokens("你好世界")  # 4个中文字
       assert t1 > 0
       t2 = estimate_tokens("Hello World")  # 11个英文字符
       assert t2 > 0

   def test_compress_short_history():
       """短历史不压缩"""
       history = [
           {"role": "user", "content": "你好"},
           {"role": "assistant", "content": "你好！欢迎来到冒险世界。"},
       ]
       result = compress_history(history)
       assert len(result) == len(history)

   def test_compress_long_history():
       """长历史被压缩"""
       history = [{"role": "system", "content": "你是GM"}]
       for i in range(30):
           history.append({"role": "user", "content": f"这是第{i}轮玩家输入，内容比较长，包含很多信息。"})
           history.append({"role": "assistant", "content": f"这是第{i}轮GM回复，描述了丰富的场景和NPC互动。"})

       # 不传 llm，使用截断降级
       result = compress_history(history)
       assert len(result) < len(history)
       # system 消息保留
       assert result[0]["role"] == "system"

   def test_trim_history():
       """裁剪历史"""
       history = [{"role": "system", "content": "系统提示"}]
       for i in range(100):
           history.append({"role": "user", "content": "x" * 500})
           history.append({"role": "assistant", "content": "y" * 500})

       result = trim_history(history, max_tokens=1000)
       assert result[0]["role"] == "system"
       assert len(result) < len(history)
   ```

**验收**: `uv run pytest tests/test_context_manager.py -v` 全绿

---

## 步骤 5.4 - 实现关键信息提取

**目的**: 自动提取和保留重要信息，防止丢失

**执行**:
1. 创建 `src/services/info_extractor.py`：
   ```python
   """关键信息提取 - 自动从对话中提取重要信息"""
   from src.services.llm_client import LLMClient
   from src.models import world_repo
   from src.utils.logger import get_logger

   logger = get_logger(__name__)

   EXTRACTION_PROMPT = """从以下游戏对话中提取关键信息，以JSON格式返回。

   提取规则:
   - new_locations: 新发现的地点
   - new_npcs: 新遇到的NPC
   - items_obtained: 获得的物品
   - key_choices: 玩家做出的重要选择
   - current_objective: 当前目标

   如果某项没有新信息，返回空列表。

   对话:
   {conversation}

   只返回JSON，不要其他内容。格式:
   {{"new_locations":[],"new_npcs":[],"items_obtained":[],"key_choices":[],"current_objective":""}}"""


   def extract_key_info(history: list[dict], llm: LLMClient | None = None) -> dict:
       """从最近对话中提取关键信息

       Args:
           history: 对话历史
           llm: LLM 客户端

       Returns:
           dict: {"new_locations": [...], "new_npcs": [...], ...}
       """
       import json

       # 只取最近 10 轮
       recent = history[-20:] if len(history) > 20 else history
       conversation = "\n".join(
           f"[{m.get('role', '?')}]: {m.get('content', '')}"
           for m in recent
       )

       try:
           llm = llm or LLMClient()
           response = llm.chat([
               {"role": "system", "content": "你是一个信息提取器。只输出JSON。"},
               {"role": "user", "content": EXTRACTION_PROMPT.format(conversation=conversation)},
           ])

           # 尝试解析 JSON
           response = response.strip()
           if response.startswith("```"):
               response = response.split("\n", 1)[1].rsplit("```", 1)[0]
           return json.loads(response)
       except (json.JSONDecodeError, Exception) as e:
           logger.warning(f"信息提取失败: {e}")
           return {"new_locations": [], "new_npcs": [], "items_obtained": [], "key_choices": [], "current_objective": ""}


   def build_world_summary(world_id: int, history: list[dict], db_path: str | None = None) -> str:
       """构建世界状态摘要（注入上下文用）"""
       info = extract_key_info(history)
       parts = []

       if info.get("new_locations"):
           parts.append(f"已探索地点: {', '.join(info['new_locations'])}")
       if info.get("new_npcs"):
           parts.append(f"已遇到NPC: {', '.join(info['new_npcs'])}")
       if info.get("items_obtained"):
           parts.append(f"已获得物品: {', '.join(info['items_obtained'])}")
       if info.get("current_objective"):
           parts.append(f"当前目标: {info['current_objective']}")

       return "\n".join(parts) if parts else ""
   ```
2. 在 `src/agent/game_master.py` 的 `_build_context()` 中注入摘要：
   ```python
   # 每 5 轮提取一次关键信息
   user_msg_count = sum(1 for m in self.history if m.get("role") == "user")
   if user_msg_count > 0 and user_msg_count % 5 == 0:
       from src.services.info_extractor import build_world_summary
       summary = build_world_summary(self.world_id, self.history, self.db_path)
       if summary:
           # 注入到 system prompt 后面
           self.history.insert(0, {"role": "assistant", "content": f"[世界状态摘要] {summary}"})
   ```
3. 创建 `tests/test_info_extractor.py`：
   ```python
   """关键信息提取测试"""
   from src.services.info_extractor import extract_key_info, build_world_summary


   def test_extract_basic():
       """基本提取（不调LLM，测试降级）"""
       history = [
           {"role": "user", "content": "我去了暗影森林"},
           {"role": "assistant", "content": "你进入了暗影森林，树木遮天蔽日。"},
       ]
       result = extract_key_info(history)
       # 降级返回空结构
       assert "new_locations" in result
       assert "new_npcs" in result

   def test_build_summary_empty():
       """空历史不崩溃"""
       summary = build_world_summary(1, [])
       assert isinstance(summary, str)

   def test_build_summary_with_history():
       """有历史时构建摘要"""
       history = [
           {"role": "user", "content": "你好"},
           {"role": "assistant", "content": "欢迎来到新手村。"},
       ]
       summary = build_world_summary(1, history)
       assert isinstance(summary, str)
   ```

**验收**: `uv run pytest tests/test_info_extractor.py -v` 全绿

---

## 步骤 5.5 - 实现响应缓存

**目的**: 相同查询不重复调用 API

**执行**:
1. 创建 `src/services/cache.py`：
   ```python
   """响应缓存 - LRU 缓存减少重复 API 调用"""
   import hashlib
   import json
   import time
   from collections import OrderedDict
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   class LRUCache:
       """线程安全的 LRU 缓存"""

       def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
           self.max_size = max_size
           self.ttl = ttl_seconds
           self._cache: OrderedDict[str, tuple] = OrderedDict()

       def _make_key(self, prompt: str, **kwargs) -> str:
           """生成缓存键"""
           raw = prompt + json.dumps(kwargs, sort_keys=True)
           return hashlib.md5(raw.encode()).hexdigest()

       def get(self, prompt: str, **kwargs) -> str | None:
           """获取缓存"""
           key = self._make_key(prompt, **kwargs)
           if key in self._cache:
               value, timestamp = self._cache[key]
               if time.time() - timestamp < self.ttl:
                   self._cache.move_to_end(key)
                   logger.debug(f"缓存命中: {key[:8]}...")
                   return value
               else:
                   del self._cache[key]
           return None

       def set(self, prompt: str, response: str, **kwargs):
           """设置缓存"""
           key = self._make_key(prompt, **kwargs)
           self._cache[key] = (response, time.time())
           if len(self._cache) > self.max_size:
               self._cache.popitem(last=False)

       def invalidate(self, prompt_prefix: str = ""):
           """清除缓存（可选按前缀）"""
           if not prompt_prefix:
               self._cache.clear()
               return
           keys_to_remove = [k for k in self._cache if prompt_prefix in str(self._cache[k])]
           for k in keys_to_remove:
               del self._cache[k]

       @property
       def size(self) -> int:
           return len(self._cache)


   # 全局缓存实例
   llm_cache = LRUCache(max_size=200, ttl_seconds=600)
   ```
2. 在 `src/services/llm_client.py` 的 `chat()` 方法中添加缓存逻辑：
   ```python
   # 在 chat() 方法开头添加:
   from src.services.cache import llm_cache

   def chat(self, messages, **kwargs):
       # 生成缓存键
       cache_key = json.dumps([m.get("content", "") for m in messages if m.get("role") != "system"], ensure_ascii=False)
       cached = llm_cache.get(cache_key)
       if cached:
           return cached

       # ... 原有 API 调用逻辑 ...

       # 缓存结果（只缓存没有工具调用的纯文本回复）
       llm_cache.set(cache_key, result)
       return result
   ```
3. 创建 `tests/test_cache.py`：
   ```python
   """缓存系统测试"""
   from src.services.cache import LRUCache


   def test_basic_cache():
       """基本缓存读写"""
       cache = LRUCache(max_size=10)
       cache.set("hello", "world")
       assert cache.get("hello") == "world"
       assert cache.get("nonexistent") is None

   def test_lru_eviction():
       """LRU 淘汰"""
       cache = LRUCache(max_size=3)
       cache.set("a", "1")
       cache.set("b", "2")
       cache.set("c", "3")
       cache.set("d", "4")  # 应该淘汰 "a"
       assert cache.get("a") is None
       assert cache.get("d") == "4"

   def test_ttl():
       """TTL 过期"""
       cache = LRUCache(max_size=10, ttl_seconds=0)
       cache.set("x", "y")
       import time
       time.sleep(0.1)
       assert cache.get("x") is None

   def test_invalidate():
       """清除缓存"""
       cache = LRUCache()
       cache.set("a", "1")
       cache.set("b", "2")
       cache.invalidate()
       assert cache.size == 0

   def test_kwargs_key():
       """不同参数不同缓存"""
       cache = LRUCache()
       cache.set("prompt", "result1", model="gpt-3")
       cache.set("prompt", "result2", model="gpt-4")
       assert cache.get("prompt", model="gpt-3") == "result1"
       assert cache.get("prompt", model="gpt-4") == "result2"
   ```

**验收**: `uv run pytest tests/test_cache.py -v` 全绿

---

## 步骤 5.6 - 实现预生成

**目的**: 提前生成可能需要的内容，降低感知延迟

**执行**:
1. 创建 `src/services/pregenerator.py`：
   ```python
   """预生成服务 - 提前生成可能需要的内容"""
   import asyncio
   from src.services.llm_client import LLMClient
   from src.services.cache import llm_cache
   from src.utils.logger import get_logger

   logger = get_logger(__name__)

   # 预生成缓存键前缀
   PREGEN_PREFIX = "pregen:"


   async def pregenerate_location_description(location_name: str, location_type: str = "普通地点") -> str:
       """预生成地点描述"""
       cache_key = f"{PREGEN_PREFIX}location:{location_name}"
       cached = llm_cache.get(cache_key)
       if cached:
           return cached

       prompt = f"为一个奇幻RPG游戏生成'{location_name}'的详细场景描述（{location_type}）。2-3句话，包含视觉、听觉、嗅觉。只输出描述。"
       llm = LLMClient()
       description = llm.chat([
           {"role": "system", "content": "你是RPG场景描述生成器。"},
           {"role": "user", "content": prompt},
       ])
       llm_cache.set(cache_key, description)
       logger.info(f"预生成地点描述: {location_name}")
       return description


   async def pregenerate_npc_greeting(npc_name: str, personality: str = "友好") -> str:
       """预生成 NPC 打招呼"""
       cache_key = f"{PREGEN_PREFIX}npc_greet:{npc_name}"
       cached = llm_cache.get(cache_key)
       if cached:
           return cached

       prompt = f"生成NPC'{npc_name}'（性格：{personality}）的首次见面打招呼语。1-2句话。只输出对话。"
       llm = LLMClient()
       greeting = llm.chat([
           {"role": "system", "content": "你是RPG NPC 对话生成器。"},
           {"role": "user", "content": prompt},
       ])
       llm_cache.set(cache_key, greeting)
       logger.info(f"预生成NPC打招呼: {npc_name}")
       return greeting


   async def pregenerate_for_location(location_name: str, npc_names: list[str] | None = None):
       """为进入新地点预生成所有内容"""
       tasks = [pregenerate_location_description(location_name)]
       if npc_names:
           for name in npc_names:
               tasks.append(pregenerate_npc_greeting(name))
       await asyncio.gather(*tasks, return_exceptions=True)
       logger.info(f"预生成完成: {location_name} ({len(tasks)}项)")
   ```
2. 在 `src/agent/game_master.py` 中，当检测到玩家移动到新地点时触发预生成：
   ```python
   # 在 process() 方法中，工具调用返回后检查是否移动了地点
   # 如果 update_world_state 工具返回包含 "移动到" 或 "前往" 等关键词，
   # 异步触发预生成
   import asyncio
   asyncio.create_task(pregenerate_for_location(new_location, npc_names))
   ```
3. 创建 `tests/test_pregenerator.py`：
   ```python
   """预生成测试"""
   import asyncio
   from src.services.pregenerator import pregenerate_location_description, pregenerate_npc_greeting


   def test_pregenerate_location():
       """预生成地点描述（同步测试）"""
       result = asyncio.run(pregenerate_location_description("龙穴", "危险地点"))
       assert result is not None
       assert len(result) > 0
       print(f"\n预生成结果: {result[:100]}")

   def test_pregenerate_npc():
       """预生成NPC打招呼"""
       result = asyncio.run(pregenerate_npc_greeting("村长", "智慧"))
       assert result is not None
       assert len(result) > 0
       print(f"\nNPC打招呼: {result[:100]}")

   def test_cache_hit():
       """第二次调用命中缓存"""
       r1 = asyncio.run(pregenerate_location_description("测试村"))
       r2 = asyncio.run(pregenerate_location_description("测试村"))
       assert r1 == r2
   ```

**验收**: `uv run pytest tests/test_pregenerator.py -v -s` 全绿

---

## 步骤 5.7 - 优化 Token 使用

**目的**: 降低 API 成本

**执行**:
1. 审计当前 Token 使用情况：
   ```python
   # 创建 scripts/token_audit.py
   """Token 使用审计脚本"""
   from src.services.context_manager import estimate_tokens
   from src.prompts.gm_system import get_system_prompt

   prompt = get_system_prompt()
   prompt_tokens = estimate_tokens(prompt)
   print(f"System Prompt: {len(prompt)} 字符, 约 {prompt_tokens} tokens")

   # 统计工具 Schema 的 Token 数
   from src.tools.executor import get_all_schemas
   schemas = get_all_schemas()
   schema_text = str(schemas)
   schema_tokens = estimate_tokens(schema_text)
   print(f"工具 Schemas ({len(schemas)}个): {len(schema_text)} 字符, 约 {schema_tokens} tokens")

   print(f"\n固定开销: 约 {prompt_tokens + schema_tokens} tokens")
   print(f"剩余可用: 约 {128000 - prompt_tokens - schema_tokens} tokens")
   ```
2. 运行审计：
   ```bash
   uv run python scripts/token_audit.py
   ```
3. 根据审计结果优化：
   - **缩短工具描述**：每个工具的 `description` 控制在 1-2 句话
   - **合并相似工具**：考虑将 `get_player_info` 和 `update_player_info` 合并为一个 `player_action` 工具（参考 Mnehmos 的 action routing 模式）
   - **精简 System Prompt**：删除冗余指令，合并重复约束
4. 在管理端 `/admin` 监控面板中查看优化前后的 Token 对比。
5. 记录到调优日志。

**验收**: 审计脚本运行正常，Token 使用量有可量化的降低

---

## 步骤 5.8 - 实现多模型路由

**目的**: 不同任务用不同模型，平衡质量和速度

**执行**:
1. 创建 `src/services/model_router.py`：
   ```python
   """多模型路由 - 不同任务用不同模型"""
   from src.utils.logger import get_logger

   logger = get_logger(__name__)

   # 模型配置
   MODEL_CONFIG = {
       "deepseek-chat": {
           "name": "deepseek-chat",
           "description": "日常对话，速度快，成本低",
           "use_cases": ["日常对话", "简单描述", "NPC闲聊"],
       },
       "deepseek-reasoner": {
           "name": "deepseek-reasoner",
           "description": "关键剧情，质量高，速度慢",
           "use_cases": ["关键剧情", "重要选择", "Boss战", "结局"],
       },
   }

   # 关键词路由规则
   CRITICAL_KEYWORDS = [
       "战斗", "boss", "决战", "死亡", "结局", "选择", "命运",
       "重要", "秘密", "真相", "最终", "关键",
   ]


   def route_model(user_input: str, history: list[dict] | None = None) -> str:
       """根据输入内容路由到合适的模型

       Args:
           user_input: 玩家输入
           history: 对话历史（可选，用于判断上下文重要性）

       Returns:
           模型名称
       """
       # 检查是否包含关键词
       input_lower = user_input.lower()
       for keyword in CRITICAL_KEYWORDS:
           if keyword in input_lower:
               logger.info(f"路由到 deepseek-reasoner (关键词: {keyword})")
               return "deepseek-reasoner"

       # 检查对话轮次（长对话可能涉及重要剧情）
       if history:
           user_count = sum(1 for m in history if m.get("role") == "user")
           if user_count > 20:
               logger.info(f"路由到 deepseek-reasoner (长对话: {user_count}轮)")
               return "deepseek-reasoner"

       # 默认用快速模型
       return "deepseek-chat"


   def get_model_config(model_name: str) -> dict:
       """获取模型配置"""
       return MODEL_CONFIG.get(model_name, MODEL_CONFIG["deepseek-chat"])
   ```
2. 修改 `src/services/llm_client.py`，支持动态切换模型：
   ```python
   # 在 chat() 方法中添加 model 参数:
   def chat(self, messages, model: str | None = None, **kwargs):
       use_model = model or self.model  # self.model 从配置读取
       # ... 使用 use_model 调用 API
   ```
3. 修改 `src/agent/game_master.py`，在调用 LLM 前路由：
   ```python
   from src.services.model_router import route_model

   # 在 process() 的 while 循环中:
   model = route_model(user_input, self.history)
   response = self.llm.chat_with_tools(messages, self.tools, model=model)
   ```
4. 创建 `tests/test_model_router.py`：
   ```python
   """多模型路由测试"""
   from src.services.model_router import route_model, get_model_config


   def test_default_route():
       """默认路由到快速模型"""
       model = route_model("你好")
       assert model == "deepseek-chat"

   def test_combat_route():
       """战斗路由到推理模型"""
       model = route_model("我挥剑攻击Boss")
       assert model == "deepseek-reasoner"

   def test_plot_route():
       """关键剧情路由到推理模型"""
       model = route_model("我要揭开真相")
       assert model == "deepseek-reasoner"

   def test_long_conversation():
       """长对话路由到推理模型"""
       history = []
       for i in range(25):
           history.append({"role": "user", "content": f"第{i}轮"})
           history.append({"role": "assistant", "content": f"回复{i}"})
       model = route_model("继续", history)
       assert model == "deepseek-reasoner"

   def test_get_config():
       """获取模型配置"""
       config = get_model_config("deepseek-chat")
       assert config["name"] == "deepseek-chat"
   ```

**验收**: `uv run pytest tests/test_model_router.py -v` 全绿

---

## 步骤 5.9 - 添加日志和监控

**目的**: 生产环境可观测

**执行**:
1. 检查 `src/utils/logger.py` 是否已有完善的日志配置。如果没有，升级：
   ```python
   """日志配置"""
   import logging
   import sys
   from pathlib import Path


   def setup_logger(name: str = "game_master", level: str = "INFO") -> logging.Logger:
       logger = logging.getLogger(name)

       if logger.handlers:
           return logger

       logger.setLevel(getattr(logging, level.upper()))

       # 控制台输出
       console_handler = logging.StreamHandler(sys.stdout)
       console_handler.setLevel(logging.INFO)
       console_format = logging.Formatter(
           "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
           datefmt="%H:%M:%S",
       )
       console_handler.setFormatter(console_format)
       logger.addHandler(console_handler)

       # 文件输出
       log_dir = Path("logs")
       log_dir.mkdir(exist_ok=True)
       file_handler = logging.FileHandler(log_dir / "game_master.log", encoding="utf-8")
       file_handler.setLevel(logging.DEBUG)
       file_format = logging.Formatter(
           "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d: %(message)s",
           datefmt="%Y-%m-%d %H:%M:%S",
       )
       file_handler.setFormatter(file_format)
       logger.addHandler(file_handler)

       return logger
   ```
2. 确保 `src/models/metrics_repo.py`（P4' 已创建）在每次 LLM 调用时记录指标。
3. 创建 `scripts/health_check.py`：
   ```python
   """健康检查脚本"""
   import sys
   from src.models import metrics_repo
   from src.services.database import get_db


   def main():
       stats = metrics_repo.get_token_stats()
       print("=== Game Master Agent 健康检查 ===")
       print(f"总调用次数: {stats.get('total_calls', 0)}")
       print(f"总 Token: {stats.get('total_tokens', 0)}")
       print(f"平均延迟: {stats.get('avg_latency', 0):.0f}ms")
       print(f"错误次数: {stats.get('error_count', 0)}")
       print(f"状态: {'正常' if stats.get('error_count', 0) < 10 else '需要关注'}")
       return 0


   if __name__ == "__main__":
       sys.exit(main())
   ```
4. 运行验证：
   ```bash
   uv run python scripts/health_check.py
   ```

**验收**: 日志文件 `logs/game_master.log` 存在，健康检查脚本正常运行

---

## 步骤 5.10 - 实现优雅降级

**目的**: API 不可用时的备选方案

**执行**:
1. 修改 `src/services/llm_client.py`，添加降级逻辑：
   ```python
   # 在 chat() 方法中添加 try-except 和降级:

   MAX_RETRIES = 3
   RETRY_DELAYS = [1, 3, 5]  # 秒

   def chat(self, messages, model=None, **kwargs):
       last_error = None
       for attempt in range(MAX_RETRIES):
           try:
               # ... 原有 API 调用逻辑 ...
               return result
           except Exception as e:
               last_error = e
               logger.warning(f"API调用失败 (第{attempt+1}次): {e}")
               if attempt < len(RETRY_DELAYS):
                   import time
                   time.sleep(RETRY_DELAYS[attempt])

       # 所有重试失败，降级
       logger.error(f"API调用彻底失败，启用降级模式: {last_error}")
       return self._fallback_response(messages)


   def _fallback_response(self, messages) -> str:
       """降级回复"""
       fallback_responses = [
           "（GM正在沉思中……请稍后再试。）",
           "（一阵迷雾笼罩了你的视野，你暂时无法感知周围的环境。）",
           "（时间仿佛静止了，等待命运的齿轮重新转动……）",
       ]
       import random
       return random.choice(fallback_responses)
   ```
2. 修改工具执行器，添加工具调用失败的降级：
   ```python
   # 在 src/tools/executor.py 的 execute_tool() 中:
   def execute_tool(name, args, db_path=None):
       try:
           func = TOOL_REGISTRY[name]["func"]
           return func(**args, db_path=db_path)
       except Exception as e:
           logger.error(f"工具 {name} 执行失败: {e}")
           return f"[工具执行失败: {name} - {str(e)}。GM将用文字描述代替。]"
   ```
3. 创建 `tests/test_graceful_degradation.py`：
   ```python
   """优雅降级测试"""
   from unittest.mock import patch, MagicMock
   from src.services.llm_client import LLMClient


   def test_api_failure_fallback():
       """API 失败时降级回复"""
       client = LLMClient()
       with patch.object(client, '_call_api', side_effect=Exception("API不可用")):
           # 需要临时设置短重试
           result = client.chat([{"role": "user", "content": "测试"}])
           assert result is not None
           assert len(result) > 0
           print(f"\n降级回复: {result}")

   def test_tool_failure_message():
       """工具失败返回友好消息"""
       from src.tools.executor import execute_tool, TOOL_REGISTRY
       # 注册一个会失败的工具
       def failing_tool():
           raise RuntimeError("故意失败")
       TOOL_REGISTRY["_test_fail"] = {"func": failing_tool, "schema": {}}
       result = execute_tool("_test_fail", {})
       assert "失败" in result
       TOOL_REGISTRY.pop("_test_fail", None)
   ```

**验收**: `uv run pytest tests/test_graceful_degradation.py -v -s` 全绿

---

## 步骤 5.11 - 邀请朋友试玩

**目的**: 收集真实用户反馈

**说明**: 这一步需要人工操作，Trae 无法自动完成。请按以下步骤手动执行：

1. 启动服务：
   ```bash
   uv run uvicorn src.api.app:app --reload --port 8000
   ```
2. 邀请 3-5 个朋友试玩：
   - 发送链接：`http://localhost:8000/static/index.html`
   - 告诉他们这是一个 AI 驱动的文字 RPG 游戏
   - **不要给任何提示**，观察他们自然游玩
3. 记录观察结果到 `docs/user_feedback.md`：
   ```markdown
   # 用户反馈记录

   ## 测试者1: XXX
   - 游玩时长: XX分钟
   - 哪里卡住了: ...
   - 哪里觉得无聊: ...
   - 哪里觉得惊喜: ...
   - 哪里叙事不合理: ...
   - 总体评价: X/10

   ## 测试者2: XXX
   ...
   ```

**验收**: 收集到 3+ 份反馈记录

---

## 步骤 5.12 - 根据反馈迭代

**目的**: 修复体验问题

**说明**: 这一步依赖 5.11 的反馈结果。以下是常见的修复方向，根据实际反馈选择执行：

1. **P0 阻塞性 Bug**：
   - 崩溃/卡死 → 检查错误日志，修复异常
   - 无响应 → 检查 API 调用，添加超时处理
   - 数据丢失 → 检查数据库写入

2. **P1 体验问题**：
   - 叙事太短/太长 → 调整 Prompt 中的长度要求
   - 战斗太难/太简单 → 调整 `src/services/combat.py` 中的数值
   - NPC 对话无趣 → 优化 `npc_templates.py` 中的性格描述
   - 重复内容 → 添加随机性，丰富模板

3. **P2 改进建议**：
   - 新功能需求 → 记录到 TODO，后续版本实现
   - 新剧情需求 → 添加到 `story_templates.py`

4. 每修复一个问题，记录到 `docs/prompt-tuning-log.md`。

**验收**: P0 和 P1 问题全部关闭

---

## 步骤 5.13 - 实现插件系统

**目的**: 方便扩展新功能

**执行**:
1. 创建 `src/plugins/__init__.py`：
   ```python
   """插件系统 - 方便扩展新功能"""
   import importlib
   import json
   from pathlib import Path
   from src.utils.logger import get_logger

   logger = get_logger(__name__)

   # 已加载的插件
   _loaded_plugins: dict[str, dict] = {}


   class GamePlugin:
       """插件基类"""

       name: str = "unnamed_plugin"
       description: str = ""

       def on_game_start(self, world_id: int, db_path: str | None = None):
           """游戏开始时触发"""
           pass

       def on_player_action(self, world_id: int, player_input: str, db_path: str | None = None):
           """玩家行动时触发"""
           pass

       def on_combat_end(self, world_id: int, victory: bool, rewards: dict, db_path: str | None = None):
           """战斗结束时触发"""
           pass

       def on_quest_complete(self, world_id: int, quest_id: int, db_path: str | None = None):
           """任务完成时触发"""
           pass

       def on_location_change(self, world_id: int, old_location: int, new_location: int, db_path: str | None = None):
           """玩家移动到新地点时触发"""
           pass

       def get_narrative_modifier(self) -> str:
           """返回要注入到叙事中的额外描述"""
           return ""


   def load_plugin(plugin_path: str) -> GamePlugin:
       """从 Python 文件加载插件"""
       spec = importlib.util.spec_from_file_location("plugin", plugin_path)
       module = importlib.util.module_from_spec(spec)
       spec.loader.exec_module(module)

       # 查找 GamePlugin 子类
       for attr_name in dir(module):
           attr = getattr(module, attr_name)
           if isinstance(attr, type) and issubclass(attr, GamePlugin) and attr != GamePlugin:
               plugin = attr()
               _loaded_plugins[plugin.name] = plugin
               logger.info(f"加载插件: {plugin.name} - {plugin.description}")
               return plugin

       raise ValueError(f"在 {plugin_path} 中未找到 GamePlugin 子类")


   def load_all_plugins(plugin_dir: str = "src/plugins"):
       """加载目录中所有插件"""
       pdir = Path(plugin_dir)
       if not pdir.exists():
           logger.info(f"插件目录不存在: {plugin_dir}")
           return

       for py_file in pdir.glob("*.py"):
           if py_file.name.startswith("_"):
               continue
           try:
               load_plugin(str(py_file))
           except Exception as e:
               logger.error(f"加载插件失败 {py_file}: {e}")


   def get_plugin(name: str) -> GamePlugin | None:
       return _loaded_plugins.get(name)


   def get_all_modifiers() -> str:
       """获取所有插件的叙事修饰"""
       modifiers = []
       for plugin in _loaded_plugins.values():
           mod = plugin.get_narrative_modifier()
           if mod:
               modifiers.append(mod)
       return "\n".join(modifiers)


   def trigger_event(event_name: str, **kwargs):
       """触发插件事件"""
       for plugin in _loaded_plugins.values():
           handler = getattr(plugin, event_name, None)
           if handler:
               try:
                   handler(**kwargs)
               except Exception as e:
                   logger.error(f"插件 {plugin.name} 事件 {event_name} 失败: {e}")
   ```
2. 创建示例插件 `src/plugins/weather_system.py`：
   ```python
   """天气系统插件 - 影响场景描述"""
   import random
   from src.plugins import GamePlugin


   class WeatherPlugin(GamePlugin):
       name = "weather_system"
       description = "天气系统，影响场景描述"

       def __init__(self):
           self.current_weather = random.choice(["晴朗", "多云", "小雨", "大雾", "暴风雨"])
           self.weather_effects = {
               "晴朗": "阳光透过树叶洒下斑驳的光影",
               "多云": "厚重的云层遮蔽了天空，空气沉闷",
               "小雨": "细雨绵绵，雨滴打在盔甲上发出清脆的声响",
               "大雾": "浓雾弥漫，能见度不足十步",
               "暴风雨": "狂风暴雨肆虐，闪电撕裂天空",
           }

       def on_game_start(self, world_id, **kwargs):
           self.current_weather = random.choice(list(self.weather_effects.keys()))

       def on_location_change(self, world_id, old_location, new_location, **kwargs):
           # 30% 概率天气变化
           if random.random() < 0.3:
               self.current_weather = random.choice(list(self.weather_effects.keys()))

       def get_narrative_modifier(self) -> str:
           effect = self.weather_effects.get(self.current_weather, "")
           return f"[天气: {self.current_weather}] {effect}"
   ```
3. 创建 `tests/test_plugin_system.py`：
   ```python
   """插件系统测试"""
   from src.plugins import GamePlugin, load_plugin, get_all_modifiers, trigger_event, _loaded_plugins


   def test_plugin_base():
       """插件基类"""
       plugin = GamePlugin()
       assert plugin.on_game_start(1) is None
       assert plugin.get_narrative_modifier() == ""


   def test_load_weather_plugin():
       """加载天气插件"""
       _loaded_plugins.clear()
       plugin = load_plugin("src/plugins/weather_system.py")
       assert plugin.name == "weather_system"
       modifier = plugin.get_narrative_modifier()
       assert "天气" in modifier


   def test_get_all_modifiers():
       """获取所有修饰"""
       _loaded_plugins.clear()
       load_plugin("src/plugins/weather_system.py")
       modifiers = get_all_modifiers()
       assert len(modifiers) > 0


   def test_trigger_event():
       """触发事件"""
       _loaded_plugins.clear()
       load_plugin("src/plugins/weather_system.py")
       # 不应该抛异常
       trigger_event("on_game_start", world_id=1)
       trigger_event("on_location_change", world_id=1, old_location=1, new_location=2)
   ```

**验收**: `uv run pytest tests/test_plugin_system.py -v` 全绿

---

## 步骤 5.14 - 编写项目文档

**目的**: 方便他人理解和使用

**执行**:
1. 创建 `README.md`：
   ```markdown
   # Game Master Agent

   AI 驱动的 RPG 游戏 Master Agent，使用 DeepSeek 大模型实时生成叙事、驱动 NPC、管理战斗。

   ## 功能特性

   - 🎭 **AI 叙事引擎**: DeepSeek 大模型实时生成沉浸式 RPG 叙事
   - 🧙 **NPC 系统**: 6 种性格模板，NPC 有记忆、有性格、有关系网
   - ⚔️ **战斗系统**: D&D 5e 简化版回合制战斗
   - 📜 **剧情系统**: 5 种剧情模板，分支选择，多结局
   - 🎮 **MUD 前端**: 经典文字冒险游戏界面
   - 🔧 **管理后台**: Vue 3 + Naive UI，Prompt 管理、AI 监控、数据管理
   - 🔌 **插件系统**: 可扩展的插件架构

   ## 快速开始

   ### 环境要求

   - Python 3.11+
   - Node.js 18+（管理端构建）
   - DeepSeek API Key

   ### 安装

   ```bash
   git clone https://github.com/Vving-JPG/Game-Master-Agent.git
   cd Game-Master-Agent
   uv sync
   ```

   ### 配置

   创建 `.env` 文件：
   ```
   DEEPSEEK_API_KEY=your_api_key_here
   DEEPSEEK_BASE_URL=https://api.deepseek.com
   ```

   ### 启动

   ```bash
   # CLI 模式
   uv run python src/cli.py

   # Web 模式
   uv run uvicorn src.api.app:app --reload --port 8000
   # 游戏界面: http://localhost:8000/static/index.html
   # 管理后台: http://localhost:8000/admin
   # API 文档: http://localhost:8000/docs
   ```

   ### 测试

   ```bash
   uv run pytest tests/ -v
   ```

   ## 项目结构

   ```
   src/
   ├── agent/          # GM Agent 核心
   ├── api/            # FastAPI 后端 + 管理端路由
   ├── admin/          # Vue 3 管理端前端
   ├── data/           # 种子数据 + 模板
   ├── models/         # 数据访问层
   ├── plugins/        # 插件系统
   ├── prompts/        # System Prompt
   ├── services/       # 业务逻辑层
   ├── tools/          # GM 工具集
   ├── utils/          # 工具函数
   └── web/            # MUD 前端
   ```

   ## 技术栈

   - **后端**: Python 3.11 + FastAPI + SQLite
   - **AI**: DeepSeek API (V3/R1)
   - **前端**: HTML/CSS/JS (MUD) + Vue 3 + Naive UI (管理端)
   - **工具**: uv + pytest
   ```
2. 创建 `docs/architecture.md`（架构文档）：
   ```markdown
   # 架构设计

   ## 整体架构

   ```
   玩家 → MUD前端/WebSocket → FastAPI → GameMaster → DeepSeek API
                                ↓
                           工具执行器 → 数据库(SQLite)
                                ↓
                           管理端 → Vue3/NaiveUI
   ```

   ## 核心模块

   - **GameMaster** (`src/agent/game_master.py`): 核心循环，while循环 + 工具调用
   - **LLMClient** (`src/services/llm_client.py`): DeepSeek API 封装
   - **ToolExecutor** (`src/tools/executor.py`): 工具注册和执行
   - **ContextManager** (`src/services/context_manager.py`): 对话历史管理

   ## 数据流

   1. 玩家输入 → WebSocket → GameMaster.process()
   2. 构建 System Prompt + 对话历史
   3. 调用 DeepSeek API（带工具定义）
   4. 如果返回工具调用 → 执行工具 → 结果加入历史 → 继续调用
   5. 如果返回文本 → 流式输出给玩家
   ```
3. 创建 `docs/contributing.md`（贡献指南）：
   ```markdown
   # 贡献指南

   ## 代码规范

   - UTF-8 编码，中文注释
   - PEP 8 风格
   - 每个模块必须有 pytest 测试
   - 使用 `uv` 管理依赖

   ## 添加新工具

   1. 在 `src/tools/` 创建工具函数
   2. 在 `src/tools/tool_definitions.py` 添加 Schema
   3. 在 `src/tools/__init__.py` 注册
   4. 编写测试

   ## 添加新插件

   1. 在 `src/plugins/` 创建 Python 文件
   2. 继承 `GamePlugin` 基类
   3. 实现需要的事件钩子
   ```
4. 创建 `docs/api.md`（API 文档）——内容直接引用 `docs/api_design.md` 和 Swagger UI。

**验收**: 所有文档文件存在，内容完整

---

## ★ P5' 里程碑验收

运行完整测试套件：

```bash
uv run pytest tests/ -v
```

逐项确认：

- [ ] 5.1 Prompt 迭代优化完成，调优日志有记录
- [ ] 5.2 Few-Shot 示例添加完成
- [ ] 5.3 LLM 摘要压缩通过单测
- [ ] 5.4 关键信息提取通过单测
- [ ] 5.5 响应缓存通过单测
- [ ] 5.6 预生成通过单测
- [ ] 5.7 Token 审计完成，有优化记录
- [ ] 5.8 多模型路由通过单测
- [ ] 5.9 日志和监控正常
- [ ] 5.10 优雅降级通过单测
- [ ] 5.11 用户反馈收集完成
- [ ] 5.12 反馈问题已修复
- [ ] 5.13 插件系统通过单测
- [ ] 5.14 项目文档完整

**全部 ✅ 后，P5' 阶段完成！Game Master Agent 项目全部完成！** 🎉

---

## P5' 完成后的项目结构

```
game-master-agent/
├── src/
│   ├── agent/
│   │   └── game_master.py          # ★ 优化: 摘要压缩 + 信息提取 + 预生成 + 多模型路由
│   ├── api/
│   │   └── ...                     # (P4' 已创建)
│   ├── admin/                      # (P4' 已创建)
│   ├── models/
│   │   └── ...                     # (P1'-P4' 已创建)
│   ├── plugins/                    # ★ 新增
│   │   ├── __init__.py             # 插件系统
│   │   └── weather_system.py       # 天气插件示例
│   ├── prompts/
│   │   └── gm_system.py            # ★ 优化: Few-Shot + 质量约束
│   ├── services/
│   │   ├── context_manager.py      # ★ 实现: 摘要压缩 + Token 估算
│   │   ├── info_extractor.py       # ★ 新增: 关键信息提取
│   │   ├── cache.py                # ★ 新增: LRU 缓存
│   │   ├── pregenerator.py         # ★ 新增: 预生成
│   │   ├── model_router.py         # ★ 新增: 多模型路由
│   │   └── ...                     # (P2'-P4' 已创建)
│   ├── tools/
│   │   └── ...                     # (P2'-P3' 已创建)
│   ├── utils/
│   │   └── logger.py               # ★ 优化: 文件日志
│   ├── data/
│   │   └── ...                     # (P1'-P3' 已创建)
│   ├── web/                        # (P2'-P4' 已创建)
│   └── cli.py
├── scripts/                        # ★ 新增
│   ├── token_audit.py              # Token 审计
│   └── health_check.py             # 健康检查
├── docs/
│   ├── api_design.md               # (P4' 已创建)
│   ├── prompt-tuning-log.md        # ★ 更新: P5' 优化记录
│   ├── user_feedback.md            # ★ 新增: 用户反馈
│   ├── architecture.md             # ★ 新增
│   ├── api.md                      # ★ 新增
│   └── contributing.md             # ★ 新增
├── logs/                           # ★ 新增: 日志目录
├── tests/                          # 160+个测试
├── README.md                       # ★ 新增
└── pyproject.toml
```
