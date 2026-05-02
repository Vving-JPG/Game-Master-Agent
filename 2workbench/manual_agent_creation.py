#!/usr/bin/env python3
"""完全模拟人工操作创建 Agent

只使用鼠标和键盘点击，不通过 API 直接操作。
结合屏幕截图和结构化状态 API 获取信息。
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
pyautogui.PAUSE = 0.5

BASE_URL = "http://127.0.0.1:18080"


def api_request(method: str, path: str, data: dict | None = None) -> dict:
    """发送 HTTP API 请求 - 仅用于获取信息，不用于操作"""
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


def get_state() -> dict:
    """获取应用状态 - 仅用于信息获取"""
    result = api_request("GET", "/api/state")
    return result.get("state", {})


def get_dom(selector: str | None = None) -> dict:
    """获取 Widget DOM 树 - 仅用于信息获取"""
    path = "/api/dom"
    if selector:
        path += f"?selector={selector}"
    result = api_request("GET", path)
    return result.get("tree", {})


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


def print_step(step_num: int, description: str):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {description}")
    print('='*60)


def find_widget_position(query: dict) -> tuple[int, int] | None:
    """通过 API 查找 Widget 位置，返回中心坐标"""
    query_str = "&".join([f"{k}={v}" for k, v in query.items()])
    result = api_request("GET", f"/api/find?{query_str}")
    
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
    
    return (center_x, center_y)


def main():
    """主流程：完全模拟人工创建 Agent"""
    print("="*60)
    print("Game Master Agent IDE - 完全模拟人工创建 Agent")
    print("="*60)
    print("\n⚠️  警告：这是一个自动化脚本，将模拟真实人工操作")
    print("     请在 3 秒内将鼠标移动到安全位置...")
    time.sleep(3)
    
    # ========== 步骤 1: 获取初始状态（信息获取） ==========
    print_step(1, "获取初始应用状态（信息获取）")
    
    state = get_state()
    print(f"📁 项目状态: {'已打开' if state.get('project', {}).get('open') else '未打开'}")
    print(f"🎨 主题: {state.get('ui', {}).get('theme', 'unknown')}")
    
    window_size = state.get('ui', {}).get('window', {}).get('size', {})
    window_width = window_size.get('width', 1600)
    window_height = window_size.get('height', 1000)
    print(f"📐 窗口尺寸: {window_width}x{window_height}")
    
    # 截图记录初始状态
    take_screenshot("manual_step1_initial")
    
    # ========== 步骤 2: 点击 File 菜单（人工操作） ==========
    print_step(2, "点击 File 菜单（人工操作）")
    
    # 通过 DOM 获取菜单栏位置信息
    menubar_dom = get_dom("menubar")
    menubar_geom = menubar_dom.get("geometry", {})
    print(f"菜单栏位置: x={menubar_geom.get('x')}, y={menubar_geom.get('y')}, "
          f"width={menubar_geom.get('width')}, height={menubar_geom.get('height')}")
    
    # File 菜单通常在左上角，估算位置
    # 根据菜单栏高度约 37px，File 菜单在 (40, 20) 左右
    file_menu_x, file_menu_y = 50, 25
    print(f"🖱️  模拟人工点击 File 菜单: ({file_menu_x}, {file_menu_y})")
    
    pyautogui.click(file_menu_x, file_menu_y)
    time.sleep(0.8)
    
    # 截图记录菜单打开状态
    take_screenshot("manual_step2_file_menu")
    
    # ========== 步骤 3: 点击 New Agent Project（人工操作） ==========
    print_step(3, "点击 New Agent Project（人工操作）")
    
    # File 菜单打开后，New Agent Project 选项通常在 File 下方
    # 菜单项高度约 25-30px，New Agent Project 在第 1 个位置
    new_project_x, new_project_y = 50, 60
    print(f"🖱️  模拟人工点击 '新建 Agent 项目': ({new_project_x}, {new_project_y})")
    
    pyautogui.click(new_project_x, new_project_y)
    time.sleep(1.5)
    
    # 截图记录对话框
    take_screenshot("manual_step3_dialog_opened")
    
    # ========== 步骤 4: 填写 Agent 名称（人工操作） ==========
    print_step(4, "填写 Agent 名称（人工操作）")
    
    # 对话框通常在屏幕中央
    # 根据窗口尺寸 1600x1000，中心位置约为 (800, 500)
    # 输入框在对话框中央偏上
    input_x, input_y = 800, 450
    print(f"🖱️  模拟人工点击输入框: ({input_x}, {input_y})")
    
    pyautogui.click(input_x, input_y)
    time.sleep(0.5)
    
    # 清除现有内容（Ctrl+A 然后 Delete）
    print("⌨️  模拟人工按 Ctrl+A 全选")
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.3)
    
    # 输入 Agent 名称
    agent_name = "my_manual_agent"
    print(f"⌨️  模拟人工输入 Agent 名称: '{agent_name}'")
    pyautogui.typewrite(agent_name, interval=0.05)
    time.sleep(0.5)
    
    # 截图记录输入状态
    take_screenshot("manual_step4_name_typed")
    
    # ========== 步骤 5: 点击确认按钮（人工操作） ==========
    print_step(5, "点击确认按钮创建 Agent（人工操作）")
    
    # 确认按钮通常在对话框右下角
    # 估算位置：中心偏右下方
    ok_button_x, ok_button_y = 950, 600
    print(f"🖱️  模拟人工点击确认按钮: ({ok_button_x}, {ok_button_y})")
    
    pyautogui.click(ok_button_x, ok_button_y)
    time.sleep(2)
    
    # 截图记录创建结果
    take_screenshot("manual_step5_created")
    
    # ========== 步骤 6: 验证创建结果（信息获取） ==========
    print_step(6, "验证 Agent 创建结果（信息获取）")
    
    # 再次获取状态
    final_state = get_state()
    project = final_state.get('project', {})
    
    if project.get('open'):
        print(f"✅ Agent 项目创建成功!")
        print(f"   项目名称: {project.get('name', 'unknown')}")
        print(f"   项目路径: {project.get('path', 'unknown')}")
        print(f"   模板: {project.get('template', 'unknown')}")
    else:
        print(f"⚠️  项目状态: 未打开，可能创建过程中出现问题")
        print(f"   建议检查截图了解实际情况")
    
    # 获取 DOM 查看资源树
    dom = get_dom()
    print(f"\n📊 Widget DOM 树摘要:")
    print(f"   根节点: {dom.get('class', 'unknown')}")
    print(f"   子节点数: {len(dom.get('children', []))}")
    
    # 最终截图
    take_screenshot("manual_step6_final")
    
    print("\n" + "="*60)
    print("🎉 人工模拟操作完成!")
    print("="*60)
    print("\n📁 所有截图已保存到 screenshots/ 目录")
    print("   请查看截图了解操作过程的实际情况")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 自动化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
