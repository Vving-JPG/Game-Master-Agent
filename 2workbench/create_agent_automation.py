#!/usr/bin/env python3
"""自动化创建 Agent 的脚本

模拟人工操作 GUI 完成 Agent 创建流程:
1. 点击 File 菜单
2. 点击 New Agent Project
3. 填写 Agent 名称
4. 确认创建

结合结构化状态 API 和屏幕截图进行信息获取。
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
    """发送 HTTP API 请求"""
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


def get_state() -> dict:
    """获取应用状态"""
    result = api_request("GET", "/api/state")
    return result.get("state", {})


def get_dom(selector: str | None = None) -> dict:
    """获取 Widget DOM 树"""
    path = "/api/dom"
    if selector:
        path += f"?selector={selector}"
    result = api_request("GET", path)
    return result.get("tree", {})


def find_widget(query: dict) -> list:
    """查找 Widget"""
    query_str = "&".join([f"{k}={v}" for k, v in query.items()])
    result = api_request("GET", f"/api/find?{query_str}")
    return result.get("results", [])


def print_step(step_num: int, description: str):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {description}")
    print('='*60)


def main():
    """主流程：自动化创建 Agent"""
    print("="*60)
    print("Game Master Agent IDE - 自动化创建 Agent")
    print("="*60)
    print("\n结合结构化状态 API 和屏幕截图进行信息获取")
    print("3秒后开始自动化操作...")
    time.sleep(3)
    
    # ========== 步骤 1: 获取初始状态 ==========
    print_step(1, "获取初始应用状态")
    
    state = get_state()
    print(f"📁 项目状态: {'已打开' if state.get('project', {}).get('open') else '未打开'}")
    print(f"🤖 Agent 状态: {state.get('agent', {}).get('status', 'unknown')}")
    print(f"🎨 主题: {state.get('ui', {}).get('theme', 'unknown')}")
    print(f"📐 窗口尺寸: {state.get('ui', {}).get('window', {}).get('size', {})}")
    
    # 截图记录初始状态
    take_screenshot("step1_initial")
    
    # ========== 步骤 2: 点击 File 菜单 ==========
    print_step(2, "点击 File 菜单")
    
    # 获取菜单栏信息
    menubar_dom = get_dom("menubar")
    print(f"菜单栏信息: {json.dumps(menubar_dom, ensure_ascii=False, indent=2)[:200]}")
    
    # 查找 File 菜单位置（通常在左上角）
    # 根据截图，File 菜单在 (30, 20) 附近
    file_menu_x, file_menu_y = 40, 35
    print(f"点击 File 菜单位置: ({file_menu_x}, {file_menu_y})")
    
    pyautogui.click(file_menu_x, file_menu_y)
    time.sleep(0.5)
    
    # 截图记录菜单打开状态
    take_screenshot("step2_file_menu_opened")
    
    # ========== 步骤 3: 点击 New Agent Project ==========
    print_step(3, "点击 New Agent Project")
    
    # File 菜单打开后，New Agent Project 通常在 File 下方
    # 估算位置：File 菜单下方约 100px
    new_project_x, new_project_y = 40, 80
    print(f"点击 New Agent Project 位置: ({new_project_x}, {new_project_y})")
    
    pyautogui.click(new_project_x, new_project_y)
    time.sleep(1)
    
    # 截图记录对话框
    screenshot_path = take_screenshot("step3_new_project_dialog")
    
    # ========== 步骤 4: 填写 Agent 名称 ==========
    print_step(4, "填写 Agent 名称")
    
    # 查找对话框中的输入框
    # 根据常见的对话框布局，输入框在中心位置
    # 窗口大小约为 1600x1000，中心位置约为 (800, 500)
    input_x, input_y = 800, 500
    print(f"点击输入框位置: ({input_x}, {input_y})")
    
    pyautogui.click(input_x, input_y)
    time.sleep(0.3)
    
    # 清除现有内容并输入新名称
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    
    agent_name = "my_automated_agent"
    print(f"输入 Agent 名称: {agent_name}")
    pyautogui.typewrite(agent_name, interval=0.01)
    time.sleep(0.3)
    
    # 截图记录输入状态
    take_screenshot("step4_name_entered")
    
    # ========== 步骤 5: 确认创建 ==========
    print_step(5, "点击确认按钮创建 Agent")
    
    # 确认按钮通常在对话框右下角
    # 估算位置：中心偏右下方
    ok_button_x, ok_button_y = 950, 600
    print(f"点击确认按钮位置: ({ok_button_x}, {ok_button_y})")
    
    pyautogui.click(ok_button_x, ok_button_y)
    time.sleep(2)
    
    # 截图记录创建结果
    take_screenshot("step5_agent_created")
    
    # ========== 步骤 6: 验证创建结果 ==========
    print_step(6, "验证 Agent 创建结果")
    
    # 再次获取状态
    final_state = get_state()
    project = final_state.get('project', {})
    
    if project.get('open'):
        print(f"[OK] Agent 项目创建成功!")
        print(f"   项目名称: {project.get('name', 'unknown')}")
        print(f"   项目路径: {project.get('path', 'unknown')}")
        print(f"   模板: {project.get('template', 'unknown')}")
    else:
        print(f"[?] 项目状态: 未打开，可能需要检查")
    
    # 获取 DOM 查看资源树
    dom = get_dom()
    print(f"\nWidget DOM 树摘要:")
    print(f"   根节点: {dom.get('class', 'unknown')}")
    print(f"   子节点数: {len(dom.get('children', []))}")
    
    # 最终截图
    take_screenshot("step6_final")
    
    print("\n" + "="*60)
    print("自动化流程完成!")
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] 自动化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
