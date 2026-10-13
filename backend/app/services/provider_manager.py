import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.config import settings
from app.models.all_models import ProviderConfiguration, UsageRecord
from app.adapters.base import BaseAIAdapter, AdapterResult
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.openrouter_adapter import OpenRouterAdapter
from app.adapters.ollama_adapter import OllamaAdapter
from app.adapters.qwen_adapter import QwenAdapter
from app.adapters.deepseek_adapter import DeepSeekAdapter

SECRETS_FILE = settings.data_dir / "provider_secrets.json"


class ProviderManager:
    _instance = None
    _secrets_cache: Dict[str, str] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load_secrets()
        return cls._instance

    def _load_secrets(self):
        # 1. First check environment variables
        if settings.openai_api_key:
            self._secrets_cache["chatgpt"] = settings.openai_api_key
        if settings.anthropic_api_key:
            self._secrets_cache["claude"] = settings.anthropic_api_key
        if settings.gemini_api_key:
            self._secrets_cache["gemini"] = settings.gemini_api_key
        if settings.openrouter_api_key:
            self._secrets_cache["openrouter"] = settings.openrouter_api_key
        if settings.dashscope_api_key:
            self._secrets_cache["qwen"] = settings.dashscope_api_key
            self._secrets_cache["dashscope"] = settings.dashscope_api_key
        if settings.deepseek_api_key:
            self._secrets_cache["deepseek"] = settings.deepseek_api_key

        # 2. Check local secrets file
        if SECRETS_FILE.exists():
            try:
                with open(SECRETS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if v and not self._secrets_cache.get(k):
                            self._secrets_cache[k] = v
            except Exception:
                pass

    def save_secret(self, provider_id: str, api_key: str):
        if api_key:
            self._secrets_cache[provider_id] = api_key.strip()
        else:
            self._secrets_cache.pop(provider_id, None)

        # Write to local persistent file with restricted permissions
        try:
            with open(SECRETS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._secrets_cache, f)
            os.chmod(SECRETS_FILE, 0o600)
        except Exception:
            pass

    def get_secret(self, provider_id: str) -> Optional[str]:
        return self._secrets_cache.get(provider_id)

    def is_api_configured(self, provider_id: str) -> bool:
        pid = provider_id.lower()
        if pid == "ollama":
            # Ollama is local, does not require API key
            return True
        key = self.get_secret(provider_id)
        return bool(key and len(key.strip()) > 5)

    def get_adapter(
        self,
        provider_id: str,
        model: Optional[str] = None,
        zero_cost_mode: Optional[bool] = None
    ) -> Optional[BaseAIAdapter]:
        z_mode = settings.zero_cost_mode if zero_cost_mode is None else zero_cost_mode
        pid = provider_id.lower()
        key = self.get_secret(provider_id)

        # Handle prefixed identifiers e.g. "openrouter:deepseek/deepseek-r1:free"
        if ":" in pid and not pid.startswith("http"):
            parts = pid.split(":", 1)
            pid = parts[0]
            if not model:
                model = parts[1]

        if pid in ("openrouter",):
            return OpenRouterAdapter(
                api_key=key or self.get_secret("openrouter"),
                model=model,
                zero_cost_mode=z_mode
            )
        elif pid in ("ollama",):
            return OllamaAdapter(
                base_url=settings.ollama_base_url,
                model=model
            )
        elif pid in ("qwen", "dashscope"):
            return QwenAdapter(
                api_key=key or self.get_secret("qwen") or self.get_secret("dashscope"),
                model=model,
                zero_cost_mode=z_mode
            )
        elif pid in ("deepseek",):
            return DeepSeekAdapter(
                api_key=key or self.get_secret("deepseek"),
                model=model,
                zero_cost_mode=z_mode
            )
        elif pid in ("chatgpt", "openai"):
            return OpenAIAdapter(api_key=key, model=model)
        elif pid in ("claude", "anthropic"):
            return AnthropicAdapter(api_key=key, model=model)
        elif pid in ("gemini", "google"):
            return GeminiAdapter(api_key=key, model=model)

        return None

    @classmethod
    def seed_default_providers(cls, db: Session):
        defaults = [
            {
                "id": "openrouter",
                "display_name": "OpenRouter (Free Models)",
                "is_enabled": True,
                "default_mode": "api",
                "official_url": "https://openrouter.ai",
                "selected_model": "deepseek/deepseek-r1:free",
                "supported_models": [
                    "deepseek/deepseek-r1:free",
                    "meta-llama/llama-3.3-70b-instruct:free",
                    "qwen/qwen-2.5-72b-instruct:free",
                    "google/gemini-2.0-flash-exp:free",
                    "mistralai/mistral-small-24b-instruct-2501:free"
                ],
                "usage_limit_monthly_usd": 0.0
            },
            {
                "id": "ollama",
                "display_name": "Ollama (Model Lokal Mac)",
                "is_enabled": True,
                "default_mode": "api",
                "official_url": "https://ollama.com",
                "selected_model": "llama3.2",
                "supported_models": [
                    "llama3.2",
                    "qwen2.5:7b",
                    "deepseek-r1:8b",
                    "mistral:7b"
                ],
                "usage_limit_monthly_usd": 0.0
            },
            {
                "id": "qwen",
                "display_name": "Qwen / Alibaba Model Studio",
                "is_enabled": True,
                "default_mode": "manual",
                "official_url": "https://www.alibabacloud.com/help/en/model-studio",
                "selected_model": "qwen-turbo",
                "supported_models": [
                    "qwen-turbo",
                    "qwen-plus",
                    "qwen-max",
                    "qwen2.5-72b-instruct"
                ],
                "usage_limit_monthly_usd": 10.0
            },
            {
                "id": "deepseek",
                "display_name": "DeepSeek API Langsung",
                "is_enabled": True,
                "default_mode": "manual",
                "official_url": "https://platform.deepseek.com",
                "selected_model": "deepseek-chat",
                "supported_models": [
                    "deepseek-chat",
                    "deepseek-reasoner"
                ],
                "usage_limit_monthly_usd": 10.0
            },
            {
                "id": "chatgpt",
                "display_name": "ChatGPT",
                "is_enabled": True,
                "default_mode": "manual",
                "official_url": "https://chatgpt.com",
                "selected_model": "gpt-4o",
                "supported_models": ["gpt-4o", "gpt-4o-mini", "o3-mini"],
                "usage_limit_monthly_usd": 20.0
            },
            {
                "id": "claude",
                "display_name": "Claude",
                "is_enabled": True,
                "default_mode": "manual",
                "official_url": "https://claude.ai",
                "selected_model": "claude-3-7-sonnet-20250219",
                "supported_models": [
                    "claude-3-7-sonnet-20250219",
                    "claude-3-5-sonnet-20241022",
                    "claude-3-5-haiku-20241022"
                ],
                "usage_limit_monthly_usd": 20.0
            },
            {
                "id": "gemini",
                "display_name": "Gemini",
                "is_enabled": True,
                "default_mode": "manual",
                "official_url": "https://gemini.google.com",
                "selected_model": "gemini-2.5-flash",
                "supported_models": [
                    "gemini-2.5-flash",
                    "gemini-2.5-pro",
                    "gemini-1.5-flash"
                ],
                "usage_limit_monthly_usd": 20.0
            },
            {
                "id": "notebooklm",
                "display_name": "NotebookLM",
                "is_enabled": True,
                "default_mode": "manual",
                "official_url": "https://notebooklm.google.com",
                "selected_model": "NotebookLM Research Workspace",
                "supported_models": ["NotebookLM Research Workspace"],
                "usage_limit_monthly_usd": 0.0
            }
        ]

        manager = cls.get_instance()
        for item in defaults:
            existing = db.query(ProviderConfiguration).filter_by(id=item["id"]).first()
            if not existing:
                cfg = ProviderConfiguration(
                    id=item["id"],
                    display_name=item["display_name"],
                    is_enabled=item["is_enabled"],
                    default_mode=item["default_mode"],
                    official_url=item["official_url"],
                    selected_model=item["selected_model"],
                    supported_models=item["supported_models"],
                    usage_limit_monthly_usd=item["usage_limit_monthly_usd"],
                    api_key_configured=manager.is_api_configured(item["id"])
                )
                db.add(cfg)
            else:
                existing.api_key_configured = manager.is_api_configured(item["id"])
                # Ensure supported_models are updated if new defaults exist
                if set(item["supported_models"]) - set(existing.supported_models or []):
                    merged = list(dict.fromkeys((existing.supported_models or []) + item["supported_models"]))
                    existing.supported_models = merged
        db.commit()


provider_manager = ProviderManager.get_instance()
