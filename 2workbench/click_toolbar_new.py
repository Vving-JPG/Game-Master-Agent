#!/usr/bin/env python3
"""点击工具栏上的"新建"按钮创建 Agent

完全模拟人工操作，只使用鼠标和键盘。
结合结构化状态 API 获取控件位置信息。
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


def find_widget_by_text(text: str) -> tuple[int, int] | None:
    """通过 API 查找包含特定文本的 Widget 位置"""
    result = api_request("GET", f"/api/find?text={text}")
    
    results = result.get("results", [])
    if not results:
        return None
    
    # 获取第一个匹配的 widget 的几何信息
    widget = results[0]
    geom = widget.get("geometry", {})
    x = geom.get("x", 0)
    y = geom.get("y", 0)
    width = geom.get("width", 0)
    height = geom.get("height", 0)
    
    # 计算中心点
    center_x = x + width // 2
    center_y = y + height // 2
    
    print(f"  找到控件: {widget.get('class')} '{widget.get('text')}' at ({center_x}, {center_y})")
    return (center_x, center_y)


def print_step(step_num: int, description: str):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {description}")
    print('='*60)


def main():
    """主流程：点击工具栏新建按钮创建 Agent"""
    print("="*60)
    print("Game Master Agent IDE - 点击工具栏新建按钮")
    print("="*60)
    print("\n⚠️  即将开始模拟人工操作...")
    print("     3秒后将控制您的鼠标和键盘！")
    time.sleep(3)
    
    # ========== 步骤 1: 查找并点击"新建"按钮 ==========
    print_step(1, "查找并点击工具栏'新建'按钮（人工操作）")
    
    # 通过 API 查找"新建"按钮位置
    print("🔍 通过结构化状态 API 查找'新建'按钮位置...")
    new_button_pos = find_widget_by_text("📂 新建")
    
    if new_button_pos:
        btn_x, btn_y = new_button_pos
    else:
        # 如果找不到，使用默认位置（工具栏通常在菜单栏下方）
        print("  未通过 API 找到，使用默认位置")
        btn_x, btn_y = 80, 65  # 工具栏按钮的估算位置
    
    print(f"🖱️  移动鼠标到 '新建' 按钮: ({btn_x}, {btn_y})")
    pyautogui.moveTo(btn_x, btn_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击 '新建' 按钮")
    pyautogui.click(btn_x, btn_y)
    time.sleep(1.5)
    
    take_screenshot("toolbar_step1_clicked")
    
    # ========== 步骤 2: 点击输入框 ==========
    print_step(2, "点击输入框（人工操作）")
    
    # 对话框在屏幕中央
    input_x, input_y = 800, 480
    print(f"🖱️  移动鼠标到输入框: ({input_x}, {input_y})")
    pyautogui.moveTo(input_x, input_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击输入框")
    pyautogui.click(input_x, input_y)
    time.sleep(0.5)
    
    take_screenshot("toolbar_step2_input")
    
    # ========== 步骤 3: 输入 Agent 名称 ==========
    print_step(3, "输入 Agent 名称（人工操作）")
    
    print("⌨️  按 Ctrl+A 全选")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('a')
    pyautogui.keyUp('a')
    pyautogui.keyUp('ctrl')
    time.sleep(0.3)
    
    agent_name = "toolbar_created_agent"
    print(f"⌨️  输入 Agent 名称: '{agent_name}'")
    pyautogui.typewrite(agent_name, interval=0.03)
    time.sleep(0.5)
    
    take_screenshot("toolbar_step3_typed")
    
    # ========== 步骤 4: 点击确认按钮 ==========
    print_step(4, "点击确认按钮（人工操作）")
    
    # 确认按钮在对话框右下角
    ok_x, ok_y = 920, 580
    print(f"🖱️  移动鼠标到确认按钮: ({ok_x}, {ok_y})")
    pyautogui.moveTo(ok_x, ok_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击确认按钮")
    pyautogui.click(ok_x, ok_y)
    time.sleep(2)
    
    take_screenshot("toolbar_step4_created")
    
    # ========== 步骤 5: 验证结果 ==========
    print_step(5, "验证创建结果（信息获取）")
    
    # 获取最终状态
    result = api_request("GET", "/api/state")
    state = result.get("state", {})
    project = state.get('project', {})
    
    if project.get('open'):
        print(f"✅ Agent 项目创建成功!")
        print(f"   项目名称: {project.get('name', 'unknown')}")
        print(f"   项目路径: {project.get('path', 'unknown')}")
    else:
        print(f"⚠️  项目状态: 未打开")
        print(f"   可能原因: 坐标不准确，未正确点击到按钮")
    
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
