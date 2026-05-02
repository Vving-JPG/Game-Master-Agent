#!/usr/bin/env python3
"""Game Master Agent IDE — HTTP CLI 控制工具

通过 HTTP API 控制 IDE 的各项功能。
适配四层架构 (Foundation/Core/Feature/Presentation)。

用法:
    python gui_ctl.py [--port 18265] [--host 127.0.0.1]

API 端点:
    GET  /api/status                    — IDE 状态
    GET  /api/state                     — 应用状态 (结构化 API)
    GET  /api/dom                       — Widget DOM 树 (结构化 API)
    GET  /api/dom?selector=console      — 特定区域 DOM
    GET  /api/dom?diff=true             — DOM 变化
    GET  /api/uia                       — Windows UIA 树
    GET  /api/find?id=run_btn           — 查找 Widget
    POST /api/project/create            — 创建项目
    POST /api/project/open              — 打开项目
    POST /api/project/close             — 关闭项目
    GET  /api/project/info              — 项目信息
    GET  /api/graph                     — 获取图定义
    POST /api/graph/save                — 保存图定义
    GET  /api/prompts                   — 列出 Prompt
    GET  /api/prompts/<name>            — 获取 Prompt
    POST /api/prompts/<name>            — 保存 Prompt
    POST /api/agent/run                 — 运行 Agent
    POST /api/agent/stop                — 停止 Agent
    GET  /api/agent/state               — Agent 状态
    GET  /api/features                  — Feature 列表
    POST /api/features/<name>/enable    — 启用 Feature
    POST /api/features/<name>/disable   — 禁用 Feature
    GET  /api/tools                     — 工具列表
    GET  /api/screenshot                — 截图

四层架构操作:
    # Foundation 层
    python gui_ctl.py foundation status
    
    # Core 层
    python gui_ctl.py core entities
    
    # Feature 层
    python gui_ctl.py feature list
    python gui_ctl.py feature enable battle
    
    # Presentation 层
    python gui_ctl.py presentation theme dark

结构化状态 API (推荐):
    # 获取应用状态
    python gui_ctl.py state
    python gui_ctl.py state --json

    # 获取 Widget DOM 树
    python gui_ctl.py dom
    python gui_ctl.py dom --selector console    # 只获取控制台区域
    python gui_ctl.py dom --selector editor     # 只获取编辑器区域
    python gui_ctl.py dom --diff                # 只显示变化

    # 获取 Windows UIA 树
    python gui_ctl.py uia

    # 查找 Widget
    python gui_ctl.py find --id run_button
    python gui_ctl.py find --class QPushButton --text "运行"

基本控制:
    # 截图
    python gui_ctl.py screenshot

    # Agent 控制
    python gui_ctl.py status
    python gui_ctl.py run --event "攻击哥布林"
    python gui_ctl.py control pause|resume|step|reset
    python gui_ctl.py turns --last 5

    # 指令注入和工具
    python gui_ctl.py inject --level user --content "打开宝箱"
    python gui_ctl.py force --tool combat.initiate --params '{"target": "哥布林"}'

    # 文件操作
    python gui_ctl.py open --path prompts/system_prompt.md
    python gui_ctl.py save
    python gui_ctl.py refresh
    python gui_ctl.py tree --path workspace
    python gui_ctl.py cat --path prompts/system_prompt.md
    python gui_ctl.py edit --path file.md --content "# 新内容"
    python gui_ctl.py create --path file.md --content "# 新文件"
    python gui_ctl.py delete --path file.md

    # 点击控件
    python gui_ctl.py click run

    # 自动化测试循环
    python gui_ctl.py loop -n 10
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

BASE_URL = "http://127.0.0.1:18080"

# 截图保存目录
SCREENSHOTS_DIR = Path("screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)


# ==================== 结构化状态 API 命令 ====================

def cmd_state(args):
    """获取应用状态 — 结构化状态 API"""
    result = _request("GET", "/api/state")

    if "error" in result:
        print(f"[X] 获取状态失败: {result['error']}")
        return 1

    state = result.get("state", {})

    # 项目状态
    project = state.get("project", {})
    print(f"📁 项目: {project.get('name', '未打开')} {'(已打开)' if project.get('open') else '(未打开)'}")

    # Agent 状态
    agent = state.get("agent", {})
    print(f"🤖 Agent: {agent.get('status', 'unknown')} | 回合: {agent.get('turn', 0)} | 模型: {agent.get('model', 'unknown')}")

    # Feature 状态
    features = state.get("features", {})
    enabled = [name for name, info in features.items() if info.get("enabled")]
    print(f"⚡ Features ({len(enabled)} 启用): {', '.join(enabled[:5])}{'...' if len(enabled) > 5 else ''}")

    # 编辑器状态
    editor = state.get("editor", {})
    if editor.get("active_tab"):
        print(f"📝 编辑器: {editor.get('active_tab')} {'(已修改)' if editor.get('modified') else ''}")

    # UI 状态
    ui = state.get("ui", {})
    print(f"🎨 主题: {ui.get('theme', 'unknown')} | 窗口: {ui.get('window', {}).get('size', {}).get('width', 0)}x{ui.get('window', {}).get('size', {}).get('height', 0)}")

    if args.json:
        print("\n完整 JSON:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


def cmd_dom(args):
    """获取 Widget DOM 树 — 结构化状态 API"""
    params = []
    if args.selector:
        params.append(f"selector={args.selector}")
    if args.diff:
        params.append("diff=true")

    path = "/api/dom"
    if params:
        path += "?" + "&".join(params)

    result = _request("GET", path)

    if "error" in result:
        print(f"[X] 获取 DOM 失败: {result['error']}")
        return 1

    tree = result.get("tree", {})

    if args.diff:
        # 显示差异模式
        print("DOM 变化:")
        changed = tree.get("changed", [])
        added = tree.get("added", [])
        removed = tree.get("removed", [])

        if changed:
            print(f"  变化 ({len(changed)}):")
            for c in changed[:10]:
                print(f"    - {c.get('id') or 'unknown'}.{c.get('field')}: {c.get('old')} → {c.get('new')}")

        if added:
            print(f"  新增 ({len(added)}): {', '.join(added[:5])}{'...' if len(added) > 5 else ''}")

        if removed:
            print(f"  移除 ({len(removed)}): {', '.join(removed[:5])}{'...' if len(removed) > 5 else ''}")

        if not changed and not added and not removed:
            print("  (无变化)")
    else:
        # 显示树结构
        print("Widget DOM 树:")
        _print_widget_tree(tree, 0)

    if args.json:
        print("\n完整 JSON:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


def _print_widget_tree(node: dict, depth: int, max_depth: int = 3):
    """打印 Widget 树"""
    if depth > max_depth:
        return

    indent = "  " * depth
    class_name = node.get("class", "Unknown")
    obj_id = node.get("id", "")
    text = node.get("text", "")[:30]
    visible = "👁" if node.get("visible") else "🚫"
    enabled = "✓" if node.get("enabled") else "✗"

    id_str = f"#{obj_id}" if obj_id else ""
    text_str = f" \"{text}\"" if text else ""

    print(f"{indent}{visible}{enabled} {class_name}{id_str}{text_str}")

    for child in node.get("children", [])[:5]:  # 最多显示 5 个子节点
        _print_widget_tree(child, depth + 1, max_depth)

    children = node.get("children", [])
    if len(children) > 5:
        print(f"{indent}  ... 还有 {len(children) - 5} 个子节点")


def cmd_uia(args):
    """获取 Windows UIA 树 — 结构化状态 API"""
    result = _request("GET", "/api/uia")

    if "error" in result:
        print(f"[X] 获取 UIA 树失败: {result['error']}")
        return 1

    if result.get("status") == "unavailable":
        print(f"[X] {result.get('error', 'UIA 不可用')}")
        print(f"[i] 提示: {result.get('hint', '')}")
        return 1

    tree = result.get("tree", {})
    print("Windows UI Automation 树:")
    _print_uia_tree(tree, 0)

    if args.json:
        print("\n完整 JSON:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


def _print_uia_tree(node: dict, depth: int, max_depth: int = 3):
    """打印 UIA 树"""
    if depth > max_depth:
        return

    indent = "  " * depth
    control_type = node.get("control_type", "Unknown")
    name = node.get("name", "")[:30]
    class_name = node.get("class_name", "")

    name_str = f" \"{name}\"" if name else ""
    class_str = f" ({class_name})" if class_name and args.json else ""

    print(f"{indent}[{control_type}]{name_str}{class_str}")

    for child in node.get("children", [])[:5]:
        _print_uia_tree(child, depth + 1, max_depth)

    children = node.get("children", [])
    if len(children) > 5:
        print(f"{indent}  ... 还有 {len(children) - 5} 个子节点")


def cmd_find(args):
    """查找 Widget — 结构化状态 API"""
    query = {}
    if args.id:
        query["id"] = args.id
    if args.class_name:
        query["class"] = args.class_name
    if args.text:
        query["text"] = args.text

    if not query:
        print("[X] 请提供至少一个查询条件: --id, --class, --text")
        return 1

    # 构建查询字符串
    query_str = "&".join([f"{k}={v}" for k, v in query.items()])
    result = _request("GET", f"/api/find?{query_str}")

    if "error" in result:
        print(f"[X] 查找失败: {result['error']}")
        return 1

    count = result.get("count", 0)
    results = result.get("results", [])

    print(f"找到 {count} 个匹配项:")
    for i, r in enumerate(results[:10], 1):
        print(f"  {i}. {r.get('class')}#{r.get('id')} \"{r.get('text', '')[:30]}\"")
        print(f"     位置: ({r.get('geometry', {}).get('x', 0)}, {r.get('geometry', {}).get('y', 0)})")

    if count > 10:
        print(f"  ... 还有 {count - 10} 个")

    if args.json:
        print("\n完整 JSON:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


def _request(method: str, path: str, data: dict | None = None) -> dict:
    """发送 HTTP 请求"""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}

    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        try:
            return json.loads(error_body)
        except:
            return {"error": error_body, "status_code": e.code}
    except urllib.error.URLError as e:
        return {"error": f"连接失败: {e.reason}", "hint": "请先启动 GUI: cd 2workbench && python app.py"}


# ==================== 四层架构操作 ====================

def cmd_foundation(args):
    """Foundation 层操作"""
    if args.action == "status":
        result = _request("GET", "/api/foundation/status")
        print(f"EventBus: {result.get('event_bus', 'unknown')}")
        print(f"Database: {result.get('database', 'unknown')}")
        print(f"Cache: {result.get('cache', 'unknown')}")
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.action == "config":
        result = _request("GET", "/api/foundation/config")
        print(f"Model: {result.get('model', 'unknown')}")
        print(f"Base URL: {result.get('base_url', 'unknown')}")
    else:
        print(f"[X] 未知操作: {args.action}")
        return 1
    return 0


def cmd_core(args):
    """Core 层操作"""
    if args.action == "entities":
        result = _request("GET", "/api/core/entities")
        entities = result.get("entities", [])
        print(f"实体类型 ({len(entities)}):")
        for e in entities:
            print(f"  - {e}")
    elif args.action == "repositories":
        result = _request("GET", "/api/core/repositories")
        repos = result.get("repositories", [])
        print(f"Repository ({len(repos)}):")
        for r in repos:
            print(f"  - {r}")
    elif args.action == "calculators":
        result = _request("GET", "/api/core/calculators")
        calc = result.get("calculators", [])
        print(f"计算器 ({len(calc)}):")
        for c in calc:
            print(f"  - {c}")
    else:
        print(f"[X] 未知操作: {args.action}")
        return 1
    return 0


def cmd_feature(args):
    """Feature 层操作"""
    if args.action == "list":
        result = _request("GET", "/api/features")
        features = result.get("features", [])
        print(f"Feature 列表 ({len(features)}):")
        for f in features:
            status = "✅" if f.get("enabled") else "⬜"
            print(f"  {status} {f.get('name', '?')}: {f.get('description', '')}")
    elif args.action == "enable":
        result = _request("POST", f"/api/features/{args.name}/enable")
        print(f"[OK] {result.get('message', f'已启用 {args.name}')}")
    elif args.action == "disable":
        result = _request("POST", f"/api/features/{args.name}/disable")
        print(f"[OK] {result.get('message', f'已禁用 {args.name}')}")
    elif args.action == "state":
        result = _request("GET", f"/api/features/{args.name}/state")
        print(f"状态: {result.get('state', {})}")
    else:
        print(f"[X] 未知操作: {args.action}")
        return 1
    return 0


def cmd_presentation(args):
    """Presentation 层操作"""
    if args.action == "theme":
        if args.value:
            result = _request("POST", "/api/presentation/theme", {"theme": args.value})
            print(f"[OK] 主题已切换为: {args.value}")
        else:
            result = _request("GET", "/api/presentation/theme")
            print(f"当前主题: {result.get('theme', 'unknown')}")
    elif args.action == "project":
        if args.value == "create":
            result = _request("POST", "/api/project/create", {"name": args.extra, "template": "trpg"})
            print(f"[OK] 项目已创建: {result.get('path', '')}")
        elif args.value == "open":
            result = _request("POST", "/api/project/open", {"path": args.extra})
            print(f"[OK] 项目已打开: {result.get('name', '')}")
        elif args.value == "close":
            result = _request("POST", "/api/project/close")
            print(f"[OK] 项目已关闭")
        else:
            result = _request("GET", "/api/project/info")
            print(f"项目: {result.get('name', '未打开')}")
    else:
        print(f"[X] 未知操作: {args.action}")
        return 1
    return 0


# ==================== 截图功能 ====================

def cmd_screenshot(args):
    """截图 GUI - 强制保存到 screenshots 目录"""
    print("[>] 截取 GUI 界面...")

    result = _request("GET", "/api/screenshot")

    if "error" in result:
        print(f"[X] 截图失败: {result['error']}")
        return 1

    # 生成强制命名格式: YYYYMMDD_HHMMSS_序号.png
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    existing = list(SCREENSHOTS_DIR.glob(f"{timestamp}_*.png"))
    seq = len(existing) + 1
    output_path = SCREENSHOTS_DIR / f"{timestamp}_{seq:03d}.png"

    # 保存截图
    img_data = base64.b64decode(result['base64'])
    with open(output_path, 'wb') as f:
        f.write(img_data)

    print(f"[OK] 截图已保存: {output_path}")
    print(f"[i] 尺寸: {result['width']}x{result['height']}")
    return 0


# ==================== Agent 控制 ====================

def cmd_status(args):
    """获取 Agent 状态"""
    result = _request("GET", "/api/status")
    print(f"Agent 状态: {result.get('status', 'unknown')}")
    print(f"回合数: {result.get('turn', 0)}")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_run(args):
    """运行 Agent"""
    result = _request("POST", "/api/run", {"event": args.event})
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = result.get("status", "unknown")
        if status == "completed":
            print(f"[OK] 回合完成")
        elif status == "started":
            print(f"[OK] Agent 已启动")
        else:
            print(f"[ERROR] {result.get('error_type', '?')}: {result.get('error', '?')}")
    return 0


def cmd_control(args):
    """控制 Agent: pause/resume/step/reset"""
    action_map = {"pause": "pause", "resume": "resume", "step": "step", "reset": "reset"}
    action = action_map.get(args.action)
    if not action:
        print(f"[X] 未知操作: {args.action}", file=sys.stderr)
        return 1
    result = _request("POST", "/api/control", {"action": action})
    print(f"[OK] {result.get('status', action)}")
    return 0


def cmd_turns(args):
    """查看轮次历史"""
    result = _request("GET", f"/api/turns?last={args.last}")
    turns = result.get("turns", [])
    print(f"共 {result.get('total', 0)} 轮, 显示最近 {len(turns)} 轮:")
    for t in turns:
        status_icon = "OK" if t.get("status") == "completed" else "X"
        print(f"  [{status_icon}] 回合 {t.get('id', '?')}: {t.get('event', '?')[:30]}")
    if args.json:
        print(json.dumps(turns, ensure_ascii=False, indent=2))
    return 0


# ==================== 指令注入和工具 ====================

def cmd_inject(args):
    """注入指令"""
    result = _request("POST", "/api/inject", {"level": args.level, "content": args.content})
    print(f"[OK] {result.get('message', '指令已注入')}")
    return 0


def cmd_force(args):
    """强制执行工具"""
    params = json.loads(args.params) if args.params else {}
    result = _request("POST", "/api/force-tool", {"tool": args.tool, "params": params})
    print(f"[OK] {result.get('result', '')}")
    return 0


# ==================== 文件操作 ====================

def cmd_open(args):
    """在 GUI 中打开文件"""
    result = _request("POST", "/api/open", {"path": args.path})
    print(f"[OK] 已打开: {args.path}")
    return 0


def cmd_save(args):
    """保存当前文件"""
    result = _request("POST", "/api/save")
    print(f"[OK] {result.get('status', '已保存')}")
    return 0


def cmd_refresh(args):
    """刷新资源树"""
    result = _request("POST", "/api/refresh")
    print(f"[OK] {result.get('status', '已刷新')}")
    return 0


def cmd_tree(args):
    """查看目录树"""
    path = f"/api/tree?path={args.path}" if args.path else "/api/tree"
    result = _request("GET", path)
    items = result.get("items", [])
    for item in items:
        icon = "[DIR]" if item["type"] == "dir" else "[FILE]"
        print(f"  {icon} {item['name']}")
    return 0


def cmd_cat(args):
    """查看文件内容"""
    result = _request("GET", f"/api/file?path={args.path}")
    print(result.get("content", ""))
    return 0


def cmd_edit(args):
    """编辑文件"""
    content = args.content
    if args.file:
        content = open(args.file, "r", encoding="utf-8").read()
    result = _request("PUT", f"/api/file?path={args.path}", {"content": content})
    print(f"[OK] {result.get('status', '')}: {args.path} ({result.get('size', 0)} chars)")
    return 0


def cmd_create(args):
    """创建文件"""
    content = args.content
    if args.file:
        content = open(args.file, "r", encoding="utf-8").read()
    result = _request("POST", f"/api/file?path={args.path}", {"content": content})
    print(f"[OK] {result.get('status', '')}: {args.path}")
    return 0


def cmd_delete(args):
    """删除文件"""
    result = _request("DELETE", f"/api/file?path={args.path}")
    print(f"[OK] {result.get('status', '')}: {args.path}")
    return 0


# ==================== 点击控件 ====================

def cmd_click(args):
    """点击控件"""
    widget = args.widget
    print(f"[>] 点击控件: {widget}")

    result = _request("GET", f"/api/click/{widget}")

    if "error" in result:
        print(f"[X] 错误: {result['error']}")
        if "available" in result:
            print(f"[i] 可用控件: {', '.join(result['available'])}")
        return 1

    print(f"[OK] 已点击: {result.get('widget', widget)}")
    return 0


# ==================== 自动化测试循环 ====================

def cmd_loop(args):
    """执行完整测试循环"""
    print("=" * 60)
    print("WorkBench GUI 自动化测试循环")
    print("=" * 60)

    iteration = 0
    max_iterations = args.max_iterations or 999999

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- 迭代 #{iteration} ---")

        # 步骤 1: 获取当前状态
        print("\n[1/4] 获取控件状态...")
        state_result = _request("GET", "/api/status")
        if "error" in state_result:
            print(f"[X] 获取状态失败: {state_result['error']}")
            break

        agent_status = state_result.get('status', 'unknown')
        print(f"  Agent 状态: {agent_status}")

        # 步骤 2: 根据状态决定操作
        print("\n[2/4] 执行界面操作...")

        if agent_status == "IDLE":
            print("  操作: 点击运行按钮")
            click_result = _request("GET", "/api/click/run")
        elif agent_status == "RUNNING":
            print("  操作: Agent 运行中，等待 1 秒")
            time.sleep(1)
            click_result = {"status": "waiting"}
        else:
            print(f"  操作: 状态为 {agent_status}，跳过")
            click_result = {"status": "skipped"}

        if "error" in click_result:
            print(f"  [X] 操作失败: {click_result['error']}")
        else:
            print(f"  [OK] 操作完成: {click_result.get('status', 'ok')}")

        # 步骤 3: 截图
        print("\n[3/4] 截图...")
        screenshot_result = _request("GET", "/api/screenshot")

        if "error" in screenshot_result:
            print(f"  [X] 截图失败: {screenshot_result['error']}")
        else:
            img_data = base64.b64decode(screenshot_result['base64'])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = SCREENSHOTS_DIR / f"loop_{timestamp}_{iteration:03d}.png"
            with open(screenshot_path, 'wb') as f:
                f.write(img_data)
            print(f"  [OK] 截图已保存: {screenshot_path}")

        # 步骤 4: 分析
        print("\n[4/4] 分析结果...")
        new_state = _request("GET", "/api/status")
        new_status = new_state.get('status', 'unknown')

        if new_status == "ERROR":
            print("  [X] 发现错误状态！")
            if args.auto_fix:
                print("  [>] 自动修复模式: 等待用户确认...")
                input("  按 Enter 继续，或 Ctrl+C 退出...")
        else:
            print(f"  [OK] 状态正常: {new_status}")

        if args.delay > 0:
            print(f"\n  等待 {args.delay} 秒...")
            time.sleep(args.delay)

        if args.single:
            print("\n[>] 单轮模式，退出")
            break

    print("\n" + "=" * 60)
    print(f"测试循环结束，共执行 {iteration} 轮")
    print("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Game Master Agent IDE — HTTP CLI 控制工具")
    parser.add_argument("--json", "-j", action="store_true", help="JSON 输出")
    parser.add_argument("--port", "-p", type=int, default=18080, help="HTTP 端口")
    sub = parser.add_subparsers(dest="command")

    # 四层架构操作
    p = sub.add_parser("foundation", help="Foundation 层操作")
    p.add_argument("action", choices=["status", "config"])

    p = sub.add_parser("core", help="Core 层操作")
    p.add_argument("action", choices=["entities", "repositories", "calculators"])

    p = sub.add_parser("feature", help="Feature 层操作")
    p.add_argument("action", choices=["list", "enable", "disable", "state"])
    p.add_argument("name", nargs="?", help="Feature 名称")

    p = sub.add_parser("presentation", help="Presentation 层操作")
    p.add_argument("action", choices=["theme", "project"])
    p.add_argument("value", nargs="?", help="值")
    p.add_argument("extra", nargs="?", help="额外参数")

    # 截图
    sub.add_parser("screenshot", help="截图 GUI")

    # Agent 控制
    p = sub.add_parser("status", help="Agent 状态")

    p = sub.add_parser("run", help="运行 Agent")
    p.add_argument("--event", "-e", required=True, help="事件内容")

    p = sub.add_parser("control", help="控制 Agent")
    p.add_argument("action", choices=["pause", "resume", "step", "reset"])

    p = sub.add_parser("turns", help="轮次历史")
    p.add_argument("--last", "-n", type=int, default=5)

    # 指令注入和工具
    p = sub.add_parser("inject", help="注入指令")
    p.add_argument("--level", "-l", default="user", choices=["system", "user", "override"])
    p.add_argument("--content", "-c", required=True)

    p = sub.add_parser("force", help="强制工具")
    p.add_argument("--tool", "-t", required=True)
    p.add_argument("--params", "-p", default="{}")

    # 文件操作
    p = sub.add_parser("open", help="打开文件")
    p.add_argument("--path", "-p", required=True)

    sub.add_parser("save", help="保存文件")
    sub.add_parser("refresh", help="刷新资源树")

    p = sub.add_parser("tree", help="目录树")
    p.add_argument("--path", "-p", default="")

    p = sub.add_parser("cat", help="查看文件")
    p.add_argument("--path", "-p", required=True)

    p = sub.add_parser("edit", help="编辑文件")
    p.add_argument("--path", "-p", required=True)
    p.add_argument("--content", "-c", default="")
    p.add_argument("--file", "-f", help="从文件读取内容")

    p = sub.add_parser("create", help="创建文件")
    p.add_argument("--path", "-p", required=True)
    p.add_argument("--content", "-c", default="")
    p.add_argument("--file", "-f", help="从文件读取内容")

    p = sub.add_parser("delete", help="删除文件")
    p.add_argument("--path", "-p", required=True)

    # 点击控件
    p = sub.add_parser("click", help="点击控件")
    p.add_argument("widget", help="控件名称 (run, pause, step, reset, refresh, save)")

    # 自动化测试循环
    p = sub.add_parser("loop", help="执行测试循环")
    p.add_argument("-n", "--max-iterations", type=int, help="最大迭代次数")
    p.add_argument("-d", "--delay", type=int, default=2, help="每轮延迟(秒)")
    p.add_argument("-s", "--single", action="store_true", help="只执行一轮")
    p.add_argument("--auto-fix", action="store_true", help="自动修复模式")

    # 结构化状态 API 命令
    p = sub.add_parser("state", help="获取应用状态 (结构化 API)")

    p = sub.add_parser("dom", help="获取 Widget DOM 树 (结构化 API)")
    p.add_argument("--selector", "-s", help="CSS-like 选择器 (如: console, editor, #run_btn)")
    p.add_argument("--diff", "-d", action="store_true", help="只显示变化部分")

    p = sub.add_parser("uia", help="获取 Windows UIA 树 (结构化 API)")

    p = sub.add_parser("find", help="查找 Widget (结构化 API)")
    p.add_argument("--id", "-i", help="按 objectName 查找")
    p.add_argument("--class", "-c", dest="class_name", help="按类名查找")
    p.add_argument("--text", "-t", help="按文本查找")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 更新 BASE_URL 如果指定了端口
    global BASE_URL
    if args.port != 18080:
        BASE_URL = f"http://127.0.0.1:{args.port}"

    commands = {
        "foundation": cmd_foundation,
        "core": cmd_core,
        "feature": cmd_feature,
        "presentation": cmd_presentation,
        "screenshot": cmd_screenshot,
        "status": cmd_status,
        "run": cmd_run,
        "control": cmd_control,
        "turns": cmd_turns,
        "inject": cmd_inject,
        "force": cmd_force,
        "open": cmd_open,
        "save": cmd_save,
        "refresh": cmd_refresh,
        "tree": cmd_tree,
        "cat": cmd_cat,
        "edit": cmd_edit,
        "create": cmd_create,
        "delete": cmd_delete,
        "click": cmd_click,
        "loop": cmd_loop,
        "state": cmd_state,
        "dom": cmd_dom,
        "uia": cmd_uia,
        "find": cmd_find,
    }

    handler = commands.get(args.command)
    if handler:
        exit_code = handler(args)
        sys.exit(exit_code)
    else:
        print(f"未知命令: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
