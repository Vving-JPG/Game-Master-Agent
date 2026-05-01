# WorkBench GUI 自动化操作 Skill

> 通过 HTTP API 操控 WorkBench GUI，支持截图、点击控件、获取状态等操作。
> 渐进式披露结构：Layer 1(必读) → Layer 2(按需) → Layer 3(参考)

---

## Layer 1: 快速开始（必读）

### 1.1 前置条件

```bash
# 1. 启动 WorkBench GUI
uv run python -m workbench

# 2. 等待 3 秒

# 3. 验证服务可用
curl -s http://127.0.0.1:18080/health
```

### 1.2 核心命令

```bash
# 截图（保存到 screenshots/YYYYMMDD_HHMMSS_序号.png）
uv run python .trae/skills/workbench-gui/gui_ctl.py screenshot

# 点击控件
uv run python .trae/skills/workbench-gui/gui_ctl.py click run
uv run python .trae/skills/workbench-gui/gui_ctl.py click pause
uv run python .trae/skills/workbench-gui/gui_ctl.py click reset

# 获取状态
uv run python .trae/skills/workbench-gui/gui_ctl.py state
uv run python .trae/skills/workbench-gui/gui_ctl.py state agent
```

### 1.3 可用控件

| 控件名 | 说明 |
|--------|------|
| `run` | 运行按钮 |
| `pause` | 暂停按钮 |
| `step` | 单步按钮 |
| `reset` | 重置按钮 |
| `refresh` | 刷新资源树 |
| `save` | 保存当前文件 |

---

## Layer 2: 按需加载（常用场景）

### 2.1 场景：截图验证 GUI 状态

```bash
# 截图并查看
uv run python .trae/skills/workbench-gui/gui_ctl.py screenshot
# 输出: screenshots/20260501_123045_001.png
```

### 2.2 场景：运行 Agent 并监控

```bash
# 1. 重置 Agent
uv run python .trae/skills/workbench-gui/gui_ctl.py click reset

# 2. 点击运行
uv run python .trae/skills/workbench-gui/gui_ctl.py click run

# 3. 等待 2 秒后截图
sleep 2
uv run python .trae/skills/workbench-gui/gui_ctl.py screenshot

# 4. 检查状态
uv run python .trae/skills/workbench-gui/gui_ctl.py state agent
```

### 2.3 场景：自动化测试循环

```bash
# 执行完整测试循环（自动截图、检测状态）
uv run python .trae/skills/workbench-gui/gui_ctl.py loop -n 10
```

### 2.4 HTTP API 直接调用

```bash
# 截图
curl -s http://127.0.0.1:18080/api/screenshot

# 点击运行
curl -s http://127.0.0.1:18080/api/click/run

# 获取 Agent 状态
curl -s http://127.0.0.1:18080/api/state?widget=agent

# 发送事件运行 Agent
curl -s -X POST http://127.0.0.1:18080/api/run \
  -H "Content-Type: application/json" \
  -d '{"event": "测试事件"}'
```

---

## Layer 3: 完整参考（技术细节）

### 3.1 API 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/screenshot` | GET | 截图 (返回 base64) |
| `/api/click/{widget}` | GET | 点击控件 |
| `/api/state` | GET | 获取状态 |
| `/api/state?widget=agent` | GET | 获取 Agent 状态 |
| `/api/run` | POST | 运行 Agent |
| `/api/control` | POST | 控制 Agent (reset/pause/step) |
| `/api/status` | GET | 获取 Agent 状态 |
| `/api/turns?last=N` | GET | 获取最近 N 轮记录 |

### 3.2 脚本参数说明

```bash
# gui_ctl.py 完整用法

# 点击控件
uv run python .trae/skills/workbench-gui/gui_ctl.py click <widget>

# 截图
uv run python .trae/skills/workbench-gui/gui_ctl.py screenshot

# 获取状态
uv run python .trae/skills/workbench-gui/gui_ctl.py state [widget]
# widget: all, agent, window, editor, resource_tree

# 测试循环
uv run python .trae/skills/workbench-gui/gui_ctl.py loop [选项]
#   -n, --max-iterations N  最大迭代次数
#   -d, --delay N           每轮延迟(秒)
#   -s, --single            只执行一轮
#   --auto-fix              自动修复模式
```

### 3.3 截图文件管理

- 所有截图保存到 `screenshots/` 目录
- 命名格式：`YYYYMMDD_HHMMSS_序号.png`
- 手动管理：定期清理旧截图

### 3.4 故障排查

| 问题 | 解决 |
|------|------|
| 连接失败 | 确认 GUI 已启动：`uv run python -m workbench` |
| 截图失败 | 检查 screenshots 目录权限 |
| 点击无反应 | 确认控件名称正确，查看可用控件列表 |

---

## 文件结构

```
.trae/skills/workbench-gui/
├── SKILL.md          # 本文件
└── gui_ctl.py        # 控制脚本
```

## 更新日志

- 2026-05-01: 创建 Skill，整合截图、点击、状态获取功能
