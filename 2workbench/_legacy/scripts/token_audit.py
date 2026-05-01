"""Token 使用审计脚本"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.context_manager import estimate_tokens
from src.prompts.gm_system import get_system_prompt
from src.tools.executor import get_all_schemas


def main():
    print("=== Token 使用审计 ===\n")

    # System Prompt Token 数
    prompt = get_system_prompt()
    prompt_tokens = estimate_tokens(prompt)
    print(f"System Prompt: {len(prompt)} 字符, 约 {prompt_tokens} tokens")

    # 工具 Schema 的 Token 数
    schemas = get_all_schemas()
    schema_text = str(schemas)
    schema_tokens = estimate_tokens(schema_text)
    print(f"工具 Schemas ({len(schemas)}个): {len(schema_text)} 字符, 约 {schema_tokens} tokens")

    print(f"\n固定开销: 约 {prompt_tokens + schema_tokens} tokens")
    print(f"剩余可用: 约 {128000 - prompt_tokens - schema_tokens} tokens")

    # 每条消息平均占用
    print(f"\n估算每条消息占用: 约 200 tokens")
    print(f"可支持的消息数: 约 {(128000 - prompt_tokens - schema_tokens) // 200} 条")


if __name__ == "__main__":
    main()
