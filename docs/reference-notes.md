# 业界 RPG-MCP 项目参考笔记

> 本文档记录三个开源 RPG-MCP 项目的借鉴点和分析

---

## 项目A - Mnehmos/mnehmos.rpg.mcp

**技术栈**: TypeScript / SQLite / MCP Server

### 借鉴点（高优先级）

1. **事件驱动架构: OODA 循环**
   - OBSERVE → ORIENT → DECIDE → ACT → VALIDATE
   - 借鉴：我们的 GM Agent 也可以采用类似的感知-决策-执行循环

2. **工具合并设计（Token效率）**
   - 195个工具合并为32个，Token开销降低85%
   - 使用 action 参数路由（如 `character_manage` 带 create/get/update/delete 动作）
   - 借鉴：我们的工具设计也应采用 action 路由模式，减少工具数量

3. **反幻觉原则: "LLMs propose, never execute"**
   - LLM只提议，引擎验证执行
   - 借鉴：核心设计原则，所有世界状态变更必须通过引擎验证

4. **确定性规则执行**
   - 骰子和战斗在服务端执行，LLM不能作弊
   - 借鉴：战斗判定、随机事件必须走引擎，不能相信LLM的"随机"结果

5. **NPC记忆系统**
   - 关系追踪（熟悉度+态度）
   - 对话记忆带重要性等级
   - 借鉴：实现 NpcMemory 表，支持重要性评分

6. **Schema驱动设计**
   - Zod验证所有边界数据
   - 借鉴：Pydantic模型严格验证所有输入输出

### 不适用点

- MCP Server 模式（我们采用直接API调用）
- TypeScript 实现（我们用Python）
- 完整的D&D 5e规则（我们简化规则）
- 网格战斗系统（MUD文本游戏不需要）

---

## 项目B - jnaskali/rpg-mcp

**技术栈**: Python / uv / MCP Server

### 借鉴点

1. **Python MCP 工具定义标准写法**
   ```python
   # 简洁的工具函数定义
   def roll_dice(expr: str) -> dict:
       # 解析 2d6+3 格式
       ...
   ```

2. **uv 项目管理方式**
   - 使用 uv sync 安装依赖
   - 借鉴：已采用 uv 作为包管理器

3. **骰子表达式解析**
   - 标准RPG记法：`1d6`, `2d8+3`, `3d6-1`
   - 借鉴：实现 dice_roll 工具支持标准记法

4. **成功判定机制**
   - `check_success(probability, critical_rate)`
   - 借鉴：技能检定时使用概率判定

5. **随机事件生成**
   - 受 Mythic Game Master Emulator 启发
   - 借鉴：可集成随机事件表到GM决策中

### 不适用点

- 纯工具集合，无持久化层（我们有完整数据库）
- MCP Server 架构（我们直接调用LLM）
- 功能较简单，无NPC记忆、任务系统等

---

## 项目C - shawnrushefsky/dmcp

**技术栈**: TypeScript / SQLite / HTTP Web UI / MCP Server

### 借鉴点

1. **170个工具的26个功能分类清单**
   - 游戏管理、角色管理、世界管理、任务、战斗、库存等
   - 借鉴：我们的数据模型覆盖这些核心领域

2. **Web UI 页面设计**
   - 角色卡、地图、任务面板
   - 借鉴：未来MUD前端可参考这种信息组织方式

3. **暂停/恢复机制**
   - `prepare_pause`, `save_pause_state`, `get_resume_context`
   - 借鉴：实现存档管理模块，支持游戏进度保存

4. **多Agent协作设计**
   - 外部Agent推送更新，DM整合
   - 借鉴：架构上预留扩展接口

5. **动态规则系统**
   - Agent根据设定（奇幻/科幻/恐怖）设计合适规则
   - 借鉴：System Prompt中世界观可配置

6. **秘密系统**
   - 可揭示的秘密，带揭示条件
   - 借鉴：任务系统可扩展前提条件检查

### 不适用点

- MCP Server 模式
- TypeScript 实现
- 多Agent协作（当前版本单GM设计）
- 170个工具过于复杂（我们精简设计）

---

## 我们的独特设计

### 核心差异

| 维度 | 参考项目 | 我们的设计 |
|------|----------|------------|
| 架构 | MCP Server | 直接API调用 |
| LLM | Claude/GPT | DeepSeek |
| 前端 | 桌面客户端 | MUD Web界面 |
| 技术栈 | TypeScript | Python |
| Agent数 | 多Agent | 单GM |
| 规则 | D&D 5e完整 | 简化规则 |

### 核心设计原则

1. **单GM架构**: 一个DeepSeek驱动的Game Master，简化协调复杂度
2. **MUD风格**: 纯文本交互，沉浸式叙事
3. **Python全栈**: 从LLM客户端到数据库全Python实现
4. **精简工具集**: 参考项目A的合并思想，但数量更少（约15-20个核心工具）
5. **反幻觉**: 所有状态变更走引擎，LLM只提议

### 工具设计策略

借鉴项目A的 action 路由模式：

```python
# 合并前（不推荐）
def create_player(...)
def get_player(...)
def update_player(...)

# 合并后（推荐）
def player_manage(action: str, ...)  # action: create/get/update/delete
```

### 数据模型重点

1. **World**: 支持多世界/多存档
2. **Location**: 地点连接关系（JSON存储出口）
3. **Player**: 完整属性 + 物品栏
4. **NPC**: 性格JSON + 记忆系统
5. **Quest**: 任务步骤追踪
6. **GameLog**: 事件日志用于上下文

---

## 下一步行动

1. 实现核心数据模型（schema.sql）
2. 设计GM System Prompt（借鉴反幻觉原则）
3. 实现Repository层（CRUD操作）
4. 设计工具接口（action路由模式）
5. 实现种子数据（默认游戏世界）
