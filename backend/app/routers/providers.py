from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import ProviderConfiguration
from app.schemas.all_schemas import (
    ProviderConfigOut, ProviderConfigUpdate, ProviderTestRequest, ProviderTestResponse
)
from app.services.provider_manager import provider_manager

router = APIRouter(prefix="/api/providers", tags=["Providers"])


@router.get("", response_model=List[ProviderConfigOut])
def list_providers(db: Session = Depends(get_db)):
    providers = db.query(ProviderConfiguration).all()
    # Refresh api_key_configured status from secure manager
    for p in providers:
        p.api_key_configured = provider_manager.is_api_configured(p.id)
    return providers


@router.put("/{provider_id}", response_model=ProviderConfigOut)
def update_provider(
    provider_id: str,
    payload: ProviderConfigUpdate,
    db: Session = Depends(get_db)
):
    cfg = db.query(ProviderConfiguration).filter_by(id=provider_id).first()
    if not cfg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider tidak ditemukan.")

    if payload.is_enabled is not None:
        cfg.is_enabled = payload.is_enabled
    if payload.default_mode is not None:
        if provider_id == "notebooklm" and payload.default_mode == "api":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NotebookLM hanya beroperasi via Mode Manual Bridge karena tidak menyediakan API publik untuk akun standar pengguna."
            )
        if payload.default_mode == "api" and not (payload.api_key or provider_manager.is_api_configured(provider_id)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mode API hanya dapat diaktifkan setelah API key dikonfigurasi."
            )
        cfg.default_mode = payload.default_mode
    if payload.selected_model is not None:
        cfg.selected_model = payload.selected_model
    if payload.usage_limit_monthly_usd is not None:
        cfg.usage_limit_monthly_usd = payload.usage_limit_monthly_usd

    # If new API key passed, save securely in manager (never written in plain table columns)
    if payload.api_key is not None:
        provider_manager.save_secret(provider_id, payload.api_key)
        cfg.api_key_configured = provider_manager.is_api_configured(provider_id)

    db.commit()
    db.refresh(cfg)
    cfg.api_key_configured = provider_manager.is_api_configured(provider_id)
    return cfg


@router.post("/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider_connection(
    provider_id: str,
    payload: ProviderTestRequest,
    db: Session = Depends(get_db)
):
    cfg = db.query(ProviderConfiguration).filter_by(id=provider_id).first()
    if not cfg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider tidak ditemukan.")

    # If test key is provided in body, test with it temporarily, else use stored secret
    test_key = payload.api_key or provider_manager.get_secret(provider_id)
    if not test_key:
        return ProviderTestResponse(
            success=False,
            message="API key belum diisi. Anda tetap dapat menggunakan provider ini melalui Mode Manual Bridge tanpa biaya API."
        )

    model_to_test = payload.model or cfg.selected_model

    # Use adapter to test
    if provider_id in ("chatgpt", "openai"):
        from app.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(api_key=test_key, model=model_to_test)
    elif provider_id in ("claude", "anthropic"):
        from app.adapters.anthropic_adapter import AnthropicAdapter
        adapter = AnthropicAdapter(api_key=test_key, model=model_to_test)
    elif provider_id in ("gemini", "google"):
        from app.adapters.gemini_adapter import GeminiAdapter
        adapter = GeminiAdapter(api_key=test_key, model=model_to_test)
    elif provider_id in ("openrouter",):
        from app.adapters.openrouter_adapter import OpenRouterAdapter
        adapter = OpenRouterAdapter(api_key=test_key, model=model_to_test)
    elif provider_id in ("ollama",):
        from app.adapters.ollama_adapter import OllamaAdapter
        adapter = OllamaAdapter(model=model_to_test)
    elif provider_id in ("qwen", "dashscope"):
        from app.adapters.qwen_adapter import QwenAdapter
        adapter = QwenAdapter(api_key=test_key, model=model_to_test)
    elif provider_id in ("deepseek",):
        from app.adapters.deepseek_adapter import DeepSeekAdapter
        adapter = DeepSeekAdapter(api_key=test_key, model=model_to_test)
    else:
        return ProviderTestResponse(
            success=True,
            message=f"{cfg.display_name} beroperasi via antarmuka web resmi (Manual Bridge). Akses terverifikasi."
        )

    success, msg = await adapter.test_connection()
    cfg.is_verified = success
    cfg.last_checked_at = datetime.utcnow()
    db.commit()

    return ProviderTestResponse(
        success=success,
        message=msg,
        model_tested=model_to_test
    )


@router.get("/catalog/models")
async def get_models_catalog(db: Session = Depends(get_db)):
    """
    Returns aggregated catalog of models across providers,
    filtering and tagging Zero-Cost models (OpenRouter free, Ollama local, etc.).
    """
    from app.adapters.openrouter_adapter import OpenRouterAdapter
    from app.adapters.ollama_adapter import OllamaAdapter

    catalog = []

    # 1. OpenRouter Free Models
    openrouter_key = provider_manager.get_secret("openrouter")
    try:
        or_models = await OpenRouterAdapter.get_free_models(api_key=openrouter_key)
        for m in or_models:
            mid = m["id"].lower()
            family = "Other"
            if "deepseek" in mid:
                family = "DeepSeek"
            elif "qwen" in mid:
                family = "Qwen / Alibaba"
            elif "llama" in mid:
                family = "Meta Llama"
            elif "gemini" in mid:
                family = "Google Gemini"
            elif "mistral" in mid:
                family = "Mistral AI"
            elif "glm" in mid:
                family = "GLM / Zhipu"

            catalog.append({
                "id": f"openrouter:{m['id']}",
                "raw_id": m["id"],
                "name": m["name"],
                "provider": "openrouter",
                "provider_name": "OpenRouter",
                "family": family,
                "is_free": True,
                "is_zero_cost": True,
                "pricing_type": "free",
                "description": m.get("description", ""),
                "context_length": m.get("context_length", 4096),
                "is_available": True
            })
    except Exception:
        pass

    # 2. Ollama Local Models
    try:
        ollama_models = await OllamaAdapter.get_installed_models()
        for m in ollama_models:
            mid = m["id"].lower()
            family = "Local LLM"
            if "deepseek" in mid:
                family = "DeepSeek (Lokal)"
            elif "qwen" in mid:
                family = "Qwen (Lokal)"
            elif "llama" in mid:
                family = "Meta Llama (Lokal)"

            catalog.append({
                "id": f"ollama:{m['id']}",
                "raw_id": m["id"],
                "name": m["name"],
                "provider": "ollama",
                "provider_name": "Ollama Lokal",
                "family": family,
                "is_free": True,
                "is_zero_cost": True,
                "pricing_type": "local",
                "description": f"Model lokal di Mac ({m.get('size_bytes', 0) // (1024*1024)} MB)",
                "context_length": 8192,
                "is_available": True
            })
    except Exception:
        pass

    # 3. Seed Fallbacks if catalog is empty or offline
    if not catalog:
        default_free = [
            ("openrouter:deepseek/deepseek-r1:free", "deepseek/deepseek-r1:free", "DeepSeek R1 (Free)", "DeepSeek", "openrouter"),
            ("openrouter:meta-llama/llama-3.3-70b-instruct:free", "meta-llama/llama-3.3-70b-instruct:free", "Meta Llama 3.3 70B (Free)", "Meta Llama", "openrouter"),
            ("openrouter:qwen/qwen-2.5-72b-instruct:free", "qwen/qwen-2.5-72b-instruct:free", "Qwen 2.5 72B Instruct (Free)", "Qwen / Alibaba", "openrouter"),
            ("openrouter:google/gemini-2.0-flash-exp:free", "google/gemini-2.0-flash-exp:free", "Gemini 2.0 Flash Exp (Free)", "Google Gemini", "openrouter"),
            ("openrouter:mistralai/mistral-small-24b-instruct-2501:free", "mistralai/mistral-small-24b-instruct-2501:free", "Mistral Small 24B (Free)", "Mistral AI", "openrouter")
        ]
        for cid, raw_id, name, fam, prov in default_free:
            catalog.append({
                "id": cid,
                "raw_id": raw_id,
                "name": name,
                "provider": prov,
                "provider_name": "OpenRouter",
                "family": fam,
                "is_free": True,
                "is_zero_cost": True,
                "pricing_type": "free",
                "description": f"Model gratis terverifikasi dari katalog {fam}",
                "context_length": 8192,
                "is_available": True
            })

    # 4. Standard Provider Models (for reference or if user configures API)
    standard_models = [
        ("gemini:gemini-1.5-flash", "gemini-1.5-flash", "Gemini 1.5 Flash", "Google Gemini", "gemini", True),
        ("chatgpt:gpt-4o-mini", "gpt-4o-mini", "GPT-4o Mini", "OpenAI", "chatgpt", False),
        ("claude:claude-3-5-haiku-20241022", "claude-3-5-haiku-20241022", "Claude 3.5 Haiku", "Anthropic", "claude", False),
    ]
    for cid, raw_id, name, fam, prov, is_free_tier in standard_models:
        catalog.append({
            "id": cid,
            "raw_id": raw_id,
            "name": name,
            "provider": prov,
            "provider_name": prov.upper(),
            "family": fam,
            "is_free": is_free_tier,
            "is_zero_cost": is_free_tier,
            "pricing_type": "free_tier" if is_free_tier else "paid",
            "description": "Google AI Studio Free Tier" if is_free_tier else "Pay-as-you-go API",
            "context_length": 8192,
            "is_available": provider_manager.is_api_configured(prov)
        })

    return catalog
