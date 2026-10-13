from typing import Optional
import httpx
from app.adapters.base import BaseAIAdapter, AdapterResult


class OpenAIAdapter(BaseAIAdapter):
    DEFAULT_MODEL = "gpt-4o"
    API_URL = "https://api.openai.com/v1/chat/completions"

    # Pricing per 1M tokens approx (USD)
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "o3-mini": {"input": 1.10, "output": 4.40},
    }

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
                error="OpenAI API key belum dikonfigurasi. Silakan atur API key di Pengaturan Provider atau gunakan Mode Manual Bridge."
            )

        model_name = self.model or self.DEFAULT_MODEL
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
            "temperature": 0.7
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(self.API_URL, headers=headers, json=payload)
                if resp.status_code != 200:
                    err_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    msg = err_json.get("error", {}).get("message", resp.text)
                    return AdapterResult(
                        content="",
                        model_id=model_name,
                        error=f"OpenAI API Error ({resp.status_code}): {msg}"
                    )

                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                p_tokens = usage.get("prompt_tokens", 0)
                c_tokens = usage.get("completion_tokens", 0)
                t_tokens = usage.get("total_tokens", p_tokens + c_tokens)

                # Cost estimate
                rates = self.PRICING.get(model_name, {"input": 2.50, "output": 10.00})
                cost = (p_tokens * rates["input"] + c_tokens * rates["output"]) / 1_000_000.0

                return AdapterResult(
                    content=content,
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
                error=f"Koneksi ke OpenAI API gagal: {str(e)}"
            )

    async def test_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "API key OpenAI belum diisi."
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if resp.status_code == 200:
                    return True, "Koneksi ke OpenAI API berhasil."
                return False, f"OpenAI mengembalikan kode {resp.status_code}"
        except Exception as e:
            return False, f"Gagal menghubungi server OpenAI: {str(e)}"
