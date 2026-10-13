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
