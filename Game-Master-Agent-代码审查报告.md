# Game-Master-Agent 代码审查与修复任务清单

> 审查日期: 2026-05-04 | 分析范围: `2workbench/` 目录全部 Python 源码（70 个文件）| 整体完成度: **91%**

---

## P0 - 紧急修复（影响运行时稳定性）

### P0-1: cache.py 线程安全缺失
- **文件**: `2workbench/foundation/cache.py`
- **问题**: 文档声称"线程安全"，但实际没有任何锁机制，多线程并发访问会导致数据竞争
- **修复方案**:
  1. 添加 `threading.Lock` 作为实例属性 `self._lock`
  2. 在 `get()`、`set()`、`delete()`、`invalidate_prefix()`、`clear()`、`get_stats()` 所有公共方法上加 `with self._lock:`
  3. 在 `_evict()` 方法上也加锁保护

### P0-2: event_bus.py 定向事件过滤逻辑错误
- **文件**: `2workbench/foundation/event_bus.py`
- **问题**: `emit()` 第196行和 `emit_async()` 第239行，当 `event.source` 和 `event.target` 都设置且不相等时跳过了处理器，导致定向事件无法被正确处理
- **修复方案**:
  1. 找到 `emit()` 中的过滤逻辑（约第196行）:
     ```python
     # 错误代码:
     if event.source and event.target and event.source != event.target:
         continue
     ```
  2. 修正为: 当事件有 target 时，只处理 target 匹配的订阅者；当没有 target 时，所有订阅者都可以处理
     ```python
     if event.target and subscription.target and subscription.target != event.target:
         continue
     ```
  3. 对 `emit_async()` 做同样的修正

### P0-3: repository.py SQL 列名与模型不匹配
- **文件**: `2workbench/core/models/repository.py`
- **问题**: `PlayerRepo.get_inventory()` 的 SQL JOIN 查询返回 `item_name`、`item_type` 等列名，但 `PlayerItem` 模型没有这些字段，直接用 `PlayerItem(**dict(row))` 会因未知字段报错
- **修复方案**:
  1. 检查 `get_inventory()` 的 SQL 查询，确认返回的列名
  2. 修改 SQL 使用 AS 别名，使列名与 `PlayerItem` 模型字段一致；或者修改反序列化逻辑，手动映射字段
  3. 同时检查其他 Repo 的 JOIN 查询是否存在类似问题

### P0-4: database.py 初始化逻辑缺陷
- **文件**: `2workbench/foundation/database.py`
- **问题**: `init_db()` 在表已存在但版本号低于 `SCHEMA_VERSION` 时会重新执行整个 schema.sql（包含 CREATE TABLE），可能导致 "table already exists" 错误
- **修复方案**:
  1. 在 `init_db()` 中添加版本比较逻辑：如果表已存在，执行增量迁移而非全量重建
  2. 短期方案: 在 schema.sql 的所有 CREATE TABLE 语句中添加 `IF NOT EXISTS`
  3. 长期方案: 实现版本化的迁移机制（如 migration_v1.sql, migration_v2.sql）

### P0-5: main_window.py 使用不安全的 QThread.terminate()
- **文件**: `2workbench/presentation/main_window.py`
- **问题**: 第1348行使用 `QThread.terminate()` 停止 Agent 线程，这是不安全的做法，可能导致资源泄漏和数据损坏
- **修复方案**:
  1. 在 Agent 线程类中添加协作式取消机制（如 `thread.should_stop = True` + 定期检查）
  2. 将 `terminate()` 替换为 `thread.requestInterruption()` 或自定义停止信号
  3. 添加超时等待，超时后再调用 `terminate()` 作为最后手段

---

## P1 - 功能完善（影响核心体验）

### P1-1: eval_workbench.py 使用模拟数据
- **文件**: `2workbench/presentation/ops/evaluator/eval_workbench.py`
- **问题**: `EvalThread.run()` 返回随机模拟结果，未真正调用 LLM，评估功能实质上不可用
- **修复方案**:
  1. 在 `EvalThread` 中集成 LLM 客户端调用
  2. 对每个评估用例，构建 prompt 并调用 `llm_client.chat_async()`
  3. 实现真实的评估指标计算（准确率、延迟、token 消耗等）
  4. 保留模拟模式作为 `--dry-run` 选项用于测试

### P1-2: gm_agent.py stream() 非真正流式
- **文件**: `2workbench/feature/ai/gm_agent.py`
- **问题**: `stream()` 方法内部只是包装了 `run()` 并一次性返回结果，没有实现逐 token 流式传输
- **修复方案**:
  1. 修改 `stream()` 使用 `llm_client.stream()` 获取异步生成器
  2. 逐 token yield `StreamEvent(type="token", data=token)`
  3. 在最终结果返回时 yield `StreamEvent(type="result", data=result)`

### P1-3: main_window.py 流式 token 回调为空
- **文件**: `2workbench/presentation/main_window.py`
- **问题**: `_on_stream_token` 方法（约第901-904行）只有 `pass`，未将 token 显示到控制台面板
- **修复方案**:
  1. 在 `_on_stream_token` 中将 token 追加到控制台输出组件
  2. 如果控制台面板尚未创建，先创建一个 `ConsoleOutput` 或 `QTextEdit` 面板
  3. 支持自动滚动到底部

### P1-4: tools.py 多处 world_id=1 硬编码
- **文件**: `2workbench/feature/ai/tools.py`
- **问题**: `update_player_stat`、`give_item`、`remove_item`、`move_to_location` 等工具函数硬编码 `world_id=1`
- **修复方案**:
  1. 从 `ToolContext` 或 `AgentState` 中动态获取 `world_id`
  2. 全局搜索 `world_id=1` 或 `world_id = 1`，逐一替换
  3. 确保 `ToolContext` 在工具调用前已正确设置 `world_id`

### P1-5: pyproject.toml 缺少关键运行时依赖
- **文件**: `pyproject.toml`
- **问题**: `Pillow`（截图功能）、`comtypes`（Windows UIA）、`python-dotenv`（配置加载）未在 dependencies 中声明
- **修复方案**:
  1. 在 `[project.dependencies]` 中添加:
     ```
     Pillow>=10.0.0
     python-dotenv>=1.0.0
     ```
  2. `comtypes` 作为 Windows 平台可选依赖添加到 `[project.optional-dependencies]`:
     ```
     windows = ["comtypes>=1.1.0"]
     ```

---

## P2 - 代码质量（影响可维护性）

### P2-1: nodes.py 系统提示词硬编码
- **文件**: `2workbench/feature/ai/nodes.py`
- **问题**: 系统提示词（100+ 行字符串）硬编码在 `_get_system_prompt()` 函数中
- **修复方案**:
  1. 将系统提示词提取到外部文件（如 `2workbench/prompts/system_prompt.md` 或 `.txt`）
  2. 在 `nodes.py` 中通过 `resource_manager.read_file()` 或直接 `Path().read_text()` 加载
  3. 支持通过项目配置覆盖默认提示词

### P2-2: interfaces.py 接口与实现类型不一致
- **文件**: `2workbench/foundation/base/interfaces.py`
- **问题**:
  - `ILLMClient.chat()` 签名（`messages: list[dict]`）与 `BaseLLMClient.chat_async()`（`messages: list[LLMMessage]`）不一致
  - `ILLMClient.chat()` 是同步方法返回 `dict`，而 `BaseLLMClient` 只有异步方法
  - `IMemoryStore.recall()` 返回 `list[dict]`，而 `MemoryRepo.recall()` 返回 `list[Memory]`
- **修复方案**:
  1. 更新 `ILLMClient` 接口，使用 `LLMMessage` 类型，添加 `chat_async()` 和 `stream()` 方法
  2. 更新 `IMemoryStore.recall()` 返回类型与 `MemoryRepo` 一致
  3. 确保所有实现类正确实现更新后的接口

### P2-3: save_manager.py 存档元数据未持久化
- **文件**: `2workbench/foundation/save_manager.py`
- **问题**: 文档声称存档元数据存入 SQLite，但实际 `save_game()` 未将 description、tags 等元数据写入任何地方
- **修复方案**:
  1. 在 schema.sql 中添加 `save_metadata` 表（save_id, description, tags, created_at）
  2. 在 `save_game()` 中将元数据写入该表
  3. 在 `list_saves()` 中从数据库读取元数据

### P2-4: 版本号不一致
- **文件**: `pyproject.toml`（version = "0.1.0"）vs `2workbench/app.py`（version="GMA IDE v2.0.0"）
- **修复方案**: 统一为同一版本号，建议以 pyproject.toml 为准，app.py 从 pyproject.toml 读取版本号

### P2-5: app.py 命令行参数未使用
- **文件**: `2workbench/app.py`
- **问题**: `--no-gui`（第34行）和 `--port`（第36行）参数已定义但在 `main()` 中未使用
- **修复方案**:
  1. `--port`: 将端口传递给 HTTP 服务器启动逻辑（替换硬编码的 18080）
  2. `--no-gui`: 实现无 GUI 模式，仅启动 HTTP 服务器和 Agent 后端

### P2-6: repository.py 大部分 Repo 缺少构造函数
- **文件**: `2workbench/core/models/repository.py`
- **问题**: 只有 `WorldRepo` 和 `PlayerRepo` 有 `__init__(self, db_path=None)`，其余 Repo 无法在构造时指定数据库路径
- **修复方案**: 为所有 Repo 类添加统一的 `__init__(self, db_path=None)` 构造函数

### P2-7: repository.py LogRepo.VALID_EVENT_TYPES 与 EventType 枚举不一致
- **文件**: `2workbench/core/models/repository.py`
- **问题**: `LogRepo.VALID_EVENT_TYPES` 是硬编码的字符串集合，与 `entities.EventType` 枚举值不一致
- **修复方案**: 将 `VALID_EVENT_TYPES` 改为从 `EventType` 枚举动态生成:
  ```python
  VALID_EVENT_TYPES = {e.value for e in EventType}
  ```

---

## P3 - 进阶优化（提升用户体验）

### P3-1: narration/system.py 标注为简化版
- **文件**: `2workbench/feature/narration/system.py`
- **问题**: 缺少真正的叙事提取、摘要生成、长期记忆整合等功能，仅将整段叙事作为会话记忆存储
- **修复方案**:
  1. 实现叙事分段提取（按场景/事件切分）
  2. 添加摘要生成功能（调用 LLM 生成叙事摘要）
  3. 实现长期记忆整合（将重要信息提取为结构化记忆存入数据库）

### P3-2: dialogue/system.py 存在 TODO
- **文件**: `2workbench/feature/dialogue/system.py`
- **问题**: 第144行 `TODO: 从数据库统计` — 对话历史统计功能未实现，当前直接返回固定值 0
- **修复方案**: 实现从数据库查询对话历史统计（总对话次数、最近对话时间等）

### P3-3: graph_editor.py 缺少 undo/redo
- **文件**: `2workbench/presentation/editor/graph_editor.py`
- **问题**: 图编辑器未实现撤销/重做功能，也缺少网格吸附和最小化地图
- **修复方案**:
  1. 实现命令模式（Command Pattern）支持 undo/redo
  2. 添加网格吸附功能
  3. 添加最小化地图（可选）

### P3-4: main_window.py 文件过大
- **文件**: `2workbench/presentation/main_window.py`
- **问题**: 约 1650 行/65KB，建议拆分
- **修复方案**:
  1. 将 `LeftPanel`、`CenterPanel`、`RightPanel` 拆分到独立文件
  2. 将菜单/工具栏创建逻辑拆分到独立文件
  3. 将 Agent 运行逻辑拆分到独立文件

### P3-5: 测试覆盖率低
- **文件**: `2workbench/tests/`
- **问题**: 仅 Foundation 和 Core 层有测试，估计总体覆盖率 15-20%。Feature 和 Presentation 层零测试。现有测试使用 `print` 验证而非 pytest 断言
- **修复方案**:
  1. 将现有测试的 `print('✅')` 替换为 `assert` 断言
  2. 为 Feature 层添加单元测试（至少覆盖 graph.py、nodes.py、tools.py）
  3. 为 Presentation 层添加关键组件测试（graph_editor.py、tool_manager.py）
  4. 为 HTTP API（server.py）添加集成测试

### P3-6: server.py 缺少请求速率限制
- **文件**: `2workbench/presentation/server.py`
- **问题**: HTTP 服务器无任何防滥用机制
- **修复方案**: 添加基于 IP 的请求速率限制（如令牌桶算法）

### P3-7: server.py reset/refresh 占位实现
- **文件**: `2workbench/presentation/server.py`
- **问题**: 第624、626行 `clicked = True  # 占位`，实际未执行任何操作
- **修复方案**: 实现真实的 reset（重置 Agent 状态）和 refresh（刷新 GUI）功能

### P3-8: state_api.py _get_metrics_state 返回全零默认值
- **文件**: `2workbench/presentation/state_api.py`
- **问题**: 第605-621行，tokens/cost/errors/uptime 全部返回默认值 0
- **修复方案**: 从 EventBus 或全局状态中获取真实的运行指标

### P3-9: openai_client.py stream() 缺少重试机制
- **文件**: `2workbench/foundation/llm/openai_client.py`
- **问题**: `chat_async()` 有 `@retry` 装饰器，但 `stream()` 没有，流式调用失败时不会自动重试
- **修复方案**: 为 `stream()` 添加重试机制（注意流式重试需要特殊处理，建议在连接建立阶段重试）

### P3-10: singleton.py 未被使用
- **文件**: `2workbench/foundation/base/singleton.py`
- **问题**: 单例基类已实现但项目中无任何模块使用
- **修复方案**: 如果确认不需要，可以删除；或者将其应用到需要单例的组件上

---

## 快速定位索引

| 关键词 | 涉及文件 |
|--------|---------|
| `world_id=1` 硬编码 | `feature/ai/tools.py`, `presentation/main_window.py` |
| `pass` 空实现 | `presentation/main_window.py:904`, `presentation/server.py:624,626` |
| TODO/FIXME | `feature/dialogue/system.py:144` |
| 硬编码端口 18080 | `presentation/server.py`, `presentation/main_window.py` |
| 模拟/伪造数据 | `presentation/ops/evaluator/eval_workbench.py` |
| 类型不一致 | `foundation/base/interfaces.py`, `core/models/repository.py` |
| 缺少 `__init__` | `core/models/repository.py`（除 WorldRepo/PlayerRepo 外的所有 Repo） |
