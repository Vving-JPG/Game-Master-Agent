# run.py - PyInstaller 打包入口
import os
import sys
import uvicorn


def resource_path(relative_path):
    """获取资源绝对路径（兼容普通运行和 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


if __name__ == "__main__":
    # 确保打包后能找到依赖模块
    sys.path.insert(0, resource_path("."))

    # 设置工作目录为 exe 所在目录（用于加载 .env 等）
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))

    print("=" * 50)
    print("WorldSim Master Agent 启动中...")
    print("=" * 50)
    print(f"资源路径: {resource_path('.')}")
    print(f"工作目录: {os.getcwd()}")
    print("-" * 50)

    # 运行 FastAPI 应用
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
