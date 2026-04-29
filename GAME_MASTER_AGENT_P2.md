# Game Master Agent - P2' 核心Agent循环

> 本文件是 Trae AI 助手执行 P2' 阶段的指引。P0 + P1' 必须已全部完成。
> **这是整个项目的心脏**——完成后你就能在终端里和 AI GM 对话了。

## 前置条件

执行本阶段前，确认以下成果已就绪：
- [ ] P0 全部完成（17步，7个测试通过）
- [ ] P1' 全部完成（13步，36个测试通过）
- [ ] `uv run pytest tests/ -v` 全部通过（43+个测试）
- [ ] `src/models/schema.sql` 存在（11个表）
- [ ] 7个 Repository 全部可用（world/location/player/npc/item/quest/log）
- [ ] `src/prompts/gm_system.py` 存在（`get_system_prompt()` 可调用）
- [ ] `src/services/llm_client.py` 存在（LLMClient 类可用）
- [ ] `src/services/database.py` 存在（`init_db()` + `get_db()` 可用）
- [ ] `src/data/seed_data.py` 存在（`seed_world()` 可调用）

## 行为准则

1. **一步一步执行**：严格按步骤顺序，每步验证通过后再继续
2. **先验证再继续**：每个步骤都有验收标准
3. **主动执行**：用户说"开始P2'"后，主动执行每一步
4. **遇到错误先尝试解决**：3次失败后再询问用户
5. **每步完成后汇报**：简要汇报结果和下一步
6. **代码规范**：UTF-8、中文注释、PEP 8、每个模块必须有 pytest 测试
7. **不要跳步**

---

## 步骤 2.1 - 定义工具 Schema

**目的**: 定义 GM 可调用的所有基础工具的 OpenAI function calling 格式

**执行**:
1. 创建 `src/tools/tool_definitions.py`：
   ```python
   """GM 工具定义 - OpenAI function calling 格式的工具 Schema"""


   # ========== 骰子工具 ==========
   ROLL_DICE_SCHEMA = {
       "type": "function",
       "function": {
           "name": "roll_dice",
           "description": "掷骰子。支持标准RPG骰子表达式，如 '2d6+3'（掷2个6面骰加3）、'1d20'（掷1个20面骰）、'd100'（掷1个100面骰）。",
           "parameters": {
               "type": "object",
               "properties": {
                   "expression": {
                       "type": "string",
                       "description": "骰子表达式，如 '2d6+3', '1d20', '3d8-1'"
                   }
               },
               "required": ["expression"]
           }
       }
   }

   # ========== 世界状态工具 ==========
   QUERY_WORLD_STATE_SCHEMA = {
       "type": "function",
       "function": {
           "name": "query_world_state",
           "description": "查询当前游戏世界的状态信息。可以查询整体概览，也可以指定查询某个方面（如玩家位置、时间、天气等）。",
           "parameters": {
               "type": "object",
               "properties": {
                   "aspect": {
                       "type": "string",
                       "description": "要查询的方面，可选值: 'overview'(概览), 'player_location'(玩家位置), 'active_quests'(活跃任务)。不指定则返回概览。"
                   }
               },
               "required": []
           }
       }
   }

   UPDATE_WORLD_STATE_SCHEMA = {
       "type": "function",
       "function": {
           "name": "update_world_state",
           "description": "更新游戏世界状态。用于改变玩家位置、时间流逝、天气变化等。",
           "parameters": {
               "type": "object",
               "properties": {
                   "aspect": {
                       "type": "string",
                       "description": "要更新的方面，如 'player_location', 'time', 'weather'"
                   },
                   "value": {
                       "type": "string",
                       "description": "新的值"
                   }
               },
               "required": ["aspect", "value"]
           }
       }
   }

   # ========== 地点工具 ==========
   GET_LOCATION_INFO_SCHEMA = {
       "type": "function",
       "function": {
           "name": "get_location_info",
           "description": "获取某个地点的详细信息，包括描述和可前往的出口方向。",
           "parameters": {
               "type": "object",
               "properties": {
                   "location_id": {
                       "type": "integer",
                       "description": "地点ID"
                   }
               },
               "required": ["location_id"]
           }
       }
   }

   LIST_NPCS_AT_LOCATION_SCHEMA = {
       "type": "function",
       "function": {
           "name": "list_npcs_at_location",
           "description": "列出某个地点中的所有NPC。",
           "parameters": {
               "type": "object",
               "properties": {
                   "location_id": {
                       "type": "integer",
                       "description": "地点ID"
                   }
               },
               "required": ["location_id"]
           }
       }
   }

   # ========== 玩家工具 ==========
   GET_PLAYER_INFO_SCHEMA = {
       "type": "function",
       "function": {
           "name": "get_player_info",
           "description": "获取玩家的完整信息，包括HP、MP、等级、经验值、金币、当前位置等。",
           "parameters": {
               "type": "object",
               "properties": {},
               "required": []
           }
       }
   }

   UPDATE_PLAYER_INFO_SCHEMA = {
       "type": "function",
       "function": {
           "name": "update_player_info",
           "description": "更新玩家属性，如HP、MP、金币、等级、位置等。",
           "parameters": {
               "type": "object",
               "properties": {
                   "hp": {"type": "integer", "description": "设置HP值"},
                   "mp": {"type": "integer", "description": "设置MP值"},
                   "gold": {"type": "integer", "description": "设置金币数量"},
                   "level": {"type": "integer", "description": "设置等级"},
                   "exp": {"type": "integer", "description": "设置经验值"},
                   "location_id": {"type": "integer", "description": "设置当前位置ID"}
               },
               "required": []
           }
       }
   }

   # ========== NPC工具 ==========
   GET_NPC_INFO_SCHEMA = {
       "type": "function",
       "function": {
           "name": "get_npc_info",
           "description": "获取NPC的详细信息，包括名字、性格、背景故事、心情等。",
           "parameters": {
               "type": "object",
               "properties": {
                   "npc_id": {
                       "type": "integer",
                       "description": "NPC的ID"
                   }
               },
               "required": ["npc_id"]
           }
       }
   }

   SEARCH_NPC_SCHEMA = {
       "type": "function",
       "function": {
           "name": "search_npc",
           "description": "按名字模糊搜索NPC。",
           "parameters": {
               "type": "object",
               "properties": {
                   "name": {
                       "type": "string",
                       "description": "NPC名字（支持模糊匹配）"
                   }
               },
               "required": ["name"]
           }
       }
   }

   # ========== 日志工具 ==========
   LOG_EVENT_SCHEMA = {
       "type": "function",
       "function": {
           "name": "log_event",
           "description": "记录游戏事件到日志。用于记录重要事件，如战斗结果、任务完成、重要发现等。",
           "parameters": {
               "type": "object",
               "properties": {
                   "event_type": {
                       "type": "string",
                       "description": "事件类型: dialog(对话), combat(战斗), quest(任务), discovery(发现), system(系统), death(死亡), trade(交易)"
                   },
                   "content": {
                       "type": "string",
                       "description": "事件内容描述"
                   }
               },
               "required": ["event_type", "content"]
           }
       }
   }

   # ========== 所有工具Schema列表 ==========
   ALL_TOOL_SCHEMAS = [
       ROLL_DICE_SCHEMA,
       QUERY_WORLD_STATE_SCHEMA,
       UPDATE_WORLD_STATE_SCHEMA,
       GET_LOCATION_INFO_SCHEMA,
       LIST_NPCS_AT_LOCATION_SCHEMA,
       GET_PLAYER_INFO_SCHEMA,
       UPDATE_PLAYER_INFO_SCHEMA,
       GET_NPC_INFO_SCHEMA,
       SEARCH_NPC_SCHEMA,
       LOG_EVENT_SCHEMA,
   ]
   ```
2. 验证：`uv run python -c "from src.tools.tool_definitions import ALL_TOOL_SCHEMAS; print(f'{len(ALL_TOOL_SCHEMAS)} tools defined'); [print(f'  - {s[\"function\"][\"name\"]}') for s in ALL_TOOL_SCHEMAS]"`

**验收**: 输出 `10 tools defined`，并列出所有工具名

---

## 步骤 2.2 - 实现骰子工具 + 单测

**目的**: 第一个工具，验证工具链路

**执行**:
1. 创建 `src/tools/dice.py`：
   ```python
   """骰子工具 - 支持标准RPG骰子表达式"""
   import re
   import random
   from src.utils.logger import get_logger

   logger = get_logger(__name__)

   # 匹配骰子表达式: 2d6+3, 1d20, d100, 3d8-1
   DICE_PATTERN = re.compile(r'^(\d*)d(\d+)([+-]\d+)?$')


   def roll_dice(expression: str) -> dict:
       """掷骰子

       Args:
           expression: 骰子表达式，如 '2d6+3', '1d20', 'd100', '3d8-1'

       Returns:
           dict: {expression, rolls, modifier, total}

       Raises:
           ValueError: 表达式格式无效
       """
       expression = expression.strip().lower()
       match = DICE_PATTERN.match(expression)

       if not match:
           raise ValueError(f"无效的骰子表达式: '{expression}'。正确格式如: '2d6+3', '1d20', 'd100'")

       count = int(match.group(1)) if match.group(1) else 1
       sides = int(match.group(2))
       modifier_str = match.group(3) or ""
       modifier = int(modifier_str) if modifier_str else 0

       if count < 1 or count > 100:
           raise ValueError(f"骰子数量必须在1-100之间，当前: {count}")
       if sides < 1 or sides > 1000:
           raise ValueError(f"骰子面数必须在1-1000之间，当前: {sides}")

       rolls = [random.randint(1, sides) for _ in range(count)]
       subtotal = sum(rolls)
       total = subtotal + modifier

       result = {
           "expression": expression,
           "rolls": rolls,
           "modifier": modifier,
           "subtotal": subtotal,
           "total": total,
       }

       logger.info(f"掷骰子: {expression} → {rolls} (合计{subtotal}) {'+' if modifier >= 0 else ''}{modifier} = {total}")
       return result
   ```
2. 创建 `tests/test_dice.py`：
   ```python
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
   ```

**验收**: `uv run pytest tests/test_dice.py -v` 全绿（7个测试）

---

## 步骤 2.3 - 实现世界状态工具 + 单测

**目的**: GM 能查看和修改世界状态

**执行**:
0. ★ 先修改 `src/data/seed_data.py`，在 `seed_world()` 末尾添加默认玩家创建：
   ```python
   # 在 seed_world() 函数的 return 之前添加:
   from src.models import player_repo
   player_id = player_repo.create_player(world_id, "冒险者", db_path)
   logger.info(f"创建默认玩家: ID={player_id}")
   return {"world_id": world_id, "player_id": player_id}
   ```
   这确保所有工具测试都有可用的玩家数据。
1. 创建 `src/tools/world_tool.py`：
   ```python
   """世界状态工具 - 查询和更新世界状态"""
   from src.models import world_repo, location_repo, npc_repo, player_repo
   from src.utils.logger import get_logger

   logger = get_logger(__name__)

   # 当前活跃的世界ID和玩家ID（由GameMaster设置）
   _active_world_id = None
   _active_player_id = None


   def set_active(world_id: int, player_id: int):
       """设置当前活跃的世界和玩家"""
       global _active_world_id, _active_player_id
       _active_world_id = world_id
       _active_player_id = player_id


   def query_world_state(aspect: str | None = None, db_path: str | None = None) -> str:
       """查询世界状态

       Args:
           aspect: 查询方面 (overview/player_location/active_quests)
       """
       wid = _active_world_id
       pid = _active_player_id

       if aspect == "player_location":
           player = player_repo.get_player(pid, db_path)
           if player and player["location_id"]:
               loc = location_repo.get_location(player["location_id"], db_path)
               return f"玩家位于: {loc['name']} - {loc['description']}"
           return "玩家位置未知"

       elif aspect == "active_quests":
           from src.models import quest_repo
           quests = quest_repo.get_quests_by_player(pid, db_path)
           active = [q for q in quests if q["status"] == "active"]
           if not active:
               return "当前没有活跃任务"
           lines = [f"- {q['title']}: {q['description']}" for q in active]
           return "活跃任务:\n" + "\n".join(lines)

       else:  # overview
           world = world_repo.get_world(wid, db_path)
           player = player_repo.get_player(pid, db_path)
           lines = [f"世界: {world['name']} ({world['setting']})"]
           if player:
               lines.append(f"玩家: {player['name']} | HP: {player['hp']}/{player['max_hp']} | MP: {player['mp']}/{player['max_mp']} | 等级: {player['level']} | 金币: {player['gold']}")
               if player["location_id"]:
                   loc = location_repo.get_location(player["location_id"], db_path)
                   lines.append(f"位置: {loc['name']}")
           return "\n".join(lines)


   def update_world_state(aspect: str, value: str, db_path: str | None = None) -> str:
       """更新世界状态"""
       pid = _active_player_id

       if aspect == "player_location":
           try:
               loc_id = int(value)
               player_repo.update_player(pid, location_id=loc_id, db_path=db_path)
               loc = location_repo.get_location(loc_id, db_path)
               logger.info(f"玩家移动到: {loc['name']}")
               return f"玩家已移动到: {loc['name']}"
           except (ValueError, Exception) as e:
               return f"移动失败: {e}"
       else:
           return f"暂不支持更新 '{aspect}'"


   def get_location_info(location_id: int, db_path: str | None = None) -> str:
       """获取地点信息"""
       loc = location_repo.get_location(location_id, db_path)
       if not loc:
           return f"未找到ID为{location_id}的地点"
       lines = [f"【{loc['name']}】"]
       lines.append(loc["description"])
       if loc["connections"]:
           exits = []
           for direction, dest_id in loc["connections"].items():
               if dest_id:
                   dest = location_repo.get_location(dest_id, db_path)
                   if dest:
                       exits.append(f"{direction}: {dest['name']}")
           if exits:
               lines.append("出口: " + ", ".join(exits))
       return "\n".join(lines)


   def list_npcs_at_location(location_id: int, db_path: str | None = None) -> str:
       """列出地点中的NPC"""
       npcs = npc_repo.get_npcs_by_location(location_id, db_path)
       if not npcs:
           return "这里没有NPC"
       lines = []
       for npc in npcs:
           mood = npc.get("mood", "neutral")
           lines.append(f"- {npc['name']} (心情: {mood})")
       return "这里的NPC:\n" + "\n".join(lines)
   ```
2. 创建 `tests/test_world_tool.py`：
   ```python
   """世界状态工具测试"""
   import tempfile
   import os
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.tools import world_tool

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       # ★ seed_world 返回的 result 中应包含 player_id
       player_id = result.get("player_id", 1)
       world_tool.set_active(result["world_id"], player_id)

   def test_query_overview():
       result = world_tool.query_world_state("overview", DB_PATH)
       assert "艾泽拉斯" in result
       assert "玩家" in result

   def test_query_player_location():
       result = world_tool.query_world_state("player_location", DB_PATH)
       assert "位于" in result or "未知" in result

   def test_get_location_info():
       result = world_tool.get_location_info(1, DB_PATH)
       assert "【" in result

   def test_list_npcs():
       result = world_tool.list_npcs_at_location(1, DB_PATH)
       assert isinstance(result, str)

   def test_update_player_location():
       result = world_tool.update_world_state("player_location", "1", DB_PATH)
       assert isinstance(result, str)
   ```

**验收**: `uv run pytest tests/test_world_tool.py -v` 全绿

---

## 步骤 2.4 - 实现玩家工具 + 单测

**目的**: GM 能查看和修改玩家状态

**执行**:
1. 创建 `src/tools/player_tool.py`：
   ```python
   """玩家工具 - 查询和更新玩家信息"""
   from src.models import player_repo
   from src.tools import world_tool  # ★ 导入模块而非变量，避免值拷贝问题
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def get_player_info(db_path: str | None = None) -> str:
       """获取玩家完整信息"""
       pid = world_tool._active_player_id  # ★ 通过模块访问，始终获取最新值
       player = player_repo.get_player(pid, db_path)
       if not player:
           return "未找到玩家信息"
       lines = [
           f"【{player['name']}】",
           f"HP: {player['hp']}/{player['max_hp']} | MP: {player['mp']}/{player['max_mp']}",
           f"等级: {player['level']} | 经验: {player['exp']} | 金币: {player['gold']}",
       ]
       inventory = player_repo.get_inventory(pid, db_path)
       if inventory:
           lines.append("背包:")
           for item in inventory:
               qty = f" x{item['quantity']}" if item["quantity"] > 1 else ""
               lines.append(f"  - {item['name']}({item['rarity']}){qty}")
       else:
           lines.append("背包: 空")
       return "\n".join(lines)


   def update_player_info(db_path: str | None = None, **kwargs) -> str:
       """更新玩家属性"""
       pid = world_tool._active_player_id  # ★ 通过模块访问，始终获取最新值
       if not kwargs:
           return "没有指定要更新的属性"
       valid_keys = {"hp", "max_hp", "mp", "max_mp", "level", "exp", "gold", "name", "location_id"}
       updates = {k: v for k, v in kwargs.items() if k in valid_keys}
       if not updates:
           return f"无效的属性名，支持: {', '.join(valid_keys)}"
       player_repo.update_player(pid, db_path=db_path, **updates)
       logger.info(f"更新玩家属性: {updates}")
       return f"玩家属性已更新: {', '.join(f'{k}={v}' for k, v in updates.items())}"
   ```
2. 创建 `tests/test_player_tool.py`：
   ```python
   """玩家工具测试"""
   import tempfile
   import os
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.tools import world_tool, player_tool

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       player_id = result.get("player_id", 1)
       world_tool.set_active(result["world_id"], player_id)

   def test_get_player_info():
       result = player_tool.get_player_info(DB_PATH)
       assert "HP:" in result
       assert "等级:" in result

   def test_update_player_info():
       result = player_tool.update_player_info(DB_PATH, hp=80, gold=100)
       assert "hp=80" in result
       assert "gold=100" in result
       # 验证更新生效
       info = player_tool.get_player_info(DB_PATH)
       assert "80" in info
   ```

**验收**: `uv run pytest tests/test_player_tool.py -v` 全绿

---

## 步骤 2.5 - 实现 NPC 信息工具 + 单测

**目的**: GM 能查询 NPC 信息

**执行**:
1. 创建 `src/tools/npc_tool.py`：
   ```python
   """NPC信息工具"""
   from src.models import npc_repo
   from src.tools.world_tool import _active_world_id
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def get_npc_info(npc_id: int, db_path: str | None = None) -> str:
       """获取NPC详细信息"""
       npc = npc_repo.get_npc(npc_id, db_path)
       if not npc:
           return f"未找到ID为{npc_id}的NPC"
       lines = [
           f"【{npc['name']}】",
           f"心情: {npc.get('mood', 'neutral')}",
       ]
       if npc.get("backstory"):
           lines.append(f"背景: {npc['backstory']}")
       if npc.get("speech_style"):
           lines.append(f"说话风格: {npc['speech_style']}")
       if npc.get("goals"):
           lines.append(f"目标: {npc['goals']}")
       return "\n".join(lines)


   def search_npc(name: str, db_path: str | None = None) -> str:
       """按名字模糊搜索NPC"""
       wid = _active_world_id
       npcs = npc_repo.get_npcs_by_location(None, db_path) if False else []
       # 简单搜索：遍历所有地点的NPC
       from src.models import location_repo
       results = []
       for loc in location_repo.get_locations_by_world(wid, db_path):
           for npc in npc_repo.get_npcs_by_location(loc["id"], db_path):
               if name.lower() in npc["name"].lower():
                   results.append(f"- {npc['name']} (位于{loc['name']}, ID:{npc['id']})")
       if not results:
           return f"未找到名字包含'{name}'的NPC"
       return "搜索结果:\n" + "\n".join(results)
   ```
2. 创建 `tests/test_npc_tool.py`：
   ```python
   """NPC工具测试"""
   import tempfile
   import os
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.tools import world_tool, npc_tool

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       player_id = result.get("player_id", 1)
       world_tool.set_active(result["world_id"], player_id)

   def test_search_npc():
       result = npc_tool.search_npc("村长", DB_PATH)
       assert "村长" in result

   def test_search_npc_not_found():
       result = npc_tool.search_npc("不存在的人", DB_PATH)
       assert "未找到" in result
   ```

**验收**: `uv run pytest tests/test_npc_tool.py -v` 全绿

---

## 步骤 2.6 - 实现日志工具 + 单测

**目的**: GM 能记录游戏事件

**执行**:
1. 创建 `src/tools/log_tool.py`：
   ```python
   """日志工具 - 记录游戏事件"""
   from src.models import log_repo
   from src.tools.world_tool import _active_world_id
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def log_event(event_type: str, content: str, db_path: str | None = None) -> str:
       """记录游戏事件

       Args:
           event_type: dialog/combat/quest/discovery/system/death/trade
           content: 事件内容
       """
       wid = _active_world_id
       log_repo.log_event(wid, event_type, content, db_path)
       logger.info(f"[{event_type}] {content}")
       return f"事件已记录: [{event_type}] {content}"
   ```
2. 创建 `tests/test_log_tool.py`：
   ```python
   """日志工具测试"""
   import tempfile
   import os
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.tools import world_tool, log_tool
   from src.models import log_repo

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       player_id = result.get("player_id", 1)
       world_tool.set_active(result["world_id"], player_id)

   def test_log_event():
       result = log_tool.log_event("system", "测试日志记录", DB_PATH)
       assert "已记录" in result
       logs = log_repo.get_recent_logs(result["world_id"] if isinstance(result, dict) else 1, 10, DB_PATH)
       assert any("测试日志记录" in log["content"] for log in logs)
   ```

**验收**: `uv run pytest tests/test_log_tool.py -v` 全绿

---

## 步骤 2.7 - 实现工具注册表和执行器

**目的**: 统一管理工具的注册和分发执行

**执行**:
1. 创建 `src/tools/executor.py`：
   ```python
   """工具注册表和执行器"""
   from src.utils.logger import get_logger

   logger = get_logger(__name__)

   # 工具注册表: {name: {"func": callable, "schema": dict}}
   TOOL_REGISTRY: dict[str, dict] = {}


   def register_tool(name: str, func: callable, schema: dict) -> None:
       """注册工具

       Args:
           name: 工具名称（必须与schema中的function.name一致）
           func: 工具执行函数
           schema: OpenAI function calling格式的schema
       """
       TOOL_REGISTRY[name] = {"func": func, "schema": schema}
       logger.debug(f"注册工具: {name}")


   def execute_tool(name: str, args: dict, **kwargs) -> str:
       """执行工具

       Args:
           name: 工具名称
           args: 工具参数（从LLM的tool_calls中提取）

       Returns:
           工具执行结果（字符串）

       Raises:
           KeyError: 工具不存在
       """
       if name not in TOOL_REGISTRY:
           logger.error(f"未知工具: {name}")
           raise KeyError(f"未知工具: {name}，可用工具: {list(TOOL_REGISTRY.keys())}")

       tool = TOOL_REGISTRY[name]
       func = tool["func"]
       logger.info(f"执行工具: {name}({args})")
       try:
           result = func(**args, **kwargs)
           return str(result) if not isinstance(result, str) else result
       except Exception as e:
           logger.error(f"工具执行失败: {name} - {e}")
           return f"工具执行失败: {e}"


   def get_all_schemas() -> list[dict]:
       """获取所有已注册工具的schema列表"""
       return [tool["schema"] for tool in TOOL_REGISTRY.values()]


   def get_tool_names() -> list[str]:
       """获取所有已注册工具的名称"""
       return list(TOOL_REGISTRY.keys())
   ```
2. 创建 `src/tools/__init__.py`（注册所有工具）：
   ```python
   """工具包 - 注册所有工具"""
   from src.tools.executor import register_tool
   from src.tools import dice, world_tool, player_tool, npc_tool, log_tool
   from src.tools.tool_definitions import (
       ROLL_DICE_SCHEMA,
       QUERY_WORLD_STATE_SCHEMA,
       UPDATE_WORLD_STATE_SCHEMA,
       GET_LOCATION_INFO_SCHEMA,
       LIST_NPCS_AT_LOCATION_SCHEMA,
       GET_PLAYER_INFO_SCHEMA,
       UPDATE_PLAYER_INFO_SCHEMA,
       GET_NPC_INFO_SCHEMA,
       SEARCH_NPC_SCHEMA,
       LOG_EVENT_SCHEMA,
   )

   # 注册所有工具
   register_tool("roll_dice", dice.roll_dice, ROLL_DICE_SCHEMA)
   register_tool("query_world_state", world_tool.query_world_state, QUERY_WORLD_STATE_SCHEMA)
   register_tool("update_world_state", world_tool.update_world_state, UPDATE_WORLD_STATE_SCHEMA)
   register_tool("get_location_info", world_tool.get_location_info, GET_LOCATION_INFO_SCHEMA)
   register_tool("list_npcs_at_location", world_tool.list_npcs_at_location, LIST_NPCS_AT_LOCATION_SCHEMA)
   register_tool("get_player_info", player_tool.get_player_info, GET_PLAYER_INFO_SCHEMA)
   register_tool("update_player_info", player_tool.update_player_info, UPDATE_PLAYER_INFO_SCHEMA)
   register_tool("get_npc_info", npc_tool.get_npc_info, GET_NPC_INFO_SCHEMA)
   register_tool("search_npc", npc_tool.search_npc, SEARCH_NPC_SCHEMA)
   register_tool("log_event", log_tool.log_event, LOG_EVENT_SCHEMA)
   ```
3. 创建 `tests/test_executor.py`：
   ```python
   """工具执行器测试"""
   import pytest
   from src.tools.executor import register_tool, execute_tool, get_all_schemas, get_tool_names, TOOL_REGISTRY


   def setup_module():
       TOOL_REGISTRY.clear()


   def teardown_module():
       """★ 清理测试注册的工具，防止污染其他测试模块"""
       # 移除测试专用的工具，保留正式工具
       for name in ["add", "dummy"]:
           TOOL_REGISTRY.pop(name, None)


   def test_register_and_execute():
       """注册→执行→结果正确"""
       def add(a: int, b: int) -> int:
           return a + b

       schema = {
           "type": "function",
           "function": {
               "name": "add",
               "description": "加法",
               "parameters": {
                   "type": "object",
                   "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                   "required": ["a", "b"]
               }
           }
       }
       register_tool("add", add, schema)
       result = execute_tool("add", {"a": 3, "b": 5})
       assert result == "8"


   def test_unknown_tool():
       """未知工具抛出异常"""
       with pytest.raises(KeyError):
           execute_tool("nonexistent", {})


   def test_get_all_schemas():
       """获取所有schema"""
       def dummy(): pass
       schema = {"type": "function", "function": {"name": "dummy", "description": "", "parameters": {"type": "object", "properties": {}}}}
       register_tool("dummy", dummy, schema)
       schemas = get_all_schemas()
       assert len(schemas) >= 1
       assert schemas[0]["function"]["name"] == "dummy"


   def test_get_tool_names():
       names = get_tool_names()
       assert "dummy" in names
   ```

**验收**: `uv run pytest tests/test_executor.py -v` 全绿（4个测试）

---

## 步骤 2.8 - 实现 GM Agent 核心循环

**目的**: 项目心脏——推理 + 工具调用的 while 循环

**执行**:
1. 创建 `src/agent/__init__.py`（空文件）
2. 创建 `src/agent/game_master.py`：
   ```python
   """Game Master Agent - 核心推理循环"""
   from src.services.llm_client import LLMClient
   from src.prompts.gm_system import get_system_prompt
   from src.tools.executor import execute_tool, get_all_schemas
   from src.tools import world_tool
   from src.services.database import init_db, get_db
   from src.models import player_repo, location_repo, world_repo
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
           # 对话历史
           messages.extend(self.history)
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

               response = self.llm.chat_with_tools(messages, self.tools)
               choice = response.choices[0]
               message = choice.message

               # 3. 检查是否有工具调用
               if message.tool_calls:
                   logger.info(f"LLM请求调用 {len(message.tool_calls)} 个工具 (第{tool_round}轮)")

                   # ★ 关键：先将assistant消息（含tool_calls）加入历史
                   # DeepSeek特有：需要保留reasoning_content传回后续请求
                   assistant_msg = {"role": "assistant", "content": message.content or ""}
                   if hasattr(message, 'reasoning_content') and message.reasoning_content:
                       assistant_msg["reasoning_content"] = message.reasoning_content
                   if message.tool_calls:
                       assistant_msg["tool_calls"] = [
                           {
                               "id": tc.id,
                               "type": "function",
                               "function": {
                                   "name": tc.function.name,
                                   "arguments": tc.function.arguments,
                               },
                           }
                           for tc in message.tool_calls
                       ]
                   self.history.append(assistant_msg)

                   for tool_call in message.tool_calls:
                       func_name = tool_call.function.name
                       func_args = {}
                       try:
                           import json
                           func_args = json.loads(tool_call.function.arguments)
                       except json.JSONDecodeError:
                           func_args = {}

                       # 执行工具
                       result = execute_tool(func_name, func_args, db_path=self.db_path)
                       logger.info(f"工具 {func_name} 返回: {result[:100]}...")

                       # ★ 关键：tool消息必须包含tool_call_id，且reasoning_content也要传递
                       tool_msg = {
                           "role": "tool",
                           "tool_call_id": tool_call.id,
                           "name": func_name,
                           "content": result,
                       }
                       if hasattr(message, 'reasoning_content') and message.reasoning_content:
                           tool_msg["reasoning_content"] = message.reasoning_content
                       self.history.append(tool_msg)
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
   ```
3. 创建 `tests/test_game_master.py`：
   ```python
   """GameMaster 核心测试"""
   import tempfile
   import os
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.services.llm_client import LLMClient
   from src.agent.game_master import GameMaster

   DB_PATH = None


   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       seed_world(DB_PATH)


   def _create_gm():
       """★ 每个测试创建独立的GM实例，避免历史累积"""
       from src.models import world_repo
       worlds = world_repo.list_worlds(DB_PATH)
       wid = worlds[0]["id"] if worlds else 1
       return GameMaster(wid, 1, LLMClient(), DB_PATH)

   def test_init():
       """GameMaster能正常初始化"""
       gm = _create_gm()
       assert gm.world_id is not None
       assert gm.tools is not None
       assert len(gm.tools) >= 10  # ★ 改为 >= 10，防止测试污染

   def test_process_simple():
       """简单对话测试"""
       gm = _create_gm()
       response = gm.process("你好")
       assert response is not None
       assert len(response) > 0
       print(f"\nGM回复: {response[:200]}")

   def test_process_look_around():
       """环顾四周测试（应该触发工具调用）"""
       gm = _create_gm()
       response = gm.process("环顾四周")
       assert response is not None
       assert len(response) > 0
       print(f"\nGM回复: {response[:200]}")

   def test_history_persistence():
       """对话历史被正确保存"""
       gm = _create_gm()
       gm.process("测试消息")
       from src.services.database import get_db
       with get_db(DB_PATH) as conn:
           count = conn.execute(
               "SELECT COUNT(*) FROM game_messages WHERE world_id = ?",
               (gm.world_id,)
           ).fetchone()[0]
       assert count >= 4
   ```

**验收**: `uv run pytest tests/test_game_master.py -v -s` 全绿（能看到GM的实际回复）

---

## 步骤 2.9 - 实现上下文管理器

**目的**: 管理对话历史长度，防止超出Token限制

**执行**:
1. 创建 `src/services/context_manager.py`：
   ```python
   """上下文管理器 - 管理对话历史长度"""
   from src.utils.logger import get_logger

   logger = get_logger(__name__)

   # 每条消息平均Token数（中文约2-3字/token，保守估计每条200 token）
   ESTIMATED_TOKENS_PER_MESSAGE = 200
   # System Prompt大约占用的Token数
   ESTIMATED_SYSTEM_TOKENS = 2000
   # DeepSeek-V3最大上下文
   MAX_CONTEXT_TOKENS = 100000
   # 保留的最大消息数
   MAX_MESSAGES = 100


   def trim_history(history: list[dict], max_tokens: int = MAX_CONTEXT_TOKENS - ESTIMATED_SYSTEM_TOKENS) -> list[dict]:
       """裁剪对话历史，确保不超过Token限制

       策略: 保留最近的消息，删除最旧的。
       """
       if not history:
           return history

       max_messages = max(10, max_tokens // ESTIMATED_TOKENS_PER_MESSAGE)
       max_messages = min(max_messages, MAX_MESSAGES)

       if len(history) <= max_messages:
           return history

       trimmed = history[-max_messages:]
       removed = len(history) - max_messages
       logger.info(f"裁剪对话历史: 移除 {removed} 条旧消息，保留 {len(trimmed)} 条")
       return trimmed


   def compress_history(history: list[dict]) -> list[dict]:
       """压缩对话历史（预留接口）

       TODO: P5'阶段实现LLM摘要压缩
       当前使用简单截断策略
       """
       return trim_history(history)
   ```
2. 在 `src/agent/game_master.py` 的 `_build_context` 方法中集成：
   ```python
   # 在文件顶部添加导入
   from src.services.context_manager import trim_history

   # 修改 _build_context 方法，在 return 前添加:
   def _build_context(self) -> list[dict]:
       system_prompt = get_system_prompt(self._get_world_context())
       messages = [{"role": "system", "content": system_prompt}]
       # 裁剪历史
       trimmed = trim_history(self.history)
       messages.extend(trimmed)
       return messages
   ```
3. 创建 `tests/test_context_manager.py`：
   ```python
   """上下文管理器测试"""
   from src.services.context_manager import trim_history, compress_history


   def test_trim_short_history():
       """短历史不裁剪"""
       history = [{"role": "user", "content": f"消息{i}"} for i in range(5)]
       result = trim_history(history)
       assert len(result) == 5


   def test_trim_long_history():
       """长历史被裁剪"""
       history = [{"role": "user", "content": f"消息{i}"} for i in range(200)]
       result = trim_history(history, max_tokens=2000)  # 约10条
       assert len(result) <= 15  # 留余量


   def test_compress_exists():
       """压缩接口存在"""
       assert callable(compress_history)
   ```

**验收**: `uv run pytest tests/test_context_manager.py -v` 全绿

---

## 步骤 2.10 - 实现流式输出

**目的**: GM 回复逐字显示

**执行**:
1. 在 `src/agent/game_master.py` 中添加 `process_stream` 方法（在 `process` 方法后面）：
   ```python
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

           # 流式调用（带工具时不能用流式，需要完整响应来解析tool_calls）
           response = self.llm.chat_with_tools(messages, self.tools)
           choice = response.choices[0]
           message = choice.message

           if message.tool_calls:
               for tool_call in message.tool_calls:
                   func_name = tool_call.function.name
                   func_args = {}
                   try:
                       import json
                       func_args = json.loads(tool_call.function.arguments)
                   except json.JSONDecodeError:
                       func_args = {}
                   result = execute_tool(func_name, func_args, db_path=self.db_path)
                   self.history.append({"role": "tool", "name": func_name, "content": result})
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
   ```
2. 更新 `tests/test_game_master.py`，添加流式测试：
   ```python
   def test_process_stream():
       """流式输出测试"""
       chunks = list(GM.process_stream("说一句话"))
       full_text = "".join(chunks)
       assert len(full_text) > 0
       print(f"\n流式回复: {full_text[:200]}")
   ```

**验收**: `uv run pytest tests/test_game_master.py::test_process_stream -v -s` 通过

---

## 步骤 2.11 - 实现 CLI 命令行界面

**目的**: 在终端中与 GM 对话

**执行**:
1. 创建 `src/cli.py`：
   ```python
   """CLI 命令行界面 - 在终端中与Game Master对话"""
   import sys
   from src.services.database import init_db
   from src.services.llm_client import LLMClient
   from src.data.seed_data import seed_world
   from src.agent.game_master import GameMaster
   from src.utils.logger import get_logger

   logger = get_logger(__name__)


   def show_status(gm: GameMaster):
       """显示当前状态"""
       from src.tools import player_tool
       print("\n" + "=" * 40)
       print(player_tool.get_player_info(gm.db_path))
       print("=" * 40)


   def show_help():
       """显示帮助"""
       print("""
   === 可用命令 ===
   /status  - 查看玩家状态
   /help    - 显示此帮助
   /quit    - 退出游戏
   /save    - 保存游戏
   /history - 查看对话历史数量
   /tokens  - 查看Token使用统计
   ==================
   其他任何输入都会发送给Game Master
   """)


   def main():
       """CLI主入口"""
       db_path = None

       # 初始化数据库和种子数据
       print("=== Game Master Agent ===")
       print("正在初始化世界...")

       try:
           result = seed_world(db_path)
           world_id = result["world_id"]
       except Exception:
           # 如果世界已存在，使用现有世界
           from src.models import world_repo
           worlds = world_repo.list_worlds(db_path)
           if worlds:
               world_id = worlds[0]["id"]
               print(f"使用已有世界: {worlds[0]['name']}")
           else:
               print("错误: 无法初始化世界")
               sys.exit(1)

       # 创建玩家（如果不存在）
       from src.models import player_repo
       from src.services.database import get_db
       with get_db(db_path) as conn:
           existing = conn.execute("SELECT id FROM players WHERE world_id = ? LIMIT 1", (world_id,)).fetchone()
       if existing:
           player_id = existing["id"]
           print(f"欢迎回来，冒险者！")
       else:
           player_id = player_repo.create_player(world_id, "冒险者", db_path)
           print(f"欢迎，新的冒险者！")

       # 创建GM
       llm = LLMClient()
       gm = GameMaster(world_id, player_id, llm, db_path)

       print(f"世界: {world_id} | 玩家ID: {player_id}")
       print("输入 /help 查看命令，/quit 退出\n")

       # 主循环
       while True:
           try:
               user_input = input("\n你> ").strip()
           except (EOFError, KeyboardInterrupt):
               print("\n再见！")
               break

           if not user_input:
               continue

           # 特殊命令
           if user_input == "/quit":
               print("再见！")
               break
           elif user_input == "/help":
               show_help()
               continue
           elif user_input == "/status":
               show_status(gm)
               continue
           elif user_input == "/tokens":
               stats = llm.get_usage_stats()
               print(f"\nToken统计: {stats}")
               continue
           elif user_input == "/history":
               print(f"\n对话历史: {len(gm.history)} 条消息")
               continue
           elif user_input.startswith("/save"):
               slot = user_input.split()[1] if len(user_input.split()) > 1 else "auto"
               from src.services.save_manager import save_game
               path = save_game(world_id, slot, db_path)
               print(f"\n游戏已保存: {path}")
               continue

           # 发送给GM
           try:
               print()
               response = gm.process(user_input)
               print(f"\nGM> {response}")
           except Exception as e:
               logger.error(f"处理失败: {e}")
               print(f"\n[系统错误] {e}")


   if __name__ == "__main__":
       main()
   ```
2. 在 `pyproject.toml` 中添加入口点（如果还没有）：
   ```toml
   [project.scripts]
   game-master = "src.cli:main"
   ```
3. 验证CLI能启动：`uv run python -c "from src.cli import main; print('CLI模块加载成功')"`

**验收**: CLI 模块能正常导入

---

## 步骤 2.12 - 对话历史持久化

**目的**: 重启后对话不丢失

**说明**: 步骤 2.8 中的 `GameMaster.__init__` 已经实现了 `_load_history()`，`process()` 中已经实现了 `_save_message()`。`game_messages` 表在 P1' 的 schema.sql 中已创建。

**执行**:
1. 验证持久化正常工作：
   ```python
   # 创建 tests/test_history_persistence.py
   """对话历史持久化测试"""
   import tempfile
   import os
   from src.services.database import init_db, get_db
   from src.data.seed_data import seed_world
   from src.services.llm_client import LLMClient
   from src.agent.game_master import GameMaster

   DB_PATH = None

   def setup_module():
       global DB_PATH
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       seed_world(DB_PATH)

   def test_history_persist_across_restarts():
       """重启后对话历史仍在"""
       result = seed_world(DB_PATH)
       wid = result["world_id"]

       # 第一次会话
       gm1 = GameMaster(wid, 1, LLMClient(), DB_PATH)
       gm1.process("记住这个词：龙之谷")
       gm1.process("我刚才让你记住什么？")

       # 模拟重启：创建新的GameMaster实例
       gm2 = GameMaster(wid, 1, LLMClient(), DB_PATH)
       assert len(gm2.history) >= 4  # 至少有之前的对话
   ```

**验收**: `uv run pytest tests/test_history_persistence.py -v -s` 通过

---

## 步骤 2.13 - 搭建 MUD 前端骨架

**目的**: 同步启动前端原型，不等 P4'

**执行**:
1. 创建 `src/web/index.html`：
   ```html
   <!DOCTYPE html>
   <html lang="zh-CN">
   <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>Game Master Agent - MUD</title>
       <link rel="stylesheet" href="css/style.css">
   </head>
   <body>
       <div id="app">
           <!-- 顶部状态栏 -->
           <header id="status-bar">
               <span id="game-title">⚔️ Game Master Agent</span>
               <div id="player-stats">
                   <span class="stat">❤️ <span id="hp">100/100</span></span>
                   <span class="stat">💙 <span id="mp">50/50</span></span>
                   <span class="stat">⭐ Lv.<span id="level">1</span></span>
                   <span class="stat">💰 <span id="gold">0</span></span>
               </div>
           </header>

           <!-- 主内容区 -->
           <div id="main-content">
               <!-- 叙事区 -->
               <div id="narrative-panel">
                   <div id="narrative-content"></div>
               </div>

               <!-- 右侧信息面板 -->
               <div id="info-panel">
                   <div class="tabs">
                       <button class="tab active" data-tab="npcs">NPC</button>
                       <button class="tab" data-tab="inventory">背包</button>
                       <button class="tab" data-tab="quests">任务</button>
                   </div>
                   <div id="tab-content">
                       <div id="tab-npcs" class="tab-pane active">
                           <p class="placeholder">暂无NPC信息</p>
                       </div>
                       <div id="tab-inventory" class="tab-pane">
                           <p class="placeholder">背包为空</p>
                       </div>
                       <div id="tab-quests" class="tab-pane">
                           <p class="placeholder">暂无任务</p>
                       </div>
                   </div>
               </div>
           </div>

           <!-- 底部输入区 -->
           <div id="input-area">
               <input type="text" id="user-input" placeholder="输入你的行动..." autocomplete="off">
               <button id="send-btn">发送</button>
           </div>
       </div>

       <script src="js/mock.js"></script>
       <script src="js/app.js"></script>
   </body>
   </html>
   ```
2. 创建 `src/web/css/style.css`：
   ```css
   * { margin: 0; padding: 0; box-sizing: border-box; }
   body {
       font-family: 'Courier New', monospace;
       background: #0a0a0a;
       color: #e0e0e0;
       height: 100vh;
       display: flex;
       flex-direction: column;
   }
   #status-bar {
       background: #1a1a2e;
       padding: 8px 16px;
       display: flex;
       justify-content: space-between;
       align-items: center;
       border-bottom: 1px solid #333;
   }
   #game-title { font-size: 16px; font-weight: bold; color: #e0e0e0; }
   #player-stats { display: flex; gap: 16px; font-size: 13px; }
   .stat { color: #aaa; }
   #main-content {
       flex: 1;
       display: flex;
       overflow: hidden;
   }
   #narrative-panel {
       flex: 1;
       padding: 16px;
       overflow-y: auto;
       background: #0d0d0d;
   }
   #narrative-content .message {
       margin-bottom: 12px;
       line-height: 1.6;
       white-space: pre-wrap;
   }
   #narrative-content .gm-text { color: #c0c0c0; }
   #narrative-content .user-text { color: #7ec8e3; }
   #narrative-content .system-text { color: #888; font-style: italic; }
   #narrative-content .combat-text { color: #e74c3c; }
   #narrative-content .npc-text { color: #f39c12; }
   #info-panel {
       width: 280px;
       background: #1a1a2e;
       border-left: 1px solid #333;
       display: flex;
       flex-direction: column;
   }
   .tabs {
       display: flex;
       border-bottom: 1px solid #333;
   }
   .tab {
       flex: 1;
       padding: 8px;
       background: transparent;
       border: none;
       color: #888;
       cursor: pointer;
       font-family: inherit;
       font-size: 13px;
   }
   .tab.active { color: #e0e0e0; border-bottom: 2px solid #7ec8e3; }
   .tab-pane { display: none; padding: 12px; font-size: 13px; overflow-y: auto; flex: 1; }
   .tab-pane.active { display: block; }
   .placeholder { color: #555; }
   #input-area {
       display: flex;
       padding: 12px;
       background: #1a1a2e;
       border-top: 1px solid #333;
   }
   #user-input {
       flex: 1;
       padding: 10px 14px;
       background: #0d0d0d;
       border: 1px solid #333;
       color: #e0e0e0;
       font-family: inherit;
       font-size: 14px;
       outline: none;
   }
   #user-input:focus { border-color: #7ec8e3; }
   #send-btn {
       padding: 10px 20px;
       background: #7ec8e3;
       border: none;
       color: #0a0a0a;
       font-family: inherit;
       font-weight: bold;
       cursor: pointer;
       margin-left: 8px;
   }
   #send-btn:hover { background: #5dade2; }
   ```
3. 创建 `src/web/js/mock.js`：
   ```javascript
   // Mock Game Client - 模拟GM回复
   class MockGameClient {
       constructor() {
           this.responses = [
               "你站在宁静村的广场上，微风拂过翠绿的田野。东边是流浪者酒馆，传来阵阵笑声和酒杯碰撞声。北方的幽暗森林在阳光下显得格外神秘。",
               "酒馆老板铁锤热情地招呼你：\"欢迎来到铁锤酒馆！今天有新鲜的麦酒和烤鹿肉！\"他擦着一个大酒杯，身后的架子上摆满了各种酒瓶。",
               "你注意到村口的老公告栏上贴着一张告示：\"幽暗森林中最近出现了哥布林的踪迹，村长悬赏50金币寻求勇者调查。\"",
               "一位身穿灰色斗篷的神秘旅者坐在酒馆角落，似乎在观察着什么。当你看向她时，她微微点头致意。",
               "铁匠铺传来叮叮当当的打铁声。铁匠铁砧正在锻造一把新剑，火炉旁堆放着各种矿石和成品武器。",
           ];
           this.index = 0;
       }

       async send(userInput) {
           // 模拟延迟
           await new Promise(r => setTimeout(r, 500 + Math.random() * 1000));

           // 选择回复（循环使用）
           const response = this.responses[this.index % this.responses.length];
           this.index++;

           // 模拟流式输出
           return { type: 'narrative', content: response };
       }
   }
   ```
4. 创建 `src/web/js/app.js`：
   ```javascript
   // MUD 前端主逻辑
   const client = new MockGameClient();
   const narrativeContent = document.getElementById('narrative-content');
   const userInput = document.getElementById('user-input');
   const sendBtn = document.getElementById('send-btn');

   // 添加消息到叙事区
   function addMessage(text, className) {
       const div = document.createElement('div');
       div.className = `message ${className}`;
       div.textContent = text;
       narrativeContent.appendChild(div);
       narrativeContent.scrollTop = narrativeContent.scrollHeight;
   }

   // 发送消息
   async function sendMessage() {
       const text = userInput.value.trim();
       if (!text) return;

       addMessage(`你> ${text}`, 'user-text');
       userInput.value = '';

       try {
           const response = await client.send(text);
           if (response.type === 'narrative') {
               // 模拟逐字显示
               const msgDiv = document.createElement('div');
               msgDiv.className = 'message gm-text';
               narrativeContent.appendChild(msgDiv);

               for (const char of response.content) {
                   msgDiv.textContent += char;
                   narrativeContent.scrollTop = narrativeContent.scrollHeight;
                   await new Promise(r => setTimeout(r, 20));
               }
           }
       } catch (e) {
           addMessage(`[错误] ${e.message}`, 'system-text');
       }
   }

   // 事件绑定
   sendBtn.addEventListener('click', sendMessage);
   userInput.addEventListener('keydown', (e) => {
       if (e.key === 'Enter') sendMessage();
   });

   // Tab切换
   document.querySelectorAll('.tab').forEach(tab => {
       tab.addEventListener('click', () => {
           document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
           document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
           tab.classList.add('active');
           document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
       });
   });
   ```

**验收**: 用浏览器打开 `src/web/index.html`，能看到完整的 MUD 界面，输入文字后显示 Mock 回复

---

## 步骤 2.14 - 实现 WebSocket Mock 连接

**说明**: 步骤 2.13 已经实现了 Mock 连接（`mock.js` + `app.js`），前端能用 Mock 数据交互。

**验收**: 在浏览器中输入文字 → 叙事区显示 Mock 回复（逐字出现）

---

## 步骤 2.15 - CLI 端到端测试

**目的**: 完整流程测试

**执行**:
1. 运行完整测试套件：`uv run pytest tests/ -v`
2. 手动启动CLI测试：`uv run python src/cli.py`
3. 在CLI中依次输入：
   - `你好` → GM自我介绍
   - `环顾四周` → 描述当前场景（应触发工具调用）
   - `查看状态` → 显示玩家信息
   - `查看背包` → 显示物品栏
   - `这里有谁` → 列出NPC
   - `帮我掷一个d20` → 应触发骰子工具
   - 连续对话5轮，检查一致性
4. 记录问题到 `docs/prompt-tuning-log.md`

**验收**: 6个场景全部正常响应，无崩溃

---

## 步骤 2.16 - 异常处理测试

**目的**: 确保程序健壮

**执行**:
1. 在CLI中测试：
   - 空输入（直接按回车）→ 应忽略
   - `/quit` → 应优雅退出
   - `/help` → 应显示帮助
   - `/status` → 应显示状态
   - Ctrl+C → 应优雅退出
2. 创建 `tests/test_error_handling.py`：
   ```python
   """异常处理测试"""
   import tempfile
   import os
   from src.services.database import init_db
   from src.data.seed_data import seed_world
   from src.services.llm_client import LLMClient
   from src.agent.game_master import GameMaster
   from src.tools.executor import execute_tool

   DB_PATH = None
   GM = None

   def setup_module():
       global DB_PATH, GM
       tmpdir = tempfile.mkdtemp()
       DB_PATH = os.path.join(tmpdir, "test.db")
       result = seed_world(DB_PATH)
       GM = GameMaster(result["world_id"], 1, LLMClient(), DB_PATH)

   def test_empty_input():
       """空输入不崩溃"""
       response = GM.process("")
       assert response is not None

   def test_unknown_tool():
       """未知工具返回错误信息"""
       result = execute_tool("nonexistent_tool", {})
       assert "未知工具" in result

   def test_long_conversation():
       """长对话不崩溃"""
       for i in range(5):
           response = GM.process(f"测试消息第{i+1}轮")
           assert response is not None
   ```

**验收**: `uv run pytest tests/test_error_handling.py -v` 全绿

---

## ★ P2' 里程碑验收

运行完整测试套件：

```bash
uv run pytest tests/ -v
```

逐项确认：

- [ ] 2.1 工具Schema定义完成（10个工具）
- [ ] 2.2 骰子工具 + 单测通过
- [ ] 2.3 世界状态工具 + 单测通过
- [ ] 2.4 玩家工具 + 单测通过
- [ ] 2.5 NPC工具 + 单测通过
- [ ] 2.6 日志工具 + 单测通过
- [ ] 2.7 工具注册表 + 执行器通过
- [ ] 2.8 GM Agent核心循环通过（能对话！）
- [ ] 2.9 上下文管理器通过
- [ ] 2.10 流式输出通过
- [ ] 2.11 CLI界面可用
- [ ] 2.12 对话历史持久化通过
- [ ] 2.13 MUD前端骨架可显示
- [ ] 2.14 Mock前端可交互
- [ ] 2.15 CLI端到端测试通过
- [ ] 2.16 异常处理测试通过

**全部 ✅ 后，P2' 阶段完成！你的 GM Agent 已经能对话了！** 🎉

---

## P2' 完成后的项目结构

```
game-master-agent/
├── src/
│   ├── config.py
│   ├── agent/
│   │   ├── __init__.py
│   │   └── game_master.py      # ★ GM核心循环
│   ├── tools/
│   │   ├── __init__.py          # 工具注册
│   │   ├── tool_definitions.py   # 工具Schema
│   │   ├── executor.py          # 工具执行器
│   │   ├── dice.py              # 骰子工具
│   │   ├── world_tool.py        # 世界状态工具
│   │   ├── player_tool.py       # 玩家工具
│   │   ├── npc_tool.py          # NPC工具
│   │   └── log_tool.py          # 日志工具
│   ├── models/                  # (P1'已创建)
│   ├── prompts/
│   │   └── gm_system.py
│   ├── services/
│   │   ├── llm_client.py
│   │   ├── database.py
│   │   ├── save_manager.py
│   │   └── context_manager.py   # ★ 上下文管理
│   ├── utils/
│   │   └── logger.py
│   ├── data/
│   │   └── seed_data.py
│   ├── cli.py                   # ★ CLI入口
│   └── web/
│       ├── index.html            # ★ MUD前端
│       ├── css/style.css
│       └── js/
│           ├── mock.js
│           └── app.js
└── tests/                      # 50+个测试
```
