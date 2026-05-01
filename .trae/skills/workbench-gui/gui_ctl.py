#!/usr/bin/env python3
"""
WorkBench GUI 控制脚本

用法:
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
        return {"error": f"连接失败: {e.reason}", "hint": "请先启动 GUI: uv run python -m workbench"}


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
    parser = argparse.ArgumentParser(description="WorkBench GUI 控制脚本")
    parser.add_argument("--json", "-j", action="store_true", help="JSON 输出")
    sub = parser.add_subparsers(dest="command")

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

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
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
