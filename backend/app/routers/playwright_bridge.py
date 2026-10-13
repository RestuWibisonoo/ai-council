from ipaddress import ip_address
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.playwright_bridge import playwright_bridge

router = APIRouter(prefix="/api/playwright-bridge", tags=["Local Playwright Bridge"])


def require_loopback(request: Request) -> None:
    """Do not expose local browser control to LAN or public clients."""
    host = request.client.host if request.client else ""
    if host in ("testclient", "localhost", "127.0.0.1", "::1"):
        return
    try:
        if not ip_address(host).is_loopback:
            raise HTTPException(status_code=403, detail="Playwright Bridge hanya menerima koneksi lokal.")
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Playwright Bridge hanya menerima koneksi lokal.") from exc



class OpenAndFillRequest(BaseModel):
    provider: Literal["chatgpt", "gemini", "claude", "notebooklm"]
    prompt: str = Field(min_length=1, max_length=100_000)


@router.get("/status")
async def bridge_status(request: Request):
    require_loopback(request)
    return await playwright_bridge.status()


@router.post("/open-fill")
async def open_and_fill(payload: OpenAndFillRequest, request: Request):
    require_loopback(request)
    try:
        return await playwright_bridge.open_and_fill(payload.provider, payload.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/close")
async def close_bridge(request: Request):
    require_loopback(request)
    return await playwright_bridge.close()
