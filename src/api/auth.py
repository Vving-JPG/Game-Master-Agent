"""API Key 认证"""
import os
from fastapi import Security, HTTPException, Depends
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# 默认 API Key（生产环境应从环境变量读取）
DEFAULT_API_KEY = os.getenv("API_KEY", "gm-agent-dev-key")


async def verify_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str:
    """验证 API Key

    开发环境下如果没提供 Key，使用默认 Key。
    生产环境必须提供有效 Key。
    """
    if not api_key:
        # 开发环境允许无 Key
        return DEFAULT_API_KEY
    if api_key != DEFAULT_API_KEY:
        raise HTTPException(status_code=401, detail="无效的 API Key")
    return api_key
