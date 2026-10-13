import asyncio
import time
from typing import Optional, List, Dict, Any, Tuple
import httpx
from app.adapters.base import BaseAIAdapter, AdapterResult
from app.config import settings


class OpenRouterAdapter(BaseAIAdapter):
    DEFAULT_MODEL = "deepseek/deepseek-r1:free"
    BASE_URL = "https://openrouter.ai/api/v1"
    CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
    MODELS_URL = "https://openrouter.ai/api/v1/models"

    # In-memory cache for models catalog
    _models_cache: Optional[List[Dict[str, Any]]] = None
    _models_cache_time: float = 0.0
    CACHE_TTL_SECONDS: float = 600.0  # 10 minutes

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        zero_cost_mode: bool = True
    ):
        super().__init__(api_key=api_key, model=model)
        self.zero_cost_mode = zero_cost_mode

    def _sanitize_error(self, err_msg: str) -> str:
        if self.api_key and self.api_key in err_msg:
            return err_msg.replace(self.api_key, "[REDACTED_API_KEY]")
        return err_msg

    @classmethod
    async def get_models_catalog(cls, api_key: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch model catalog dynamically from OpenRouter API with caching."""
        now = time.time()
        if not force_refresh and cls._models_cache and (now - cls._models_cache_time < cls.CACHE_TTL_SECONDS):
            return cls._models_cache

        headers = {
            "HTTP-Referer": "https://github.com/RestuWibisonoo/ai-council",
            "X-Title": "AI Council",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(cls.MODELS_URL, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", [])
                    cls._models_cache = models
                    cls._models_cache_time = now
                    return models
        except Exception:
            pass

        # Return cached if available, else empty list
        return cls._models_cache or []

    @classmethod
    async def get_free_models(cls, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return only models with verified 0.0 input and output pricing."""
        all_models = await cls.get_models_catalog(api_key=api_key)
        free_models = []
        for m in all_models:
            pricing = m.get("pricing", {})
            try:
                p_prompt = float(pricing.get("prompt", 1.0))
                p_completion = float(pricing.get("completion", 1.0))
                p_request = float(pricing.get("request", 0.0))
                if p_prompt == 0.0 and p_completion == 0.0 and p_request == 0.0:
                    free_models.append({
                        "id": m.get("id"),
                        "name": m.get("name") or m.get("id"),
                        "description": m.get("description", ""),
                        "context_length": m.get("context_length", 4096),
                        "pricing": pricing,
                        "is_free": True,
                        "provider": "openrouter"
                    })
            except (ValueError, TypeError):
                continue

        # Sort free models putting DeepSeek, Qwen, and Llama first
        def model_priority(item):
            mid = item["id"].lower()
            if "deepseek" in mid:
                return 0
            if "qwen" in mid:
                return 1
            if "llama" in mid:
                return 2
            return 3

        free_models.sort(key=model_priority)
        return free_models

    async def verify_model_is_free(self, model_id: str) -> Tuple[bool, str]:
        """Strictly verify pricing metadata before sending request."""
        catalog = await self.get_models_catalog(api_key=self.api_key)
        if not catalog:
            # If catalog cannot be reached, fallback check: ID must contain :free or specific verified free IDs
            if ":free" in model_id.lower():
                return True, "Model memiliki tag :free resmi OpenRouter."
            return False, f"Katalog OpenRouter tidak dapat dimuat; status harga model '{model_id}' tidak dapat diverifikasi."

        matched = next((m for m in catalog if m.get("id") == model_id), None)
        if not matched:
            # Check if variant without/with :free
            alt_id = model_id if ":free" in model_id else f"{model_id}:free"
            matched = next((m for m in catalog if m.get("id") == alt_id), None)

        if not matched:
            return False, f"Model '{model_id}' tidak ditemukan di katalog resmi OpenRouter."

        pricing = matched.get("pricing", {})
        try:
            p_prompt = float(pricing.get("prompt", 1.0))
            p_completion = float(pricing.get("completion", 1.0))
            p_request = float(pricing.get("request", 0.0))
            if p_prompt == 0.0 and p_completion == 0.0 and p_request == 0.0:
                return True, "Harga input dan output terverifikasi 0 (Gratis)."
            return False, f"Model '{model_id}' adalah model berbayar (Prompt: ${p_prompt}, Completion: ${p_completion}). Ditolak dalam Zero-Cost Mode."
        except (ValueError, TypeError):
            return False, f"Metadata harga model '{model_id}' tidak valid atau tidak diketahui. Ditolak dalam Zero-Cost Mode."

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: float = 60.0
    ) -> AdapterResult:
        model_name = self.model or self.DEFAULT_MODEL

        if not self.api_key:
            return AdapterResult(
                content="",
                model_id=model_name,
                error="OpenRouter API key belum dikonfigurasi. Atur OPENROUTER_API_KEY di .env atau Pengaturan Provider."
            )

        # Zero-Cost Mode enforcement
        if self.zero_cost_mode:
            is_free, reason = await self.verify_model_is_free(model_name)
            if not is_free:
                return AdapterResult(
                    content="",
                    model_id=model_name,
                    error=f"Keamanan Biaya (Zero-Cost Mode): {reason}"
                )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/RestuWibisonoo/ai-council",
            "X-Title": "AI Council",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": settings.max_tokens_per_response
        }

        # Limited exponential backoff for temporary rate limits (429) or 503
        max_retries = 2
        last_error = ""

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(self.CHAT_URL, headers=headers, json=payload)

                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if not choices:
                            return AdapterResult(
                                content="",
                                model_id=model_name,
                                error="OpenRouter mengembalikan respons kosong (tidak ada choices)."
                            )

                        content = choices[0].get("message", {}).get("content", "")
                        usage = data.get("usage", {})
                        p_tokens = usage.get("prompt_tokens", 0)
                        c_tokens = usage.get("completion_tokens", 0)
                        t_tokens = usage.get("total_tokens", p_tokens + c_tokens)

                        return AdapterResult(
                            content=content,
                            prompt_tokens=p_tokens,
                            completion_tokens=c_tokens,
                            total_tokens=t_tokens,
                            estimated_cost_usd=0.0,  # Zero-cost verified
                            model_id=model_name,
                            is_actual_cost=True
                        )

                    elif resp.status_code == 429:
                        last_error = "OpenRouter Rate Limit (HTTP 429): Batas kuota gratis tercapai untuk saat ini."
                        if attempt < max_retries:
                            await asyncio.sleep(2.0 * (attempt + 1))
                            continue
                        return AdapterResult(
                            content="",
                            model_id=model_name,
                            error=last_error
                        )

                    elif resp.status_code in (401, 403):
                        return AdapterResult(
                            content="",
                            model_id=model_name,
                            error=f"OpenRouter Autentikasi Gagal (HTTP {resp.status_code}): Periksa OPENROUTER_API_KEY Anda."
                        )

                    elif resp.status_code == 404:
                        return AdapterResult(
                            content="",
                            model_id=model_name,
                            error=f"OpenRouter Model Tidak Ditemukan (HTTP 404): Model '{model_name}' tidak aktif."
                        )

                    else:
                        err_json = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
                        raw_msg = err_json.get("error", {}).get("message", resp.text)
                        msg = self._sanitize_error(str(raw_msg))
                        last_error = f"OpenRouter API Error ({resp.status_code}): {msg}"
                        if resp.status_code in (502, 503, 504) and attempt < max_retries:
                            await asyncio.sleep(1.5 * (attempt + 1))
                            continue
                        return AdapterResult(
                            content="",
                            model_id=model_name,
                            error=last_error
                        )

            except httpx.TimeoutException:
                last_error = f"OpenRouter timeout setelah {timeout} detik saat memanggil model '{model_name}'."
                if attempt < max_retries:
                    await asyncio.sleep(1.0)
                    continue
                return AdapterResult(
                    content="",
                    model_id=model_name,
                    error=last_error
                )
            except Exception as e:
                return AdapterResult(
                    content="",
                    model_id=model_name,
                    error=f"Koneksi ke OpenRouter gagal: {self._sanitize_error(str(e))}"
                )

        return AdapterResult(
            content="",
            model_id=model_name,
            error=last_error or "Gagal memanggil OpenRouter setelah retry."
        )

    async def test_connection(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "API key OpenRouter belum diisi."
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    self.MODELS_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    free_count = sum(
                        1 for m in models
                        if float(m.get("pricing", {}).get("prompt", 1.0)) == 0.0
                    )
                    return True, f"Koneksi ke OpenRouter API berhasil ({len(models)} model tersedia, {free_count} model gratis)."
                return False, f"OpenRouter mengembalikan kode {resp.status_code}."
        except Exception as e:
            return False, f"Gagal menghubungi server OpenRouter: {self._sanitize_error(str(e))}"
