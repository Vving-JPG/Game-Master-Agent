"""
测试点击工具并查看右侧面板属性显示
"""
from __future__ import annotations

import urllib.request
import json

BASE_URL = "http://127.0.0.1:18080"


def click_tool(widget: str):
    """点击工具"""
    url = f"{BASE_URL}/api/click/{widget}"
    req = urllib.request.Request(url, method="GET")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # 点击第一个工具
    result = click_tool("run")
    print(f"点击结果: {result}")
