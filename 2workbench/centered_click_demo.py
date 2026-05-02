#!/usr/bin/env python3
"""先将窗口和鼠标移到正中心，然后创建 Agent

完全模拟人工操作，结合结构化状态 API 获取控件位置。
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


def get_screen_size() -> tuple[int, int]:
    """获取屏幕尺寸"""
    return pyautogui.size()


def print_step(step_num: int, description: str):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {description}")
    print('='*60)


def main():
    """主流程：窗口和鼠标移到正中心后创建 Agent"""
    print("="*60)
    print("Game Master Agent IDE - 窗口和鼠标正中心对齐")
    print("="*60)
    print("\n⚠️  即将开始模拟人工操作...")
    print("     3秒后将控制您的鼠标和键盘！")
    time.sleep(3)
    
    # ========== 步骤 1: 获取屏幕和窗口信息 ==========
    print_step(1, "获取屏幕和窗口信息")
    
    screen_width, screen_height = get_screen_size()
    print(f"  屏幕尺寸: {screen_width}x{screen_height}")
    
    # 获取窗口信息
    result = api_request("GET", "/api/dom")
    tree = result.get("tree", {})
    window_geom = tree.get("geometry", {})
    window_width = window_geom.get("width", 1600)
    window_height = window_geom.get("height", 1000)
    print(f"  窗口尺寸: {window_width}x{window_height}")
    
    # 计算屏幕中心和窗口应该移动到的位置
    screen_center_x = screen_width // 2
    screen_center_y = screen_height // 2
    print(f"  屏幕中心: ({screen_center_x}, {screen_center_y})")
    
    take_screenshot("centered_step1_info")
    
    # ========== 步骤 2: 将鼠标移到屏幕正中心 ==========
    print_step(2, "将鼠标移到屏幕正中心")
    
    print(f"🖱️  移动鼠标到屏幕正中心: ({screen_center_x}, {screen_center_y})")
    pyautogui.moveTo(screen_center_x, screen_center_y, duration=0.5)
    time.sleep(0.5)
    
    take_screenshot("centered_step2_mouse_centered")
    
    # ========== 步骤 3: 计算控件相对位置并点击"新建"按钮 ==========
    print_step(3, "计算控件相对位置并点击'新建'按钮（人工操作）")
    
    # 从 Widget 树中找到工具栏
    def find_toolbar(widget):
        if widget.get("class") == "QToolBar":
            return widget
        for child in widget.get("children", []):
            result = find_toolbar(child)
            if result:
                return result
        return None
    
    toolbar = find_toolbar(tree)
    if toolbar:
        toolbar_geom = toolbar.get("geometry", {})
        toolbar_y = toolbar_geom.get("y", 37)
        toolbar_height = toolbar_geom.get("height", 30)
        print(f"  工具栏位置: y={toolbar_y}, height={toolbar_height}")
        
        # 查找"新建"按钮
        def find_new_button(widget):
            if widget.get("class") == "QToolButton" and "新建" in widget.get("text", ""):
                return widget
            for child in widget.get("children", []):
                result = find_new_button(child)
                if result:
                    return result
            return None
        
        new_button = find_new_button(tree)
        if new_button:
            btn_geom = new_button.get("geometry", {})
            # 计算按钮中心相对于窗口的位置
            btn_center_x = btn_geom.get("x", 0) + btn_geom.get("width", 0) // 2
            btn_center_y = btn_geom.get("y", 0) + btn_geom.get("height", 0) // 2
            print(f"  🎯 '新建'按钮相对窗口位置: ({btn_center_x}, {btn_center_y})")
        else:
            # 估算位置：工具栏左侧第一个按钮
            btn_center_x = 50
            btn_center_y = toolbar_y + toolbar_height // 2
            print(f"  ⚠️  未找到按钮，使用估算位置: ({btn_center_x}, {btn_center_y})")
    else:
        btn_center_x, btn_center_y = 50, 55
        print(f"  ⚠️  未找到工具栏，使用默认位置: ({btn_center_x}, {btn_center_y})")
    
    print(f"🖱️  移动鼠标到 '新建' 按钮: ({btn_center_x}, {btn_center_y})")
    pyautogui.moveTo(btn_center_x, btn_center_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击 '新建' 按钮")
    pyautogui.click(btn_center_x, btn_center_y)
    time.sleep(1.5)
    
    take_screenshot("centered_step3_new_clicked")
    
    # ========== 步骤 4: 点击对话框中的输入框 ==========
    print_step(4, "点击对话框中的输入框（人工操作）")
    
    # 对话框在屏幕中央，尺寸约 500x400
    # 输入框在对话框上部，约 y=200
    # 对话框居中：x = (1600-500)/2 = 550, 中心 x = 800
    dialog_center_x = screen_center_x
    dialog_center_y = screen_center_y
    input_x = dialog_center_x
    input_y = dialog_center_y - 50  # 输入框在中心偏上
    
    print(f"  对话框中心: ({dialog_center_x}, {dialog_center_y})")
    print(f"🖱️  移动鼠标到输入框: ({input_x}, {input_y})")
    pyautogui.moveTo(input_x, input_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击输入框")
    pyautogui.click(input_x, input_y)
    time.sleep(0.5)
    
    take_screenshot("centered_step4_input_clicked")
    
    # ========== 步骤 5: 输入 Agent 名称 ==========
    print_step(5, "输入 Agent 名称（人工操作）")
    
    print("⌨️  按 Ctrl+A 全选")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('a')
    pyautogui.keyUp('a')
    pyautogui.keyUp('ctrl')
    time.sleep(0.3)
    
    agent_name = "centered_agent"
    print(f"⌨️  输入 Agent 名称: '{agent_name}'")
    pyautogui.typewrite(agent_name, interval=0.03)
    time.sleep(0.5)
    
    take_screenshot("centered_step5_name_typed")
    
    # ========== 步骤 6: 点击确认按钮 ==========
    print_step(6, "点击确认按钮（人工操作）")
    
    # 确认按钮在对话框右下角
    # 对话框宽度 500，高度约 400
    # 确认按钮在对话框右下角，相对中心偏移约 (+150, +100)
    ok_x = dialog_center_x + 100
    ok_y = dialog_center_y + 80
    
    print(f"🖱️  移动鼠标到确认按钮: ({ok_x}, {ok_y})")
    pyautogui.moveTo(ok_x, ok_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击确认按钮")
    pyautogui.click(ok_x, ok_y)
    time.sleep(2)
    
    take_screenshot("centered_step6_created")
    
    # ========== 步骤 7: 验证结果 ==========
    print_step(7, "验证创建结果（信息获取）")
    
    # 获取最终状态
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
    
    take_screenshot("centered_step7_final")
    
    print("\n" + "="*60)
    print("🎉 操作完成!")
    print("="*60)
    print("\n📁 所有截图已保存到 screenshots/ 目录")


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
