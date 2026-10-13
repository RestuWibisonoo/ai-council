from typing import Optional, Tuple
import httpx
from app.adapters.base import BaseAIAdapter, AdapterResult
from app.config import settings


class DeepSeekAdapter(BaseAIAdapter):
    DEFAULT_MODEL = "deepseek-chat"
    BASE_URL = "https://api.deepseek.com/v1"
    CHAT_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        zero_cost_mode: bool = True,
        allow_unverified_free: bool = False
    ):
        super().__init__(api_key=api_key, model=model)
        self.zero_cost_mode = zero_cost_mode
        self.allow_unverified_free = allow_unverified_free

    def _sanitize_error(self, err_msg: str) -> str:
        if self.api_key and self.api_key in err_msg:
            return err_msg.replace(self.api_key, "[REDACTED_API_KEY]")
        return err_msg

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
                error="DeepSeek API key belum dikonfigurasi. Atur DEEPSEEK_API_KEY di .env atau gunakan DeepSeek via OpenRouter Free."
            )

        # Enforce Zero-Cost Mode
        # DeepSeek direct API is a pay-as-you-go service by default (no permanent free tier guaranteed).
        if self.zero_cost_mode and not self.allow_unverified_free:
            return AdapterResult(
                content="",
                model_id=model_name,
                error=(
                    "Keamanan Biaya (Zero-Cost Mode): DeepSeek API langsung berbayar per-token secara default. "
                    "Gunakan model 'deepseek/deepseek-r1:free' melalui OpenRouter atau nonaktifkan Zero-Cost Mode jika Anda memiliki saldo promosi."
                )
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": settings.max_tokens_per_response
        }

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
                            error="DeepSeek API mengembalikan respons kosong."
                        )

                    raw_msg = choices[0].get("message", {}) or {}
                    content = raw_msg.get("content") or ""
                    usage = data.get("usage", {}) or {}
                    p_tokens = usage.get("prompt_tokens") or 0
                    c_tokens = usage.get("completion_tokens") or 0
                    t_tokens = usage.get("total_tokens") or (p_tokens + c_tokens)

                    return AdapterResult(
                        content=content,
                        prompt_tokens=p_tokens,
                        completion_tokens=c_tokens,
                        total_tokens=t_tokens,
                        estimated_cost_usd=0.0,
                        model_id=model_name,
                        is_actual_cost=False
                    )
                elif resp.status_code == 402:
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error="DeepSeek Saldo Habis (HTTP 402 Insufficient Balance)."
                    )
                elif resp.status_code == 429:
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error="DeepSeek Rate Limit tercapai (HTTP 429)."
                    )
                elif resp.status_code in (401, 403):
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error=f"DeepSeek Autentikasi Gagal (HTTP {resp.status_code}): API key salah."
                    )
                else:
                    err_json = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
                    raw_msg = err_json.get("error", {}).get("message", resp.text)
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error=f"DeepSeek API Error ({resp.status_code}): {self._sanitize_error(str(raw_msg))}"
                    )
        except httpx.TimeoutException:
            return AdapterResult(
                content="",
                model_id=model_name,
                error=f"DeepSeek API timeout setelah {timeout} detik."
            )
        except Exception as e:
            return AdapterResult(
                content="",
                model_id=model_name,
                error=f"Koneksi ke DeepSeek API gagal: {self._sanitize_error(str(e))}"
            )

    async def test_connection(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "API key DeepSeek belum diisi."
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.deepseek.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if resp.status_code == 200:
                    return True, "Koneksi ke DeepSeek API berhasil."
                return False, f"DeepSeek mengembalikan status HTTP {resp.status_code}."
        except Exception as e:
            return False, f"Gagal menguji koneksi DeepSeek: {self._sanitize_error(str(e))}"
