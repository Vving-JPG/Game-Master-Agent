"""模型管理器 — 数据层

负责模型配置的加载、保存、增删改查。
与 UI 解耦，可被测试或复用。
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, asdict

from foundation.logger import get_logger

logger = get_logger(__name__)

CONFIG_FILE = Path("config.json")

# Provider 配置映射: keyword -> (key, display_name)
_PROVIDER_MAP: Dict[str, Tuple[str, str]] = {
    "deepseek": ("deepseek", "DeepSeek"),
    "gpt": ("openai", "OpenAI"),
    "openai": ("openai", "OpenAI"),
    "claude": ("anthropic", "Anthropic"),
    "anthropic": ("anthropic", "Anthropic"),
    "qwen": ("qwen", "Qwen"),
    "glm": ("glm", "GLM"),
}


def _infer_base_url(model_name: str) -> str:
    """根据模型名返回默认 API 地址"""
    mapping = {
        "deepseek": "https://api.deepseek.com",
        "glm": "https://open.bigmodel.cn/api/paas/v4",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    lower = model_name.lower()
    for key, url in mapping.items():
        if key in lower:
            return url
    return ""


def _get_provider_info(model_name: str) -> Tuple[str, str]:
    """根据模型名称获取 provider 信息
    
    Returns:
        Tuple[str, str]: (provider_key, display_name)
    """
    n = model_name.lower()
    for keyword, (key, name) in _PROVIDER_MAP.items():
        if keyword in n:
            return key, name
    return "custom", "自定义"


def _get_provider_name(provider_key: str) -> str:
    """从 provider key 获取显示名称"""
    for key, name in _PROVIDER_MAP.values():
        if key == provider_key:
            return name
    return "自定义"


@dataclass
class ModelConfig:
    """模型配置数据类"""
    id: str
    model: str
    api_key: str
    base_url: str = ""
    provider: str = ""
    enabled: bool = True
    
    def __post_init__(self):
        if not self.provider:
            _, self.provider = _get_provider_info(self.model)
        if not self.base_url:
            self.base_url = _infer_base_url(self.model)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ModelConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ModelManager:
    """模型管理器 — 负责数据持久化和 CRUD"""
    
    def __init__(self, project_path: Path | None = None):
        self._project_path = project_path
        self._models: List[ModelConfig] = []
        self._listeners: List[Callable] = []
        
    @property
    def project_path(self) -> Path | None:
        return self._project_path
        
    def set_project_path(self, path: Path | None) -> None:
        """设置项目路径并重新加载"""
        self._project_path = path
        self.load()
        
    def add_listener(self, callback: Callable) -> None:
        """添加数据变更监听器"""
        self._listeners.append(callback)
        
    def remove_listener(self, callback: Callable) -> None:
        """移除数据变更监听器"""
        if callback in self._listeners:
            self._listeners.remove(callback)
            
    def _notify(self) -> None:
        """通知所有监听器数据已变更"""
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                logger.error(f"通知监听器失败: {e}")
    
    def get_config_file(self) -> Path | None:
        """获取配置文件路径"""
        if not self._project_path:
            return None
        return Path(self._project_path) / CONFIG_FILE
    
    def load(self) -> None:
        """从配置文件加载模型列表"""
        self._models = []
        
        config_file = self.get_config_file()
        if not config_file or not config_file.exists():
            logger.debug("配置文件不存在，使用空列表")
            return
            
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
            providers: Dict[str, Any] = {}
            
            # 优先从新格式 providers 读取
            if "providers" in config and isinstance(config["providers"], dict):
                providers.update(config["providers"])
                
            # 兼容旧格式
            for key in ["deepseek", "openai", "anthropic", "qwen", "glm", "custom"]:
                if key in config and isinstance(config[key], dict):
                    providers[key] = config[key]
                    
            # 转换为模型列表
            for provider_key, provider_config in providers.items():
                if not isinstance(provider_config, dict):
                    continue
                model_name = provider_config.get("model", "")
                if not model_name:
                    continue
                    
                model_id = provider_config.get("id") or str(uuid.uuid4())
                self._models.append(ModelConfig(
                    id=model_id,
                    model=model_name,
                    api_key=provider_config.get("api_key", ""),
                    base_url=provider_config.get("base_url", ""),
                    provider=_get_provider_name(provider_key),
                    enabled=provider_config.get("enabled", True),
                ))
                
            logger.debug(f"加载了 {len(self._models)} 个模型")
            
        except FileNotFoundError:
            logger.debug("配置文件不存在")
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
        except Exception as e:
            logger.exception(f"加载配置失败: {e}")
    
    def save(self) -> bool:
        """保存模型列表到配置文件"""
        config_file = self.get_config_file()
        if not config_file:
            logger.warning("没有项目路径，无法保存")
            return False
            
        try:
            config: Dict[str, Any] = {}
            if config_file.exists():
                try:
                    config = json.loads(config_file.read_text(encoding="utf-8"))
                except Exception:
                    config = {}
                    
            # 更新 providers
            config["providers"] = {}
            
            for m in self._models:
                if not m.enabled:
                    continue
                provider_key, _ = _get_provider_info(m.model)
                
                config["providers"][provider_key] = {
                    "id": m.id,
                    "api_key": m.api_key,
                    "base_url": m.base_url,
                    "model": m.model,
                    "enabled": m.enabled,
                }
                
            # 原子写入
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_json = json.dumps(config, ensure_ascii=False, indent=2)
            temp_file = config_file.with_suffix('.tmp')
            
            try:
                temp_file.write_text(config_json, encoding="utf-8")
                temp_file.replace(config_file)
                logger.info(f"配置已保存到 {config_file}")
                self._notify()
                return True
            except Exception as e:
                logger.error(f"写入失败: {e}")
                if temp_file.exists():
                    temp_file.unlink()
                return False
                
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def get_models(self) -> List[ModelConfig]:
        """获取所有模型列表"""
        return self._models.copy()
    
    def get_enabled_models(self) -> List[ModelConfig]:
        """获取启用的模型列表"""
        return [m for m in self._models if m.enabled]
    
    def get_model_by_id(self, model_id: str) -> ModelConfig | None:
        """根据 ID 获取模型"""
        for m in self._models:
            if m.id == model_id:
                return m
        return None
    
    def add_model(self, model: str, api_key: str, base_url: str = "") -> ModelConfig:
        """添加新模型"""
        config = ModelConfig(
            id=str(uuid.uuid4()),
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        self._models.append(config)
        self.save()
        return config
    
    def update_model(self, model_id: str, **kwargs) -> bool:
        """更新模型配置"""
        for i, m in enumerate(self._models):
            if m.id == model_id:
                data = m.to_dict()
                data.update(kwargs)
                # 如果模型名变了，重新推断 provider
                if "model" in kwargs and kwargs["model"] != m.model:
                    _, data["provider"] = _get_provider_info(kwargs["model"])
                    data["base_url"] = _infer_base_url(kwargs["model"])
                self._models[i] = ModelConfig.from_dict(data)
                self.save()
                return True
        return False
    
    def delete_model(self, model_id: str) -> bool:
        """删除模型"""
        for i, m in enumerate(self._models):
            if m.id == model_id:
                self._models.pop(i)
                self.save()
                return True
        return False
