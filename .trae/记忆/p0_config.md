# P0-02: Config 配置管理

> 模块: `foundation.config`
> 文件: `2workbench/foundation/config.py`
> 全局单例: `settings`

---

## 核心类

### Settings 类

```python
class Settings:
    # API 配置
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    
    default_provider: str  # "deepseek" | "openai"
    
    # 应用配置
    debug: bool
    log_level: str
    database_url: str

    def get_provider_config(self, provider: str | None = None) -> dict
    def get_available_providers(self) -> list[str]
```

---

## 环境变量映射

```env
# DeepSeek
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# 默认
DEFAULT_PROVIDER=deepseek

# 应用
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./game_master.db
```

---

## 使用示例

```python
from foundation.config import settings

# 获取默认供应商配置
config = settings.get_provider_config()  # 默认 deepseek

# 获取指定供应商配置
openai_config = settings.get_provider_config("openai")

# 获取已配置的供应商列表
available = settings.get_available_providers()  # ["deepseek", "openai"]

# 直接访问配置
api_key = settings.deepseek_api_key
```

---

## 多模型配置

支持同时配置多个 LLM 供应商，通过 `ModelRouter` 智能路由选择。
