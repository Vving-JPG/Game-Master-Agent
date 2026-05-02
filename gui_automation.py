#!/usr/bin/env python3
"""GUI 自动化脚本 — 模拟人工操作创建 Agent 项目"""

import time
import subprocess
import sys

# 添加项目路径
sys.path.insert(0, '2workbench')

def find_window_by_title(title_substring):
    """通过标题查找窗口句柄"""
    import ctypes
    from ctypes import wintypes
    
    found_hwnd = None
    
    def enum_windows_callback(hwnd, extra):
        nonlocal found_hwnd
        if found_hwnd:
            return True
        
        # 检查窗口是否可见
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
            
        # 获取窗口标题
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
            window_title = buffer.value
            
            if title_substring.lower() in window_title.lower():
                found_hwnd = hwnd
                return False
        return True
    
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM
    )
    
    ctypes.windll.user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
    return found_hwnd


def click_menu_item(hwnd, menu_path):
    """点击菜单项
    
    Args:
        hwnd: 窗口句柄
        menu_path: 菜单路径，如 ["File", "New Agent Project"]
    """
    import ctypes
    from ctypes import wintypes
    
    # 获取菜单栏
    hMenu = ctypes.windll.user32.GetMenu(hwnd)
    if not hMenu:
        print("未找到菜单栏")
        return False
    
    # 获取菜单项数量
    menu_count = ctypes.windll.user32.GetMenuItemCount(hMenu)
    print(f"菜单栏有 {menu_count} 个顶级菜单")
    
    # 遍历查找匹配的菜单项
    for i in range(menu_count):
        # 获取菜单项信息
        class MENUITEMINFOW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("fMask", wintypes.UINT),
                ("fType", wintypes.UINT),
                ("fState", wintypes.UINT),
                ("wID", wintypes.UINT),
                ("hSubMenu", wintypes.HMENU),
                ("hbmpChecked", wintypes.HBITMAP),
                ("hbmpUnchecked", wintypes.HBITMAP),
                ("dwItemData", wintypes.LPVOID),
                ("dwTypeData", wintypes.LPWSTR),
                ("cch", wintypes.UINT),
                ("hbmpItem", wintypes.HBITMAP),
            ]
        
        # 先获取文本长度
        mii = MENUITEMINFOW()
        mii.cbSize = ctypes.sizeof(MENUITEMINFOW)
        mii.fMask = 0x00000040 | 0x00000010  # MIIM_STRING | MIIM_ID
        mii.dwTypeData = None
        mii.cch = 0
        
        result = ctypes.windll.user32.GetMenuItemInfoW(hMenu, i, True, ctypes.byref(mii))
        if result:
            # 分配缓冲区获取文本
            buffer = ctypes.create_unicode_buffer(mii.cch + 1)
            mii.dwTypeData = buffer
            mii.cch = mii.cch + 1
            
            result = ctypes.windll.user32.GetMenuItemInfoW(hMenu, i, True, ctypes.byref(mii))
            if result:
                menu_text = buffer.value
                print(f"  菜单项 {i}: {menu_text}")
    
    return True


def simulate_click(x, y):
    """模拟鼠标点击"""
    import ctypes
    
    # 移动鼠标
    ctypes.windll.user32.SetCursorPos(x, y)
    time.sleep(0.1)
    
    # 左键按下
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
    time.sleep(0.05)
    
    # 左键释放
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
    time.sleep(0.1)
    
    print(f"点击坐标: ({x}, {y})")


def get_window_rect(hwnd):
    """获取窗口位置和大小"""
    import ctypes
    from ctypes import wintypes
    
    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]
    
    rect = RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    
    return {
        "x": rect.left,
        "y": rect.top,
        "width": rect.right - rect.left,
        "height": rect.bottom - rect.top
    }


def main():
    print("=== GUI 自动化: 创建 Agent 项目 ===\n")
    
    # 1. 查找 Game Master Agent IDE 窗口
    print("1. 查找 IDE 窗口...")
    hwnd = find_window_by_title("Game Master Agent IDE")
    if not hwnd:
        print("错误: 未找到 IDE 窗口，请确保应用已启动")
        return 1
    
    print(f"   找到窗口句柄: {hwnd}")
    
    # 获取窗口位置
    rect = get_window_rect(hwnd)
    print(f"   窗口位置: ({rect['x']}, {rect['y']}) 大小: {rect['width']}x{rect['height']}")
    
    # 2. 点击 File 菜单
    print("\n2. 点击 File 菜单...")
    # File 菜单通常在左上角，坐标大约是窗口左上角 + (30, 30)
    file_menu_x = rect['x'] + 30
    file_menu_y = rect['y'] + 30
    simulate_click(file_menu_x, file_menu_y)
    
    time.sleep(0.5)
    
    # 3. 点击 New Agent Project
    print("\n3. 点击 New Agent Project...")
    # 菜单项通常在 File 下方
    new_project_x = file_menu_x
    new_project_y = file_menu_y + 30
    simulate_click(new_project_x, new_project_y)
    
    print("\n4. 等待对话框打开...")
    time.sleep(1)
    
    print("\n✓ 自动化操作完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
