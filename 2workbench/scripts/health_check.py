"""健康检查脚本"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import metrics_repo


def main():
    stats = metrics_repo.get_token_stats()
    print("=== Game Master Agent 健康检查 ===")
    print(f"总调用次数: {stats.get('total_calls', 0)}")
    print(f"总 Token: {stats.get('total_tokens', 0)}")
    print(f"平均延迟: {stats.get('avg_latency', 0):.0f}ms")
    print(f"错误次数: {stats.get('error_count', 0)}")
    print(f"状态: {'正常' if stats.get('error_count', 0) < 10 else '需要关注'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
