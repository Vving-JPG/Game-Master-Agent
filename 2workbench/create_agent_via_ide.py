"""
通过 IDE 的 HTTP API 创建 Agent 项目
"""
from __future__ import annotations

import urllib.request
import json

BASE_URL = "http://127.0.0.1:18080"


def create_project(name: str, template: str = "trpg", directory: str = "data") -> bool:
    """通过 HTTP API 创建项目"""
    print(f"正在创建 Agent 项目: {name} (模板: {template})")
    
    data = json.dumps({
        "name": name,
        "template": template,
        "directory": directory
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/project/create",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if "error" in result:
                print(f"❌ 错误: {result['error']}")
                return False
            print(f"✅ {result.get('status', 'ok')}: {result.get('name', name)}")
            return True
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def main():
    # 创建一个新的 Agent 项目
    project_name = "my_trpg_agent"
    
    print("=" * 60)
    print("🎮 通过 IDE 创建 Agent 项目")
    print("=" * 60)
    
    if create_project(project_name, template="trpg"):
        print("\n✅ Agent 项目创建成功！")
        print(f"项目将保存在: data/{project_name}.agent/")
    else:
        print("\n❌ 创建失败")


if __name__ == "__main__":
    main()
