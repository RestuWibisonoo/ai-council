from typing import Optional, Tuple
import httpx
from app.adapters.base import BaseAIAdapter, AdapterResult
from app.config import settings


class QwenAdapter(BaseAIAdapter):
    DEFAULT_MODEL = "qwen-turbo"
    DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        zero_cost_mode: bool = True
    ):
        super().__init__(api_key=api_key, model=model)
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.chat_url = f"{self.base_url}/chat/completions"
        self.zero_cost_mode = zero_cost_mode

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
                error="DashScope / Qwen API key belum dikonfigurasi. Atur DASHSCOPE_API_KEY di .env atau Pengaturan Provider."
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
                resp = await client.post(self.chat_url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        return AdapterResult(
                            content="",
                            model_id=model_name,
                            error="Qwen API mengembalikan respons kosong."
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
                        estimated_cost_usd=0.0,
                        model_id=model_name,
                        is_actual_cost=False
                    )
                elif resp.status_code == 429:
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error="Qwen / DashScope Rate Limit atau kuota promosi gratis habis (HTTP 429)."
                    )
                elif resp.status_code in (401, 403):
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error=f"Qwen Autentikasi Gagal (HTTP {resp.status_code}): API key salah atau tidak aktif."
                    )
                else:
                    err_json = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
                    raw_msg = err_json.get("error", {}).get("message", resp.text)
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error=f"Qwen API Error ({resp.status_code}): {self._sanitize_error(str(raw_msg))}"
                    )
        except httpx.TimeoutException:
            return AdapterResult(
                content="",
                model_id=model_name,
                error=f"Qwen API timeout setelah {timeout} detik."
            )
        except Exception as e:
            return AdapterResult(
                content="",
                model_id=model_name,
                error=f"Koneksi ke Qwen API gagal: {self._sanitize_error(str(e))}"
            )

    async def test_connection(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "API key DashScope belum diisi."
        try:
            # Send minimal test completion
            res = await self.complete(prompt="Halo, tes koneksi 1 kata.", timeout=15.0)
            if res.error:
                return False, f"Tes Qwen gagal: {res.error}"
            return True, f"Koneksi ke Alibaba Cloud Model Studio (Qwen) berhasil menggunakan model '{self.model or self.DEFAULT_MODEL}'."
        except Exception as e:
            return False, f"Gagal menguji koneksi Qwen: {self._sanitize_error(str(e))}"
