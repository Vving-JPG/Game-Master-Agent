"""安装依赖脚本 - 使用国内镜像源"""
import subprocess
import sys


# 国内镜像源
MIRRORS = {
    "清华": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "阿里云": "https://mirrors.aliyun.com/pypi/simple",
    "腾讯云": "https://mirrors.cloud.tencent.com/pypi/simple",
    "豆瓣": "https://pypi.douban.com/simple",
}

DEFAULT_MIRROR = "清华"


def install_with_uv():
    """使用 uv 安装依赖"""
    mirror_url = MIRRORS[DEFAULT_MIRROR]
    
    print(f"使用 {DEFAULT_MIRROR} 镜像源: {mirror_url}")
    print("=" * 50)
    
    # 安装 PyQt6 和其他依赖
    deps = [
        "PyQt6",
        "PyQt6-Qt6",
        "requests",
        "sseclient-py",
        "python-frontmatter",
        "pyyaml",
    ]
    
    for dep in deps:
        print(f"\n安装 {dep}...")
        cmd = [
            sys.executable, "-m", "uv", "pip", "install",
            "--index-url", mirror_url,
            dep
        ]
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"警告: {dep} 安装失败")
            
    print("\n" + "=" * 50)
    print("依赖安装完成！")


def install_with_pip():
    """使用 pip 安装依赖（备用）"""
    mirror_url = MIRRORS[DEFAULT_MIRROR]
    
    print(f"使用 {DEFAULT_MIRROR} 镜像源: {mirror_url}")
    print("=" * 50)
    
    requirements = [
        "PyQt6",
        "requests",
        "sseclient-py",
        "python-frontmatter",
        "pyyaml",
    ]
    
    cmd = [
        sys.executable, "-m", "pip", "install",
        "-i", mirror_url,
        "--trusted-host", mirror_url.replace("https://", "").split("/")[0],
    ] + requirements
    
    subprocess.run(cmd)


if __name__ == "__main__":
    print("Game Master Agent GUI 依赖安装")
    print("=" * 50)
    
    # 检测是否有 uv
    try:
        subprocess.run([sys.executable, "-m", "uv", "--version"], 
                      capture_output=True, check=True)
        print("检测到 uv，使用 uv 安装...\n")
        install_with_uv()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("未检测到 uv，使用 pip 安装...\n")
        install_with_pip()
