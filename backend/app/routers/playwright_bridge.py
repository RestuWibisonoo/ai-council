from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.playwright_bridge import playwright_bridge

router = APIRouter(prefix="/api/playwright-bridge", tags=["Local Playwright Bridge"])


class OpenAndFillRequest(BaseModel):
    provider: Literal["chatgpt", "gemini", "claude", "notebooklm"]
    prompt: str = Field(min_length=1, max_length=100_000)


@router.get("/status")
async def bridge_status():
    return await playwright_bridge.status()


@router.post("/open-fill")
async def open_and_fill(payload: OpenAndFillRequest):
    try:
        return await playwright_bridge.open_and_fill(payload.provider, payload.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/close")
async def close_bridge():
    return await playwright_bridge.close()
