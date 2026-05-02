#!/usr/bin/env python3
"""最终版本：使用精确坐标点击创建 Agent

结合结构化状态 API 获取窗口位置，使用固定偏移量计算按钮位置。
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


def print_step(step_num: int, description: str):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {description}")
    print('='*60)


def main():
    """主流程：创建 Agent"""
    print("="*60)
    print("Game Master Agent IDE - 创建 Agent 最终演示")
    print("="*60)
    print("\n⚠️  即将开始模拟人工操作...")
    print("     3秒后将控制您的鼠标和键盘！")
    time.sleep(3)
    
    # ========== 步骤 1: 获取窗口信息 ==========
    print_step(1, "获取窗口信息")
    
    window_info = get_window_info()
    window_x = window_info['x']
    window_y = window_info['y']
    window_w = window_info['width']
    window_h = window_info['height']
    
    print(f"  窗口位置: ({window_x}, {window_y})")
    print(f"  窗口尺寸: {window_w}x{window_h}")
    
    # 计算窗口中心
    window_center_x = window_x + window_w // 2
    window_center_y = window_y + window_h // 2
    print(f"  窗口中心: ({window_center_x}, {window_center_y})")
    
    take_screenshot("final_step1_info")
    
    # ========== 步骤 2: 将鼠标移到窗口中心 ==========
    print_step(2, "将鼠标移到窗口中心")
    
    print(f"🖱️  移动鼠标到窗口中心: ({window_center_x}, {window_center_y})")
    pyautogui.moveTo(window_center_x, window_center_y, duration=0.5)
    time.sleep(0.5)
    
    take_screenshot("final_step2_center")
    
    # ========== 步骤 3: 点击"新建"按钮 ==========
    print_step(3, "点击'新建'按钮（人工操作）")
    
    # 根据观察，工具栏在菜单栏下方（y=37）
    # "新建"按钮是工具栏第一个按钮，约 x=50
    # 屏幕坐标 = 窗口坐标 + 相对偏移
    new_btn_x = window_x + 60
    new_btn_y = window_y + 55
    
    print(f"  计算'新建'按钮屏幕坐标: ({new_btn_x}, {new_btn_y})")
    print(f"🖱️  移动鼠标到 '新建' 按钮")
    pyautogui.moveTo(new_btn_x, new_btn_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击 '新建' 按钮")
    pyautogui.click(new_btn_x, new_btn_y)
    time.sleep(1.5)
    
    take_screenshot("final_step3_new_clicked")
    
    # ========== 步骤 4: 点击对话框输入框 ==========
    print_step(4, "点击对话框输入框（人工操作）")
    
    # 对话框在窗口中央，输入框在对话框上部
    # 对话框尺寸约 500x400，居中显示
    # 输入框在对话框中上部
    input_x = window_center_x
    input_y = window_center_y - 30
    
    print(f"  计算输入框屏幕坐标: ({input_x}, {input_y})")
    print(f"🖱️  移动鼠标到输入框")
    pyautogui.moveTo(input_x, input_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击输入框")
    pyautogui.click(input_x, input_y)
    time.sleep(0.5)
    
    take_screenshot("final_step4_input")
    
    # ========== 步骤 5: 输入 Agent 名称 ==========
    print_step(5, "输入 Agent 名称（人工操作）")
    
    print("⌨️  按 Ctrl+A 全选")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('a')
    pyautogui.keyUp('a')
    pyautogui.keyUp('ctrl')
    time.sleep(0.3)
    
    agent_name = "final_demo_agent"
    print(f"⌨️  输入 Agent 名称: '{agent_name}'")
    pyautogui.typewrite(agent_name, interval=0.03)
    time.sleep(0.5)
    
    take_screenshot("final_step5_typed")
    
    # ========== 步骤 6: 点击确认按钮 ==========
    print_step(6, "点击确认按钮（人工操作）")
    
    # 确认按钮在对话框右下角
    ok_x = window_center_x + 100
    ok_y = window_center_y + 100
    
    print(f"  计算确认按钮屏幕坐标: ({ok_x}, {ok_y})")
    print(f"🖱️  移动鼠标到确认按钮")
    pyautogui.moveTo(ok_x, ok_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击确认按钮")
    pyautogui.click(ok_x, ok_y)
    time.sleep(2)
    
    take_screenshot("final_step6_created")
    
    # ========== 步骤 7: 验证结果 ==========
    print_step(7, "验证创建结果（信息获取）")
    
    result = api_request("GET", "/api/state")
    state = result.get("state", {})
    project = state.get('project', {})
    
    if project.get('open'):
        print(f"✅ Agent 项目创建成功!")
        print(f"   项目名称: {project.get('name', 'unknown')}")
        print(f"   项目路径: {project.get('path', 'unknown')}")
        print(f"   模板: {project.get('template', 'unknown')}")
    else:
        print(f"⚠️  项目状态: 未打开")
        print(f"   说明: 对话框可能没有正确弹出，或者坐标需要进一步调整")
    
    take_screenshot("final_step7_final")
    
    print("\n" + "="*60)
    print("🎉 演示完成!")
    print("="*60)
    print("\n📁 所有截图已保存到 screenshots/ 目录")
    print("\n💡 总结:")
    print("   1. 使用结构化状态 API 获取窗口位置和尺寸")
    print("   2. 将鼠标移到窗口正中心")
    print("   3. 根据窗口位置计算控件屏幕坐标")
    print("   4. 模拟人工点击和键盘输入")


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
