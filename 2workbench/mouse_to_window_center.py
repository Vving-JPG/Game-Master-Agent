#!/usr/bin/env python3
"""将鼠标移到窗口正中心，然后创建 Agent

完全模拟人工操作，结合结构化状态 API 获取窗口位置和尺寸。
"""
from __future__ import annotations

import time
import sys
import json
import urllib.request
from pathlib import Path

import pyautogui

# 设置安全模式
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

BASE_URL = "http://127.0.0.1:18080"


def api_request(method: str, path: str, data: dict | None = None) -> dict:
    """发送 HTTP API 请求 - 仅用于获取信息"""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def take_screenshot(name: str) -> str:
    """截取屏幕截图"""
    result = api_request("GET", "/api/screenshot")
    
    if "error" in result:
        print(f"[X] 截图失败: {result['error']}")
        return ""
    
    import base64
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    
    output_path = screenshots_dir / f"{name}_{timestamp}.png"
    
    img_data = base64.b64decode(result['base64'])
    with open(output_path, 'wb') as f:
        f.write(img_data)
    
    print(f"[OK] 截图已保存: {output_path}")
    return str(output_path)


def get_window_info() -> dict:
    """获取窗口信息（位置和尺寸）"""
    result = api_request("GET", "/api/dom")
    tree = result.get("tree", {})
    return {
        "x": tree.get("geometry", {}).get("x", 0),
        "y": tree.get("geometry", {}).get("y", 0),
        "width": tree.get("geometry", {}).get("width", 1600),
        "height": tree.get("geometry", {}).get("height", 1000),
    }


def calculate_window_center(window_info: dict) -> tuple[int, int]:
    """计算窗口中心点（屏幕坐标）"""
    center_x = window_info["x"] + window_info["width"] // 2
    center_y = window_info["y"] + window_info["height"] // 2
    return (center_x, center_y)


def print_step(step_num: int, description: str):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {description}")
    print('='*60)


def find_widget_in_tree(tree: dict, predicate) -> dict | None:
    """在 Widget 树中查找符合条件的控件"""
    if predicate(tree):
        return tree
    for child in tree.get("children", []):
        result = find_widget_in_tree(child, predicate)
        if result:
            return result
    return None


def main():
    """主流程：鼠标移到窗口中心后创建 Agent"""
    print("="*60)
    print("Game Master Agent IDE - 鼠标移到窗口正中心")
    print("="*60)
    print("\n⚠️  即将开始模拟人工操作...")
    print("     3秒后将控制您的鼠标和键盘！")
    time.sleep(3)
    
    # ========== 步骤 1: 获取窗口信息 ==========
    print_step(1, "通过结构化状态 API 获取窗口位置和尺寸")
    
    window_info = get_window_info()
    print(f"  窗口位置: ({window_info['x']}, {window_info['y']})")
    print(f"  窗口尺寸: {window_info['width']}x{window_info['height']}")
    
    # 计算窗口中心（屏幕坐标）
    window_center_x, window_center_y = calculate_window_center(window_info)
    print(f"  窗口中心（屏幕坐标）: ({window_center_x}, {window_center_y})")
    
    take_screenshot("win_center_step1_info")
    
    # ========== 步骤 2: 将鼠标移到窗口正中心 ==========
    print_step(2, "将鼠标移到窗口正中心")
    
    print(f"🖱️  移动鼠标到窗口中心: ({window_center_x}, {window_center_y})")
    pyautogui.moveTo(window_center_x, window_center_y, duration=0.5)
    time.sleep(0.5)
    
    take_screenshot("win_center_step2_mouse_centered")
    
    # ========== 步骤 3: 获取 Widget 树并查找"新建"按钮 ==========
    print_step(3, "获取 Widget 树并查找'新建'按钮")
    
    result = api_request("GET", "/api/dom")
    tree = result.get("tree", {})
    
    # 查找"新建"按钮
    new_button = find_widget_in_tree(tree, lambda w: 
        w.get("class") == "QToolButton" and "新建" in w.get("text", ""))
    
    if new_button:
        btn_geom = new_button.get("geometry", {})
        # 计算按钮中心（屏幕坐标）
        btn_screen_x = window_info["x"] + btn_geom.get("x", 0) + btn_geom.get("width", 0) // 2
        btn_screen_y = window_info["y"] + btn_geom.get("y", 0) + btn_geom.get("height", 0) // 2
        print(f"  🎯 找到'新建'按钮: '{new_button.get('text')}'")
        print(f"     相对窗口: ({btn_geom.get('x')}, {btn_geom.get('y')})")
        print(f"     屏幕坐标: ({btn_screen_x}, {btn_screen_y})")
    else:
        # 估算位置：工具栏在 y=37，按钮约 x=50
        btn_screen_x = window_info["x"] + 50
        btn_screen_y = window_info["y"] + 50
        print(f"  ⚠️  未找到按钮，使用估算屏幕坐标: ({btn_screen_x}, {btn_screen_y})")
    
    # ========== 步骤 4: 点击"新建"按钮 ==========
    print_step(4, "点击'新建'按钮（人工操作）")
    
    print(f"🖱️  移动鼠标到 '新建' 按钮: ({btn_screen_x}, {btn_screen_y})")
    pyautogui.moveTo(btn_screen_x, btn_screen_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击 '新建' 按钮")
    pyautogui.click(btn_screen_x, btn_screen_y)
    time.sleep(1.5)
    
    take_screenshot("win_center_step4_new_clicked")
    
    # ========== 步骤 5: 点击对话框输入框 ==========
    print_step(5, "点击对话框输入框（人工操作）")
    
    # 对话框在窗口中央，尺寸约 500x400
    # 输入框在对话框上部
    dialog_input_x = window_center_x
    dialog_input_y = window_center_y - 50
    
    print(f"  对话框输入框估算位置: ({dialog_input_x}, {dialog_input_y})")
    print(f"🖱️  移动鼠标到输入框")
    pyautogui.moveTo(dialog_input_x, dialog_input_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击输入框")
    pyautogui.click(dialog_input_x, dialog_input_y)
    time.sleep(0.5)
    
    take_screenshot("win_center_step5_input_clicked")
    
    # ========== 步骤 6: 输入 Agent 名称 ==========
    print_step(6, "输入 Agent 名称（人工操作）")
    
    print("⌨️  按 Ctrl+A 全选")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('a')
    pyautogui.keyUp('a')
    pyautogui.keyUp('ctrl')
    time.sleep(0.3)
    
    agent_name = "window_center_agent"
    print(f"⌨️  输入 Agent 名称: '{agent_name}'")
    pyautogui.typewrite(agent_name, interval=0.03)
    time.sleep(0.5)
    
    take_screenshot("win_center_step6_name_typed")
    
    # ========== 步骤 7: 点击确认按钮 ==========
    print_step(7, "点击确认按钮（人工操作）")
    
    # 确认按钮在对话框右下角
    ok_x = window_center_x + 100
    ok_y = window_center_y + 80
    
    print(f"🖱️  移动鼠标到确认按钮: ({ok_x}, {ok_y})")
    pyautogui.moveTo(ok_x, ok_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击确认按钮")
    pyautogui.click(ok_x, ok_y)
    time.sleep(2)
    
    take_screenshot("win_center_step7_created")
    
    # ========== 步骤 8: 验证结果 ==========
    print_step(8, "验证创建结果（信息获取）")
    
    result = api_request("GET", "/api/state")
    state = result.get("state", {})
    project = state.get('project', {})
    
    if project.get('open'):
        print(f"✅ Agent 项目创建成功!")
        print(f"   项目名称: {project.get('name', 'unknown')}")
        print(f"   项目路径: {project.get('path', 'unknown')}")
    else:
        print(f"⚠️  项目状态: 未打开")
    
    take_screenshot("win_center_step8_final")
    
    print("\n" + "="*60)
    print("🎉 操作完成!")
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
