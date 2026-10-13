from typing import Optional
import httpx
from app.adapters.base import BaseAIAdapter, AdapterResult


class AnthropicAdapter(BaseAIAdapter):
    DEFAULT_MODEL = "claude-3-7-sonnet-20250219"
    API_URL = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION = "2023-06-01"

    PRICING = {
        "claude-3-7-sonnet-20250219": {"input": 3.00, "output": 15.00},
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    }

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
        if not self.api_key:
            return AdapterResult(
                content="",
                model_id=self.model or self.DEFAULT_MODEL,
                error="Anthropic API key belum dikonfigurasi. Silakan atur API key di Pengaturan Provider atau gunakan Mode Manual Bridge."
            )

        model_name = self.model or self.DEFAULT_MODEL
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": "application/json"
        }
        payload = {
            "model": model_name,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(self.API_URL, headers=headers, json=payload)
                if resp.status_code != 200:
                    err_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    raw_msg = err_json.get("error", {}).get("message", resp.text)
                    msg = self._sanitize_error(str(raw_msg))
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error=f"Anthropic API Error ({resp.status_code}): {msg}"
                    )

                data = resp.json()
                content_blocks = data.get("content", [])
                text_content = "".join([b.get("text", "") for b in content_blocks if b.get("type") == "text"])
                usage = data.get("usage", {})
                p_tokens = usage.get("input_tokens", 0)
                c_tokens = usage.get("output_tokens", 0)
                t_tokens = p_tokens + c_tokens

                rates = self.PRICING.get(model_name, {"input": 3.00, "output": 15.00})
                cost = (p_tokens * rates["input"] + c_tokens * rates["output"]) / 1_000_000.0

                return AdapterResult(
                    content=text_content,
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    estimated_cost_usd=round(cost, 6),
                    model_id=model_name,
                    is_actual_cost=False
                )
        except Exception as e:
            return AdapterResult(
                content="",
                model_id=model_name,
                error=f"Koneksi ke Anthropic API gagal: {self._sanitize_error(str(e))}"
            )

    async def test_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "API key Anthropic belum diisi."
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": self.ANTHROPIC_VERSION,
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "max_tokens": 5,
                        "messages": [{"role": "user", "content": "ping"}]
                    }
                )
                if resp.status_code == 200:
                    return True, "Koneksi ke Anthropic API berhasil."
                return False, f"Anthropic mengembalikan kode {resp.status_code}"
        except Exception as e:
            return False, f"Gagal menghubungi server Anthropic: {self._sanitize_error(str(e))}"
