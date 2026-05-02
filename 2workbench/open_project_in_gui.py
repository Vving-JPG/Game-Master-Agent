"""
通过 HTTP API 在 GUI 中打开 Agent 项目

用法:
    python open_project_in_gui.py [项目路径]
    
示例:
    python open_project_in_gui.py data/my_first_agent.agent
"""
from __future__ import annotations

import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:18080"


def _request(method: str, path: str, data: dict | None = None) -> dict:
    """发送 HTTP 请求"""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        try:
            return json.loads(error_body)
        except:
            return {"error": error_body, "status_code": e.code}
    except urllib.error.URLError as e:
        return {"error": f"连接失败: {e.reason}", "hint": "请先启动 GUI: cd 2workbench && python app.py"}


def open_project(project_path: str) -> bool:
    """通过 HTTP API 在 GUI 中打开项目"""
    print(f"正在打开项目: {project_path}")
    
    result = _request("POST", "/api/project/open", {"path": project_path})
    
    if "error" in result:
        print(f"❌ 错误: {result['error']}")
        if "hint" in result:
            print(f"提示: {result['hint']}")
        return False
    
    print(f"✅ {result.get('status', 'ok')}: {result.get('path', project_path)}")
    return True


def main():
    # 获取项目路径
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        # 默认路径
        project_path = "data/my_first_agent.agent"
    
    # 检查 GUI 是否运行
    status = _request("GET", "/api/status")
    if "error" in status:
        print("❌ 无法连接到 GUI")
        print("请先启动应用: cd 2workbench && python app.py")
        sys.exit(1)
    
    print(f"GUI 状态: {status.get('status', 'unknown')}")
    print(f"窗口: {status.get('window', 'unknown')}")
    print()
    
    # 打开项目
    if open_project(project_path):
        print("\n✅ 项目已在 IDE 中打开！")
        print("请查看 GUI 界面")
    else:
        print("\n❌ 打开项目失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
