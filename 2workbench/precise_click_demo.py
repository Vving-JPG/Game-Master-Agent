#!/usr/bin/env python3
"""使用结构化状态 API 获取精确位置后点击创建 Agent

完全模拟人工操作，结合 state_api.md 中的结构化状态 API 获取控件位置。
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


def get_widget_tree() -> dict:
    """获取完整 Widget DOM 树"""
    result = api_request("GET", "/api/dom")
    return result.get("tree", {})


def find_widget_in_tree(tree: dict, predicate) -> dict | None:
    """在 Widget 树中查找符合条件的控件"""
    if predicate(tree):
        return tree
    
    for child in tree.get("children", []):
        result = find_widget_in_tree(child, predicate)
        if result:
            return result
    
    return None


def get_center_position(widget: dict) -> tuple[int, int]:
    """获取控件中心点坐标"""
    geom = widget.get("geometry", {})
    x = geom.get("x", 0)
    y = geom.get("y", 0)
    width = geom.get("width", 0)
    height = geom.get("height", 0)
    
    center_x = x + width // 2
    center_y = y + height // 2
    
    return (center_x, center_y)


def print_step(step_num: int, description: str):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {description}")
    print('='*60)


def main():
    """主流程：使用精确位置点击创建 Agent"""
    print("="*60)
    print("Game Master Agent IDE - 使用结构化状态 API 精确点击")
    print("="*60)
    print("\n⚠️  即将开始模拟人工操作...")
    print("     3秒后将控制您的鼠标和键盘！")
    time.sleep(3)
    
    # ========== 步骤 1: 获取 Widget 树 ==========
    print_step(1, "通过结构化状态 API 获取 Widget DOM 树")
    
    tree = get_widget_tree()
    print(f"  根节点: {tree.get('class')}")
    print(f"  窗口尺寸: {tree.get('geometry', {}).get('width')}x{tree.get('geometry', {}).get('height')}")
    
    # 查找工具栏
    toolbar = find_widget_in_tree(tree, lambda w: w.get("class") == "QToolBar")
    if toolbar:
        print(f"  找到工具栏: {toolbar.get('text')} at y={toolbar.get('geometry', {}).get('y')}")
    
    take_screenshot("precise_step1_initial")
    
    # ========== 步骤 2: 查找并点击"新建"按钮 ==========
    print_step(2, "在 Widget 树中查找'新建'按钮并点击（人工操作）")
    
    # 查找包含"新建"文本的 QToolButton
    def is_new_button(w):
        return w.get("class") == "QToolButton" and "新建" in w.get("text", "")
    
    new_button = find_widget_in_tree(tree, is_new_button)
    
    if new_button:
        btn_x, btn_y = get_center_position(new_button)
        print(f"  🎯 找到'新建'按钮: '{new_button.get('text')}' at ({btn_x}, {btn_y})")
        print(f"  📐 按钮尺寸: {new_button.get('geometry', {}).get('width')}x{new_button.get('geometry', {}).get('height')}")
    else:
        # 如果找不到，根据工具栏位置估算
        if toolbar:
            toolbar_geom = toolbar.get("geometry", {})
            # 工具栏第一个按钮通常在工具栏左侧，约 x=50
            btn_x = toolbar_geom.get("x", 0) + 50
            btn_y = toolbar_geom.get("y", 0) + toolbar_geom.get("height", 0) // 2
        else:
            btn_x, btn_y = 50, 60
        print(f"  ⚠️  未找到按钮，使用估算位置: ({btn_x}, {btn_y})")
    
    print(f"🖱️  移动鼠标到 '新建' 按钮: ({btn_x}, {btn_y})")
    pyautogui.moveTo(btn_x, btn_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击 '新建' 按钮")
    pyautogui.click(btn_x, btn_y)
    time.sleep(1.5)
    
    take_screenshot("precise_step2_clicked")
    
    # ========== 步骤 3: 获取对话框位置并点击输入框 ==========
    print_step(3, "获取对话框位置并点击输入框（人工操作）")
    
    # 重新获取 Widget 树，此时应该包含对话框
    tree = get_widget_tree()
    
    # 查找 QLineEdit（输入框）
    def is_name_input(w):
        return w.get("class") == "QLineEdit" and w.get("id") == "_name_edit"
    
    name_input = find_widget_in_tree(tree, is_name_input)
    
    if name_input:
        input_x, input_y = get_center_position(name_input)
        print(f"  🎯 找到输入框: '{name_input.get('id')}' at ({input_x}, {input_y})")
    else:
        # 对话框通常在屏幕中央
        # 根据 p6_state_api.md，对话框最小宽度 500
        # 主窗口 1600x1000，对话框居中
        input_x, input_y = 800, 500
        print(f"  ⚠️  未找到输入框，使用估算位置: ({input_x}, {input_y})")
    
    print(f"🖱️  移动鼠标到输入框: ({input_x}, {input_y})")
    pyautogui.moveTo(input_x, input_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击输入框")
    pyautogui.click(input_x, input_y)
    time.sleep(0.5)
    
    take_screenshot("precise_step3_input")
    
    # ========== 步骤 4: 输入 Agent 名称 ==========
    print_step(4, "输入 Agent 名称（人工操作）")
    
    print("⌨️  按 Ctrl+A 全选")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('a')
    pyautogui.keyUp('a')
    pyautogui.keyUp('ctrl')
    time.sleep(0.3)
    
    agent_name = "precise_agent"
    print(f"⌨️  输入 Agent 名称: '{agent_name}'")
    pyautogui.typewrite(agent_name, interval=0.03)
    time.sleep(0.5)
    
    take_screenshot("precise_step4_typed")
    
    # ========== 步骤 5: 查找并点击确认按钮 ==========
    print_step(5, "查找并点击确认按钮（人工操作）")
    
    # 重新获取 Widget 树
    tree = get_widget_tree()
    
    # 查找 QDialogButtonBox 中的 OK 按钮
    def is_ok_button(w):
        return w.get("class") == "QPushButton" and "OK" in w.get("text", "")
    
    ok_button = find_widget_in_tree(tree, is_ok_button)
    
    if ok_button:
        ok_x, ok_y = get_center_position(ok_button)
        print(f"  🎯 找到确认按钮: '{ok_button.get('text')}' at ({ok_x}, {ok_y})")
    else:
        # 确认按钮通常在对话框右下角
        # 对话框宽度 500，在屏幕中央 (800, 500)
        # 确认按钮在对话框右下角，约 (950, 600)
        ok_x, ok_y = 950, 600
        print(f"  ⚠️  未找到确认按钮，使用估算位置: ({ok_x}, {ok_y})")
    
    print(f"🖱️  移动鼠标到确认按钮: ({ok_x}, {ok_y})")
    pyautogui.moveTo(ok_x, ok_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击确认按钮")
    pyautogui.click(ok_x, ok_y)
    time.sleep(2)
    
    take_screenshot("precise_step5_created")
    
    # ========== 步骤 6: 验证结果 ==========
    print_step(6, "验证创建结果（信息获取）")
    
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
        print(f"   可能原因: 坐标仍不准确，或对话框未正确弹出")
    
    # 获取最终 DOM
    tree = get_widget_tree()
    print(f"\n📊 最终 Widget 树摘要:")
    print(f"   根节点: {tree.get('class', 'unknown')}")
    children = tree.get("children", [])
    print(f"   子节点数: {len(children)}")
    for child in children[:3]:
        print(f"     - {child.get('class')}: {child.get('text', '')[:30]}")
    
    take_screenshot("precise_step6_final")
    
    print("\n" + "="*60)
    print("🎉 精确点击操作完成!")
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
