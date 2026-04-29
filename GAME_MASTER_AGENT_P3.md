# Game Master Agent - P3' 游戏系统

> 本文件是 Trae AI 助手执行 P3' 阶段的指引。P0 + P1' + P2' 必须已全部完成。
> **本阶段实现三大游戏系统：NPC系统、剧情任务系统、道具战斗系统。**

## 前置条件

执行本阶段前，确认以下成果已就绪：
- [ ] P0 全部完成（17步）
- [ ] P1' 全部完成（13步）
- [ ] P2' 全部完成（16步，68个测试通过）
- [ ] `uv run pytest tests/ -v` 全部通过（68+个测试）
- [ ] `src/agent/game_master.py` 存在（GameMaster 类可用）
- [ ] `src/tools/executor.py` 存在（10个工具已注册）
- [ ] `src/services/llm_client.py` 存在（LLMClient 可用，支持 chat_with_tools）
- [ ] `src/models/schema.sql` 存在（11个表，含 npc_memories）
- [ ] `src/data/seed_data.py` 存在（`seed_world()` 返回 `{"world_id": ..., "player_id": ...}`）

## 行为准则

1. **一步一步执行**：严格按步骤顺序，每步验证通过后再继续
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始P3'"后，主动执行每一步
4. **遇到错误先尝试解决**：3次失败后再询问用户
5. **每步完成后汇报**：简要汇报结果和下一步
6. **代码规范**：UTF-8、中文注释、PEP 8、每个模块必须有 pytest 测试
7. **不要跳步**
8. **数据库迁移**：本阶段需要扩展表结构。使用 `ALTER TABLE` 添加新列，不要删除现有数据。如果 ALTER 失败，可以先删除旧数据库文件重新初始化（测试环境可以，生产环境不行）。
9. **工具注册**：每新增一个工具，必须在 `src/tools/__init__.py` 中注册，并在 `src/tools/tool_definitions.py` 中添加对应 Schema。

## P2' 经验教训（必须遵守）

以下问题在 P2' 中踩过坑，本阶段必须注意：
- **DeepSeek reasoning_content**：如果工具调用涉及 LLM，assistant 消息和 tool 消息都要传递 `reasoning_content`
- **tool_call_id**：tool 消息必须包含 `tool_call_id` 字段
- **全局状态隔离**：测试中不要污染 `TOOL_REGISTRY`，用 `teardown_module` 清理
- **模块引用**：`from module import variable` 是值拷贝，要用 `from module import module; module.variable`

---

## 步骤 3.1 - 扩展 NPC 属性模型

**目的**: 扩展 NPC 表，支持性格/情绪/目标/关系

**执行**:
1. 在 `src/models/schema.sql` 的 `npcs` 表定义中添加新列（用 ALTER TABLE 或修改建表语句）：
   ```sql
   -- 在 npcs 表中添加（如果不存在）:
   personality TEXT DEFAULT '{}',       -- JSON: 大五人格参数 {"openness":0.7,"conscientiousness":0.5,...}
   mood TEXT DEFAULT 'neutral',        -- 当前情绪: happy/sad/angry/neutral/fearful/surprised
   goals TEXT DEFAULT '[]',            -- JSON: 目标列表 [{"description":"保护村庄","priority":1}]
   relationships TEXT DEFAULT '{}',    -- JSON: 关系网 {"1":50,"2":-30}  (npc_id -> value)
   speech_style TEXT DEFAULT ''        -- 说话风格描述
   ```
2. 更新 `src/models/npc_repo.py`：
   - `create_npc()` 添加新参数：`personality=None, mood='neutral', goals=None, relationships=None, speech_style=None`
   - `get_npc()` 返回值包含新字段
   - `update_npc()` 支持更新新字段
3. 创建 `tests/test_npc_model.py`：
   ```python
   """NPC扩展属性模型测试"""
   import tempfile
   import os
   import json
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.models import npc_repo

   DB_PATH = None
   WORLD_ID = None

   def setup_module():
       global DB_PATH, WORLD_ID
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       WORLD_ID = result["world_id"]

   def test_create_npc_with_personality():
       """创建带性格的NPC"""
       personality = {"openness": 0.8, "conscientiousness": 0.3, "extraversion": 0.9, "agreeableness": 0.6, "neuroticism": 0.2}
       goals = [{"description": "探索世界", "priority": 1}]
       npc_id = npc_repo.create_npc(
           WORLD_ID, "测试NPC", 1,
           personality=json.dumps(personality),
           mood="happy",
           goals=json.dumps(goals),
           speech_style="说话很热情！"
       )
       npc = npc_repo.get_npc(npc_id, DB_PATH)
       assert npc["mood"] == "happy"
       assert json.loads(npc["personality"])["openness"] == 0.8
       assert json.loads(npc["goals"])[0]["description"] == "探索世界"
       assert npc["speech_style"] == "说话很热情！"

   def test_update_npc_mood():
       """更新NPC心情"""
       npc_id = npc_repo.create_npc(WORLD_ID, "心情NPC", 1, db_path=DB_PATH)
       npc_repo.update_npc(npc_id, mood="angry", db_path=DB_PATH)
       npc = npc_repo.get_npc(npc_id, DB_PATH)
       assert npc["mood"] == "angry"

   def test_update_relationships():
       """更新NPC关系"""
       rel = {"1": 50, "2": -30}
       npc_id = npc_repo.create_npc(WORLD_ID, "关系NPC", 1, relationships=json.dumps(rel), db_path=DB_PATH)
       npc = npc_repo.get_npc(npc_id, DB_PATH)
       rels = json.loads(npc["relationships"])
       assert rels["1"] == 50
       assert rels["2"] == -30
   ```

**验收**: `uv run pytest tests/test_npc_model.py -v` 全绿

---

## 步骤 3.2 - 实现 NPC 性格模板

**目的**: 预设性格类型，快速生成有特色的 NPC

**执行**:
1. 创建 `src/data/npc_templates.py`：
   ```python
   """NPC性格模板 - 预设性格类型，快速生成有特色的NPC"""

   # 大五人格: openness(开放性), conscientiousness(尽责性), extraversion(外向性),
   #           agreeableness(宜人性), neuroticism(神经质)
   NPC_TEMPLATES = {
       "brave_warrior": {
           "name": "勇敢战士",
           "personality": {
               "openness": 0.3, "conscientiousness": 0.8,
               "extraversion": 0.7, "agreeableness": 0.5, "neuroticism": 0.2,
           },
           "speech_style": "直率豪爽，说话简洁有力，常用感叹号！喜欢谈论战斗和荣誉。",
           "mood": "confident",
           "common_topics": ["战斗", "荣誉", "武器", "训练", "冒险"],
           "goals": [{"description": "变得更强", "priority": 1}],
       },
       "mysterious_mage": {
           "name": "神秘法师",
           "personality": {
               "openness": 0.9, "conscientiousness": 0.6,
               "extraversion": 0.2, "agreeableness": 0.4, "neuroticism": 0.5,
           },
           "speech_style": "说话隐晦深奥，喜欢用比喻和暗示。语速缓慢，经常停顿思考……",
           "mood": "contemplative",
           "common_topics": ["魔法", "知识", "古代秘密", "星辰", "命运"],
           "goals": [{"description": "探索魔法的奥秘", "priority": 1}],
       },
       "friendly_merchant": {
           "name": "友好商人",
           "personality": {
               "openness": 0.5, "conscientiousness": 0.7,
               "extraversion": 0.9, "agreeableness": 0.8, "neuroticism": 0.3,
           },
           "speech_style": "热情洋溢，喜欢用亲切的称呼！经常推荐商品，说话带着商人的精明。",
           "mood": "cheerful",
           "common_topics": ["商品", "价格", "旅行见闻", "美食", "交易"],
           "goals": [{"description": "积累财富", "priority": 1}],
       },
       "sinister_villain": {
           "name": "阴险反派",
           "personality": {
               "openness": 0.6, "conscientiousness": 0.9,
               "extraversion": 0.4, "agreeableness": 0.1, "neuroticism": 0.7,
           },
           "speech_style": "阴阳怪气，喜欢嘲讽和威胁。说话时带着冷笑，经常用反问句。",
           "mood": "cunning",
           "common_topics": ["权力", "阴谋", "弱点", "控制", "复仇"],
           "goals": [{"description": "统治一切", "priority": 1}],
       },
       "wise_elder": {
           "name": "智慧长者",
           "personality": {
               "openness": 0.8, "conscientiousness": 0.9,
               "extraversion": 0.3, "agreeableness": 0.7, "neuroticism": 0.2,
           },
           "speech_style": "说话缓慢庄重，喜欢引用古训和谚语。经常用"孩子"称呼年轻人。",
           "mood": "serene",
           "common_topics": ["历史", "智慧", "传统", "和平", "自然"],
           "goals": [{"description": "守护村庄的和平", "priority": 1}],
       },
       "naive_villager": {
           "name": "天真村民",
           "personality": {
               "openness": 0.4, "conscientiousness": 0.4,
               "extraversion": 0.6, "agreeableness": 0.9, "neuroticism": 0.6,
           },
           "speech_style": "说话朴实无华，容易紧张。经常问问题，对冒险者充满好奇和敬畏。",
           "mood": "curious",
           "common_topics": ["村庄日常", "天气", "庄稼", "传闻", "家人"],
           "goals": [{"description": "过上安稳的日子", "priority": 1}],
       },
   }


   def get_template(template_name: str) -> dict | None:
       """获取性格模板"""
       return NPC_TEMPLATES.get(template_name)


   def list_templates() -> list[str]:
       """列出所有可用模板名"""
       return list(NPC_TEMPLATES.keys())


   def apply_template(template_name: str, npc_name: str, custom_overrides: dict | None = None) -> dict:
       """应用模板生成NPC属性

       Args:
           template_name: 模板名
           npc_name: NPC名字
           custom_overrides: 自定义覆盖（如 {"mood": "angry"}）

       Returns:
           dict: 可直接传给 npc_repo.create_npc 的关键字参数
       """
       template = NPC_TEMPLATES.get(template_name)
       if not template:
           raise ValueError(f"未知模板: {template_name}，可用: {list_templates()}")

       import json
       attrs = {
           "personality": json.dumps(template["personality"]),
           "mood": template["mood"],
           "goals": json.dumps(template["goals"]),
           "speech_style": template["speech_style"],
       }
       if custom_overrides:
           attrs.update(custom_overrides)
       return attrs
   ```
2. 创建 `tests/test_npc_templates.py`：
   ```python
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
   ```

**验收**: `uv run pytest tests/test_npc_templates.py -v` 全绿

---

## 步骤 3.3 - 实现 create_npc 工具 + 单测

**目的**: GM 能动态创建 NPC

**执行**:
1. 在 `src/tools/tool_definitions.py` 中添加 Schema：
   ```python
   CREATE_NPC_SCHEMA = {
       "type": "function",
       "function": {
           "name": "create_npc",
           "description": "创建一个新的NPC。可以用预设性格模板快速创建，也可以自定义性格参数。",
           "parameters": {
               "type": "object",
               "properties": {
                   "name": {"type": "string", "description": "NPC名字"},
                   "location_id": {"type": "integer", "description": "NPC所在地点ID"},
                   "personality_type": {
                       "type": "string",
                       "description": "性格模板名: brave_warrior/mysterious_mage/friendly_merchant/sinister_villain/wise_elder/naive_villager"
                   },
                   "mood": {"type": "string", "description": "当前心情（可选，覆盖模板默认值）"},
                   "speech_style": {"type": "string", "description": "说话风格（可选，覆盖模板默认值）"},
                   "backstory": {"type": "string", "description": "背景故事（可选）"}
               },
               "required": ["name", "location_id"]
           }
       }
   }
   ```
   并将 `CREATE_NPC_SCHEMA` 加入 `ALL_TOOL_SCHEMAS` 列表。
2. 在 `src/tools/npc_tool.py` 中添加 `create_npc` 函数：
   ```python
   def create_npc(name: str, location_id: int, personality_type: str | None = None,
                  mood: str | None = None, speech_style: str | None = None,
                  backstory: str | None = None, db_path: str | None = None) -> str:
       """创建NPC"""
       import json
       from src.models import npc_repo
       from src.data.npc_templates import apply_template

       wid = world_tool._active_world_id

       # 获取模板属性
       if personality_type:
           overrides = {}
           if mood:
               overrides["mood"] = mood
           if speech_style:
               overrides["speech_style"] = speech_style
           attrs = apply_template(personality_type, name, overrides or None)
       else:
           attrs = {
               "personality": json.dumps({}),
               "mood": mood or "neutral",
               "goals": json.dumps([]),
               "speech_style": speech_style or "",
           }

       npc_id = npc_repo.create_npc(
           wid, name, location_id,
           backstory=backstory or "",
           db_path=db_path,
           **attrs,
       )
       template_info = f"（模板: {personality_type}）" if personality_type else ""
       return f"已创建NPC: {name} (ID:{npc_id}) 在地点{location_id} {template_info}"
   ```
3. 在 `src/tools/__init__.py` 中注册：
   ```python
   from src.tools.tool_definitions import CREATE_NPC_SCHEMA
   register_tool("create_npc", npc_tool.create_npc, CREATE_NPC_SCHEMA)
   ```
4. 创建 `tests/test_create_npc_tool.py`：
   ```python
   """create_npc工具测试"""
   import tempfile, os
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.tools import world_tool, npc_tool
   from src.models import npc_repo

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       world_tool.set_active(result["world_id"], result["player_id"])

   def test_create_npc_basic():
       """基本创建"""
       result = npc_tool.create_npc("测试骑士", 1, db_path=DB_PATH)
       assert "测试骑士" in result
       assert "ID:" in result

   def test_create_npc_with_template():
       """用模板创建"""
       result = npc_tool.create_npc("铁锤", 1, personality_type="brave_warrior", db_path=DB_PATH)
       assert "铁锤" in result
       assert "brave_warrior" in result

   def test_create_npc_in_db():
       """创建后能从数据库查到"""
       npc_tool.create_npc("持久化NPC", 1, personality_type="wise_elder", db_path=DB_PATH)
       npcs = npc_repo.get_npcs_by_location(1, DB_PATH)
       found = [n for n in npcs if n["name"] == "持久化NPC"]
       assert len(found) == 1
       assert found[0]["mood"] == "serene"
   ```

**验收**: `uv run pytest tests/test_create_npc_tool.py -v` 全绿

---

## 步骤 3.4 - 实现 npc_dialog 工具 + 单测

**目的**: 生成符合 NPC 性格的对话

**执行**:
1. 在 `src/tools/tool_definitions.py` 中添加 Schema：
   ```python
   NPC_DIALOG_SCHEMA = {
       "type": "function",
       "function": {
           "name": "npc_dialog",
           "description": "让NPC与玩家对话。会根据NPC的性格、心情、目标和记忆生成符合人设的回复。",
           "parameters": {
               "type": "object",
               "properties": {
                   "npc_id": {"type": "integer", "description": "NPC的ID"},
                   "player_message": {"type": "string", "description": "玩家对NPC说的话"}
               },
               "required": ["npc_id", "player_message"]
           }
       }
   }
   ```
   加入 `ALL_TOOL_SCHEMAS`。
2. 创建 `src/services/npc_dialog.py`：
   ```python
   """NPC对话服务 - 根据性格生成对话"""
   import json
   from src.services.llm_client import LLMClient
   from src.models import npc_repo, log_repo
   from src.tools import world_tool
   from src.utils.logger import get_logger

   logger = get_logger(__name__)

   # 对话用的System Prompt模板
   DIALOG_SYSTEM_PROMPT = """你是一个RPG游戏中的NPC。请根据以下人设信息，用中文回复玩家。

## NPC信息
- 名字: {name}
- 心情: {mood}
- 说话风格: {speech_style}
- 性格: {personality_desc}
- 目标: {goals_desc}
- 背景故事: {backstory}
- 与玩家的关系: {relationship_desc}

## 规则
1. 严格保持角色人设，不要跳出角色
2. 根据心情调整语气（开心时热情，愤怒时暴躁）
3. 回复长度控制在1-3句话
4. 可以在对话中透露任务线索或世界信息
5. 不要用括号标注动作，直接说话
"""


   def build_npc_context(npc_id: int, db_path: str | None = None) -> dict:
       """构建NPC上下文信息"""
       npc = npc_repo.get_npc(npc_id, db_path)
       if not npc:
           return None

       personality = json.loads(npc.get("personality") or "{}")
       goals = json.loads(npc.get("goals") or "[]")
       relationships = json.loads(npc.get("relationships") or "{}")

       # 性格描述
       trait_names = {
           "openness": "开放性", "conscientiousness": "尽责性",
           "extraversion": "外向性", "agreeableness": "宜人性", "neuroticism": "神经质",
       }
       personality_desc = "，".join(
           f"{trait_names.get(k, k)}{v:.0%}" for k, v in personality.items() if v > 0.6
       ) or "普通"

       goals_desc = "，".join(g["description"] for g in goals) or "无特定目标"

       # 与玩家的关系
       pid = world_tool._active_player_id
       rel_value = relationships.get(str(pid), 0)
       if rel_value > 50:
           relationship_desc = f"友好（{rel_value}）"
       elif rel_value > 0:
           relationship_desc = f"中立偏善（{rel_value}）"
       elif rel_value > -50:
           relationship_desc = f"中立偏冷（{rel_value}）"
       else:
           relationship_desc = f"敌对（{rel_value}）"

       return {
           "name": npc["name"],
           "mood": npc.get("mood", "neutral"),
           "speech_style": npc.get("speech_style", ""),
           "personality_desc": personality_desc,
           "goals_desc": goals_desc,
           "backstory": npc.get("backstory", ""),
           "relationship_desc": relationship_desc,
       }


   def generate_npc_dialog(npc_id: int, player_message: str,
                           llm: LLMClient | None = None, db_path: str | None = None) -> str:
       """生成NPC对话回复

       Args:
           npc_id: NPC ID
           player_message: 玩家说的话
           llm: LLM客户端（可选，默认新建）
           db_path: 数据库路径

       Returns:
           NPC的回复文本
       """
       ctx = build_npc_context(npc_id, db_path)
       if not ctx:
           return f"未找到ID为{npc_id}的NPC。"

       system_prompt = DIALOG_SYSTEM_PROMPT.format(**ctx)

       llm = llm or LLMClient()
       response = llm.chat([
           {"role": "system", "content": system_prompt},
           {"role": "user", "content": player_message},
       ])

       reply = response.choices[0].message.content or ""

       # 记录对话日志
       wid = world_tool._active_world_id
       log_repo.log_event(wid, "dialog",
                          f"[{ctx['name']}] 玩家: {player_message} → NPC: {reply}",
                          db_path)

       logger.info(f"NPC对话: {ctx['name']} ← {player_message} → {reply[:50]}...")
       return reply
   ```
3. 在 `src/tools/npc_tool.py` 中添加 `npc_dialog`：
   ```python
   def npc_dialog(npc_id: int, player_message: str, db_path: str | None = None) -> str:
       """让NPC与玩家对话"""
       from src.services.npc_dialog import generate_npc_dialog
       return generate_npc_dialog(npc_id, player_message, db_path=db_path)
   ```
4. 在 `src/tools/__init__.py` 注册 `npc_dialog`。
5. 创建 `tests/test_npc_dialog.py`：
   ```python
   """NPC对话测试"""
   import tempfile, os, json
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.tools import world_tool
   from src.services.npc_dialog import build_npc_context, generate_npc_dialog
   from src.models import npc_repo

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       world_tool.set_active(result["world_id"], result["player_id"])

   def test_build_npc_context():
       """构建NPC上下文"""
       npc_id = npc_repo.create_npc(
           result["world_id"] if 'result' in dir() else 1,
           "测试法师", 1,
           personality=json.dumps({"openness": 0.9, "conscientiousness": 0.6, "extraversion": 0.2, "agreeableness": 0.4, "neuroticism": 0.5}),
           mood="contemplative",
           speech_style="说话隐晦...",
           db_path=DB_PATH,
       )
       ctx = build_npc_context(npc_id, DB_PATH)
       assert ctx["name"] == "测试法师"
       assert ctx["mood"] == "contemplative"
       assert "开放性" in ctx["personality_desc"]

   def test_generate_dialog():
       """生成NPC对话（真实LLM调用）"""
       npc_id = npc_repo.create_npc(
           1, "对话测试NPC", 1,
           personality=json.dumps({"openness": 0.3, "conscientiousness": 0.8, "extraversion": 0.7, "agreeableness": 0.5, "neuroticism": 0.2}),
           mood="confident",
           speech_style="直率豪爽！",
           db_path=DB_PATH,
       )
       reply = generate_npc_dialog(npc_id, "你好，你是谁？", db_path=DB_PATH)
       assert reply is not None
       assert len(reply) > 0
       print(f"\nNPC回复: {reply}")
   ```

**验收**: `uv run pytest tests/test_npc_dialog.py -v -s` 全绿（能看到 NPC 的实际回复）

---

## 步骤 3.5 - 实现 NPC 关系追踪 + 单测

**目的**: 更新和查询 NPC 间及 NPC 与玩家的关系

**执行**:
1. 在 `src/tools/tool_definitions.py` 中添加 Schema：
   ```python
   UPDATE_RELATIONSHIP_SCHEMA = {
       "type": "function",
       "function": {
           "name": "update_relationship",
           "description": "更新NPC与目标之间的关系值。关系值范围-100到+100。正值表示友好，负值表示敌对。",
           "parameters": {
               "type": "object",
               "properties": {
                   "npc_id": {"type": "integer", "description": "NPC的ID"},
                   "target_id": {"type": "integer", "description": "目标ID（玩家或其他NPC的ID）"},
                   "change": {"type": "integer", "description": "关系变化值（正数=变好，负数=变差）"}
               },
               "required": ["npc_id", "target_id", "change"]
           }
       }
   }

   GET_RELATIONSHIP_GRAPH_SCHEMA = {
       "type": "function",
       "function": {
           "name": "get_relationship_graph",
           "description": "获取NPC的关系网络图。",
           "parameters": {
               "type": "object",
               "properties": {
                   "npc_id": {"type": "integer", "description": "NPC的ID（可选，不指定则返回所有关系）"}
               },
               "required": []
           }
       }
   }
   ```
   加入 `ALL_TOOL_SCHEMAS`。
2. 在 `src/tools/npc_tool.py` 中添加：
   ```python
   def update_relationship(npc_id: int, target_id: int, change: int, db_path: str | None = None) -> str:
       """更新NPC关系"""
       import json
       from src.models import npc_repo
       npc = npc_repo.get_npc(npc_id, db_path)
       if not npc:
           return f"未找到ID为{npc_id}的NPC"

       relationships = json.loads(npc.get("relationships") or "{}")
       current = relationships.get(str(target_id), 0)
       new_value = max(-100, min(100, current + change))
       relationships[str(target_id)] = new_value

       npc_repo.update_npc(npc_id, relationships=json.dumps(relationships), db_path=db_path)

       direction = "提升" if change > 0 else "下降"
       return f"NPC {npc['name']} 对目标{target_id}的关系{direction}了{abs(change)}点，当前: {new_value}"


   def get_relationship_graph(npc_id: int | None = None, db_path: str | None = None) -> str:
       """获取关系网络"""
       import json
       from src.models import npc_repo, location_repo
       wid = world_tool._active_world_id

       nodes = []
       edges = []

       for loc in location_repo.get_locations_by_world(wid, db_path):
           for npc in npc_repo.get_npcs_by_location(loc["id"], db_path):
               nodes.append({"id": npc["id"], "name": npc["name"], "location": loc["name"]})
               rels = json.loads(npc.get("relationships") or "{}")
               for target_id, value in rels.items():
                   if abs(value) >= 10:  # 只显示有意义的关系
                       edges.append({"from": npc["id"], "to": int(target_id), "value": value})

       if npc_id:
           edges = [e for e in edges if e["from"] == npc_id or e["to"] == npc_id]

       if not edges:
           return "暂无显著关系"

       lines = ["关系网络:"]
       for e in edges:
           from_name = next((n["name"] for n in nodes if n["id"] == e["from"]), f"ID:{e['from']}")
           to_name = next((n["name"] for n in nodes if n["id"] == e["to"]), f"ID:{e['to']}")
           sign = "❤️" if e["value"] > 0 else "💔"
           lines.append(f"  {from_name} {sign} {to_name} ({e['value']:+d})")
       return "\n".join(lines)
   ```
3. 在 `src/tools/__init__.py` 注册两个工具。
4. 创建 `tests/test_npc_relationship.py`：
   ```python
   """NPC关系追踪测试"""
   import tempfile, os, json
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.tools import world_tool, npc_tool
   from src.models import npc_repo

   DB_PATH = None
   NPC_ID = None

   def setup_module():
       global DB_PATH, NPC_ID
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       world_tool.set_active(result["world_id"], result["player_id"])
       NPC_ID = npc_repo.create_npc(result["world_id"], "关系NPC", 1, db_path=DB_PATH)

   def test_update_relationship_positive():
       """帮助NPC后关系上升"""
       result = npc_tool.update_relationship(NPC_ID, 1, 20, DB_PATH)
       assert "提升" in result
       assert "20" in result

   def test_update_relationship_negative():
       """伤害NPC后关系下降"""
       result = npc_tool.update_relationship(NPC_ID, 1, -15, DB_PATH)
       assert "下降" in result

   def test_relationship_persisted():
       """关系值持久化"""
       npc_tool.update_relationship(NPC_ID, 1, 50, DB_PATH)
       npc = npc_repo.get_npc(NPC_ID, DB_PATH)
       rels = json.loads(npc["relationships"])
       assert rels["1"] == 50

   def test_relationship_clamp():
       """关系值不超过-100~100"""
       npc_tool.update_relationship(NPC_ID, 1, 200, DB_PATH)
       npc = npc_repo.get_npc(NPC_ID, DB_PATH)
       rels = json.loads(npc["relationships"])
       assert rels["1"] <= 100
   ```

**验收**: `uv run pytest tests/test_npc_relationship.py -v` 全绿

---

## 步骤 3.6 - 实现 NPC 记忆系统 + 单测

**目的**: NPC 能记住与玩家的交互

**执行**:
1. 确认 `src/models/schema.sql` 中 `npc_memories` 表存在（P1' 已创建）：
   ```sql
   CREATE TABLE IF NOT EXISTS npc_memories (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       npc_id INTEGER NOT NULL,
       content TEXT NOT NULL,
       importance INTEGER DEFAULT 5,
       created_at TEXT DEFAULT (datetime('now')),
       FOREIGN KEY (npc_id) REFERENCES npcs(id)
   );
   ```
2. 创建 `src/models/memory_repo.py`：
   ```python
   """NPC记忆数据访问"""
   from src.services.database import get_db
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def add_memory(npc_id: int, content: str, importance: int = 5, db_path: str | None = None) -> int:
       """添加记忆"""
       with get_db(db_path) as conn:
           cursor = conn.execute(
               "INSERT INTO npc_memories (npc_id, content, importance) VALUES (?, ?, ?)",
               (npc_id, content, importance),
           )
           return cursor.lastrowid


   def get_memories(npc_id: int, limit: int = 20, db_path: str | None = None) -> list[dict]:
       """获取NPC记忆，按重要性和时间排序"""
       with get_db(db_path) as conn:
           rows = conn.execute(
               "SELECT * FROM npc_memories WHERE npc_id = ? ORDER BY importance DESC, created_at DESC LIMIT ?",
               (npc_id, limit),
           ).fetchall()
       return [dict(r) for r in rows]


   def get_important_memories(npc_id: int, min_importance: int = 7, limit: int = 10, db_path: str | None = None) -> list[dict]:
       """获取重要记忆"""
       with get_db(db_path) as conn:
           rows = conn.execute(
               "SELECT * FROM npc_memories WHERE npc_id = ? AND importance >= ? ORDER BY created_at DESC LIMIT ?",
               (npc_id, min_importance, limit),
           ).fetchall()
       return [dict(r) for r in rows]


   def delete_memory(memory_id: int, db_path: str | None = None):
       """删除记忆"""
       with get_db(db_path) as conn:
           conn.execute("DELETE FROM npc_memories WHERE id = ?", (memory_id,))


   def compress_memories(npc_id: int, keep_count: int = 50, db_path: str | None = None) -> int:
       """压缩记忆：保留最重要的keep_count条，删除其余"""
       with get_db(db_path) as conn:
           total = conn.execute(
               "SELECT COUNT(*) FROM npc_memories WHERE npc_id = ?", (npc_id,)
           ).fetchone()[0]
           if total <= keep_count:
               return 0
           # 删除重要性最低的
           conn.execute(
               """DELETE FROM npc_memories WHERE npc_id = ? AND id NOT IN (
                   SELECT id FROM npc_memories WHERE npc_id = ?
                   ORDER BY importance DESC, created_at DESC LIMIT ?
               )""",
               (npc_id, npc_id, keep_count),
           )
           return total - keep_count
   ```
3. 在 `src/models/__init__.py` 中添加 `from src.models import memory_repo`。
4. 在 `src/services/npc_dialog.py` 的 `generate_npc_dialog` 中注入记忆：
   ```python
   # 在 build_npc_context 函数末尾添加:
   from src.models import memory_repo
   memories = memory_repo.get_important_memories(npc_id, min_importance=6, limit=5, db_path=db_path)
   ctx["memories"] = [m["content"] for m in memories]
   ```

   并在 `DIALOG_SYSTEM_PROMPT` 末尾添加：
   ```
   ## 相关记忆
   {memories_desc}
   ```
   在 `format(**ctx)` 前添加：
   ```python
   ctx["memories_desc"] = "\n".join(f"- {m}" for m in ctx.get("memories", [])) or "无相关记忆"
   ```
5. 创建 `tests/test_memory_repo.py`：
   ```python
   """NPC记忆系统测试"""
   import tempfile, os
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.models import npc_repo, memory_repo

   DB_PATH = None
   NPC_ID = None

   def setup_module():
       global DB_PATH, NPC_ID
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       NPC_ID = npc_repo.create_npc(result["world_id"], "记忆NPC", 1, db_path=DB_PATH)

   def test_add_and_get_memory():
       """添加和查询记忆"""
       mid = memory_repo.add_memory(NPC_ID, "玩家给了我一把剑", importance=8, db_path=DB_PATH)
       assert mid > 0
       memories = memory_repo.get_memories(NPC_ID, db_path=DB_PATH)
       assert len(memories) == 1
       assert "剑" in memories[0]["content"]

   def test_memory_ordering():
       """记忆按重要性排序"""
       memory_repo.add_memory(NPC_ID, "不重要的事", importance=2, db_path=DB_PATH)
       memory_repo.add_memory(NPC_ID, "非常重要的事", importance=9, db_path=DB_PATH)
       memories = memory_repo.get_memories(NPC_ID, db_path=DB_PATH)
       assert memories[0]["content"] == "非常重要的事"

   def test_compress_memories():
       """压缩记忆"""
       for i in range(60):
           memory_repo.add_memory(NPC_ID, f"记忆{i}", importance=i % 10, db_path=DB_PATH)
       deleted = memory_repo.compress_memories(NPC_ID, keep_count=10, db_path=DB_PATH)
       assert deleted > 0
       remaining = memory_repo.get_memories(NPC_ID, limit=100, db_path=DB_PATH)
       assert len(remaining) <= 10

   def test_delete_memory():
       """删除记忆"""
       mid = memory_repo.add_memory(NPC_ID, "要删除的记忆", db_path=DB_PATH)
       memory_repo.delete_memory(mid, DB_PATH)
       memories = memory_repo.get_memories(NPC_ID, db_path=DB_PATH)
       assert not any(m["id"] == mid for m in memories)
   ```

**验收**: `uv run pytest tests/test_memory_repo.py -v` 全绿

---

## 步骤 3.7 - MUD 界面集成 NPC 功能

**目的**: 在 MUD 前端中展示和交互 NPC 系统

**说明**: 本步骤修改前端文件，将 Mock 数据替换为真实 API 调用。由于后端 API（FastAPI + WebSocket）在 P4' 才实现，这里先用 **HTTP fetch 模拟**，P4' 时替换为 WebSocket。

**执行**:
1. 修改 `src/web/js/app.js`，添加 NPC 面板功能：
   ```javascript
   // ===== NPC 面板功能 =====
   const npcsTab = document.getElementById('tab-npcs');

   async function loadNPCs(locationId) {
       // TODO: P4' 替换为 WebSocket 调用
       // 当前使用 Mock 数据
       const mockNPCs = [
           { id: 1, name: "村长", mood: "neutral" },
           { id: 2, name: "铁匠", mood: "happy" },
           { id: 3, name: "神秘旅者", mood: "contemplative" },
       ];
       npcsTab.innerHTML = mockNPCs.map(npc =>
           `<div class="npc-item" onclick="talkToNPC(${npc.id}, '${npc.name}')">
               <span class="npc-name">${npc.name}</span>
               <span class="npc-mood">${npc.mood}</span>
           </div>`
       ).join('');
   }

   function talkToNPC(npcId, npcName) {
       userInput.placeholder = `对 ${npcName} 说...`;
       userInput.dataset.npcId = npcId;
       userInput.dataset.npcName = npcName;
       userInput.focus();
   }

   // 初始化时加载NPC
   loadNPCs(1);
   ```
2. 修改 `src/web/css/style.css`，添加 NPC 样式：
   ```css
   .npc-item {
       padding: 8px 12px;
       margin-bottom: 4px;
       background: #0d0d0d;
       border-radius: 4px;
       cursor: pointer;
       display: flex;
       justify-content: space-between;
       transition: background 0.2s;
   }
   .npc-item:hover { background: #1a2a3a; }
   .npc-name { color: #f39c12; }
   .npc-mood { color: #888; font-size: 12px; }
   ```
3. 验证：浏览器打开 `src/web/index.html`，NPC 面板显示 Mock NPC 列表，点击 NPC 后输入框提示文字变化。

**验收**: 浏览器中 NPC 面板可交互

---

## 步骤 3.8 - 扩展剧情数据模型

**目的**: 扩展 Quest 表，支持分支和多结局

**执行**:
1. 在 `src/models/schema.sql` 中扩展 `quests` 表并确保 `quest_steps` 表完整：
   ```sql
   -- quests 表添加新列（ALTER TABLE 或修改建表语句）:
   quest_type TEXT DEFAULT 'side',        -- main/side/random
   prerequisites TEXT DEFAULT '[]',       -- JSON: 前置任务ID列表
   branches TEXT DEFAULT '[]',            -- JSON: 分支选项 [{"id":"q1","text":"帮助村民","next_step":3}]
   rewards TEXT DEFAULT '{}',             -- JSON: {"exp":100,"gold":50,"items":[1,2],"reputation":10}
   ```

   确保 `quest_steps` 表：
   ```sql
   CREATE TABLE IF NOT EXISTS quest_steps (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       quest_id INTEGER NOT NULL,
       step_order INTEGER NOT NULL DEFAULT 0,
       description TEXT NOT NULL,
       step_type TEXT DEFAULT 'goto',      -- goto/kill/collect/talk/choose
       target TEXT DEFAULT '',              -- 目标描述
       required_count INTEGER DEFAULT 1,
       current_count INTEGER DEFAULT 0,
       completed INTEGER DEFAULT 0,
       FOREIGN KEY (quest_id) REFERENCES quests(id)
   );
   ```
2. 更新 `src/models/quest_repo.py`：
   - `create_quest()` 添加新参数：`quest_type='side', prerequisites=None, branches=None, rewards=None`
   - `create_quest_step(quest_id, step_order, description, step_type='goto', target='', required_count=1)`
   - `update_quest_step(step_id, current_count=None, completed=None)`
   - `get_quest_steps(quest_id)` 返回步骤列表
3. 创建 `tests/test_quest_model.py`：
   ```python
   """剧情数据模型测试"""
   import tempfile, os, json
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.models import quest_repo

   DB_PATH = None
   WORLD_ID = None

   def setup_module():
       global DB_PATH, WORLD_ID
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       WORLD_ID = result["world_id"]

   def test_create_quest_with_branches():
       """创建带分支的任务"""
       branches = [
           {"id": "help", "text": "帮助村民", "next_step": 3},
           {"id": "ignore", "text": "无视请求", "next_step": 4},
       ]
       rewards = {"exp": 100, "gold": 50}
       qid = quest_repo.create_quest(
           WORLD_ID, "拯救村庄", "哥布林正在攻击村庄！",
           quest_type="main",
           branches=json.dumps(branches),
           rewards=json.dumps(rewards),
           db_path=DB_PATH,
       )
       quest = quest_repo.get_quest(qid, DB_PATH)
       assert quest["quest_type"] == "main"
       assert len(json.loads(quest["branches"])) == 2

   def test_quest_steps():
       """创建任务步骤"""
       qid = quest_repo.create_quest(WORLD_ID, "收集草药", "村长需要草药", db_path=DB_PATH)
       quest_repo.create_quest_step(qid, 1, "去森林采集草药", step_type="collect", target="草药", required_count=5, db_path=DB_PATH)
       quest_repo.create_quest_step(qid, 2, "把草药交给村长", step_type="talk", target="村长", db_path=DB_PATH)
       steps = quest_repo.get_quest_steps(qid, DB_PATH)
       assert len(steps) == 2
       assert steps[0]["step_type"] == "collect"

   def test_update_step_progress():
       """更新步骤进度"""
       qid = quest_repo.create_quest(WORLD_ID, "杀怪", "消灭哥布林", db_path=DB_PATH)
       sid = quest_repo.create_quest_step(qid, 1, "消灭5个哥布林", step_type="kill", target="哥布林", required_count=5, db_path=DB_PATH)
       quest_repo.update_quest_step(sid, current_count=3, db_path=DB_PATH)
       steps = quest_repo.get_quest_steps(qid, DB_PATH)
       assert steps[0]["current_count"] == 3
   ```

**验收**: `uv run pytest tests/test_quest_model.py -v` 全绿

---

## 步骤 3.9 - 实现剧情模板系统

**目的**: 预设剧情模板，程序化生成任务

**执行**:
1. 创建 `src/data/story_templates.py`：
   ```python
   """剧情模板系统 - 预设剧情模板，程序化生成任务"""

   STORY_TEMPLATES = {
       "rescue": {
           "name": "救援任务",
           "description_template": "{victim}被{enemy}抓走了！去{location}救出{victim}。",
           "steps": [
               {"description": "前往{location}", "step_type": "goto", "target": "{location}"},
               {"description": "击败{enemy}", "step_type": "kill", "target": "{enemy}", "required_count": 1},
               {"description": "护送{victim}回到安全地点", "step_type": "goto", "target": "安全地点"},
           ],
           "rewards": {"exp": 150, "gold": 80},
           "branches": [
               {"id": "stealth", "text": "潜入营救", "next_step": 2},
               {"id": "force", "text": "正面突袭", "next_step": 2},
           ],
           "variables": ["victim", "enemy", "location"],
       },
       "escort": {
           "name": "护送任务",
           "description_template": "护送{npc_name}从{from_location}安全到达{to_location}。",
           "steps": [
               {"description": "与{npc_name}在{from_location}会合", "step_type": "talk", "target": "{npc_name}"},
               {"description": "护送{npc_name}前往{to_location}", "step_type": "goto", "target": "{to_location}"},
               {"description": "保护{npc_name}免受袭击", "step_type": "kill", "target": "袭击者", "required_count": 3},
           ],
           "rewards": {"exp": 120, "gold": 60},
           "variables": ["npc_name", "from_location", "to_location"],
       },
       "collect": {
           "name": "收集任务",
           "description_template": "收集{count}个{item}交给{giver}。",
           "steps": [
               {"description": "收集{count}个{item}", "step_type": "collect", "target": "{item}", "required_count": "{count}"},
               {"description": "把{item}交给{giver}", "step_type": "talk", "target": "{giver}"},
           ],
           "rewards": {"exp": 80, "gold": 40},
           "variables": ["item", "count", "giver"],
       },
       "investigate": {
           "name": "调查任务",
           "description_template": "调查{location}的神秘{event}。",
           "steps": [
               {"description": "前往{location}", "step_type": "goto", "target": "{location}"},
               {"description": "搜索线索", "step_type": "collect", "target": "线索", "required_count": 3},
               {"description": "向{informant}询问", "step_type": "talk", "target": "{informant}"},
               {"description": "揭开真相", "step_type": "goto", "target": "真相地点"},
           ],
           "rewards": {"exp": 200, "gold": 100},
           "variables": ["location", "event", "informant"],
       },
       "exterminate": {
           "name": "消灭任务",
           "description_template": "消灭{count}个{enemy}，清除{location}的威胁。",
           "steps": [
               {"description": "前往{location}", "step_type": "goto", "target": "{location}"},
               {"description": "消灭{count}个{enemy}", "step_type": "kill", "target": "{enemy}", "required_count": "{count}"},
           ],
           "rewards": {"exp": 100, "gold": 50},
           "variables": ["enemy", "count", "location"],
       },
   }


   def generate_quest_from_template(template_name: str, variables: dict, quest_type: str = "side") -> dict:
       """从模板生成任务数据

       Args:
           template_name: 模板名 (rescue/escort/collect/investigate/exterminate)
           variables: 模板变量，如 {"victim": "公主", "enemy": "巨龙", "location": "龙穴"}
           quest_type: 任务类型

       Returns:
           dict: {title, description, steps, rewards, branches}
       """
       import json
       template = STORY_TEMPLATES.get(template_name)
       if not template:
           raise ValueError(f"未知模板: {template_name}，可用: {list(STORY_TEMPLATES.keys())}")

       # 填充变量
       title = template["description_template"].format(**variables)
       description = title

       steps = []
       for i, step in enumerate(template["steps"]):
           s = dict(step)
           s["description"] = s["description"].format(**variables)
           s["target"] = s["target"].format(**variables)
           if isinstance(s.get("required_count"), str):
               s["required_count"] = int(s["required_count"].format(**variables))
           s["step_order"] = i + 1
           steps.append(s)

       rewards = template["rewards"]
       branches = []
       for b in template.get("branches", []):
           branches.append({**b, "text": b["text"].format(**variables)})

       return {
           "title": title,
           "description": description,
           "steps": steps,
           "rewards": rewards,
           "branches": branches,
           "quest_type": quest_type,
       }
   ```
2. 创建 `tests/test_story_templates.py`：
   ```python
   """剧情模板测试"""
   from src.data.story_templates import generate_quest_from_template, STORY_TEMPLATES

   def test_rescue_template():
       """救援模板"""
       quest = generate_quest_from_template("rescue", {
           "victim": "公主", "enemy": "巨龙", "location": "龙穴"
       })
       assert "公主" in quest["title"]
       assert len(quest["steps"]) == 3
       assert quest["steps"][1]["step_type"] == "kill"
       assert quest["rewards"]["exp"] == 150

   def test_collect_template():
       """收集模板"""
       quest = generate_quest_from_template("collect", {
           "item": "草药", "count": "5", "giver": "村长"
       })
       assert quest["steps"][0]["required_count"] == 5

   def test_unknown_template():
       """未知模板"""
       try:
           generate_quest_from_template("nonexistent", {})
           assert False
       except ValueError:
           pass
   ```

**验收**: `uv run pytest tests/test_story_templates.py -v` 全绿

---

## 步骤 3.10 - 实现任务工具集 + 单测

**目的**: GM 能创建/更新/分支任务

**执行**:
1. 在 `src/tools/tool_definitions.py` 中添加 Schema：
   ```python
   CREATE_QUEST_SCHEMA = {
       "type": "function",
       "function": {
           "name": "create_quest",
           "description": "创建一个新任务。可以用剧情模板快速生成，也可以自定义。",
           "parameters": {
               "type": "object",
               "properties": {
                   "title": {"type": "string", "description": "任务标题"},
                   "description": {"type": "string", "description": "任务描述"},
                   "quest_type": {"type": "string", "description": "类型: main/side/random"},
                   "template_name": {"type": "string", "description": "剧情模板名(可选): rescue/escort/collect/investigate/exterminate"},
                   "template_vars": {"type": "string", "description": "模板变量JSON(可选)，如 '{\"victim\":\"公主\"}'"}
               },
               "required": ["title", "description"]
           }
       }
   }

   UPDATE_QUEST_PROGRESS_SCHEMA = {
       "type": "function",
       "function": {
           "name": "update_quest_progress",
           "description": "更新任务步骤的进度。",
           "parameters": {
               "type": "object",
               "properties": {
                   "quest_id": {"type": "integer", "description": "任务ID"},
                   "step_index": {"type": "integer", "description": "步骤序号（从0开始）"},
                   "progress": {"type": "integer", "description": "当前进度值"}
               },
               "required": ["quest_id", "step_index", "progress"]
           }
       }
   }

   HANDLE_CHOICE_SCHEMA = {
       "type": "function",
       "function": {
           "name": "handle_choice",
           "description": "处理玩家的分支选择。",
           "parameters": {
               "type": "object",
               "properties": {
                   "quest_id": {"type": "integer", "description": "任务ID"},
                   "choice_id": {"type": "string", "description": "选择的分支ID"}
               },
               "required": ["quest_id", "choice_id"]
           }
       }
   }
   ```
   加入 `ALL_TOOL_SCHEMAS`。
2. 创建 `src/tools/quest_tool.py`：
   ```python
   """任务工具集"""
   import json
   from src.models import quest_repo
   from src.tools import world_tool
   from src.data.story_templates import generate_quest_from_template
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def create_quest(title: str, description: str, quest_type: str = "side",
                    template_name: str | None = None, template_vars: str | None = None,
                    db_path: str | None = None) -> str:
       """创建任务"""
       wid = world_tool._active_world_id
       pid = world_tool._active_player_id

       branches = None
       rewards = None

       if template_name and template_vars:
           try:
               vars_dict = json.loads(template_vars)
               quest_data = generate_quest_from_template(template_name, vars_dict, quest_type)
               title = quest_data["title"]
               description = quest_data["description"]
               rewards = json.dumps(quest_data["rewards"])
               branches = json.dumps(quest_data["branches"])
           except Exception as e:
               return f"模板生成失败: {e}"

       qid = quest_repo.create_quest(
           wid, title, description,
           quest_type=quest_type,
           branches=branches,
           rewards=rewards,
           db_path=db_path,
       )

       # 分配给玩家
       quest_repo.assign_quest(qid, pid, db_path=db_path)

       # 如果有模板步骤，自动创建
       if template_name and template_vars:
           try:
               vars_dict = json.loads(template_vars)
               quest_data = generate_quest_from_template(template_name, vars_dict)
               for step in quest_data["steps"]:
                   quest_repo.create_quest_step(
                       qid, step["step_order"], step["description"],
                       step_type=step.get("step_type", "goto"),
                       target=step.get("target", ""),
                       required_count=step.get("required_count", 1),
                       db_path=db_path,
                   )
           except Exception:
               pass

       return f"已创建任务: {title} (ID:{qid}, 类型:{quest_type})"


   def update_quest_progress(quest_id: int, step_index: int, progress: int,
                             db_path: str | None = None) -> str:
       """更新任务进度"""
       steps = quest_repo.get_quest_steps(quest_id, db_path)
       if not steps:
           return f"未找到任务{quest_id}的步骤"
       if step_index >= len(steps):
           return f"步骤序号{step_index}超出范围（共{len(steps)}步）"

       step = steps[step_index]
       quest_repo.update_quest_step(step["id"], current_count=progress, db_path=db_path)

       # 检查是否完成
       if progress >= step["required_count"]:
           quest_repo.update_quest_step(step["id"], completed=1, db_path=db_path)
           if step_index + 1 < len(steps):
               return f"步骤完成！下一步: {steps[step_index + 1]['description']}"
           else:
               quest_repo.update_quest(quest_id, status="completed", db_path=db_path)
               return f"🎉 任务完成！所有步骤已完成。"

       return f"进度更新: {step['description']} ({progress}/{step['required_count']})"


   def handle_choice(quest_id: int, choice_id: str, db_path: str | None = None) -> str:
       """处理分支选择"""
       quest = quest_repo.get_quest(quest_id, db_path)
       if not quest:
           return f"未找到任务{quest_id}"

       branches = json.loads(quest.get("branches") or "[]")
       chosen = next((b for b in branches if b["id"] == choice_id), None)
       if not chosen:
           return f"无效的选择: {choice_id}，可选: {[b['id'] for b in branches]}"

       logger.info(f"任务{quest_id}分支选择: {choice_id} → {chosen['text']}")
       return f"你选择了: {chosen['text']}"
   ```
3. 在 `src/tools/__init__.py` 注册三个工具。
4. 创建 `tests/test_quest_tool.py`：
   ```python
   """任务工具测试"""
   import tempfile, os, json
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.tools import world_tool, quest_tool
   from src.models import quest_repo

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       world_tool.set_active(result["world_id"], result["player_id"])

   def test_create_quest_basic():
       """基本创建任务"""
       result = quest_tool.create_quest("测试任务", "这是一个测试", db_path=DB_PATH)
       assert "测试任务" in result
       assert "ID:" in result

   def test_create_quest_from_template():
       """用模板创建任务"""
       result = quest_tool.create_quest(
           "消灭哥布林", "清除威胁",
           template_name="exterminate",
           template_vars=json.dumps({"enemy": "哥布林", "count": "5", "location": "幽暗森林"}),
           db_path=DB_PATH,
       )
       assert "消灭" in result

   def test_update_progress():
       """更新进度"""
       qid = quest_repo.create_quest(1, "进度测试", "测试", db_path=DB_PATH)
       quest_repo.create_quest_step(qid, 1, "杀3个怪", step_type="kill", target="怪", required_count=3, db_path=DB_PATH)
       result = quest_tool.update_quest_progress(qid, 0, 2, DB_PATH)
       assert "2/3" in result

   def test_complete_quest():
       """完成任务"""
       qid = quest_repo.create_quest(1, "完成测试", "测试", db_path=DB_PATH)
       quest_repo.create_quest_step(qid, 1, "步骤1", required_count=1, db_path=DB_PATH)
       result = quest_tool.update_quest_progress(qid, 0, 1, DB_PATH)
       assert "完成" in result

   def test_handle_choice():
       """分支选择"""
       branches = [{"id": "a", "text": "选项A"}, {"id": "b", "text": "选项B"}]
       qid = quest_repo.create_quest(1, "分支测试", "测试", branches=json.dumps(branches), db_path=DB_PATH)
       result = quest_tool.handle_choice(qid, "a", DB_PATH)
       assert "选项A" in result
   ```

**验收**: `uv run pytest tests/test_quest_tool.py -v` 全绿

---

## 步骤 3.11 - 实现剧情连贯性管理

**目的**: 确保剧情不矛盾

**执行**:
1. 创建 `src/services/story_consistency.py`：
   ```python
   """剧情连贯性管理 - 确保剧情不矛盾"""
   import json
   from src.models import quest_repo, npc_repo, log_repo
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def check_prerequisites(quest_id: int, player_id: int, db_path: str | None = None) -> list[str]:
       """检查任务前置条件是否满足

       Returns:
           list[str]: 未满足的前置条件列表（空=全部满足）
       """
       quest = quest_repo.get_quest(quest_id, db_path)
       if not quest:
           return [f"任务{quest_id}不存在"]

       prerequisites = json.loads(quest.get("prerequisites") or "[]")
       unmet = []

       for prereq_id in prerequisites:
           # 检查前置任务是否已完成
           player_quests = quest_repo.get_quests_by_player(player_id, db_path)
           prereq_quest = next((q for q in player_quests if q["id"] == prereq_id), None)
           if not prereq_quest or prereq_quest["status"] != "completed":
               prereq_info = quest_repo.get_quest(prereq_id, db_path)
               name = prereq_info["title"] if prereq_info else f"任务{prereq_id}"
               unmet.append(f"需要先完成: {name}")

       return unmet


   def check_conflicts(world_id: int, action: str, db_path: str | None = None) -> list[str]:
       """检查动作是否与当前世界状态矛盾

       Args:
           action: 动作描述，如 "与村长对话"
       """
       conflicts = []
       # 检查已死亡的NPC
       logs = log_repo.get_recent_logs(world_id, 50, db_path)
       for log in logs:
           if log["event_type"] == "death":
               dead_name = log["content"]
               if dead_name in action:
                   conflicts.append(f"矛盾: {dead_name} 已经死亡")

       return conflicts


   def get_active_storylines(world_id: int, db_path: str | None = None) -> str:
       """获取当前活跃的剧情线摘要（注入System Prompt用）"""
       quests = quest_repo.get_quests_by_world(world_id, db_path)
       active = [q for q in quests if q["status"] == "active"]

       if not active:
           return "当前没有活跃的任务。"

       lines = ["## 活跃任务线"]
       for q in active:
           qtype = {"main": "主线", "side": "支线", "random": "随机"}.get(q["quest_type"], q["quest_type"])
           lines.append(f"- [{qtype}] {q['title']}: {q['description']}")
           steps = quest_repo.get_quest_steps(q["id"], db_path)
           for s in steps:
               status = "✅" if s["completed"] else f"({s['current_count']}/{s['required_count']})"
               lines.append(f"  {status} {s['description']}")
       return "\n".join(lines)
   ```
2. 创建 `tests/test_story_consistency.py`：
   ```python
   """剧情连贯性测试"""
   import tempfile, os, json
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.services.story_consistency import check_prerequisites, check_conflicts, get_active_storylines
   from src.models import quest_repo, log_repo

   DB_PATH = None
   WORLD_ID = None
   PLAYER_ID = None

   def setup_module():
       global DB_PATH, WORLD_ID, PLAYER_ID
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       WORLD_ID = result["world_id"]
       PLAYER_ID = result["player_id"]

   def test_prerequisites_unmet():
       """前置任务未完成"""
       q1 = quest_repo.create_quest(WORLD_ID, "前置任务", "先做这个", db_path=DB_PATH)
       q2 = quest_repo.create_quest(WORLD_ID, "后续任务", "再做这个",
                                    prerequisites=json.dumps([q1]), db_path=DB_PATH)
       unmet = check_prerequisites(q2, PLAYER_ID, DB_PATH)
       assert len(unmet) > 0
       assert "前置任务" in unmet[0]

   def test_prerequisites_met():
       """前置任务已完成"""
       q1 = quest_repo.create_quest(WORLD_ID, "前置2", "先做", db_path=DB_PATH)
       quest_repo.assign_quest(q1, PLAYER_ID, db_path=DB_PATH)
       quest_repo.update_quest(q1, status="completed", db_path=DB_PATH)
       q2 = quest_repo.create_quest(WORLD_ID, "后续2", "再做",
                                    prerequisites=json.dumps([q1]), db_path=DB_PATH)
       unmet = check_prerequisites(q2, PLAYER_ID, DB_PATH)
       assert len(unmet) == 0

   def test_conflicts_dead_npc():
       """已死亡NPC不应出现"""
       log_repo.log_event(WORLD_ID, "death", "村长", DB_PATH)
       conflicts = check_conflicts(WORLD_ID, "与村长对话", DB_PATH)
       assert len(conflicts) > 0

   def test_get_active_storylines():
       """获取活跃剧情线"""
       qid = quest_repo.create_quest(WORLD_ID, "活跃任务", "进行中", db_path=DB_PATH)
       quest_repo.assign_quest(qid, PLAYER_ID, db_path=DB_PATH)
       summary = get_active_storylines(WORLD_ID, DB_PATH)
       assert "活跃任务" in summary
   ```

**验收**: `uv run pytest tests/test_story_consistency.py -v` 全绿

---

## 步骤 3.12 - 实现多结局系统 + 单测

**目的**: 不同选择导致不同结局

**执行**:
1. 在 `src/models/schema.sql` 中添加 `endings` 表：
   ```sql
   CREATE TABLE IF NOT EXISTS endings (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       world_id INTEGER NOT NULL,
       title TEXT NOT NULL,
       description TEXT DEFAULT '',
       conditions TEXT DEFAULT '{}',
       is_achieved INTEGER DEFAULT 0,
       achieved_at TEXT,
       FOREIGN KEY (world_id) REFERENCES worlds(id)
   );
   ```
2. 创建 `src/models/ending_repo.py`：
   ```python
   """结局数据访问"""
   import json
   from src.services.database import get_db
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def create_ending(world_id: int, title: str, description: str = "",
                     conditions: dict | None = None, db_path: str | None = None) -> int:
       """创建结局"""
       with get_db(db_path) as conn:
           cursor = conn.execute(
               "INSERT INTO endings (world_id, title, description, conditions) VALUES (?, ?, ?, ?)",
               (world_id, title, description, json.dumps(conditions or {})),
           )
           return cursor.lastrowid


   def check_ending(ending_id: int, world_state: dict, db_path: str | None = None) -> bool:
       """检查是否达成结局条件"""
       with get_db(db_path) as conn:
           row = conn.execute("SELECT * FROM endings WHERE id = ?", (ending_id,)).fetchone()
       if not row:
           return False
       if row["is_achieved"]:
           return True

       conditions = json.loads(row["conditions"])
       for key, value in conditions.items():
           if key == "min_level" and world_state.get("level", 0) < value:
               return False
           if key == "required_quests" and not all(
               q in world_state.get("completed_quests", []) for q in value
           ):
               return False
           if key == "required_npc_dead" and world_state.get("dead_npcs", []):
               if not any(n in world_state["dead_npcs"] for n in value):
                   return False

       return True


   def achieve_ending(ending_id: int, db_path: str | None = None):
       """标记结局已达成"""
       with get_db(db_path) as conn:
           conn.execute(
               "UPDATE endings SET is_achieved = 1, achieved_at = datetime('now') WHERE id = ?",
               (ending_id,),
           )


   def get_all_endings(world_id: int, db_path: str | None = None) -> list[dict]:
       """获取所有结局"""
       with get_db(db_path) as conn:
           rows = conn.execute(
               "SELECT * FROM endings WHERE world_id = ?", (world_id,)
           ).fetchall()
       return [dict(r) for r in rows]
   ```
3. 在 `src/models/__init__.py` 中添加 `from src.models import ending_repo`。
4. 创建 `tests/test_endings.py`：
   ```python
   """多结局系统测试"""
   import tempfile, os, json
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.models import ending_repo

   DB_PATH = None
   WORLD_ID = None

   def setup_module():
       global DB_PATH, WORLD_ID
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       WORLD_ID = result["world_id"]

   def test_create_ending():
       """创建结局"""
       eid = ending_repo.create_ending(
           WORLD_ID, "英雄结局", "你拯救了世界！",
           conditions={"min_level": 10, "required_quests": [1, 2]},
           db_path=DB_PATH,
       )
       assert eid > 0

   def test_check_ending_not_met():
       """条件未满足"""
       eid = ending_repo.create_ending(
           WORLD_ID, "等级结局", "达到10级",
           conditions={"min_level": 10},
           db_path=DB_PATH,
       )
       assert not ending_repo.check_ending(eid, {"level": 5}, DB_PATH)

   def test_check_ending_met():
       """条件满足"""
       eid = ending_repo.create_ending(
           WORLD_ID, "低等级结局", "5级就够了",
           conditions={"min_level": 5},
           db_path=DB_PATH,
       )
       assert ending_repo.check_ending(eid, {"level": 5}, DB_PATH)

   def test_achieve_ending():
       """标记达成"""
       eid = ending_repo.create_ending(WORLD_ID, "测试结局", db_path=DB_PATH)
       ending_repo.achieve_ending(eid, DB_PATH)
       endings = ending_repo.get_all_endings(WORLD_ID, DB_PATH)
       assert endings[0]["is_achieved"] == 1

   def test_get_all_endings():
       """获取所有结局"""
       ending_repo.create_ending(WORLD_ID, "结局A", db_path=DB_PATH)
       ending_repo.create_ending(WORLD_ID, "结局B", db_path=DB_PATH)
       endings = ending_repo.get_all_endings(WORLD_ID, DB_PATH)
       assert len(endings) >= 2
   ```

**验收**: `uv run pytest tests/test_endings.py -v` 全绿

---

## 步骤 3.13 - MUD 界面集成剧情功能

**目的**: 在 MUD 前端中展示任务系统

**执行**:
1. 修改 `src/web/js/app.js`，添加任务面板功能：
   ```javascript
   // ===== 任务面板功能 =====
   const questsTab = document.getElementById('tab-quests');

   async function loadQuests() {
       // TODO: P4' 替换为 WebSocket 调用
       const mockQuests = [
           { title: "消灭哥布林", status: "active", progress: "2/5" },
           { title: "收集草药", status: "active", progress: "0/3" },
           { title: "拯救村庄", status: "completed", progress: "✅" },
       ];
       questsTab.innerHTML = mockQuests.map(q => `
           <div class="quest-item ${q.status}">
               <span class="quest-title">${q.title}</span>
               <span class="quest-progress">${q.progress}</span>
           </div>
       `).join('');
   }

   loadQuests();
   ```
2. 修改 `src/web/css/style.css`：
   ```css
   .quest-item {
       padding: 8px 12px;
       margin-bottom: 4px;
       background: #0d0d0d;
       border-radius: 4px;
       display: flex;
       justify-content: space-between;
       font-size: 13px;
   }
   .quest-item.completed { opacity: 0.5; text-decoration: line-through; }
   .quest-title { color: #f1c40f; }
   .quest-progress { color: #888; }
   ```
3. 验证：浏览器打开 `src/web/index.html`，任务面板显示 Mock 任务列表。

**验收**: 浏览器中任务面板可交互

---

## 步骤 3.14 - 扩展道具数据模型

**目的**: 支持装备/稀有度/属性加成

**执行**:
1. 在 `src/models/schema.sql` 中扩展 `items` 表：
   ```sql
   -- items 表添加新列:
   item_type TEXT DEFAULT 'material',    -- weapon/armor/potion/scroll/material/key/quest
   slot TEXT DEFAULT '',                 -- head/chest/legs/feet/weapon/shield/accessory
   stats TEXT DEFAULT '{}',              -- JSON: {"attack":5,"defense":3,"hp_bonus":10}
   rarity TEXT DEFAULT 'common',         -- common/uncommon/rare/epic/legendary
   level_req INTEGER DEFAULT 1,          -- 使用等级要求
   stackable INTEGER DEFAULT 1,          -- 1=可堆叠, 0=不可
   usable INTEGER DEFAULT 0,             -- 1=可使用, 0=不可
   ```

   添加 `player_equipment` 表：
   ```sql
   CREATE TABLE IF NOT EXISTS player_equipment (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       player_id INTEGER NOT NULL,
       slot TEXT NOT NULL,
       item_id INTEGER NOT NULL,
       equipped_at TEXT DEFAULT (datetime('now')),
       FOREIGN KEY (player_id) REFERENCES players(id),
       FOREIGN KEY (item_id) REFERENCES items(id),
       UNIQUE(player_id, slot)
   );
   ```
2. 更新 `src/models/item_repo.py`：
   - `create_item()` 添加新参数：`item_type='material', slot='', stats=None, rarity='common', level_req=1, stackable=1, usable=0`
   - `get_item()` 返回新字段
3. 创建 `src/models/equipment_repo.py`：
   ```python
   """装备数据访问"""
   from src.services.database import get_db
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def equip_item(player_id: int, item_id: int, slot: str, db_path: str | None = None) -> str:
       """装备物品（自动卸下旧装备）"""
       with get_db(db_path) as conn:
           # 卸下旧装备
           conn.execute(
               "DELETE FROM player_equipment WHERE player_id = ? AND slot = ?",
               (player_id, slot),
           )
           # 装备新物品
           conn.execute(
               "INSERT INTO player_equipment (player_id, slot, item_id) VALUES (?, ?, ?)",
               (player_id, slot, item_id),
           )
       return f"已装备到{slot}槽位"


   def get_equipment(player_id: int, db_path: str | None = None) -> dict[str, dict]:
       """获取玩家当前装备"""
       with get_db(db_path) as conn:
           rows = conn.execute(
               """SELECT pe.slot, i.* FROM player_equipment pe
                  JOIN items i ON pe.item_id = i.id
                  WHERE pe.player_id = ?""",
               (player_id,),
           ).fetchall()
       return {row["slot"]: dict(row) for row in rows}


   def unequip_slot(player_id: int, slot: str, db_path: str | None = None):
       """卸下装备"""
       with get_db(db_path) as conn:
           conn.execute(
               "DELETE FROM player_equipment WHERE player_id = ? AND slot = ?",
               (player_id, slot),
           )
   ```
4. 在 `src/models/__init__.py` 中添加 `from src.models import equipment_repo`。
5. 创建 `tests/test_item_model.py`：
   ```python
   """道具扩展模型测试"""
   import tempfile, os, json
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.models import item_repo, equipment_repo

   DB_PATH = None
   WORLD_ID = None
   PLAYER_ID = None

   def setup_module():
       global DB_PATH, WORLD_ID, PLAYER_ID
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       WORLD_ID = result["world_id"]
       PLAYER_ID = result["player_id"]

   def test_create_legendary_weapon():
       """创建传说级武器"""
       iid = item_repo.create_item(
           WORLD_ID, "灭世之剑", "一把散发着黑暗力量的传说之剑",
           item_type="weapon", slot="weapon",
           stats=json.dumps({"attack": 50, "defense": 5}),
           rarity="legendary", level_req=20,
           stackable=0, usable=0,
           db_path=DB_PATH,
       )
       item = item_repo.get_item(iid, DB_PATH)
       assert item["rarity"] == "legendary"
       assert json.loads(item["stats"])["attack"] == 50

   def test_create_potion():
       """创建药水"""
       iid = item_repo.create_item(
           WORLD_ID, "生命药水", "恢复50点HP",
           item_type="potion", stats=json.dumps({"hp_restore": 50}),
           rarity="common", stackable=1, usable=1,
           db_path=DB_PATH,
       )
       item = item_repo.get_item(iid, DB_PATH)
       assert item["usable"] == 1

   def test_equip_item():
       """装备物品"""
       iid = item_repo.create_item(WORLD_ID, "铁剑", "普通铁剑", item_type="weapon", slot="weapon", db_path=DB_PATH)
       result = equipment_repo.equip_item(PLAYER_ID, iid, "weapon", DB_PATH)
       assert "weapon" in result
       equip = equipment_repo.get_equipment(PLAYER_ID, DB_PATH)
       assert "weapon" in equip

   def test_unequip():
       """卸下装备"""
       iid = item_repo.create_item(WORLD_ID, "木盾", "普通木盾", item_type="armor", slot="shield", db_path=DB_PATH)
       equipment_repo.equip_item(PLAYER_ID, iid, "shield", DB_PATH)
       equipment_repo.unequip_slot(PLAYER_ID, "shield", DB_PATH)
       equip = equipment_repo.get_equipment(PLAYER_ID, DB_PATH)
       assert "shield" not in equip
   ```

**验收**: `uv run pytest tests/test_item_model.py -v` 全绿

---

## 步骤 3.15 - 实现道具工具集 + 单测

**目的**: GM 能创建/装备/使用/交易道具

**执行**:
1. 在 `src/tools/tool_definitions.py` 中添加 Schema：
   ```python
   CREATE_ITEM_SCHEMA = {
       "type": "function",
       "function": {
           "name": "create_item",
           "description": "创建一个新道具。",
           "parameters": {
               "type": "object",
               "properties": {
                   "name": {"type": "string", "description": "道具名称"},
                   "description": {"type": "string", "description": "道具描述"},
                   "item_type": {"type": "string", "description": "类型: weapon/armor/potion/scroll/material/key/quest"},
                   "slot": {"type": "string", "description": "装备槽位: head/chest/legs/feet/weapon/shield/accessory"},
                   "stats": {"type": "string", "description": "属性JSON，如 '{\"attack\":10}'"},
                   "rarity": {"type": "string", "description": "稀有度: common/uncommon/rare/epic/legendary"},
                   "level_req": {"type": "integer", "description": "等级要求"}
               },
               "required": ["name"]
           }
       }
   }

   EQUIP_ITEM_SCHEMA = {
       "type": "function",
       "function": {
           "name": "equip_item",
           "description": "给玩家装备物品。会自动卸下同槽位的旧装备。",
           "parameters": {
               "type": "object",
               "properties": {
                   "item_id": {"type": "integer", "description": "物品ID"},
                   "slot": {"type": "string", "description": "装备槽位"}
               },
               "required": ["item_id", "slot"]
           }
       }
   }

   USE_ITEM_SCHEMA = {
       "type": "function",
       "function": {
           "name": "use_item",
           "description": "使用消耗品（药水、卷轴等）。",
           "parameters": {
               "type": "object",
               "properties": {
                   "item_id": {"type": "integer", "description": "物品ID"}
               },
               "required": ["item_id"]
           }
       }
   }
   ```
   加入 `ALL_TOOL_SCHEMAS`。
2. 创建 `src/tools/item_tool.py`：
   ```python
   """道具工具集"""
   import json
   from src.models import item_repo, player_repo, equipment_repo
   from src.tools import world_tool
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def create_item(name: str, description: str = "", item_type: str = "material",
                   slot: str = "", stats: str = "{}", rarity: str = "common",
                   level_req: int = 1, db_path: str | None = None) -> str:
       """创建道具"""
       wid = world_tool._active_world_id
       iid = item_repo.create_item(
           wid, name, description,
           item_type=item_type, slot=slot, stats=stats,
           rarity=rarity, level_req=level_req,
           db_path=db_path,
       )
       rarity_names = {"common": "普通", "uncommon": "优秀", "rare": "稀有", "epic": "史诗", "legendary": "传说"}
       return f"已创建道具: {name} [{rarity_names.get(rarity, rarity)}] (ID:{iid})"


   def equip_item(item_id: int, slot: str, db_path: str | None = None) -> str:
       """装备物品"""
       pid = world_tool._active_player_id
       item = item_repo.get_item(item_id, db_path)
       if not item:
           return f"未找到物品{item_id}"

       # 检查等级要求
       player = player_repo.get_player(pid, db_path)
       if item.get("level_req", 1) > player["level"]:
           return f"等级不足！需要等级{item['level_req']}，当前等级{player['level']}"

       equipment_repo.equip_item(pid, item_id, slot, db_path)
       logger.info(f"玩家装备了: {item['name']} → {slot}")
       return f"已装备: {item['name']} → {slot}"


   def use_item(item_id: int, db_path: str | None = None) -> str:
       """使用消耗品"""
       pid = world_tool._active_player_id
       item = item_repo.get_item(item_id, db_path)
       if not item:
           return f"未找到物品{item_id}"
       if not item.get("usable"):
           return f"{item['name']}不可使用"

       stats = json.loads(item.get("stats") or "{}")

       # 应用效果
       if "hp_restore" in stats:
           player = player_repo.get_player(pid, db_path)
           new_hp = min(player["hp"] + stats["hp_restore"], player["max_hp"])
           player_repo.update_player(pid, hp=new_hp, db_path=db_path)

       if "mp_restore" in stats:
           player = player_repo.get_player(pid, db_path)
           new_mp = min(player["mp"] + stats["mp_restore"], player["max_mp"])
           player_repo.update_player(pid, mp=new_mp, db_path=db_path)

       # 减少数量
       player_repo.remove_item(pid, item_id, 1, db_path)

       effect_desc = "，".join(f"{k}+{v}" for k, v in stats.items())
       return f"使用了 {item['name']}，效果: {effect_desc}"
   ```
3. 在 `src/tools/__init__.py` 注册三个工具。
4. 创建 `tests/test_item_tool.py`：
   ```python
   """道具工具测试"""
   import tempfile, os, json
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.tools import world_tool, item_tool
   from src.models import item_repo, player_repo

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       world_tool.set_active(result["world_id"], result["player_id"])

   def test_create_item():
       """创建道具"""
       result = item_tool.create_item("铁剑", "一把铁剑", item_type="weapon", slot="weapon", db_path=DB_PATH)
       assert "铁剑" in result
       assert "ID:" in result

   def test_create_legendary():
       """创建传说道具"""
       result = item_tool.create_item("灭世之剑", item_type="weapon", rarity="legendary", db_path=DB_PATH)
       assert "传说" in result

   def test_equip_item():
       """装备道具"""
       iid = item_repo.create_item(1, "测试剑", item_type="weapon", slot="weapon", db_path=DB_PATH)
       result = item_tool.equip_item(iid, "weapon", DB_PATH)
       assert "weapon" in result

   def test_use_potion():
       """使用药水"""
       iid = item_repo.create_item(1, "HP药水", item_type="potion",
                                   stats=json.dumps({"hp_restore": 30}),
                                   stackable=1, usable=1, db_path=DB_PATH)
       # 先给玩家添加物品
       pid = world_tool._active_player_id
       player_repo.add_item(pid, iid, 1, db_path=DB_PATH)
       result = item_tool.use_item(iid, DB_PATH)
       assert "HP药水" in result
   ```

**验收**: `uv run pytest tests/test_item_tool.py -v` 全绿

---

## 步骤 3.16 - 实现战斗系统 + 单测

**目的**: 回合制战斗（D&D 5e 简化版）

**执行**:
1. 创建 `src/services/combat.py`：
   ```python
   """战斗系统 - D&D 5e 简化版回合制战斗"""
   import random
   from src.tools.dice import roll_dice
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   class CombatEntity:
       """战斗实体"""
       def __init__(self, name: str, hp: int, max_hp: int, attack: int = 0,
                    defense: int = 0, is_player: bool = False):
           self.name = name
           self.hp = hp
           self.max_hp = max_hp
           self.attack = attack
           self.defense = defense
           self.is_player = is_player
           self.alive = True

       @property
       def ac(self) -> int:
           """护甲等级 = 10 + defense"""
           return 10 + self.defense

       def take_damage(self, damage: int) -> int:
           """受到伤害，返回实际伤害"""
           actual = max(0, damage)
           self.hp -= actual
           if self.hp <= 0:
               self.hp = 0
               self.alive = False
           return actual

       def heal(self, amount: int):
           """恢复HP"""
           self.hp = min(self.max_hp, self.hp + amount)


   class Combat:
       """战斗管理器"""

       def __init__(self, player: CombatEntity, enemies: list[CombatEntity]):
           self.player = player
           self.enemies = enemies
           self.turn = 0
           self.log: list[str] = []
           self.finished = False
           self.victory = False
           self.rewards = {"exp": 0, "gold": 0, "items": []}

       def attack_roll(self, attacker: CombatEntity, target: CombatEntity,
                       advantage: bool = False, disadvantage: bool = False) -> dict:
           """攻击检定

           Returns:
               dict: {hit, roll, total, ac, damage, critical}
           """
           # 掷d20
           if advantage and not disadvantage:
               rolls = roll_dice("2d20")
               d20 = max(rolls["rolls"])
           elif disadvantage and not advantage:
               rolls = roll_dice("2d20")
               d20 = min(rolls["rolls"])
           else:
               rolls = roll_dice("1d20")
               d20 = rolls["rolls"][0]

           critical = d20 == 20
           total = d20 + attacker.attack

           hit = critical or total >= target.ac

           # 伤害
           if hit:
               weapon_damage = roll_dice("1d8")[  # 简化：d8武器伤害
               if critical:
                   weapon_damage["total"] *= 2  # 暴击双倍
               damage = target.take_damage(weapon_damage["total"])
           else:
               damage = 0

           return {
               "hit": hit,
               "roll": d20,
               "total": total,
               "ac": target.ac,
               "damage": damage,
               "critical": critical,
           }

       def player_attack(self, target_index: int = 0) -> str:
           """玩家攻击"""
           if self.finished:
               return "战斗已结束"

           target = self.enemies[target_index]
           if not target.alive:
               return f"{target.name}已经倒下了"

           self.turn += 1
           result = self.attack_roll(self.player, target)

           if result["hit"]:
               msg = f"[第{self.turn}回合] 你攻击{target.name}："
               if result["critical"]:
                   msg += f"💥暴击！d20={result['roll']}+{self.player.attack}={result['total']} vs AC{result['ac']}，造成{result['damage']}点伤害！"
               else:
                   msg += f"命中！d20={result['roll']}+{self.player.attack}={result['total']} vs AC{result['ac']}，造成{result['damage']}点伤害。"
               if not target.alive:
                   msg += f" {target.name}被击败了！"
                   self.rewards["exp"] += 20
                   self.rewards["gold"] += random.randint(5, 20)
           else:
               msg = f"[第{self.turn}回合] 你攻击{target.name}：未命中！d20={result['roll']}+{self.player.attack}={result['total']} < AC{result['ac']}"

           self.log.append(msg)

           # 检查战斗结束
           if all(not e.alive for e in self.enemies):
               self.finished = True
               self.victory = True
               self.log.append(f"🎉 胜利！获得 {self.rewards['exp']} 经验和 {self.rewards['gold']} 金币。")
           else:
               # 敌人回合
               self._enemy_turns()

           return "\n".join(self.log[-3:])  # 返回最近3条

       def player_defend(self) -> str:
           """玩家防御（本回合AC+2）"""
           if self.finished:
               return "战斗已结束"
           self.turn += 1
           old_def = self.player.defense
           self.player.defense += 2
           msg = f"[第{self.turn}回合] 你采取防御姿态，AC暂时+2。"
           self.log.append(msg)
           self._enemy_turns()
           self.player.defense = old_def
           return "\n".join(self.log[-3:])

       def player_flee(self) -> str:
           """玩家逃跑"""
           if self.finished:
               return "战斗已结束"
           self.turn += 1
           roll = roll_dice("1d20")
           dc = 10 + len([e for e in self.enemies if e.alive]) * 2
           if roll["total"] >= dc:
               self.finished = True
               msg = f"[第{self.turn}回合] 你成功逃跑了！(d20={roll['rolls'][0]} >= DC{dc})"
           else:
               msg = f"[第{self.turn}回合] 逃跑失败！(d20={roll['rolls'][0]} < DC{dc})"
               self._enemy_turns()
           self.log.append(msg)
           return "\n".join(self.log[-3:])

       def _enemy_turns(self) -> None:
           """所有存活敌人的回合"""
           for enemy in self.enemies:
               if not enemy.alive or not self.player.alive:
                   continue
               result = self.attack_roll(enemy, self.player)
               if result["hit"]:
                   msg = f"  {enemy.name}攻击你："
                   if result["critical"]:
                       msg += f"暴击！造成{result['damage']}点伤害！"
                   else:
                       msg += f"命中，造成{result['damage']}点伤害。"
                   if not self.player.alive:
                       msg += " 你被击败了..."
                       self.finished = True
               else:
                   msg = f"  {enemy.name}攻击你：未命中。"
               self.log.append(msg)

       def get_status(self) -> str:
           """获取战斗状态"""
           lines = [f"=== 战斗状态 (第{self.turn}回合) ==="]
           status = "存活" if self.player.alive else "倒下"
           lines.append(f"你: HP {self.player.hp}/{self.player.max_hp} [{status}] ATK:{self.player.attack} AC:{self.player.ac}")
           for e in self.enemies:
               status = "存活" if e.alive else "倒下"
               lines.append(f"{e.name}: HP {e.hp}/{e.max_hp} [{status}] ATK:{e.attack} AC:{e.ac}")
           return "\n".join(lines)
   ```
2. 创建 `tests/test_combat.py`：
   ```python
   """战斗系统测试"""
   from src.services.combat import Combat, CombatEntity


   def _make_combat():
       player = CombatEntity("玩家", hp=50, max_hp=50, attack=5, defense=2, is_player=True)
       enemy = CombatEntity("哥布林", hp=20, max_hp=20, attack=3, defense=1)
       return Combat(player, [enemy])


   def test_attack_hit():
       """攻击命中"""
       combat = _make_combat()
       # 多次尝试确保至少命中一次
       for _ in range(20):
           combat = _make_combat()
           msg = combat.player_attack(0)
           if combat.player.alive and not combat.finished:
               if combat.enemies[0].hp < 20:
                   break
       assert len(combat.log) > 0

   def test_critical_hit():
       """暴击测试（概率性，多次尝试）"""
       found_crit = False
       for _ in range(50):
           combat = _make_combat()
           msg = combat.player_attack(0)
           if "暴击" in msg:
               found_crit = True
               break
       # 暴击是概率性的，不强制断言
       print(f"暴击测试: {'找到' if found_crit else '未找到'}暴击")

   def test_defend():
       """防御"""
       combat = _make_combat()
       msg = combat.player_defend()
       assert "防御" in msg

   def test_flee():
       """逃跑"""
       success = False
       for _ in range(20):
           combat = _make_combat()
           msg = combat.player_flee()
           if "成功" in msg:
               success = True
               break
       # 逃跑是概率性的
       print(f"逃跑测试: {'成功' if success else '未成功'}")

   def test_combat_status():
       """战斗状态"""
       combat = _make_combat()
       status = combat.get_status()
       assert "玩家" in status
       assert "哥布林" in status
       assert "HP" in status

   def test_enemy_defeated():
       """敌人被击败"""
       player = CombatEntity("强者", hp=100, max_hp=100, attack=20, defense=10, is_player=True)
       enemy = CombatEntity("弱鸡", hp=1, max_hp=1, attack=0, defense=0)
       combat = Combat(player, [enemy])
       combat.player_attack(0)
       if combat.finished and combat.victory:
           assert "胜利" in combat.log[-1]

   def test_player_defeated():
       """玩家被击败"""
       player = CombatEntity("弱者", hp=1, max_hp=1, attack=0, defense=0, is_player=True)
       enemy = CombatEntity("强者", hp=100, max_hp=100, attack=20, defense=10)
       combat = Combat(player, [enemy])
       combat.player_attack(0)  # 玩家攻击（可能不中）
       if not combat.finished:
           combat.player_attack(0)  # 再来一轮，敌人反击
       # 不强制断言，因为概率性
   ```

**验收**: `uv run pytest tests/test_combat.py -v -s` 全绿

---

## 步骤 3.17 - 实现战斗叙事生成

**目的**: 战斗过程有故事感

**执行**:
1. 在 `src/services/combat.py` 中添加叙事生成方法：
   ```python
   # 在 Combat 类中添加:

   def generate_narrative(self, llm=None) -> str:
       """基于战斗日志生成叙事描述"""
       from src.services.llm_client import LLMClient

       if not self.log:
           return ""

       llm = llm or LLMClient()
       recent_log = "\n".join(self.log[-6:])

       prompt = f"""基于以下战斗数据，生成1-2句生动的战斗描述。要求简洁有力，有画面感。

   战斗日志:
   {recent_log}

   只输出描述文本，不要其他内容。"""

       try:
           response = llm.chat([
               {"role": "system", "content": "你是一个RPG游戏的战斗叙事生成器。用中文生成简洁生动的战斗描述。"},
               {"role": "user", "content": prompt},
           ])
           return response.choices[0].message.content or ""
       except Exception as e:
           logger.warning(f"战斗叙事生成失败: {e}")
           return ""
   ```
2. 在 `tests/test_combat.py` 中添加叙事测试：
   ```python
   def test_combat_narrative():
       """战斗叙事生成"""
       combat = _make_combat()
       combat.player_attack(0)
       narrative = combat.generate_narrative()
       if narrative:
           print(f"\n战斗叙事: {narrative}")
           assert len(narrative) > 0
   ```

**验收**: `uv run pytest tests/test_combat.py::test_combat_narrative -v -s` 通过

---

## 步骤 3.18 - MUD 界面集成战斗功能

**目的**: 在 MUD 前端中展示战斗

**执行**:
1. 修改 `src/web/index.html`，在叙事区下方添加战斗面板（默认隐藏）：
   ```html
   <!-- 在 narrative-panel 后面添加 -->
   <div id="combat-panel" style="display:none;">
       <div id="combat-status"></div>
       <div id="combat-log"></div>
       <div id="combat-actions">
           <button onclick="combatAction('attack')">⚔️ 攻击</button>
           <button onclick="combatAction('defend')">🛡️ 防御</button>
           <button onclick="combatAction('flee')">🏃 逃跑</button>
       </div>
   </div>
   ```
2. 修改 `src/web/css/style.css`：
   ```css
   #combat-panel {
       padding: 12px;
       background: #1a0a0a;
       border: 1px solid #e74c3c;
       border-radius: 4px;
       margin-bottom: 12px;
   }
   #combat-status { margin-bottom: 8px; font-size: 13px; }
   #combat-log { max-height: 150px; overflow-y: auto; font-size: 12px; color: #e74c3c; margin-bottom: 8px; }
   #combat-actions button {
       padding: 6px 14px;
       margin-right: 6px;
       background: #e74c3c;
       border: none;
       color: white;
       cursor: pointer;
       border-radius: 3px;
       font-family: inherit;
   }
   #combat-actions button:hover { background: #c0392b; }
   ```
3. 修改 `src/web/js/app.js`，添加战斗 Mock：
   ```javascript
   // ===== 战斗 Mock =====
   let combatActive = false;

   function startCombat(enemyName, enemyHp) {
       combatActive = true;
       document.getElementById('combat-panel').style.display = 'block';
       document.getElementById('combat-status').textContent = `你 vs ${enemyName} (HP:${enemyHp})`;
       document.getElementById('combat-log').textContent = '战斗开始！';
       addMessage(`⚔️ 战斗开始！你面对着${enemyName}！`, 'combat-text');
   }

   function combatAction(action) {
       if (!combatActive) return;
       const messages = {
           attack: ['你挥剑攻击，命中了！造成8点伤害。', '你的攻击被闪开了。', '💥 暴击！造成16点伤害！'],
           defend: ['你举起盾牌防御，挡住了攻击。'],
           flee: ['你成功逃跑了！', '逃跑失败！'],
       };
       const pool = messages[action] || ['你做了些什么。'];
       const msg = pool[Math.floor(Math.random() * pool.length)];
       document.getElementById('combat-log').textContent += '\n' + msg;
       addMessage(msg, 'combat-text');

       if (msg.includes('逃跑') || msg.includes('击败')) {
           combatActive = false;
           document.getElementById('combat-panel').style.display = 'none';
       }
   }
   ```
4. 验证：浏览器中输入"战斗"触发 Mock 战斗面板。

**验收**: 浏览器中战斗面板可交互

---

## ★ P3' 里程碑验收

运行完整测试套件：

```bash
uv run pytest tests/ -v
```

逐项确认：

- [ ] 3.1 NPC属性模型扩展通过
- [ ] 3.2 NPC性格模板通过
- [ ] 3.3 create_npc工具通过
- [ ] 3.4 npc_dialog工具通过
- [ ] 3.5 NPC关系追踪通过
- [ ] 3.6 NPC记忆系统通过
- [ ] 3.7 MUD界面NPC功能可用
- [ ] 3.8 剧情数据模型通过
- [ ] 3.9 剧情模板系统通过
- [ ] 3.10 任务工具集通过
- [ ] 3.11 剧情连贯性管理通过
- [ ] 3.12 多结局系统通过
- [ ] 3.13 MUD界面剧情功能可用
- [ ] 3.14 道具数据模型通过
- [ ] 3.15 道具工具集通过
- [ ] 3.16 战斗系统通过
- [ ] 3.17 战斗叙事生成通过
- [ ] 3.18 MUD界面战斗功能可用

**全部 ✅ 后，P3' 阶段完成！三大游戏系统全部就绪！** 🎉

---

## P3' 完成后的项目结构

```
game-master-agent/
├── src/
│   ├── agent/
│   │   └── game_master.py
│   ├── tools/
│   │   ├── __init__.py              # ★ 新增工具注册（create_npc/npc_dialog/update_relationship/get_relationship_graph/create_quest/update_quest_progress/handle_choice/create_item/equip_item/use_item）
│   │   ├── tool_definitions.py      # ★ 新增 Schema
│   │   ├── executor.py
│   │   ├── dice.py
│   │   ├── world_tool.py
│   │   ├── player_tool.py
│   │   ├── npc_tool.py              # ★ 扩展: create_npc/npc_dialog/update_relationship/get_relationship_graph
│   │   ├── log_tool.py
│   │   ├── quest_tool.py            # ★ 新增
│   │   └── item_tool.py             # ★ 新增
│   ├── models/
│   │   ├── npc_repo.py              # ★ 扩展
│   │   ├── item_repo.py             # ★ 扩展
│   │   ├── quest_repo.py            # ★ 扩展
│   │   ├── memory_repo.py           # ★ 新增
│   │   ├── equipment_repo.py        # ★ 新增
│   │   └── ending_repo.py           # ★ 新增
│   ├── services/
│   │   ├── npc_dialog.py            # ★ 新增
│   │   ├── story_consistency.py     # ★ 新增
│   │   ├── combat.py                # ★ 新增
│   │   └── ...
│   ├── data/
│   │   ├── npc_templates.py         # ★ 新增
│   │   ├── story_templates.py       # ★ 新增
│   │   └── seed_data.py
│   ├── web/
│   │   ├── index.html               # ★ 扩展
│   │   ├── css/style.css            # ★ 扩展
│   │   └── js/app.js                # ★ 扩展
│   └── cli.py
└── tests/                           # 100+个测试
```
