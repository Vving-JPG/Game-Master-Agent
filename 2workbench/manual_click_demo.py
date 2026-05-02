#!/usr/bin/env python3
"""演示纯人工点击操作 - 创建 Agent

完全模拟人工操作，只使用鼠标和键盘。
"""
from __future__ import annotations

import time
import sys
from pathlib import Path

import pyautogui

# 设置安全模式
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3


def take_screenshot(name: str) -> str:
    """截取屏幕截图"""
    import base64
    import json
    import urllib.request
    from datetime import datetime
    
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:18080/api/screenshot",
            headers={"Content-Type": "application/json"},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            
            if "error" in data:
                return ""
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            output_path = screenshots_dir / f"{name}_{timestamp}.png"
            
            img_data = base64.b64decode(data['base64'])
            with open(output_path, 'wb') as f:
                f.write(img_data)
            
            print(f"[OK] 截图已保存: {output_path}")
            return str(output_path)
    except Exception as e:
        print(f"[X] 截图失败: {e}")
        return ""


def print_step(step_num: int, description: str):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {description}")
    print('='*60)


def main():
    """主流程：完全模拟人工创建 Agent"""
    print("="*60)
    print("Game Master Agent IDE - 纯人工点击演示")
    print("="*60)
    print("\n⚠️  即将开始模拟人工操作...")
    print("     3秒后将控制您的鼠标和键盘！")
    print("     如需取消，请将鼠标快速移动到屏幕角落触发 FAILSAFE")
    time.sleep(3)
    
    # ========== 步骤 1: 点击"文件"菜单 ==========
    print_step(1, "点击'文件'菜单（人工操作）")
    
    # 从截图看，"文件(F)"在左上角，约 (30, 20) 位置
    file_menu_x, file_menu_y = 30, 20
    print(f"🖱️  移动鼠标到 '文件' 菜单: ({file_menu_x}, {file_menu_y})")
    pyautogui.moveTo(file_menu_x, file_menu_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击 '文件' 菜单")
    pyautogui.click(file_menu_x, file_menu_y)
    time.sleep(0.8)
    
    take_screenshot("click_step1_file_menu")
    
    # ========== 步骤 2: 点击"新建 Agent 项目" ==========
    print_step(2, "点击'新建 Agent 项目'（人工操作）")
    
    # 菜单打开后，第一个菜单项在菜单下方约 30px
    # 估算位置：在 File 菜单下方
    new_project_x, new_project_y = 30, 50
    print(f"🖱️  移动鼠标到 '新建 Agent 项目': ({new_project_x}, {new_project_y})")
    pyautogui.moveTo(new_project_x, new_project_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击 '新建 Agent 项目'")
    pyautogui.click(new_project_x, new_project_y)
    time.sleep(1.5)
    
    take_screenshot("click_step2_menu_item")
    
    # ========== 步骤 3: 点击输入框 ==========
    print_step(3, "点击输入框（人工操作）")
    
    # 对话框在屏幕中央，输入框在对话框中央偏上
    # 窗口尺寸约 1600x1000，中心点 (800, 500)
    # 对话框通常比窗口小，输入框在对话框上部
    input_x, input_y = 800, 480
    print(f"🖱️  移动鼠标到输入框: ({input_x}, {input_y})")
    pyautogui.moveTo(input_x, input_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击输入框")
    pyautogui.click(input_x, input_y)
    time.sleep(0.5)
    
    take_screenshot("click_step3_input_box")
    
    # ========== 步骤 4: 输入 Agent 名称 ==========
    print_step(4, "输入 Agent 名称（人工操作）")
    
    print("⌨️  按 Ctrl+A 全选现有内容")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('a')
    pyautogui.keyUp('a')
    pyautogui.keyUp('ctrl')
    time.sleep(0.3)
    
    agent_name = "my_clicked_agent"
    print(f"⌨️  输入 Agent 名称: '{agent_name}'")
    pyautogui.typewrite(agent_name, interval=0.03)
    time.sleep(0.5)
    
    take_screenshot("click_step4_name_entered")
    
    # ========== 步骤 5: 点击确认按钮 ==========
    print_step(5, "点击确认按钮（人工操作）")
    
    # 确认按钮通常在对话框右下角
    # 估算位置：中心偏右下方
    ok_button_x, ok_button_y = 920, 580
    print(f"🖱️  移动鼠标到确认按钮: ({ok_button_x}, {ok_button_y})")
    pyautogui.moveTo(ok_button_x, ok_button_y, duration=0.5)
    time.sleep(0.3)
    print(f"🖱️  点击确认按钮")
    pyautogui.click(ok_button_x, ok_button_y)
    time.sleep(2)
    
    take_screenshot("click_step5_created")
    
    print("\n" + "="*60)
    print("🎉 人工点击操作完成!")
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
