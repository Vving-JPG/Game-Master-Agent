#!/usr/bin/env python3
"""GUI 自动化控制工具

用于自动化控制 PyQt6 GUI 和 TUI 界面，支持截图、点击、输入等操作。

使用方法:
    python gui_automation.py --help
    python gui_automation.py screenshot
    python gui_automation.py click 100 200
    python gui_automation.py type "Hello World"
    python gui_automation.py key ctrl+n
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pyautogui

# 设置安全模式，防止鼠标失控时无法停止
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5


def take_screenshot(output_path: str | None = None) -> str:
    """截取屏幕截图
    
    通过 HTTP API 调用 server.py 的截图功能，支持 DPI 感知和自动前台/最小化。
    
    Args:
        output_path: 截图保存路径，默认为 screenshots/YYYYMMDD_HHMMSS.png
        
    Returns:
        截图保存路径
    """
    import base64
    import json
    from urllib.request import urlopen, Request
    from urllib.error import URLError
    
    # 默认保存路径
    if output_path is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshots_dir = Path("screenshots")
        screenshots_dir.mkdir(exist_ok=True)
        output_path = screenshots_dir / f"screenshot_{timestamp}.png"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 通过 HTTP API 调用 server.py 的截图功能
    try:
        req = Request("http://127.0.0.1:18080/api/screenshot", method="GET")
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            
            if "error" in data:
                raise RuntimeError(f"截图 API 错误: {data['error']}")
            
            # 解码 base64 图片数据
            img_data = base64.b64decode(data["base64"])
            
            # 保存图片
            with open(output_path, "wb") as f:
                f.write(img_data)
            
            print(f"截图已保存: {output_path}")
            print(f"尺寸: {data['width']}x{data['height']}")
            return str(output_path)
            
    except URLError as e:
        # 如果 HTTP API 不可用，回退到 pyautogui
        print(f"[警告] HTTP API 不可用 ({e})，使用 pyautogui 截图")
        screenshot = pyautogui.screenshot()
        screenshot.save(output_path)
        print(f"截图已保存: {output_path}")
        return str(output_path)
    except Exception as e:
        raise RuntimeError(f"截图失败: {e}")


def click_at(x: int, y: int, clicks: int = 1, button: str = "left") -> None:
    """在指定位置点击
    
    Args:
        x: X 坐标
        y: Y 坐标
        clicks: 点击次数
        button: 鼠标按钮 (left/right/middle)
    """
    pyautogui.click(x, y, clicks=clicks, button=button)
    print(f"已在 ({x}, {y}) 点击 {clicks} 次")


def click_on(image_path: str, confidence: float = 0.9) -> tuple[int, int] | None:
    """在屏幕上查找图像并点击
    
    Args:
        image_path: 要查找的图像路径
        confidence: 匹配置信度 (0-1)
        
    Returns:
        点击位置的坐标，如果未找到则返回 None
    """
    try:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        if location:
            center = pyautogui.center(location)
            pyautogui.click(center)
            print(f"已在图像位置 ({center.x}, {center.y}) 点击")
            return (center.x, center.y)
        else:
            print(f"未找到图像: {image_path}")
            return None
    except Exception as e:
        print(f"查找图像失败: {e}")
        return None


def type_text(text: str, interval: float = 0.01) -> None:
    """输入文本
    
    Args:
        text: 要输入的文本
        interval: 每个字符之间的间隔（秒）
    """
    pyautogui.typewrite(text, interval=interval)
    print(f"已输入文本: {text}")


def press_key(key: str) -> None:
    """按下键盘按键
    
    Args:
        key: 按键名称，如 'ctrl', 'alt', 'shift', 'enter', 'esc' 等
             组合键用 '+' 连接，如 'ctrl+n', 'alt+f4'
    """
    pyautogui.keyDown(key)
    pyautogui.keyUp(key)
    print(f"已按下按键: {key}")


def hotkey(*keys: str) -> None:
    """按下组合键
    
    Args:
        keys: 按键名称列表，如 'ctrl', 'n'
    """
    pyautogui.hotkey(*keys)
    print(f"已按下组合键: {'+'.join(keys)}")


def move_to(x: int, y: int, duration: float = 0.5) -> None:
    """移动鼠标到指定位置
    
    Args:
        x: X 坐标
        y: Y 坐标
        duration: 移动持续时间（秒）
    """
    pyautogui.moveTo(x, y, duration=duration)
    print(f"鼠标已移动到 ({x}, {y})")


def get_mouse_position() -> tuple[int, int]:
    """获取当前鼠标位置
    
    Returns:
        (x, y) 坐标
    """
    x, y = pyautogui.position()
    print(f"当前鼠标位置: ({x}, {y})")
    return (x, y)


def wait_for_image(image_path: str, timeout: float = 10.0, confidence: float = 0.9) -> tuple[int, int] | None:
    """等待图像出现在屏幕上
    
    Args:
        image_path: 要查找的图像路径
        timeout: 超时时间（秒）
        confidence: 匹配置信度
        
    Returns:
        图像中心坐标，如果超时则返回 None
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                print(f"找到图像: {image_path} 在 ({center.x}, {center.y})")
                return (center.x, center.y)
        except:
            pass
        time.sleep(0.5)
    
    print(f"等待图像超时: {image_path}")
    return None


def scroll(amount: int, x: int | None = None, y: int | None = None) -> None:
    """滚动鼠标滚轮
    
    Args:
        amount: 滚动量，正值向上，负值向下
        x: 滚动位置的 X 坐标（可选）
        y: 滚动位置的 Y 坐标（可选）
    """
    if x is not None and y is not None:
        pyautogui.scroll(amount, x, y)
        print(f"在 ({x}, {y}) 滚动 {amount}")
    else:
        pyautogui.scroll(amount)
        print(f"滚动 {amount}")


def main():
    parser = argparse.ArgumentParser(description="GUI 自动化控制工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # screenshot 命令
    screenshot_parser = subparsers.add_parser("screenshot", help="截取屏幕截图")
    screenshot_parser.add_argument("-o", "--output", help="输出路径")
    
    # click 命令
    click_parser = subparsers.add_parser("click", help="在指定位置点击")
    click_parser.add_argument("x", type=int, help="X 坐标")
    click_parser.add_argument("y", type=int, help="Y 坐标")
    click_parser.add_argument("-c", "--clicks", type=int, default=1, help="点击次数")
    click_parser.add_argument("-b", "--button", default="left", choices=["left", "right", "middle"], help="鼠标按钮")
    
    # click-on 命令
    click_on_parser = subparsers.add_parser("click-on", help="点击屏幕上的图像")
    click_on_parser.add_argument("image", help="图像路径")
    click_on_parser.add_argument("--confidence", type=float, default=0.9, help="匹配置信度")
    
    # type 命令
    type_parser = subparsers.add_parser("type", help="输入文本")
    type_parser.add_argument("text", help="要输入的文本")
    type_parser.add_argument("--interval", type=float, default=0.01, help="字符间隔")
    
    # key 命令
    key_parser = subparsers.add_parser("key", help="按下键盘按键")
    key_parser.add_argument("keys", help="按键名称，组合键用 + 连接")
    
    # move 命令
    move_parser = subparsers.add_parser("move", help="移动鼠标")
    move_parser.add_argument("x", type=int, help="X 坐标")
    move_parser.add_argument("y", type=int, help="Y 坐标")
    move_parser.add_argument("-d", "--duration", type=float, default=0.5, help="移动持续时间")
    
    # pos 命令
    pos_parser = subparsers.add_parser("pos", help="获取鼠标位置")
    
    # wait 命令
    wait_parser = subparsers.add_parser("wait", help="等待图像出现")
    wait_parser.add_argument("image", help="图像路径")
    wait_parser.add_argument("-t", "--timeout", type=float, default=10.0, help="超时时间")
    wait_parser.add_argument("--confidence", type=float, default=0.9, help="匹配置信度")
    
    # scroll 命令
    scroll_parser = subparsers.add_parser("scroll", help="滚动鼠标滚轮")
    scroll_parser.add_argument("amount", type=int, help="滚动量")
    scroll_parser.add_argument("-x", type=int, help="X 坐标")
    scroll_parser.add_argument("-y", type=int, help="Y 坐标")
    
    # demo 命令 - 演示自动化
    demo_parser = subparsers.add_parser("demo", help="运行演示脚本")
    
    args = parser.parse_args()
    
    if args.command == "screenshot":
        take_screenshot(args.output)
    elif args.command == "click":
        click_at(args.x, args.y, args.clicks, args.button)
    elif args.command == "click-on":
        click_on(args.image, args.confidence)
    elif args.command == "type":
        type_text(args.text, args.interval)
    elif args.command == "key":
        if "+" in args.keys:
            keys = args.keys.split("+")
            hotkey(*keys)
        else:
            press_key(args.keys)
    elif args.command == "move":
        move_to(args.x, args.y, args.duration)
    elif args.command == "pos":
        get_mouse_position()
    elif args.command == "wait":
        wait_for_image(args.image, args.timeout, args.confidence)
    elif args.command == "scroll":
        scroll(args.amount, args.x, args.y)
    elif args.command == "demo":
        run_demo()
    else:
        parser.print_help()


def run_demo():
    """运行演示脚本"""
    print("=== GUI 自动化演示 ===")
    print("3秒后开始...")
    time.sleep(3)
    
    # 获取鼠标位置
    print("\n1. 获取当前鼠标位置")
    get_mouse_position()
    
    # 移动鼠标
    print("\n2. 移动鼠标到屏幕中心")
    screen_width, screen_height = pyautogui.size()
    move_to(screen_width // 2, screen_height // 2)
    
    # 截图
    print("\n3. 截取屏幕")
    take_screenshot()
    
    print("\n演示完成！")


if __name__ == "__main__":
    main()
